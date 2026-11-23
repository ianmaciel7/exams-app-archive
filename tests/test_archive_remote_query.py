#!/usr/bin/env python3
"""Test GitHub-based private FTS5 request bridge using synthetic data."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/archive_remote_query.py"


class RemoteQueryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.requests = self.dir / "requests"
        self.results = self.dir / "results"
        self.requests.mkdir()
        self.db = self.dir / "index.sqlite"
        with sqlite3.connect(self.db) as c:
            c.executescript("""
            CREATE TABLE repositories(id INTEGER PRIMARY KEY,name TEXT);
            CREATE TABLE commits(repo_id INTEGER,sha TEXT,date TEXT,subject TEXT);
            CREATE TABLE changes(repo_id INTEGER,sha TEXT,status TEXT,path TEXT,previous_path TEXT);
            CREATE TABLE images(repo_id INTEGER,path TEXT,blob TEXT,commit_sha TEXT,kind TEXT,bytes INTEGER);
            CREATE VIRTUAL TABLE commit_fts USING fts5(subject,repo_id UNINDEXED,sha UNINDEXED);
            CREATE VIRTUAL TABLE change_fts USING fts5(path,repo_id UNINDEXED,sha UNINDEXED,status UNINDEXED);
            INSERT INTO repositories VALUES(1,'exams-app-antigo-2');
            INSERT INTO commits VALUES(1,'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','2026-01-01','Grafo antigo');
            INSERT INTO commit_fts VALUES('Grafo antigo','1','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
            INSERT INTO changes VALUES(1,'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','D','docs/grafo.png','');
            INSERT INTO change_fts VALUES('docs/grafo.png','1','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','D');
            INSERT INTO images VALUES(1,'docs/grafo.png','bbbb','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','deleted',42);
            """)

    def write_request(self, identifier="test-grafo-01", **changes):
        obj = {"version": 1, "id": identifier, "operation": "search", "query": "grafo"}
        obj.update(changes)
        path = self.requests / (identifier + ".json")
        path.write_text(json.dumps(obj))
        return path

    def execute(self):
        return subprocess.run([sys.executable, str(RUNNER), "--root", str(ROOT),
            "--requests", str(self.requests), "--results", str(self.results),
            "--db", str(self.db), "--offline"], capture_output=True, text=True)

    def test_search_and_idempotent_result(self):
        self.write_request()
        first = self.execute()
        self.assertEqual(first.returncode, 0, first.stderr)
        obj = json.loads((self.results / "test-grafo-01.json").read_text())
        self.assertTrue(obj["ok"], obj)
        self.assertEqual({r["kind"] for r in obj["results"]}, {"commit", "file", "image"})
        self.assertTrue(all(r["sha"] == "a"*40 for r in obj["results"]))
        self.assertEqual(obj["index_release"], "offline-test")
        again = self.execute()
        self.assertEqual(json.loads(again.stdout)["processed"], 0)

    def test_deleted_images(self):
        self.write_request(identifier="test-images-01", operation="images",
                           repo="exams-app-antigo-2", deleted_only=True, query=None)
        path = self.requests / "test-images-01.json"
        obj = json.loads(path.read_text())
        del obj["query"]
        path.write_text(json.dumps(obj))
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-images-01.json").read_text())
        self.assertTrue(doc["ok"], doc)
        self.assertEqual(doc["results"][0]["path"], "docs/grafo.png")

    def test_bad_data_yields_error_not_crash(self):
        self.write_request(identifier="test-invalid-01", query="a"*150)
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-invalid-01.json").read_text())
        self.assertFalse(doc["ok"])
        self.assertIn("120", doc["error"])

    def test_pending_batch_status_and_retention_pruning(self):
        self.write_request(identifier="test-batch-01")
        self.write_request(identifier="test-batch-02")
        self.write_request(identifier="test-batch-03")
        p1 = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--root",
                str(ROOT),
                "--requests",
                str(self.requests),
                "--results",
                str(self.results),
                "--db",
                str(self.db),
                "--offline",
                "--batch-limit",
                "2",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(p1.returncode, 0, p1.stderr)
        meta1 = json.loads(p1.stdout)
        self.assertEqual(meta1["processed"], 2)
        self.assertEqual(meta1["pending_remaining"], 1)
        self.assertEqual(meta1["status"], "pending")

        p2 = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--root",
                str(ROOT),
                "--requests",
                str(self.requests),
                "--results",
                str(self.results),
                "--db",
                str(self.db),
                "--offline",
                "--batch-limit",
                "2",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(p2.returncode, 0, p2.stderr)
        meta2 = json.loads(p2.stdout)
        self.assertEqual(meta2["processed"], 1)
        self.assertEqual(meta2["pending_remaining"], 0)
        self.assertEqual(meta2["status"], "complete")

        # Mark test-batch-01 pair older than 14 days and prune
        import os
        import time
        old_ts = time.time() - (20 * 86400)
        for p in (self.requests / "test-batch-01.json", self.results / "test-batch-01.json"):
            os.utime(p, (old_ts, old_ts))
        p3 = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--root",
                str(ROOT),
                "--requests",
                str(self.requests),
                "--results",
                str(self.results),
                "--db",
                str(self.db),
                "--offline",
                "--retention-days",
                "14",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(p3.returncode, 0, p3.stderr)
        meta3 = json.loads(p3.stdout)
        self.assertEqual(meta3["pruned"], 1)
        self.assertFalse((self.requests / "test-batch-01.json").exists())
        self.assertFalse((self.results / "test-batch-01.json").exists())
        self.assertTrue((self.requests / "test-batch-02.json").exists())


if __name__ == "__main__":
    unittest.main()
