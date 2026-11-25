import importlib.util
import sqlite3
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("research_index", Path(__file__).resolve().parents[1] / "scripts/research_index.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ResearchIndexTests(unittest.TestCase):
    def test_all_catalogs(self):
        records = mod.load_records()
        c = mod.coverage(records)
        self.assertEqual(c["catalogs"]["general"], 47)
        self.assertEqual(c["catalogs"]["workspace"], 35)
        self.assertGreaterEqual(c["catalogs"]["visual"], 36)
        self.assertEqual(len({r["id"] for r in records}), len(records))
        self.assertTrue(all(r["catalog_sha256"] for r in records))
    def test_queries(self):
        with sqlite3.connect(":memory:") as db:
            mod.build(db, mod.load_records())
            for q in ["side panel", "wall", "shared layout", "kanban", "vídeo"]:
                self.assertTrue(mod.search(db, q), q)
            self.assertTrue(mod.search(db, "sidebar", "pattern"))
            self.assertFalse(mod.search(db, "zzzz-unfindable"))
            self.assertTrue(all(r["kind"] == "visual" for r in mod.search(db, "video","visual")))
