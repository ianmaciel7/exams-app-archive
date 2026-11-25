#!/usr/bin/env python3
"""Tests for hierarchical and recursive context retriever with pre-ranking filters (#86)."""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import hierarchical_retriever as hr  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class HierarchicalRetrieverTests(unittest.TestCase):
    def test_hierarchy_modeling_across_document_code_and_media(self) -> None:
        conn = sqlite3.connect(":memory:")
        store = hr.HierarchicalStore(conn=conn)
        try:
            # 1. Document: document > section > subsection > passage
            doc_md = (
                "# Spec Sidebar\n\n"
                "## Interactions\n\n"
                "### Hover Peek\n\n"
                "Hovering the rail for 300ms opens the peek drawer.\n"
            )
            doc_ids = store.add_document_from_markdown(
                doc_md, doc_id="doc:sidebar", path="docs/sidebar.md", domain="workspace", license_name="MIT"
            )
            levels_doc = {store.nodes[nid].level for nid in doc_ids}
            self.assertEqual(levels_doc, {"document", "section", "subsection", "passage"})

            # 2. Code: module > symbol > member
            py_code = (
                "class SidebarController:\n"
                "    def open_peek(self):\n"
                "        return 'peek'\n"
            )
            code_ids = store.add_code_from_source(
                py_code, module_id="code:sidebar", path="src/sidebar.py", language="python", domain="engenharia", license_name="MIT"
            )
            levels_code = {store.nodes[nid].level for nid in code_ids}
            self.assertEqual(levels_code, {"module", "symbol", "member"})

            # 3. Media: asset > segment > state
            media_rec = {
                "id": "demo-sidebar",
                "title": "Sidebar hover demo",
                "product": "Linear",
                "kind": "video",
                "keywords": ["sidebar", "peek"],
                "status": "archived-blob-verified",
                "path": "media/linear/sidebar.mp4",
                "blob_sha": "aa" * 20,
                "source_repo": "example/repo",
                "source_commit": "bb" * 20,
                "license": "MIT",
                "segment_evidence": {
                    "source_blob_sha": "aa" * 20,
                    "segment": {"start_seconds": 0.0, "end_seconds": 4.0},
                    "pattern": "hover-peek",
                    "component": "Sidebar",
                    "trigger": "pointerenter",
                    "observations": ["Drawer slides in smoothly"],
                    "states": ["collapsed", "peek-open"],
                },
            }
            media_ids = store.add_media_from_record(media_rec)
            levels_media = {store.nodes[nid].level for nid in media_ids}
            self.assertEqual(levels_media, {"asset", "segment", "state"})

            # Verify SQLite persistence matches in-memory node/edge counts
            db_nodes = conn.execute("SELECT COUNT(*) FROM hier_nodes").fetchone()[0]
            db_edges = conn.execute("SELECT COUNT(*) FROM hier_edges").fetchone()[0]
            self.assertEqual(db_nodes, len(store.nodes))
            self.assertEqual(db_edges, len(store.edges))
        finally:
            conn.close()

    def test_pre_ranking_filters_block_before_scoring_and_during_expansion(self) -> None:
        store = hr.HierarchicalStore()
        # Public verified leaf whose parent is private/unverified -> expansion MUST NOT leak parent
        store.add_node(
            hr.HierarchyNode(
                node_id="doc:private-parent",
                modality="document",
                level="document",
                title="Private Architecture Secret",
                content="Internal unreleased credential architecture",
                scope="authenticated_archive",
                repo="notes-app",
                ref="refs/heads/old-5",
                version="1.0.0",
                domain="governanca",
                license="proprietary",
                provenance_status="verified",
            )
        )
        store.add_node(
            hr.HierarchyNode(
                node_id="doc:public-leaf",
                modality="document",
                level="passage",
                title="Public Sidebar Hint",
                content="Sidebar collapse shortcut behavior",
                parent_id="doc:private-parent",
                scope="public",
                repo="exams-app",
                ref="refs/heads/main",
                version="1.0.0",
                domain="workspace",
                license="MIT",
                provenance_status="verified",
            )
        )
        # Unverified synthetic node that would match lexically if not pre-filtered
        store.add_node(
            hr.HierarchyNode(
                node_id="doc:synthetic-unverified",
                modality="document",
                level="passage",
                title="Sidebar Collapse Fake",
                content="Sidebar collapse shortcut behavior repeated sidebar collapse",
                scope="public",
                repo="exams-app",
                ref="refs/heads/main",
                version="1.0.0",
                domain="workspace",
                license="MIT",
                provenance_status="synthetic",
            )
        )
        # Wrong version/license node
        store.add_node(
            hr.HierarchyNode(
                node_id="doc:old-version",
                modality="document",
                level="passage",
                title="Sidebar Collapse v0",
                content="Sidebar collapse shortcut behavior",
                scope="public",
                repo="exams-app",
                ref="refs/heads/main",
                version="0.1.0",
                domain="workspace",
                license="GPL-3.0",
                provenance_status="verified",
            )
        )
        store.finalize_links()

        pf = hr.PreRankingFilter(
            authorized=False,
            allowed_scopes=("public",),
            repo="exams-app",
            ref="refs/heads/main",
            version="1.0.0",
            domain="workspace",
            license="MIT",
            provenance_statuses=("verified",),
        )
        res = hr.retrieve_hierarchical(
            store, "sidebar collapse shortcut", pre_filter=pf, depth_limit=2, expansion_policy="parents_and_refs"
        )
        returned_ids = {r["node_id"] for r in res["results"]}
        self.assertEqual(returned_ids, {"doc:public-leaf"})
        self.assertEqual(res["pre_filter_stats"]["eligible_nodes"], 1)
        self.assertEqual(res["pre_filter_stats"]["rejected_nodes"], 3)
        # Ensure parent was blocked during recursive expansion
        filtered_exp_ids = {f["node_id"] for f in res["filtered_during_expansion"]}
        self.assertIn("doc:private-parent", filtered_exp_ids)

    def test_recursive_cycle_protection_and_depth_limit(self) -> None:
        store = hr.HierarchicalStore()
        store.add_node(
            hr.HierarchyNode(
                node_id="n1",
                modality="code",
                level="member",
                title="handleClick",
                content="Triggers modal state update",
                scope="public",
                provenance_status="verified",
            )
        )
        store.add_node(
            hr.HierarchyNode(
                node_id="n2",
                modality="code",
                level="symbol",
                title="ModalPanel",
                content="Renders dialog",
                scope="public",
                provenance_status="verified",
            )
        )
        store.add_node(
            hr.HierarchyNode(
                node_id="n3",
                modality="document",
                level="section",
                title="ADR Modal",
                content="Modal decision doc",
                scope="public",
                provenance_status="verified",
            )
        )
        # Create explicit cycle n1 -> n2 -> n3 -> n1
        store.add_reference("n1", "n2", "references")
        store.add_reference("n2", "n3", "references")
        store.add_reference("n3", "n1", "references")

        res = hr.retrieve_hierarchical(
            store,
            "handleClick",
            depth_limit=4,
            expansion_policy="parents_and_refs",
            budget_tokens=4000,
        )
        returned_ids = [r["node_id"] for r in res["results"]]
        self.assertEqual(returned_ids, ["n1", "n2", "n3"])
        self.assertTrue(res["cycles_prevented"])
        self.assertEqual(res["cycles_prevented"][0]["to"], "n1")
        self.assertEqual(res["visited_set"], ["n1", "n2", "n3"])

        # Depth limit 1 must stop before n3
        res_d1 = hr.retrieve_hierarchical(
            store, "handleClick", depth_limit=1, expansion_policy="parents_and_refs", budget_tokens=4000
        )
        self.assertEqual({r["node_id"] for r in res_d1["results"]}, {"n1", "n2"})

    def test_compound_query_decomposition_and_gap_reporting(self) -> None:
        store, _ = hr.build_benchmark_store()
        subqs = hr.decompose_compound_query("Validar SHA-256 dos pacotes e gabarito comentado oculto")
        self.assertEqual(len(subqs), 2)

        res = hr.retrieve_hierarchical(
            store,
            "Validar SHA-256 dos pacotes e termo_inexistente_xyz",
            depth_limit=2,
            expansion_policy="parents_and_refs",
            budget_tokens=3000,
        )
        self.assertEqual(len(res["subqueries"]), 2)
        self.assertTrue(any(sq["gap"] for sq in res["subqueries"]))
        self.assertTrue(any(g.startswith("no_evidence_for_subquery:") for g in res["gaps"]))
        self.assertTrue(all("retrieval_reason" in r for r in res["results"]))

    def test_specific_first_ordering_and_budget_enforcement(self) -> None:
        store, _ = hr.build_benchmark_store()
        res = hr.retrieve_hierarchical(
            store,
            "gabarito comentado oculto",
            depth_limit=2,
            expansion_policy="parents",
            budget_tokens=300,
        )
        self.assertLessEqual(res["tokens_used"], 300)
        # First retrieved node (depth 0) must be the specific passage rather than root document
        self.assertEqual(res["results"][0]["level"], "passage")
        self.assertEqual(res["results"][0]["depth"], 0)

    def test_flat_vs_recursive_benchmark_shows_gain_and_cli(self) -> None:
        comp = hr.compare_flat_vs_recursive()
        self.assertGreater(comp["recursive_mean_recall"], comp["flat_mean_recall"])
        self.assertEqual(comp["recursive_mean_recall"], 1.0)
        self.assertGreater(comp["recall_gain"], 0.0)

        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "hierarchical_retriever.py"), "--benchmark"],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["recursive_mean_recall"], 1.0)

    def test_zero_emoji_compliance(self) -> None:
        for p in (SCRIPTS_DIR / "hierarchical_retriever.py", Path(__file__).resolve()):
            text = p.read_text(encoding="utf-8")
            self.assertEqual(EMOJI_REGEX.findall(text), [], f"Emoji found in {p}")


if __name__ == "__main__":
    unittest.main()
