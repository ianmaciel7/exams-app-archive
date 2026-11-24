#!/usr/bin/env python3
"""Integration tests for approved enhancements in the Exams Archive CLI and matrix doc (Issue #36)."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NATIVE_CLI = ROOT / "plugins" / "exams-archive-native" / "scripts" / "archive_query.py"
LEGACY_CLI = ROOT / "plugins" / "exams-archive" / "scripts" / "archive_query.py"
MATRIX_DOC = ROOT / "docs" / "ENHANCEMENT-INTEGRATION-MATRIX.md"
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class IntegrationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)

    def _run_cli(self, cli: Path, *args: str, expected_rc: int | None = 0) -> tuple[subprocess.CompletedProcess[str], dict | list | None]:
        proc = subprocess.run(
            [sys.executable, str(cli), *args],
            capture_output=True,
            text=True,
        )
        if expected_rc is not None:
            self.assertEqual(proc.returncode, expected_rc, msg=f"stderr={proc.stderr}\nstdout={proc.stdout}")
        parsed = json.loads(proc.stdout) if proc.stdout.strip() else None
        return proc, parsed

    def test_native_and_legacy_cli_remain_identical_and_backwards_compatible(self) -> None:
        self.assertEqual(NATIVE_CLI.read_bytes(), LEGACY_CLI.read_bytes())

        db_path = self.tmp_path / "legacy-fts.sqlite"
        conn = sqlite3.connect(db_path)
        conn.executescript(
            """
            CREATE TABLE repositories(id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE commits(repo_id INTEGER, sha TEXT, date TEXT, subject TEXT);
            CREATE TABLE changes(repo_id INTEGER, sha TEXT, status TEXT, path TEXT, previous_path TEXT);
            CREATE TABLE images(repo_id INTEGER, path TEXT, blob TEXT, commit_sha TEXT, kind TEXT, bytes INTEGER);
            CREATE VIRTUAL TABLE commit_fts USING fts5(subject, repo_id UNINDEXED, sha UNINDEXED);
            CREATE VIRTUAL TABLE change_fts USING fts5(path, repo_id UNINDEXED, sha UNINDEXED, status UNINDEXED);
            INSERT INTO repositories VALUES(1, 'exams-app');
            INSERT INTO commits VALUES(1, '1111111111111111111111111111111111111111', '2026-11-20', 'Sidebar prototype');
            INSERT INTO commit_fts VALUES('Sidebar prototype', '1', '1111111111111111111111111111111111111111');
            INSERT INTO changes VALUES(1, '1111111111111111111111111111111111111111', 'A', 'src/sidebar.tsx', '');
            INSERT INTO change_fts VALUES('src/sidebar.tsx', '1', '1111111111111111111111111111111111111111', 'A');
            INSERT INTO images VALUES(1, 'docs/sidebar.png', 'aaaa', '1111111111111111111111111111111111111111', 'branch-head', 128);
            """
        )
        conn.commit()
        conn.close()

        for cli in (NATIVE_CLI, LEGACY_CLI):
            _, rows = self._run_cli(cli, "--db", str(db_path), "search", "sidebar", "--limit", "10")
            self.assertEqual({r["kind"] for r in rows}, {"commit", "file", "image"})
            _, stats = self._run_cli(cli, "--db", str(db_path), "stats")
            self.assertEqual(stats, [{"repository": "exams-app", "commits": 1}])

    def test_ast_subcommand_extracts_chunks_and_motion_contracts(self) -> None:
        tsx_file = self.tmp_path / "SidebarPeek.tsx"
        tsx_file.write_text(
            "import React, { useState } from 'react';\n"
            "export function SidebarPeek() {\n"
            "  const [open, setOpen] = useState(false);\n"
            "  const handleMouseEnter = () => {\n"
            "    setTimeout(() => setOpen(true), 300);\n"
            "  };\n"
            "  return <aside onMouseEnter={handleMouseEnter} className='transition-all duration-200 ease-out motion-reduce:transition-none'>{String(open)}</aside>;\n"
            "}\n",
            encoding="utf-8",
        )

        _, payload = self._run_cli(NATIVE_CLI, "ast", str(tsx_file), "--summary-only")
        self.assertEqual(payload["language"], "tsx")
        self.assertGreaterEqual(payload["chunk_count"], 2)
        self.assertGreaterEqual(payload["motion_contract_count"], 2)
        names = {(c["node_type"], c["name"]) for c in payload["chunks"]}
        self.assertIn(("component", "SidebarPeek"), names)
        self.assertIn(("handler", "handleMouseEnter"), names)

    def test_graph_subcommand_builds_and_queries_multi_repo_inventory(self) -> None:
        inv_dir = self.tmp_path / "inventory"
        notes_dir = inv_dir / "notes-app"
        notes_dir.mkdir(parents=True)

        (inv_dir / "exams-app-branch-files.json").write_text(
            json.dumps(
                {
                    "source": "ianmaciel7/exams-app",
                    "branch_inventories": [
                        {
                            "branch": "dev",
                            "ref": "refs/heads/dev",
                            "sha": "a" * 40,
                            "files": [
                                {"path": "docs/revisao/app-shell/decisoes.md", "sha": "b" * 40, "size": 100},
                                {"path": "docs/revisao/sidebar-prototipo/capturas/m-dark-2-gaveta.png", "sha": "c" * 40, "size": 200},
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (notes_dir / "source-pulls-2026-11-23.json").write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "number": 40,
                            "title": "Fix sidebar hover header alignment",
                            "body": "Decision: align sidebar peek timing.",
                            "state": "closed",
                            "created_at": "2026-08-20T10:00:00Z",
                            "merged_at": "2026-08-21T10:00:00Z",
                            "merge_commit_sha": "d" * 40,
                            "head": {"ref": "feat/sidebar", "sha": "d" * 40},
                            "base": {"ref": "main", "sha": "e" * 40},
                            "html_url": "https://github.com/ianmaciel7/notes-app/pull/40",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (notes_dir / "source-issues-2026-11-23.json").write_text(json.dumps({"entries": []}), encoding="utf-8")

        graph_db = self.tmp_path / "graph.sqlite"
        _, res = self._run_cli(
            NATIVE_CLI,
            "graph",
            "Sidebar",
            "--graph-db",
            str(graph_db),
            "--inventory-dir",
            str(inv_dir),
            "--hops",
            "2",
        )
        self.assertEqual(res["repos_touched"], ["exams-app", "notes-app"])
        self.assertGreaterEqual(len(res["decisions"]), 1)
        self.assertGreaterEqual(len(res["images"]), 1)

        _, stats = self._run_cli(NATIVE_CLI, "graph", "--graph-db", str(graph_db), "--stats")
        self.assertGreater(stats["total_nodes"], 0)
        self.assertGreater(stats["total_edges"], 0)

    def test_context_subcommand_imports_inventory_and_queries_timeline(self) -> None:
        inv_dir = self.tmp_path / "ctx_inv"
        notes_dir = inv_dir / "notes-app"
        platform_dir = notes_dir / "platform"
        platform_dir.mkdir(parents=True)

        (notes_dir / "source-pulls-2026-11-23.json").write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "number": 40,
                            "title": "Sidebar hover peek",
                            "body": "Rationale: keep 300ms dwell delay.",
                            "state": "closed",
                            "user": {"login": "ianmaciel7"},
                            "created_at": "2026-08-20T10:00:00Z",
                            "merged_at": "2026-08-21T10:00:00Z",
                            "merge_commit_sha": "f" * 40,
                            "head": {"ref": "feat/sidebar", "sha": "f" * 40},
                            "base": {"ref": "main", "sha": "1" * 40},
                            "html_url": "https://github.com/ianmaciel7/notes-app/pull/40",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (platform_dir / "pr-file-diffs-batch-01.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "number": 40,
                            "files": [
                                {
                                    "filename": "src/components/space-frame.tsx",
                                    "status": "modified",
                                    "sha": "2" * 40,
                                    "additions": 10,
                                    "deletions": 2,
                                    "patch": "@@ -1,2 +1,3 @@\n+setTimeout(() => setPeek(true), 300)",
                                    "blob_url": "https://github.com/ianmaciel7/notes-app/blob/" + ("f" * 40) + "/src/components/space-frame.tsx",
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        ctx_db = self.tmp_path / "context.sqlite"
        _, res = self._run_cli(
            NATIVE_CLI,
            "context",
            "space-frame.tsx",
            "--context-db",
            str(ctx_db),
            "--inventory-dir",
            str(inv_dir),
        )
        self.assertEqual(res["total_files"], 1)
        self.assertEqual(res["files"][0]["path"], "src/components/space-frame.tsx")
        self.assertTrue(res["files"][0]["commits"][0]["has_cited_justification"])

        _, stats = self._run_cli(NATIVE_CLI, "context", "--context-db", str(ctx_db), "--stats")
        self.assertEqual(stats["items"], 1)

    def test_secrets_check_subcommand_blocks_and_passes_clean_targets(self) -> None:
        clean_dir = self.tmp_path / "clean"
        clean_dir.mkdir()
        (clean_dir / "app.ts").write_text("export const version = '1.0.0';\n", encoding="utf-8")
        _, clean_report = self._run_cli(LEGACY_CLI, "secrets-check", str(clean_dir), expected_rc=0)
        self.assertFalse(clean_report["blocked"])
        self.assertEqual(clean_report["gate_decision"], "PASS")

        dirty_dir = self.tmp_path / "dirty"
        dirty_dir.mkdir()
        canary = "ghp_" + "syntheticIntegrationGateToken1234567890"
        (dirty_dir / "leak.ts").write_text(f"const tok = '{canary}';\n", encoding="utf-8")
        _, dirty_report = self._run_cli(NATIVE_CLI, "secrets-check", str(dirty_dir), expected_rc=2)
        self.assertTrue(dirty_report["blocked"])
        self.assertEqual(dirty_report["gate_decision"], "BLOCK")
        self.assertNotIn(canary, json.dumps(dirty_report))

    def test_matrix_document_and_zero_emoji_policy(self) -> None:
        self.assertTrue(MATRIX_DOC.is_file(), "Missing docs/ENHANCEMENT-INTEGRATION-MATRIX.md")
        matrix_text = MATRIX_DOC.read_text(encoding="utf-8")
        for ref in ("#9", "#10", "#30", "#31", "#32", "#33"):
            self.assertIn(ref, matrix_text, f"Missing {ref} in integration matrix")
        for keyword in ("ast", "graph", "context", "secrets-check", "Candidate", "Baseline", "Decisao"):
            self.assertIn(keyword, matrix_text, f"Missing {keyword} in integration matrix")

        for target in (NATIVE_CLI, LEGACY_CLI, MATRIX_DOC, Path(__file__)):
            content = target.read_text(encoding="utf-8")
            self.assertEqual(EMOJI_REGEX.findall(content), [], f"Found disallowed emoji in {target}")


if __name__ == "__main__":
    unittest.main()
