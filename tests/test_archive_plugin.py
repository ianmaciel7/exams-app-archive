#!/usr/bin/env python3
"""Black-box tests of the portable archive CLI (no network or credentials)."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "plugins/exams-archive/scripts/archive_query.py"


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "tiny.sqlite"
        conn = sqlite3.connect(self.db)
        conn.executescript("""
          CREATE TABLE repositories(id INTEGER PRIMARY KEY,name TEXT);
          CREATE TABLE commits(repo_id INTEGER,sha TEXT,date TEXT,subject TEXT);
          CREATE TABLE changes(repo_id INTEGER,sha TEXT,status TEXT,path TEXT,previous_path TEXT);
          CREATE TABLE images(repo_id INTEGER,path TEXT,blob TEXT,commit_sha TEXT,kind TEXT,bytes INTEGER);
          CREATE VIRTUAL TABLE commit_fts USING fts5(subject,repo_id UNINDEXED,sha UNINDEXED);
          CREATE VIRTUAL TABLE change_fts USING fts5(path,repo_id UNINDEXED,sha UNINDEXED,status UNINDEXED);
          INSERT INTO repositories VALUES(1,'exams-app-antigo-2');
          INSERT INTO commits VALUES(1,'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','2026-01-01','Grafo antigo');
          INSERT INTO commit_fts VALUES('Grafo antigo','1','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
          INSERT INTO changes VALUES(1,'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','A','prototypes/grafo.png','');
          INSERT INTO change_fts VALUES('prototypes/grafo.png','1','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','A');
          INSERT INTO images VALUES(1,'prototypes/grafo.png','bbbb','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','deleted',42);
        """)
        conn.commit()
        conn.close()

    def cmd(self, *args):
        p = subprocess.run([sys.executable, str(CLI), "--db", str(self.db), *args],
                           text=True, capture_output=True)
        return p, json.loads(p.stdout) if p.returncode == 0 else None

    def test_search_with_provenance(self):
        p, rows = self.cmd("search", "grafo", "--limit", "20")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual({r["kind"] for r in rows}, {"commit", "file", "image"})
        self.assertTrue(all(r["repository"] == "exams-app-antigo-2" for r in rows))
        self.assertTrue(all(len(r["sha"]) == 40 for r in rows))

    def test_filter_and_deleted_images(self):
        p, rows = self.cmd("images", "--deleted-only", "--repo", "exams-app-antigo-2")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bytes"], 42)
        p, rows = self.cmd("search", "grafo", "--kind", "image", "--repo", "unknown")
        self.assertEqual(rows, [])

    def test_export_private_browser_dataset(self):
        target = Path(self.temp.name) / "private.archive-browser.json"
        p, result = self.cmd("export-pages", "--output", str(target))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(result["records"], 3)
        doc = json.loads(target.read_text())
        self.assertEqual(doc["version"], 1)
        self.assertEqual(len(doc["records"]), 3)
        self.assertTrue(result["private"])
        repeat, _ = self.cmd("export-pages", "--output", str(target))
        self.assertNotEqual(repeat.returncode, 0)
        self.assertEqual(len(json.loads(target.read_text())["records"]), 3)

    def test_existing_recovered_file_is_never_deleted(self):
        bare = Path(self.temp.name) / "bare"
        bare.mkdir()
        (bare / "HEAD").write_text("ref: refs/heads/main\n")
        existing = Path(self.temp.name) / "keep.txt"
        existing.write_text("DO NOT DELETE")
        p, _ = self.cmd("recover", "--git-dir", str(bare), "--sha", "a"*40,
                        "--path", "readme.md", "--output", str(existing))
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(existing.read_text(), "DO NOT DELETE")

    def test_no_unsafe_recovery_paths(self):
        p, _ = self.cmd("recover", "--git-dir", self.temp.name, "--sha", "a"*40,
                        "--path", "../secret", "--output", str(Path(self.temp.name)/"leak"))
        self.assertNotEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
