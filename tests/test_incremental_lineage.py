#!/usr/bin/env python3
"""Unit tests for incremental lineage DAG, memoization, selective invalidation, and rollback (#87)."""
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

import incremental_lineage as il  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class IncrementalLineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "lineage.sqlite"
        self.conn = il.open_lineage_db(self.db_path)
        self.engine = il.IncrementalLineageEngine(self.conn)
        self.sources = [
            il.SourceInput(
                source_id="repo.exams-app",
                path="src/Sidebar.tsx",
                content="export function Sidebar() { return <nav>sidebar</nav>; }\n",
                scope="public",
            ),
            il.SourceInput(
                source_id="repo.exams-app",
                path="src/Tabs.tsx",
                content="export function Tabs() { return <div>tabs</div>; }\n",
                scope="public",
            ),
        ]

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_memoization_idempotence_and_equivalence(self) -> None:
        cfg = il.PipelineConfig()
        r1 = self.engine.refresh(self.sources, cfg, scope="public", incremental=True)
        self.assertEqual(r1["status"], "committed")
        self.assertEqual(r1["computed_calls"], 8)  # 2 files * 4 derived stages
        self.assertEqual(r1["memo_hits"], 0)
        self.assertEqual(r1["dag_nodes"], 10)  # 2 files * 5 stages (including source)
        self.assertEqual(r1["dag_edges"], 8)

        # Second identical run must have 0 computed calls and 100% memo hits
        r2 = self.engine.refresh(self.sources, cfg, scope="public", incremental=True)
        self.assertEqual(r2["computed_calls"], 0)
        self.assertEqual(r2["memo_hits"], 8)
        self.assertEqual(r2["state_hash"], r1["state_hash"])

        # Compare against independent full rebuild
        full_conn = il.open_lineage_db(":memory:")
        full_engine = il.IncrementalLineageEngine(full_conn)
        rf = full_engine.refresh(self.sources, cfg, scope="public", incremental=False)
        self.assertEqual(r2["state_hash"], rf["state_hash"])
        full_conn.close()

    def test_selective_invalidation_on_taxonomy_and_extractor_change(self) -> None:
        cfg = il.PipelineConfig()
        self.engine.refresh(self.sources, cfg, scope="public", incremental=True)

        # Taxonomy change must NOT recompute extraction or chunk stages
        tax_cfg = il.PipelineConfig(
            taxonomy_version="2.0.0",
            taxonomy_terms=cfg.taxonomy_terms + ("navigation",),
        )
        r_tax = self.engine.refresh(self.sources, tax_cfg, scope="public", incremental=True)
        self.assertEqual(r_tax["stage_memo_hits"]["extraction"], 2)
        self.assertEqual(r_tax["stage_memo_hits"]["chunk"], 2)
        self.assertEqual(r_tax["stage_computed"]["extraction"], 0)
        self.assertEqual(r_tax["stage_computed"]["chunk"], 0)
        self.assertEqual(r_tax["stage_computed"]["entity_edge"], 2)
        self.assertEqual(r_tax["stage_computed"]["index_context"], 2)

        # Extractor version bump on `chunk` invalidates chunk + downstream (entity_edge, index_context)
        # while still hitting memo cache on `extraction`
        chk_cfg = il.PipelineConfig(
            extractor_versions={
                "extract": "1.0.0",
                "chunk": "2.0.0",
                "entity_edge": "1.0.0",
                "index_context": "1.0.0",
            },
            taxonomy_version=tax_cfg.taxonomy_version,
            taxonomy_terms=tax_cfg.taxonomy_terms,
        )
        r_chk = self.engine.refresh(self.sources, chk_cfg, scope="public", incremental=True)
        self.assertEqual(r_chk["stage_memo_hits"]["extraction"], 2)
        self.assertEqual(r_chk["stage_computed"]["extraction"], 0)
        self.assertEqual(r_chk["stage_computed"]["chunk"], 2)
        self.assertEqual(r_chk["stage_computed"]["entity_edge"], 2)
        self.assertEqual(r_chk["stage_computed"]["index_context"], 2)

    def test_identical_bytes_keep_occurrence_and_language_provenance(self) -> None:
        content = "export const X = 1;\n"
        sources = [
            il.SourceInput("repo.a", "src/A.ts", content),
            il.SourceInput("repo.a", "src/B.md", content),
            il.SourceInput("repo.b", "src/A.ts", content, language="text"),
        ]
        first = self.engine.refresh(sources, scope="public")
        self.assertEqual(first["status"], "committed")
        rows = self.conn.execute(
            "SELECT source_id, source_path, payload_json FROM lineage_nodes "
            "WHERE scope='public' AND stage='extraction'"
        ).fetchall()
        extracted = {(sid, path): json.loads(payload) for sid, path, payload in rows}
        self.assertEqual(len(extracted), 3)
        for src in sources:
            payload = extracted[(src.source_id, src.path)]
            self.assertEqual(payload["source_id"], src.source_id)
            self.assertEqual(payload["path"], src.path)
        self.assertEqual(extracted[("repo.a", "src/A.ts")]["language"], "typescript")
        self.assertEqual(extracted[("repo.a", "src/B.md")]["language"], "text")
        self.assertEqual(extracted[("repo.b", "src/A.ts")]["language"], "text")
        chunks = self.conn.execute(
            "SELECT payload_json FROM lineage_nodes WHERE source_id='repo.a' "
            "AND source_path='src/B.md' AND stage='chunk'"
        ).fetchone()
        self.assertEqual(json.loads(chunks[0])["chunks"][0]["name"], "B.md")
        second = self.engine.refresh(sources, scope="public")
        self.assertEqual(second["memo_hits"], 12)
        self.assertEqual(second["state_hash"], first["state_hash"])
        full = self.engine.refresh(sources, scope="public", incremental=False)
        self.assertEqual(full["state_hash"], first["state_hash"])

    def test_language_override_change_invalidates_extraction(self) -> None:
        src = il.SourceInput("repo.a", "src/A.ts", "export const X = 1;")
        self.engine.refresh([src], scope="public")
        changed = il.SourceInput(src.source_id, src.path, src.content, language="text")
        result = self.engine.refresh([changed], scope="public")
        self.assertEqual(result["stage_computed"]["extraction"], 1)
        row = self.conn.execute(
            "SELECT payload_json FROM lineage_nodes WHERE stage='extraction'"
        ).fetchone()
        self.assertEqual(json.loads(row[0])["language"], "text")
        full = self.engine.refresh([changed], scope="public", incremental=False)
        self.assertEqual(result["state_hash"], full["state_hash"])

    def test_scope_isolation_prevents_cross_acl_cache_reuse(self) -> None:
        cfg = il.PipelineConfig()
        private_sources = [
            il.SourceInput(
                source_id="bundle.notes-app",
                path="src/Sidebar.tsx",
                content=self.sources[0].content,  # identical content SHA!
                scope="authenticated_archive",
            )
        ]
        r_priv = self.engine.refresh(private_sources, cfg, scope="authenticated_archive", incremental=True)
        self.assertEqual(r_priv["computed_calls"], 4)

        # Public run with identical file bytes MUST NOT reuse authenticated_archive memo cache
        r_pub = self.engine.refresh([self.sources[0]], cfg, scope="public", incremental=True)
        self.assertEqual(r_pub["memo_hits"], 0)
        self.assertEqual(r_pub["computed_calls"], 4)

    def test_unavailability_vs_removal_and_historical_preservation(self) -> None:
        cfg = il.PipelineConfig()
        self.engine.refresh(self.sources, cfg, scope="public", incremental=True)

        # Mark Tabs.tsx temporarily unavailable -> preserved as temporarily_unavailable
        temp_sources = [
            self.sources[0],
            il.SourceInput(
                source_id="repo.exams-app",
                path="src/Tabs.tsx",
                content="",
                scope="public",
                availability="temporarily_unavailable",
            ),
        ]
        r_temp = self.engine.refresh(temp_sources, cfg, scope="public", incremental=True)
        self.assertEqual(r_temp["temporarily_unavailable_preserved"], 1)
        status_row = self.conn.execute(
            "SELECT status FROM lineage_nodes WHERE source_path='src/Tabs.tsx' AND stage='source'"
        ).fetchone()
        self.assertIsNotNone(status_row)
        self.assertEqual(status_row[0], "temporarily_unavailable")

        # Confirm removal of Tabs.tsx -> removed from current projection, historical version preserved!
        removed_sources = [self.sources[0]]
        r_rem = self.engine.refresh(removed_sources, cfg, scope="public", incremental=True)
        self.assertGreaterEqual(r_rem["reconciled_removed"], 1)
        active_paths = {c["path"] for c in self.engine.get_active_contexts(scope="public")}
        self.assertEqual(active_paths, {"src/Sidebar.tsx"})

        hist_paths = {h["source_path"] for h in self.engine.get_historical_versions(scope="public")}
        self.assertEqual(hist_paths, {"src/Sidebar.tsx", "src/Tabs.tsx"})

    def test_atomic_rollback_on_interruption(self) -> None:
        cfg = il.PipelineConfig()
        r1 = self.engine.refresh(self.sources, cfg, scope="public", incremental=True)
        pre_hash = self.engine.current_state_hash(scope="public")

        # Inject mid-run failure after 1st item
        r_fail = self.engine.refresh(
            [
                il.SourceInput(
                    source_id="repo.exams-app",
                    path="src/NewBroken.tsx",
                    content="export const X = 1;",
                    scope="public",
                ),
                self.sources[1],
            ],
            cfg,
            scope="public",
            incremental=True,
            fail_after_items=1,
        )
        self.assertEqual(r_fail["status"], "rolled_back")
        self.assertEqual(self.engine.current_state_hash(scope="public"), pre_hash)
        self.assertEqual(r_fail["state_hash"], r1["state_hash"])

    def test_benchmark_equivalence_and_zero_emoji(self) -> None:
        bench = il.run_benchmark(num_files=8)
        self.assertTrue(bench["all_scenarios_equivalent_to_full_rebuild"])
        self.assertTrue(bench["rollback_integrity_verified"])
        for sc in bench["scenarios"]:
            if "work_avoided_ratio" in sc:
                self.assertGreater(sc["work_avoided_ratio"], 0.4)

        script_txt = (SCRIPTS_DIR / "incremental_lineage.py").read_text(encoding="utf-8")
        self.assertFalse(EMOJI_REGEX.search(script_txt))
        self.assertFalse(EMOJI_REGEX.search(json.dumps(bench, ensure_ascii=False)))


if __name__ == "__main__":
    unittest.main()
