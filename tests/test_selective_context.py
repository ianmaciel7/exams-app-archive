#!/usr/bin/env python3
"""Tests for scripts/selective_context.py covering budgets, modes, sanitization, dedup, and benchmark."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import archive_flow  # noqa: E402
import content_index  # noqa: E402
import selective_context  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


def run_git(*args: str, cwd: Path | None = None, date: str | None = None) -> str:
    env = None
    if date is not None:
        import os

        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout


class SelectiveContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()

        run_git("init", "-q", "-b", "main", str(self.work))
        run_git("config", "user.email", "selective-test@example.invalid", cwd=self.work)
        run_git("config", "user.name", "Selective Test", cwd=self.work)

        (self.work / "src").mkdir()
        (self.work / "docs").mkdir()
        (self.work / "secrets").mkdir()

        ts_body = "\n".join(
            [
                "import React from 'react';",
                "",
                "export interface SidebarConfig {",
                "  collapsed: boolean;",
                "  widthPx: number;",
                "}",
                "",
                "export function buildExamSidebar(config: SidebarConfig) {",
                "  const panel = 'capacities-sidebar';",
            ]
            + [f"  const helper_{i} = {i};" for i in range(1, 35)]
            + [
                "  return { panel, collapsed: config.collapsed, width: config.widthPx };",
                "}",
            ]
        )
        (self.work / "src" / "sidebar.ts").write_text(ts_body + "\n", encoding="utf-8")
        # Identical blob at second path to test blob deduplication
        (self.work / "src" / "sidebar_copy.ts").write_text(ts_body + "\n", encoding="utf-8")

        py_body = (
            '"""Sidebar recall helper."""\n'
            "def get_sidebar_mode(collapsed: bool) -> str:\n"
            "    # capacities-sidebar state helper\n"
            "    return 'rail' if collapsed else 'expanded'\n"
        )
        (self.work / "src" / "sidebar_helper.py").write_text(py_body, encoding="utf-8")

        md_body = (
            "# Sidebar Layout Notes\n\n"
            "## Summary\n"
            "Use `capacities-sidebar` with deterministic collapse state.\n"
        )
        (self.work / "docs" / "sidebar.md").write_text(md_body, encoding="utf-8")

        # Secret files by path and by inline content (must never be returned or staged)
        (self.work / ".env").write_text(
            "API_KEY=ghp_syntheticTokenNeverExported12345678\n", encoding="utf-8"
        )
        (self.work / ".env.local").write_text(
            "TOKEN=sk_live_syntheticSecretKey9876543210\n", encoding="utf-8"
        )
        (self.work / "secrets" / "deploy.pem").write_text(
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA\n", encoding="utf-8"
        )
        (self.work / "src" / "leaked.ts").write_text(
            "export const capacities_sidebar_leak = 'ghp_syntheticInlineSecretToken1234567890';\n",
            encoding="utf-8",
        )

        run_git("add", ".", cwd=self.work)
        run_git(
            "commit",
            "-qm",
            "feat: initial sidebar fixtures",
            cwd=self.work,
            date="2026-11-01T10:00:00Z",
        )
        self.first_sha = run_git("rev-parse", "HEAD", cwd=self.work).strip()

        # Multiple commits touching src/sidebar.ts so grouping/dedup has multi-commit history
        for rev in range(1, 4):
            updated = ts_body.replace("width: config.widthPx", f"width: config.widthPx + {rev}")
            (self.work / "src" / "sidebar.ts").write_text(updated + "\n", encoding="utf-8")
            run_git("add", "src/sidebar.ts", cwd=self.work)
            run_git(
                "commit",
                "-qm",
                f"refactor: sidebar width rev {rev}",
                cwd=self.work,
                date=f"2026-11-0{rev + 1}T10:00:00Z",
            )
        self.latest_sha = run_git("rev-parse", "HEAD", cwd=self.work).strip()

        self.bare = self.root / "repo.git"
        run_git("clone", "--mirror", "-q", str(self.work), str(self.bare))
        self.bundle = self.root / "repo.bundle"
        run_git("--git-dir=" + str(self.bare), "bundle", "create", str(self.bundle), "--all")

        self.db_path = self.root / "content.sqlite"
        conn = content_index.open_db(self.db_path)
        try:
            content_index.ingest_repo(self.bundle, "synthetic-repo", conn, all_commits=True)
        finally:
            conn.close()

    def test_delivery_modes_and_provenance(self):
        budget = selective_context.ContextBudget(
            max_files=10, max_bytes=64 * 1024, max_lines=500, max_tokens=8000
        )

        meta = selective_context.run_pipeline(
            "sidebar",
            source=self.bundle,
            db_path=self.db_path,
            mode="metadata-only",
            budget=budget,
        )
        self.assertTrue(meta["ok"])
        self.assertEqual(meta["mode"], "metadata-only")
        self.assertEqual(meta["usage"]["content_bytes"], 0)
        self.assertGreaterEqual(meta["usage"]["files"], 3)
        for item in meta["items"]:
            self.assertNotIn("content", item)
            self.assertRegex(item["commit_sha"], r"^[0-9a-f]{40,64}$")
            self.assertIn("provenance", item)
            self.assertTrue(item["commit_date"])

        snip = selective_context.run_pipeline(
            "sidebar",
            source=self.bundle,
            db_path=self.db_path,
            mode="snippet",
            budget=budget,
        )
        self.assertEqual(snip["mode"], "snippet")
        self.assertGreater(snip["usage"]["content_lines"], 0)

        exact = selective_context.run_pipeline(
            "sidebar",
            source=self.bundle,
            db_path=self.db_path,
            mode="exact-file",
            budget=budget,
        )
        self.assertEqual(exact["mode"], "exact-file")
        self.assertGreater(exact["usage"]["content_bytes"], snip["usage"]["content_bytes"])

        pack = selective_context.run_pipeline(
            "sidebar",
            source=self.bundle,
            db_path=self.db_path,
            mode="context-pack",
            budget=budget,
            use_repomix=False,
        )
        self.assertEqual(pack["mode"], "context-pack")
        self.assertFalse(pack["repomix"]["used"])
        ts_item = next(i for i in pack["items"] if i["path"] == "src/sidebar.ts")
        self.assertEqual(ts_item["compaction"], "builtin-outline")
        self.assertEqual(ts_item["commits_matched"], 4)
        self.assertEqual(ts_item["first_sha"], self.first_sha)
        self.assertEqual(ts_item["last_sha"], self.latest_sha)
        self.assertIn("SidebarConfig", ts_item["content"])
        self.assertIn("Changed in 4 commit(s)", ts_item["content"])

    def test_deduplication_by_path_and_blob(self):
        budget = selective_context.ContextBudget(
            max_files=20, max_bytes=128 * 1024, max_lines=2000, max_tokens=50_000
        )
        no_dedup = selective_context.run_pipeline(
            "sidebar",
            source=self.bundle,
            db_path=self.db_path,
            mode="exact-file",
            deduplicate=False,
            budget=budget,
        )
        with_dedup = selective_context.run_pipeline(
            "sidebar",
            source=self.bundle,
            db_path=self.db_path,
            mode="exact-file",
            deduplicate=True,
            budget=budget,
        )

        # Without deduplication, repeated revisions of src/sidebar.ts multiply returned files/tokens
        self.assertGreater(no_dedup["usage"]["files"], with_dedup["usage"]["files"])
        self.assertGreater(
            no_dedup["usage"]["total_estimated_tokens"],
            with_dedup["usage"]["total_estimated_tokens"],
        )

        # Unique paths only, and identical blob between sidebar.ts (rev 0) and sidebar_copy.ts is collapsed if blob matches
        paths = [item["path"] for item in with_dedup["items"]]
        self.assertEqual(len(paths), len(set(paths)))
        blobs = [item["blob_sha"] for item in with_dedup["items"]]
        self.assertEqual(len(blobs), len(set(blobs)))

        # Direct test on identical blob collapse across two distinct paths
        fake_hits = [
            {
                "repository": "repo",
                "ref": "refs/heads/main",
                "commit_sha": self.first_sha,
                "path": "a/file.ts",
                "extension": ".ts",
                "language": "typescript",
                "blob_sha": "b" * 40,
                "status": "ref-head",
                "start_line": 1,
                "end_line": 5,
                "snippet": "export const x = 1;",
                "score": -2.0,
            },
            {
                "repository": "repo",
                "ref": "refs/heads/main",
                "commit_sha": self.first_sha,
                "path": "b/duplicate.ts",
                "extension": ".ts",
                "language": "typescript",
                "blob_sha": "b" * 40,
                "status": "ref-head",
                "start_line": 1,
                "end_line": 5,
                "snippet": "export const x = 1;",
                "score": -1.0,
            },
        ]
        selected, stats = selective_context.select_candidates(fake_hits, deduplicate=True, max_files=10)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["path"], "a/file.ts")
        self.assertEqual(stats["blob_duplicates_collapsed"], 1)
        self.assertEqual(selected[0]["duplicate_paths"][0]["path"], "b/duplicate.ts")

    def test_budget_limits_and_safe_truncation(self):
        # 1. max_files limit
        b_files = selective_context.run_pipeline(
            "sidebar",
            source=self.bundle,
            db_path=self.db_path,
            mode="exact-file",
            budget=selective_context.ContextBudget(
                max_files=2, max_bytes=64 * 1024, max_lines=500, max_tokens=10_000
            ),
        )
        self.assertLessEqual(b_files["usage"]["files"], 2)

        # 2. max_lines and max_bytes limits with safe UTF-8 / line truncation
        b_lines_bytes = selective_context.run_pipeline(
            "sidebar",
            source=self.bundle,
            db_path=self.db_path,
            mode="exact-file",
            budget=selective_context.ContextBudget(
                max_files=10, max_bytes=350, max_lines=8, max_tokens=4000
            ),
        )
        self.assertLessEqual(b_lines_bytes["usage"]["content_lines"], 8)
        self.assertLessEqual(b_lines_bytes["usage"]["content_bytes"], 350)
        self.assertGreaterEqual(b_lines_bytes["usage"]["truncated_items"], 1)

        # 3. Strict max_tokens guard on total serialized envelope
        b_tokens = selective_context.run_pipeline(
            "sidebar",
            source=self.bundle,
            db_path=self.db_path,
            mode="context-pack",
            budget=selective_context.ContextBudget(
                max_files=10, max_bytes=64 * 1024, max_lines=500, max_tokens=450
            ),
        )
        self.assertLessEqual(b_tokens["usage"]["total_estimated_tokens"], 450)
        self.assertLessEqual(
            selective_context.estimate_json_tokens(b_tokens), 450
        )

    def test_secret_sanitization_and_blocking(self):
        # Search never returns .env, .pem, or inline secret file
        res = selective_context.run_pipeline(
            "capacities-sidebar",
            source=self.bundle,
            db_path=self.db_path,
            mode="exact-file",
        )
        returned_paths = {item["path"] for item in res["items"]}
        self.assertNotIn(".env", returned_paths)
        self.assertNotIn(".env.local", returned_paths)
        self.assertNotIn("secrets/deploy.pem", returned_paths)
        self.assertNotIn("src/leaked.ts", returned_paths)

        # Even if injected directly into recover_stage or _compact_with_repomix, secrets are blocked
        for secret_path in (".env", ".env.production", "keys/id_rsa", "secrets/token.key"):
            blocked, _ = selective_context.is_secret_or_blocked(secret_path)
            self.assertTrue(blocked, f"Expected secret path to be blocked: {secret_path}")

        recovered, rec_stats = selective_context.recover_stage(
            self.bundle,
            [
                {
                    "repository": "synthetic-repo",
                    "path": ".env",
                    "ref": "refs/heads/main",
                    "commit_sha": self.first_sha,
                    "commit_date": "",
                    "blob_sha": "",
                    "language": "text",
                    "extension": ".env",
                    "status": "ref-head",
                    "score": -1.0,
                    "commits_matched": 1,
                    "first_sha": self.first_sha,
                    "last_sha": self.first_sha,
                    "history": [],
                    "snippets": [],
                },
                {
                    "repository": "synthetic-repo",
                    "path": "src/leaked.ts",
                    "ref": "refs/heads/main",
                    "commit_sha": self.first_sha,
                    "commit_date": "",
                    "blob_sha": "",
                    "language": "typescript",
                    "extension": ".ts",
                    "status": "ref-head",
                    "score": -1.0,
                    "commits_matched": 1,
                    "first_sha": self.first_sha,
                    "last_sha": self.first_sha,
                    "history": [],
                    "snippets": [],
                },
            ],
            mode="exact-file",
        )
        self.assertEqual(recovered, [])
        self.assertEqual(rec_stats["blocked_secrets"], 2)

        with self.assertRaises(archive_flow.PermissionDeniedError):
            selective_context._compact_with_repomix(
                {"src/config.ts": "const token = 'ghp_syntheticSecretNeverStage12345678';"}
            )

    def test_optional_repomix_fallback_and_integration(self):
        # When Repomix is unavailable, context-pack falls back deterministically without error
        with mock.patch.object(selective_context, "_find_repomix_command", return_value=None):
            fallback = selective_context.run_pipeline(
                "sidebar",
                source=self.bundle,
                db_path=self.db_path,
                mode="context-pack",
                use_repomix=True,
            )
            self.assertTrue(fallback["ok"])
            self.assertTrue(fallback["repomix"]["requested"])
            self.assertFalse(fallback["repomix"]["used"])
            self.assertEqual(fallback["repomix"]["reason"], "repomix_unavailable")
            self.assertGreaterEqual(fallback["usage"]["files"], 1)

        # If repomix is available locally, verify optional --use-repomix succeeds cleanly
        if selective_context._find_repomix_command() is not None:
            with_rmx = selective_context.run_pipeline(
                "sidebar",
                source=self.bundle,
                db_path=self.db_path,
                mode="context-pack",
                use_repomix=True,
                repomix_compress=True,
            )
            self.assertTrue(with_rmx["ok"])
            self.assertTrue(with_rmx["repomix"]["used"])
            self.assertTrue(
                any(i.get("compaction") == "repomix-tree-sitter" for i in with_rmx["items"])
            )

    def test_benchmark_and_cli_and_zero_emoji_policy(self):
        bench = selective_context.run_benchmark(include_repomix=False)
        self.assertTrue(bench["ok"])
        self.assertGreater(bench["comparisons"]["dedup_vs_no_dedup_savings_pct"], 50.0)
        self.assertGreater(bench["comparisons"]["snippet_vs_no_dedup_savings_pct"], 70.0)

        cli = SCRIPTS_DIR / "selective_context.py"
        proc = subprocess.run(
            [
                sys.executable,
                str(cli),
                "export",
                "sidebar",
                "--source",
                str(self.bundle),
                "--db",
                str(self.db_path),
                "--mode",
                "context-pack",
                "--max-tokens",
                "2000",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        parsed = json.loads(proc.stdout)
        self.assertTrue(parsed["ok"])
        self.assertLessEqual(parsed["usage"]["total_estimated_tokens"], 2000)

        # Zero Emoji Policy across script, benchmark doc, and tests
        for target in (
            cli,
            ROOT / "docs" / "SELECTIVE-CONTEXT-BENCHMARK.md",
            Path(__file__),
        ):
            self.assertTrue(target.is_file(), f"Missing deliverable {target}")
            content = target.read_text(encoding="utf-8")
            self.assertEqual(
                EMOJI_REGEX.findall(content), [], f"Unexpected emoji in {target}"
            )


if __name__ == "__main__":
    unittest.main()
