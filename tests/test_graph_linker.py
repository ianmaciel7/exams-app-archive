#!/usr/bin/env python3
"""Tests for scripts/graph_linker.py covering nodes, edges, neighborhood queries, and Zero Emoji Policy."""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import graph_linker  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class GraphLinkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.db_path = self.tmp_path / "graph.sqlite"
        self.conn = graph_linker.open_db(self.db_path)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_all_node_and_edge_types_and_validation(self) -> None:
        repo_a = graph_linker.upsert_node(
            self.conn, node_type="Repo", label="notes-app", repo="notes-app"
        )
        repo_b = graph_linker.upsert_node(
            self.conn, node_type="Repo", label="exams-app", repo="exams-app"
        )
        ref_a = graph_linker.upsert_node(
            self.conn,
            node_type="Ref",
            label="old-5",
            repo="notes-app",
            ref="refs/heads/old-5",
            commit_sha="a" * 40,
            validity_status="valid_in_commit",
        )
        commit_a = graph_linker.upsert_node(
            self.conn,
            node_type="Commit",
            label="aaaaaaa",
            repo="notes-app",
            ref="old-5",
            commit_sha="a" * 40,
            timestamp="2026-06-01T10:00:00Z",
            validity_status="valid_in_commit",
        )
        file_sidebar = graph_linker.upsert_node(
            self.conn,
            node_type="File",
            label="app-sidebar.tsx",
            repo="notes-app",
            ref="old-5",
            path="src/components/app-sidebar.tsx",
            commit_sha="a" * 40,
            timestamp="2026-06-01T10:00:00Z",
            validity_status="valid_in_commit",
        )
        file_shell = graph_linker.upsert_node(
            self.conn,
            node_type="File",
            label="app-shell.tsx",
            repo="notes-app",
            ref="old-5",
            path="src/components/app-shell.tsx",
            commit_sha="a" * 40,
            timestamp="2026-06-01T10:00:00Z",
        )
        comp_sidebar = graph_linker.upsert_node(
            self.conn,
            node_type="Component",
            label="Sidebar",
            repo="multi-repo",
            validity_status="valid_in_commit",
        )
        pr_40 = graph_linker.upsert_node(
            self.conn,
            node_type="PR",
            label="PR #40: fix sidebar header",
            repo="notes-app",
            ref="feat/sidebar",
            commit_sha="b" * 40,
            timestamp="2026-08-21T23:50:50Z",
        )
        issue_30 = graph_linker.upsert_node(
            self.conn,
            node_type="Issue",
            label="Issue #30: sidebar graph",
            repo="exams-app",
            timestamp="2026-11-23T12:00:00Z",
        )
        img_sidebar = graph_linker.upsert_node(
            self.conn,
            node_type="Image",
            label="m-dark-2-gaveta.png",
            repo="exams-app",
            ref="dev",
            path="docs/revisao/sidebar-prototipo/capturas/m-dark-2-gaveta.png",
            commit_sha="c" * 40,
            timestamp="2026-11-20T10:00:00Z",
            validity_status="valid_in_commit",
        )
        dec_old = graph_linker.upsert_node(
            self.conn,
            node_type="Decision",
            label="Decision: Sidebar hover reveal",
            repo="notes-app",
            ref="old-5",
            path="docs/sidebar-hover.md",
            commit_sha="a" * 40,
            timestamp="2026-06-01T10:00:00Z",
            validity_status="valid_in_commit",
        )
        dec_new = graph_linker.upsert_node(
            self.conn,
            node_type="Decision",
            label="Decision: Sidebar header alignment",
            repo="exams-app",
            ref="dev",
            path="docs/app-shell/decisoes.md",
            commit_sha="c" * 40,
            timestamp="2026-11-20T10:00:00Z",
            validity_status="valid_in_commit",
        )

        graph_linker.upsert_edge(
            self.conn,
            src_id=ref_a,
            dst_id=repo_a,
            edge_type="DOCUMENTED_IN",
            confidence="EXTRACTED",
            repo="notes-app",
            ref="old-5",
            commit_sha="a" * 40,
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=commit_a,
            dst_id=file_sidebar,
            edge_type="MODIFIES",
            confidence="EXTRACTED",
            repo="notes-app",
            ref="old-5",
            commit_sha="a" * 40,
            timestamp="2026-06-01T10:00:00Z",
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=file_sidebar,
            dst_id=comp_sidebar,
            edge_type="MODIFIES",
            confidence="EXTRACTED",
            repo="notes-app",
            ref="old-5",
            commit_sha="a" * 40,
            timestamp="2026-06-01T10:00:00Z",
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=file_shell,
            dst_id=file_sidebar,
            edge_type="IMPORTS",
            confidence="EXTRACTED",
            repo="notes-app",
            ref="old-5",
            commit_sha="a" * 40,
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=file_sidebar,
            dst_id=file_shell,
            edge_type="CO_OCCURS_WITH",
            confidence="INFERRED",
            repo="notes-app",
            ref="old-5",
            commit_sha="a" * 40,
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=dec_old,
            dst_id=comp_sidebar,
            edge_type="MODIFIES",
            confidence="INFERRED",
            repo="notes-app",
            ref="old-5",
            commit_sha="a" * 40,
            timestamp="2026-06-01T10:00:00Z",
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=dec_new,
            dst_id=comp_sidebar,
            edge_type="MODIFIES",
            confidence="EXTRACTED",
            repo="exams-app",
            ref="dev",
            commit_sha="c" * 40,
            timestamp="2026-11-20T10:00:00Z",
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=dec_new,
            dst_id=img_sidebar,
            edge_type="EVIDENCED_BY",
            confidence="EXTRACTED",
            repo="exams-app",
            ref="dev",
            commit_sha="c" * 40,
            timestamp="2026-11-20T10:00:00Z",
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=pr_40,
            dst_id=issue_30,
            edge_type="DOCUMENTED_IN",
            confidence="EXTRACTED",
            repo="notes-app",
            timestamp="2026-08-21T23:50:50Z",
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=repo_b,
            dst_id=issue_30,
            edge_type="DOCUMENTED_IN",
            confidence="EXTRACTED",
            repo="exams-app",
        )
        self.conn.commit()

        sup_count = graph_linker.link_temporal_supersession(self.conn)
        self.assertGreaterEqual(sup_count, 1)

        stats = graph_linker.graph_stats(self.conn)
        self.assertEqual(set(stats["nodes_by_type"].keys()), set(graph_linker.NODE_TYPES))
        self.assertEqual(set(stats["edges_by_type"].keys()), set(graph_linker.EDGE_TYPES))
        self.assertEqual(stats["edges_by_confidence"]["EXTRACTED"] >= 6, True)
        self.assertEqual(stats["edges_by_confidence"]["INFERRED"] >= 2, True)

        with self.assertRaises(ValueError):
            graph_linker.upsert_node(self.conn, node_type="UnknownNode", label="x")
        with self.assertRaises(ValueError):
            graph_linker.upsert_edge(
                self.conn, src_id=repo_a, dst_id=repo_b, edge_type="UNKNOWN_EDGE"
            )
        with self.assertRaises(ValueError):
            graph_linker.upsert_edge(
                self.conn,
                src_id=repo_a,
                dst_id=repo_b,
                edge_type="MODIFIES",
                confidence="GUESSED",
            )

    def test_neighborhood_and_temporal_impact_cross_repo_sidebar(self) -> None:
        comp = graph_linker.upsert_node(
            self.conn, node_type="Component", label="Sidebar", repo="multi-repo"
        )
        dec_1 = graph_linker.upsert_node(
            self.conn,
            node_type="Decision",
            label="PR #40: fix app sidebar header integration",
            repo="notes-app",
            ref="feat/app-sidebar",
            commit_sha="1" * 40,
            timestamp="2026-08-21T23:50:50Z",
            validity_status="valid_in_commit",
        )
        dec_2 = graph_linker.upsert_node(
            self.conn,
            node_type="Decision",
            label="Decision doc: app-shell decisoes.md",
            repo="exams-app",
            ref="dev",
            path="docs/01-planejamento/revisao/app-shell/decisoes.md",
            commit_sha="2" * 40,
            timestamp="2026-11-23T15:00:00Z",
            validity_status="valid_in_commit",
        )
        img_1 = graph_linker.upsert_node(
            self.conn,
            node_type="Image",
            label="m-dark-2-gaveta.png",
            repo="exams-app",
            ref="dev",
            path="docs/revisao/sidebar-prototipo/capturas/m-dark-2-gaveta.png",
            commit_sha="2" * 40,
            timestamp="2026-11-23T15:00:00Z",
            validity_status="valid_in_commit",
        )
        img_2 = graph_linker.upsert_node(
            self.conn,
            node_type="Image",
            label="capacities-sidebar-task-placement.webp",
            repo="notes-app",
            ref="old-5",
            path="assets/capacities-sidebar-task-placement.webp",
            commit_sha="3" * 40,
            timestamp="2026-08-24T10:00:00Z",
            validity_status="valid_in_commit",
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=dec_1,
            dst_id=comp,
            edge_type="MODIFIES",
            confidence="EXTRACTED",
            repo="notes-app",
            ref="feat/app-sidebar",
            commit_sha="1" * 40,
            timestamp="2026-08-21T23:50:50Z",
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=dec_2,
            dst_id=comp,
            edge_type="MODIFIES",
            confidence="EXTRACTED",
            repo="exams-app",
            ref="dev",
            commit_sha="2" * 40,
            timestamp="2026-11-23T15:00:00Z",
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=dec_2,
            dst_id=img_1,
            edge_type="EVIDENCED_BY",
            confidence="INFERRED",
            repo="exams-app",
            ref="dev",
            commit_sha="2" * 40,
            timestamp="2026-11-23T15:00:00Z",
        )
        graph_linker.upsert_edge(
            self.conn,
            src_id=img_2,
            dst_id=comp,
            edge_type="EVIDENCED_BY",
            confidence="EXTRACTED",
            repo="notes-app",
            ref="old-5",
            commit_sha="3" * 40,
            timestamp="2026-08-24T10:00:00Z",
        )
        self.conn.commit()
        graph_linker.link_temporal_supersession(self.conn)

        # Query both in EN ("Sidebar") and PT ("barra lateral")
        res_en = graph_linker.query_neighborhood(self.conn, "Sidebar", hops=2)
        res_pt = graph_linker.query_neighborhood(self.conn, "barra lateral", hops=2)

        self.assertEqual(res_en["repos_touched"], ["exams-app", "notes-app"])
        self.assertEqual(res_pt["repos_touched"], ["exams-app", "notes-app"])
        self.assertEqual(len(res_en["decisions"]), 2)
        self.assertEqual(len(res_en["images"]), 2)
        self.assertEqual(res_en["decisions"][0]["validity_status"], "superseded_in_later_branch")
        self.assertEqual(res_en["decisions"][1]["validity_status"], "valid_in_commit")

        # Temporal filtering restricts older events cleanly
        res_recent = graph_linker.query_neighborhood(
            self.conn, "Sidebar", hops=2, since="2026-11-01T00:00:00Z"
        )
        self.assertEqual(res_recent["repos_touched"], ["exams-app"])
        self.assertEqual(len(res_recent["decisions"]), 1)

    def test_extract_imports_and_export_json_guard(self) -> None:
        ts_code = (
            'import * as React from "react"\n'
            'import { AppShell } from "@/components/app-shell"\n'
            'const lib = require("./sidebar-state")\n'
        )
        self.assertEqual(
            graph_linker.extract_imports_from_source("sidebar.tsx", ts_code),
            ["react", "@/components/app-shell", "./sidebar-state"],
        )
        py_code = "import json\nfrom pathlib import Path\n"
        self.assertEqual(
            graph_linker.extract_imports_from_source("linker.py", py_code),
            ["json", "pathlib"],
        )

        # Reject writing private graph data to site/
        with self.assertRaises(ValueError):
            graph_linker.open_db(ROOT / "site" / "leak.sqlite")
        with self.assertRaises(ValueError):
            graph_linker.export_graph_json(self.conn, ROOT / "site" / "leak.json")

        json_out = self.tmp_path / "graph-export.json"
        summary = graph_linker.export_graph_json(self.conn, json_out)
        self.assertTrue(json_out.is_file())
        parsed = json.loads(json_out.read_text(encoding="utf-8"))
        self.assertEqual(parsed["schema_version"], 1)
        self.assertEqual(parsed["node_count"], summary["node_count"])

    def test_ingest_real_repo_inventories_and_cli_query(self) -> None:
        exams_inv = ROOT / "inventory" / "exams-app-branch-files.json"
        notes_dir = ROOT / "inventory" / "notes-app"
        if not exams_inv.is_file() or not notes_dir.is_dir():
            self.skipTest("Repository inventory fixtures unavailable")

        graph_linker.ingest_branch_inventory(self.conn, exams_inv, repo_override="exams-app")
        graph_linker.ingest_notes_platform_inventory(self.conn, notes_dir, repo_name="notes-app")
        graph_linker.link_temporal_supersession(self.conn)

        sidebar = graph_linker.query_neighborhood(self.conn, "Sidebar", hops=2, limit=150)
        self.assertEqual(sidebar["repos_touched"], ["exams-app", "notes-app"])
        self.assertGreater(len(sidebar["decisions"]), 0)
        self.assertGreater(len(sidebar["images"]), 0)

        # CLI query roundtrip
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "graph_linker.py"),
                "--db",
                str(self.db_path),
                "query",
                "Sidebar",
                "--hops",
                "2",
                "--limit",
                "30",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        cli_out = json.loads(proc.stdout)
        self.assertEqual(cli_out["query"], "Sidebar")
        self.assertEqual(cli_out["repos_touched"], ["exams-app", "notes-app"])

    def test_zero_emoji_policy(self) -> None:
        targets = [
            ROOT / "scripts" / "graph_linker.py",
            ROOT / "tests" / "test_graph_linker.py",
            ROOT / "reports" / "GRAPH-REPRESENTATION-BENCHMARK.md",
        ]
        for target in targets:
            if target.exists():
                content = target.read_text(encoding="utf-8")
                self.assertEqual(
                    EMOJI_REGEX.findall(content),
                    [],
                    f"Found disallowed emoji in {target}",
                )


if __name__ == "__main__":
    unittest.main()
