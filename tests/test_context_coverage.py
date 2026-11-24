#!/usr/bin/env python3
"""End-to-end tests for scripts/context_coverage.py and reports/MULTI-STEP-SEARCH-COVERAGE.md (Issue #29)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import context_coverage  # noqa: E402
import context_linker  # noqa: E402
import graph_linker  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class ContextCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp_path = Path(cls._tmp.name)

        cls.docs, cls.code_blobs = context_coverage.build_multirepo_coverage_corpus()
        cls.arch_conn = context_coverage.populate_archive_corpus_db(
            cls.tmp_path / "arch.sqlite", cls.docs
        )

        cls.graph_conn = graph_linker.open_db(cls.tmp_path / "graph.sqlite")
        graph_linker.ingest_branch_inventory(
            cls.graph_conn,
            ROOT / "inventory" / "exams-app-branch-files.json",
            repo_override="exams-app",
        )
        graph_linker.ingest_notes_platform_inventory(
            cls.graph_conn,
            ROOT / "inventory" / "notes-app",
            repo_name="notes-app",
        )
        graph_linker.link_temporal_supersession(cls.graph_conn)

        cls.ctx_conn = context_linker.open_db(cls.tmp_path / "ctx.sqlite")
        context_linker.import_inventory(ROOT / "inventory", cls.ctx_conn)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.ctx_conn.close()
        cls.graph_conn.close()
        cls.arch_conn.close()
        cls._tmp.cleanup()

    def test_enumerates_all_9_repos_and_mandatory_sidebar_branches(self) -> None:
        catalog = context_coverage.load_source_catalog(
            ROOT / "inventory" / "source-refs-2026-11-23.json",
            archive_conn=self.arch_conn,
            graph_conn=self.graph_conn,
            context_conn=self.ctx_conn,
        )
        self.assertEqual(catalog["total_repositories"], 9)
        repo_names = {r["name"] for r in catalog["repositories"]}
        self.assertEqual(
            repo_names,
            {
                "fcc-responsive-web-design",
                "ianmaciel7",
                "notes-app",
                "shadcn-template",
                "shadcn-firebase-template",
                "exams-app-old",
                "exams-app-antigo-2",
                "exams-app",
                "exams-app-archive",
            },
        )
        candidate_ids = {c["source_id"] for c in catalog["candidate_sources"]}
        for mandatory in context_coverage.MANDATORY_SIDEBAR_REGRESSION_SOURCES:
            self.assertIn(mandatory, candidate_ids)

    def test_end_to_end_sidebar_query_hits_all_5_stages_and_100_percent_coverage(self) -> None:
        res = context_coverage.run_multi_step_search(
            "todas as caracteristicas das sidebars",
            archive_conn=self.arch_conn,
            graph_conn=self.graph_conn,
            context_conn=self.ctx_conn,
            code_blobs=self.code_blobs,
            source_refs_path=ROOT / "inventory" / "source-refs-2026-11-23.json",
        )
        self.assertTrue(res["intent"]["exhaustive_required"])
        self.assertEqual(res["intent"]["focus_query"], "sidebar")
        self.assertEqual(res["source_inventory"]["total_repositories_in_archive"], 9)
        self.assertEqual(res["coverage_metrics"]["coverage_at_source"], 1.0)
        self.assertEqual(res["coverage_metrics"]["candidate_branch_coverage"], 1.0)
        self.assertTrue(res["coverage_metrics"]["inventory_complete_claim_allowed"])
        self.assertFalse(res["coverage_metrics"]["partial"])

        # Mandatory regression set from issue #29
        reg = res["coverage_metrics"]["mandatory_regression_sources"]
        for src in context_coverage.MANDATORY_SIDEBAR_REGRESSION_SOURCES:
            self.assertEqual(reg[src], "verified_with_evidence", f"Missing regression evidence for {src}")

        # Verify all 5 stages produced structured output
        self.assertGreater(res["stages"]["fts5_bm25"]["hits_count"], 10)
        self.assertGreater(res["stages"]["graph_linker"]["total_nodes"], 20)
        self.assertGreater(res["stages"]["graph_linker"]["decisions_count"], 0)
        self.assertGreater(res["stages"]["ast_chunker"]["chunks_matched"], 0)
        self.assertGreater(res["stages"]["ast_chunker"]["motion_contracts_count"], 0)
        self.assertGreater(res["stages"]["context_linker"]["files_count"], 0)

        # Static images must never claim to prove animation timing
        self.assertTrue(res["visual_elements_index"])
        for img in res["visual_elements_index"]:
            self.assertEqual(img["inspection_level"], "cataloged_metadata_only")
            self.assertFalse(img["proves_animation_timing"])

    def test_end_to_end_variants_grafo_hover_peek_drag_tooltip_drawer(self) -> None:
        for query in ("grafo", "hover peek", "drag-and-drop", "tooltip", "drawer mobile"):
            res = context_coverage.run_multi_step_search(
                query,
                archive_conn=self.arch_conn,
                graph_conn=self.graph_conn,
                context_conn=self.ctx_conn,
                code_blobs=self.code_blobs,
                source_refs_path=ROOT / "inventory" / "source-refs-2026-11-23.json",
            )
            self.assertEqual(res["coverage_metrics"]["coverage_at_source"], 1.0, query)
            self.assertTrue(res["coverage_metrics"]["inventory_complete_claim_allowed"], query)
            self.assertGreater(res["stages"]["fts5_bm25"]["hits_count"], 0, query)
            self.assertGreater(res["stages"]["graph_linker"]["total_nodes"], 0, query)
            self.assertGreater(res["stages"]["context_linker"]["files_count"], 0, query)

    def test_partial_degradation_when_source_unavailable_or_timeout(self) -> None:
        res_unavail = context_coverage.run_multi_step_search(
            "todas as caracteristicas das sidebars",
            archive_conn=self.arch_conn,
            graph_conn=self.graph_conn,
            context_conn=self.ctx_conn,
            code_blobs=self.code_blobs,
            source_refs_path=ROOT / "inventory" / "source-refs-2026-11-23.json",
            simulate_unavailable_repos={"notes-app"},
        )
        self.assertTrue(res_unavail["coverage_metrics"]["partial"])
        self.assertLess(res_unavail["coverage_metrics"]["coverage_at_source"], 1.0)
        self.assertFalse(res_unavail["coverage_metrics"]["inventory_complete_claim_allowed"])
        self.assertIn("notes-app", res_unavail["source_inventory"]["missing_repositories"])

        res_timeout = context_coverage.run_multi_step_search(
            "todas as caracteristicas das sidebars",
            archive_conn=self.arch_conn,
            graph_conn=self.graph_conn,
            context_conn=self.ctx_conn,
            code_blobs=self.code_blobs,
            source_refs_path=ROOT / "inventory" / "source-refs-2026-11-23.json",
            timeout_seconds=0.0,
        )
        self.assertTrue(res_timeout["coverage_metrics"]["partial"])
        self.assertFalse(res_timeout["coverage_metrics"]["inventory_complete_claim_allowed"])
        self.assertLess(res_timeout["coverage_metrics"]["coverage_at_source"], 1.0)

    def test_privacy_rejects_site_output_and_benchmark_cli_works(self) -> None:
        with self.assertRaises(ValueError):
            context_coverage.validate_private_output_path(ROOT / "site" / "leak.json")

        out_json = self.tmp_path / "bench-coverage.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "context_coverage.py"),
                "benchmark",
                "--output",
                str(out_json),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        parsed = json.loads(proc.stdout)
        self.assertTrue(out_json.is_file())
        self.assertFalse(parsed["integrated_baseline"]["external_embedding_server_required"])
        self.assertEqual(parsed["integrated_baseline"]["mean_coverage_at_source"], 1.0)
        comp = parsed["comparative_evaluation_on_sidebar_query"]
        self.assertEqual(comp["integrated_orchestrator"]["coverage_at_source"], 1.0)
        self.assertLess(comp["xerj_bm25_proxy"]["coverage_at_source"], 1.0)
        self.assertLess(comp["grepai_semantic_proxy"]["coverage_at_source"], 1.0)

    def test_report_and_zero_emoji_policy(self) -> None:
        report_path = ROOT / "reports" / "MULTI-STEP-SEARCH-COVERAGE.md"
        self.assertTrue(report_path.is_file())
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("todas as caracteristicas das sidebars", report_text)
        self.assertIn("grafo", report_text)
        self.assertIn("grepai", report_text)
        self.assertIn("XERJ", report_text)
        self.assertIn("coverage@source", report_text)

        for target in (
            SCRIPTS_DIR / "context_coverage.py",
            report_path,
            Path(__file__),
        ):
            content = target.read_text(encoding="utf-8")
            self.assertEqual(EMOJI_REGEX.findall(content), [], f"Disallowed emoji in {target}")


if __name__ == "__main__":
    unittest.main()
