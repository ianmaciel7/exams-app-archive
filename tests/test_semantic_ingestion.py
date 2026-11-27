#!/usr/bin/env python3
"""Unit tests for multimodal semantic ingestion audit and traceability graph (#82)."""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import semantic_ingestion_audit as sia  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class SemanticIngestionAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = sia.run_audit()

    def test_lifecycle_states_and_modalities_covered(self) -> None:
        summary = self.audit["summary"]
        self.assertGreater(summary["files_included"], 200)
        self.assertGreater(summary["files_excluded"], 0)
        self.assertGreater(summary["knowledge_units_total"], 1000)

        self.assertEqual(sum(summary["by_modality_units"].values()), summary["knowledge_units_total"])
        self.assertEqual(summary["local_file_units"] + summary["visual_manifest_units"], summary["knowledge_units_total"])
        self.assertEqual(summary["visual_manifest_units"], self.audit["visual_media_audit"]["total_visual_records"])

        # All 4 modalities must have files & extracted knowledge units
        for mod in sia.MODALITIES:
            self.assertGreater(summary["by_modality_files"].get(mod, 0), 0, f"Missing files for {mod}")
            self.assertGreater(summary["by_modality_units"].get(mod, 0), 0, f"Missing units for {mod}")

        # Lifecycle vocabulary matches specification
        self.assertEqual(
            self.audit["lifecycle_vocabulary"],
            ["located", "retrieved", "extracted", "indexed", "queryable", "verified", "partial", "unavailable"],
        )
        # Ensure authenticated unavailable sources are explicitly tracked as unavailable publicly
        self.assertGreater(summary["by_lifecycle_state"].get("unavailable", 0), 0)
        self.assertGreater(summary["by_local_file_lifecycle_state"].get("extracted", 0), 0)
        # Extraction and file hashes are not proof of operational index membership.
        self.assertEqual(summary["index_coverage_status"], "NOT_MEASURED")
        self.assertIsNone(summary["index_coverage_percent"])
        local = summary["by_local_file_lifecycle_state"]
        remote = summary["by_remote_source_lifecycle_state"]
        for state in ("indexed", "queryable", "verified"):
            self.assertEqual(local.get(state, 0), 0)
        self.assertEqual(sum(local.values()), summary["local_eligible_occurrences"])
        self.assertEqual(sum(local.values()) - local.get("unavailable", 0), summary["files_included"])
        self.assertEqual(sum(remote.values()), sum(s["adapter"] != "local_fs" for s in self.audit["sources"]))
        for state in sia.LIFECYCLE_STATES:
            self.assertEqual(summary["by_lifecycle_state"].get(state, 0),
                             local.get(state, 0) + remote.get(state, 0))

    def test_visual_media_distinguishes_verified_vs_inferred(self) -> None:
        vis = self.audit["visual_media_audit"]
        self.assertGreater(vis["total_visual_records"], 30)
        self.assertGreater(vis["verified_blobs"], 0)
        self.assertGreater(vis["link_only"], 0)
        self.assertGreater(vis["sampled_frames_reviewed"], 0)
        self.assertGreater(vis["uninspected_media"], 0)

        gap_types = {g["gap_type"] for g in self.audit["backlog_gaps"]}
        self.assertIn("visual_semantic_inspection_incomplete", gap_types)
        self.assertIn("authorization_or_bundle_restore_required", gap_types)

    def test_traceability_graph_and_bundle_recovery(self) -> None:
        tg = self.audit["traceability_graph"]
        self.assertGreater(tg["nodes_count"], 100)
        self.assertGreater(tg["edges_count"], 100)
        for required_type in ("requirement", "decision_or_doc", "implementation", "test", "visual_evidence", "version"):
            self.assertGreater(tg["node_types"].get(required_type, 0), 0, f"Missing node type: {required_type}")

        recovery = self.audit["bundle_recovery_verification"]
        self.assertGreaterEqual(len(recovery), 5)
        self.assertTrue(all(r["operational_index_separated"] for r in recovery))
        self.assertTrue(all(r["manifest_present"] for r in recovery))

    def test_report_generation_and_zero_emoji(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            jpath = Path(td) / "audit.json"
            mpath = Path(td) / "audit.md"
            sia.write_reports(self.audit, json_path=jpath, md_path=mpath)

            loaded = json.loads(jpath.read_text(encoding="utf-8"))
            md_txt = mpath.read_text(encoding="utf-8")
            self.assertEqual(loaded["summary"]["files_included"], self.audit["summary"]["files_included"])
            self.assertIn("# Semantic Ingestion & Source Coverage Audit (#82)", md_txt)
            self.assertIn("Index coverage: **NOT MEASURED**", md_txt)
            self.assertIn("Local file occurrences | Remote sources", md_txt)
            self.assertFalse(EMOJI_REGEX.search(md_txt))
            self.assertFalse(EMOJI_REGEX.search(jpath.read_text(encoding="utf-8")))

        script_txt = (SCRIPTS_DIR / "semantic_ingestion_audit.py").read_text(encoding="utf-8")
        self.assertFalse(EMOJI_REGEX.search(script_txt))


if __name__ == "__main__":
    unittest.main()
