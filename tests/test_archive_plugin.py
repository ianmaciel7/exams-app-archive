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

    def test_kind_all_quota_across_types(self):
        conn = sqlite3.connect(self.db)
        for idx in range(15):
            sha = f"{idx + 1:040x}"
            conn.execute("INSERT INTO commits VALUES(1,?,?,?)",
                         (sha, f"2026-02-{idx + 1:02d}", f"sidebar update {idx}"))
            conn.execute("INSERT INTO commit_fts VALUES(?,?,?)",
                         (f"sidebar update {idx}", "1", sha))
            fpath = f"src/sidebar_{idx}.tsx"
            conn.execute("INSERT INTO changes VALUES(1,?,'M',?,'')", (sha, fpath))
            conn.execute("INSERT INTO change_fts VALUES(?,'1',?,'M')", (fpath, sha))
            conn.execute("INSERT INTO images VALUES(1,?,?,?,?,?)",
                         (f"assets/sidebar_{idx}.png", f"blob{idx:036x}", sha, "branch-head", 100 + idx))
        conn.commit()
        conn.close()

        p, rows = self.cmd("search", "sidebar", "--limit", "10")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len(rows), 10)
        counts = {}
        for r in rows:
            counts[r["kind"]] = counts.get(r["kind"], 0) + 1
        self.assertGreaterEqual(counts.get("commit", 0), 3)
        self.assertGreaterEqual(counts.get("file", 0), 3)
        self.assertGreaterEqual(counts.get("image", 0), 3)

    def test_file_and_image_deduplication(self):
        conn = sqlite3.connect(self.db)
        shas = [f"1{i:039x}" for i in range(12)]
        for i, sha in enumerate(shas):
            conn.execute("INSERT INTO commits VALUES(1,?,?,?)",
                         (sha, f"2026-03-{i + 1:02d}", f"touch sidebar {i}"))
            conn.execute("INSERT INTO changes VALUES(1,?,'M','src/components/ui/sidebar.tsx','')", (sha,))
            conn.execute("INSERT INTO change_fts VALUES('src/components/ui/sidebar.tsx','1',?,'M')", (sha,))
        conn.execute("INSERT INTO changes VALUES(1,?,'A','src/domain/sidebar.ts','')", (shas[0],))
        conn.execute("INSERT INTO change_fts VALUES('src/domain/sidebar.ts','1',?,'A')", (shas[0],))

        # Same image blob across multiple paths/states should deduplicate by blob
        same_blob = "deadbeef" * 5
        conn.execute("INSERT INTO images VALUES(1,'prototype/sidebar_shot.png',?,?,?,?)",
                     (same_blob, shas[0], "branch-head", 500))
        conn.execute("INSERT INTO images VALUES(1,'prototypes/sidebar_shot.png',?,?,?,?)",
                     (same_blob, shas[1], "deleted", 500))
        conn.commit()
        conn.close()

        p, files = self.cmd("search", "sidebar", "--kind", "file", "--limit", "20")
        self.assertEqual(p.returncode, 0, p.stderr)
        paths = [(r["repository"], r["path"]) for r in files]
        self.assertEqual(len(paths), len(set(paths)))
        ui_sidebar = next(r for r in files if r["path"] == "src/components/ui/sidebar.tsx")
        self.assertEqual(ui_sidebar["commits"], 12)
        self.assertEqual(ui_sidebar["first_sha"], shas[0])
        self.assertEqual(ui_sidebar["last_sha"], shas[-1])

        p, imgs = self.cmd("search", "sidebar", "--kind", "image", "--limit", "20")
        self.assertEqual(p.returncode, 0, p.stderr)
        blobs = [r["blob"] for r in imgs]
        self.assertEqual(blobs.count(same_blob), 1)
        self.assertEqual(imgs[0]["occurrences"], 2)
        self.assertEqual(imgs[0]["deleted"], 1)

    def test_bm25_ranking_and_and_or_fallback(self):
        conn = sqlite3.connect(self.db)
        s_exact = "2" * 40
        s_both = "3" * 40
        s_one = "4" * 40
        conn.execute("INSERT INTO commits VALUES(1,?,'2026-04-01','sidebar panel layout')", (s_exact,))
        conn.execute("INSERT INTO commit_fts VALUES('sidebar panel layout','1',?)", (s_exact,))
        conn.execute("INSERT INTO commits VALUES(1,?,'2026-04-02','panel inside sidebar with extra noise words here')", (s_both,))
        conn.execute("INSERT INTO commit_fts VALUES('panel inside sidebar with extra noise words here','1',?)", (s_both,))
        conn.execute("INSERT INTO commits VALUES(1,?,'2026-04-03','sidebar only change')", (s_one,))
        conn.execute("INSERT INTO commit_fts VALUES('sidebar only change','1',?)", (s_one,))
        conn.commit()
        conn.close()

        # AND/phrase-first excludes single-token match when multi-token match exists
        p, rows = self.cmd("search", "sidebar panel", "--kind", "commit", "--limit", "10")
        self.assertEqual(p.returncode, 0, p.stderr)
        shas = [r["sha"] for r in rows]
        self.assertEqual(shas, [s_exact, s_both])

        # Falls back to OR when no document contains all tokens
        p, fallback = self.cmd("search", "sidebar nonexistenttoken", "--kind", "commit", "--limit", "10")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len(fallback), 3)

    def test_backwards_compatible_columns_and_stable_order(self):
        required_keys = {"repository", "kind", "sha", "path", "summary", "blob", "bytes", "deleted"}
        p1, rows1 = self.cmd("search", "grafo", "--limit", "10")
        p2, rows2 = self.cmd("search", "grafo", "--limit", "10")
        self.assertEqual(p1.returncode, 0)
        self.assertEqual(rows1, rows2)
        for row in rows1:
            self.assertTrue(required_keys.issubset(row.keys()))

    def test_high_frequency_file_not_truncated_and_cli_compat(self):
        conn = sqlite3.connect(self.db)
        # More than 250 changes for one file must not hide other files or miscount commits
        for i in range(260):
            sha = f"a{i:039x}"
            conn.execute("INSERT INTO commits VALUES(1,?,?,?)",
                         (sha, f"2026-05-01T{i // 60:02d}:{i % 60:02d}:00Z", f"noise {i}"))
            conn.execute("INSERT INTO change_fts VALUES('src/heavy/sidebar_heavy.tsx','1',?,'M')", (sha,))
        conn.execute("INSERT INTO commits VALUES(1,?,'2026-05-02T00:00:00Z','exact')", ("b" * 40,))
        conn.execute("INSERT INTO change_fts VALUES('sidebar_exact.tsx','1',?,'A')", ("b" * 40,))
        conn.commit()
        conn.close()

        p, files = self.cmd("search", "sidebar", "--kind", "file", "--limit", "5")
        self.assertEqual(p.returncode, 0, p.stderr)
        by_path = {r["path"]: r for r in files}
        self.assertIn("src/heavy/sidebar_heavy.tsx", by_path)
        self.assertIn("sidebar_exact.tsx", by_path)
        self.assertEqual(by_path["src/heavy/sidebar_heavy.tsx"]["commits"], 260)
        self.assertEqual(by_path["src/heavy/sidebar_heavy.tsx"]["first_sha"], f"a{0:039x}")
        self.assertEqual(by_path["src/heavy/sidebar_heavy.tsx"]["last_sha"], f"a{259:039x}")

        # CLI accepts search without --kind or --repo (backwards compatibility)
        p_legacy, legacy_rows = self.cmd("search", "sidebar")
        self.assertEqual(p_legacy.returncode, 0, p_legacy.stderr)
        self.assertTrue(len(legacy_rows) > 0)


if __name__ == "__main__":
    unittest.main()
