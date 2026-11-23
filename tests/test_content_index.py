#!/usr/bin/env python3
"""Tests for scripts/content_index.py using temporary synthetic Git repositories and bundles."""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from content_index import (  # noqa: E402
    chunk_text,
    ingest_repo,
    open_db,
    recover_lines,
    search,
    stats,
)


def run(*cmd: str, cwd: Path | None = None) -> bytes:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


class ContentIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.work = self.root / "work"
        self.work.mkdir()
        run("git", "init", "-q", "-b", "main", str(self.work))
        run("git", "config", "user.email", "archive@example.invalid", cwd=self.work)
        run("git", "config", "user.name", "Archive Test", cwd=self.work)

        # Build a multi-line TypeScript file so chunking & line numbers are exercised.
        sidebar_lines = [f"// header comment line {i}" for i in range(1, 35)]
        sidebar_lines.extend(
            [
                "export function LegacySidebarNavigation() {",
                '  return { panel: "capacities-sidebar", mode: "docked" };',
                "}",
            ]
        )
        (self.work / "src").mkdir()
        (self.work / "src" / "sidebar.ts").write_text("\n".join(sidebar_lines) + "\n", encoding="utf-8")

        # Shared utility file to verify blob deduplication across branches/repos.
        shared_py = "def compute_fsrs_stability(days: float) -> float:\n    return days * 1.45\n"
        (self.work / "src" / "fsrs.py").write_text(shared_py, encoding="utf-8")

        # Deleted file in history (later removed on main).
        (self.work / "src" / "legacy_graph.ts").write_text(
            "export const LEGACY_GRAPH_MARKER = 'graph-node-physics-v1';\n",
            encoding="utf-8",
        )

        # Binary disguised with .ts extension (contains NUL bytes).
        (self.work / "src" / "fake_binary.ts").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00IHDRbinary_marker")

        # Oversized file (> max_file_bytes tested below, and default check).
        (self.work / "src" / "huge.txt").write_text("oversized_token\n" * 200, encoding="utf-8")

        # Secret files by path and by inline token pattern (synthetic test values).
        (self.work / ".env").write_text("DATABASE_URL=postgres://user:supersecretpass@db.local:5432/app\n", encoding="utf-8")
        (self.work / ".env.production").write_text("STRIPE_SECRET=sk_test_syntheticvalue1234567890\n", encoding="utf-8")
        (self.work / "serviceAccountKey.json").write_text('{"private_key": "synthetic-key-file"}\n', encoding="utf-8")
        (self.work / "src" / "leaked_config.ts").write_text(
            'export const GH_FAKE = "ghp_syntheticTestTokenValue1234567890123456";\n',
            encoding="utf-8",
        )
        (self.work / "src" / "pem_holder.py").write_text(
            'KEY = "-----BEGIN RSA PRIVATE KEY-----\\nMIIEpAIBAAKCAQEA"\n',
            encoding="utf-8",
        )

        run("git", "add", ".", cwd=self.work)
        run("git", "commit", "-qm", "feat: initial synthetic codebase", cwd=self.work)
        self.initial_sha = run("git", "rev-parse", "HEAD", cwd=self.work).decode().strip()

        # Feature branch keeping identical fsrs.py blob + adding markdown doc.
        run("git", "checkout", "-qb", "feature/notes", cwd=self.work)
        (self.work / "docs").mkdir()
        (self.work / "docs" / "architecture.md").write_text(
            "# Architecture\n\nRecall uses `qconcursos_importer` pipeline.\n",
            encoding="utf-8",
        )
        run("git", "add", ".", cwd=self.work)
        run("git", "commit", "-qm", "docs: add architecture notes", cwd=self.work)
        self.branch_sha = run("git", "rev-parse", "HEAD", cwd=self.work).decode().strip()

        # Back to main: delete legacy_graph.ts so it only lives in commit history.
        run("git", "checkout", "-q", "main", cwd=self.work)
        (self.work / "src" / "legacy_graph.ts").unlink()
        run("git", "add", "-u", cwd=self.work)
        run("git", "commit", "-qm", "chore: remove legacy graph module", cwd=self.work)
        self.main_sha = run("git", "rev-parse", "HEAD", cwd=self.work).decode().strip()

        self.bare = self.root / "repo.git"
        run("git", "clone", "--mirror", "-q", str(self.work), str(self.bare))

        self.bundle = self.root / "repo.bundle"
        run("git", "bundle", "create", str(self.bundle), "--all", cwd=self.bare)

        self.db_path = self.root / "content-index.sqlite"
        self.conn = open_db(self.db_path)
        self.addCleanup(self.conn.close)

    def test_deterministic_chunking(self):
        text = "\n".join(f"line-{i}" for i in range(1, 95)) + "\n"
        c1 = chunk_text(text, chunk_lines=30, overlap_lines=5, max_chunk_chars=2000)
        c2 = chunk_text(text, chunk_lines=30, overlap_lines=5, max_chunk_chars=2000)
        self.assertEqual(c1, c2)
        self.assertEqual(c1[0][0], 1)
        self.assertEqual(c1[0][1], 30)
        # Overlap of 5 lines -> second chunk starts at line 26.
        self.assertEqual(c1[1][0], 26)
        self.assertEqual(c1[-1][1], 94)

    def test_search_precision_provenance_and_filters(self):
        info = ingest_repo(self.bare, "exams-app", self.conn, max_file_bytes=2048)
        self.assertGreater(info["new_blobs_indexed"], 0)
        self.assertGreater(info["skipped_binary"], 0)
        self.assertGreater(info["skipped_size"], 0)

        hits = search(self.conn, "LegacySidebarNavigation", repo="exams-app", branch="main", extension=".ts")
        self.assertGreaterEqual(len(hits), 1)
        hit = hits[0]
        self.assertEqual(hit["repository"], "exams-app")
        self.assertEqual(hit["ref"], "refs/heads/main")
        self.assertEqual(hit["commit_sha"], self.main_sha)
        self.assertEqual(hit["path"], "src/sidebar.ts")
        self.assertEqual(hit["language"], "typescript")
        self.assertIn("LegacySidebarNavigation", hit["snippet"])
        self.assertGreaterEqual(hit["start_line"], 30)
        self.assertLessEqual(hit["end_line"], 40)

        # Provenance verification: SHA + path + line range reproduces exact snippet.
        recovered = recover_lines(
            self.bare,
            hit["commit_sha"],
            hit["path"],
            start_line=hit["start_line"],
            end_line=hit["end_line"],
        )
        self.assertEqual(recovered["content"], hit["snippet"])

        # Branch filter isolates markdown file on feature/notes.
        md_main = search(self.conn, "qconcursos_importer", branch="main")
        self.assertEqual(md_main, [])
        md_feat = search(self.conn, "qconcursos_importer", branch="feature/notes", extension="md")
        self.assertEqual(len(md_feat), 1)
        self.assertEqual(md_feat[0]["commit_sha"], self.branch_sha)
        self.assertEqual(md_feat[0]["path"], "docs/architecture.md")

    def test_removed_file_history_and_provenance(self):
        ingest_repo(self.bare, "exams-app", self.conn, max_file_bytes=2048)
        # Deleted from main, still present on feature/notes.
        deleted_hits = search(self.conn, "LEGACY_GRAPH_MARKER", status="deleted")
        self.assertEqual(len(deleted_hits), 1)
        hit = deleted_hits[0]
        self.assertEqual(hit["status"], "deleted")
        self.assertEqual(hit["commit_sha"], self.initial_sha)
        self.assertEqual(hit["path"], "src/legacy_graph.ts")

        recovered = recover_lines(self.bare, hit["commit_sha"], hit["path"], hit["start_line"], hit["end_line"])
        self.assertIn("LEGACY_GRAPH_MARKER", recovered["content"])

    def test_blob_deduplication_across_branches_and_repos(self):
        ingest_repo(self.bare, "repo-a", self.conn, max_file_bytes=2048)
        summary_a = stats(self.conn)
        blob_count_after_a = summary_a["unique_blobs"]

        # fsrs.py exists on both main and feature/notes with same blob_sha.
        occ_fsrs = self.conn.execute(
            "SELECT COUNT(DISTINCT blob_sha), COUNT(*) FROM content_occurrences WHERE repo='repo-a' AND path='src/fsrs.py'"
        ).fetchone()
        self.assertEqual(occ_fsrs[0], 1)
        self.assertEqual(occ_fsrs[1], 2)

        # Re-ingesting identical bundle under a second repository name reuses existing blobs.
        info_b = ingest_repo(self.bundle, "repo-b", self.conn, max_file_bytes=2048)
        self.assertEqual(info_b["new_blobs_indexed"], 0)
        self.assertEqual(info_b["new_chunks_indexed"], 0)
        self.assertGreater(info_b["deduped_blob_hits"], 0)
        self.assertEqual(stats(self.conn)["unique_blobs"], blob_count_after_a)

        # Search still returns both repositories with their respective provenance.
        hits = search(self.conn, "compute_fsrs_stability", branch="main")
        self.assertEqual({h["repository"] for h in hits}, {"repo-a", "repo-b"})

    def test_secret_and_binary_exclusion(self):
        info = ingest_repo(self.bundle, "exams-bundle", self.conn, max_file_bytes=2048)
        self.assertGreaterEqual(info["skipped_secret_path"], 3)
        self.assertGreaterEqual(info["skipped_secret_content"], 2)
        self.assertGreaterEqual(info["skipped_binary"], 1)

        for secret_query in (
            "supersecretpass",
            "sk_test_syntheticvalue1234567890",
            "synthetic-key-file",
            "ghp_syntheticTestTokenValue1234567890123456",
            "MIIEpAIBAAKCAQEA",
            "binary_marker",
            "oversized_token",
        ):
            self.assertEqual(search(self.conn, secret_query), [], msg=f"Unexpected hit for {secret_query}")

        indexed_paths = {
            row[0]
            for row in self.conn.execute("SELECT path FROM content_occurrences WHERE repo='exams-bundle'")
        }
        self.assertNotIn(".env", indexed_paths)
        self.assertNotIn(".env.production", indexed_paths)
        self.assertNotIn("serviceAccountKey.json", indexed_paths)
        self.assertNotIn("src/leaked_config.ts", indexed_paths)
        self.assertNotIn("src/pem_holder.py", indexed_paths)
        self.assertNotIn("src/fake_binary.ts", indexed_paths)
        self.assertNotIn("src/huge.txt", indexed_paths)

    def test_cli_end_to_end_with_bundle(self):
        cli = Path(__file__).resolve().parents[1] / "scripts" / "content_index.py"
        ingest_out = run(
            sys.executable,
            str(cli),
            "--db",
            str(self.db_path),
            "ingest",
            "--repo",
            str(self.bundle),
            "--name",
            "bundle-repo",
            "--max-bytes",
            "2048",
        )
        parsed = json.loads(ingest_out.decode())
        self.assertEqual(parsed["repository"], "bundle-repo")

        search_out = run(
            sys.executable,
            str(cli),
            "--db",
            str(self.db_path),
            "search",
            "capacities",
            "--repo",
            "bundle-repo",
            "--branch",
            "main",
            "--ext",
            ".ts",
        )
        results = json.loads(search_out.decode())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["path"], "src/sidebar.ts")
        self.assertEqual(results[0]["ref"], "refs/heads/main")


if __name__ == "__main__":
    unittest.main()
