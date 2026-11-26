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
        self.assertGreaterEqual(c["catalogs"]["general"], 47)
        self.assertTrue(any(r["record_id"] == "liquid-glass" for r in records))
        self.assertTrue(any(r["record_id"] == "claude-data-refresh" for r in records))
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

    def test_incremental_reconciliation(self):
        def row(ident, title):
            return {"id": ident, "kind": "pattern", "catalog": "fixture",
                    "title": title, "catalog_sha256": "fixture"}
        a, b = row("a", "oldword"), row("b", "stableword")
        with sqlite3.connect(":memory:") as db:
            self.assertEqual(mod.build(db, [a, b]),
                             {"added": 2, "updated": 0, "removed": 0, "unchanged": 0})
            original = db.execute("SELECT rowid FROM research_fts WHERE id='b'").fetchone()
            self.assertEqual(mod.build(db, [a, b]),
                             {"added": 0, "updated": 0, "removed": 0, "unchanged": 2})
            self.assertEqual(mod.build(db, [row("a", "newword"), b, row("c", "extra")]),
                             {"added": 1, "updated": 1, "removed": 0, "unchanged": 1})
            self.assertFalse(mod.search(db, "oldword"))
            self.assertEqual(mod.search(db, "newword")[0]["id"], "a")
            self.assertEqual(db.execute("SELECT rowid FROM research_fts WHERE id='b'").fetchone(), original)
            self.assertEqual(mod.build(db, [b])["removed"], 2)
            self.assertFalse(mod.search(db, "newword"))
            self.assertEqual(db.execute("SELECT count(*) FROM research_fts").fetchone()[0], 1)
            with self.assertRaises(ValueError):
                mod.build(db, [b, b])
            self.assertEqual(db.execute("SELECT count(*) FROM research").fetchone()[0], 1)

    def test_filters_graph_and_audit(self):
        records = mod.load_records()
        graph = mod.provenance_graph(records)
        ids = {n["id"] for n in graph["nodes"]}
        self.assertTrue(all(e["source"] in ids and e["target"] in ids for e in graph["edges"]))
        self.assertEqual(len(graph["edges"]), sum(len(set(r["sources"])) for r in records))
        self.assertTrue(all(r["record_sha256"] for r in records))
        with sqlite3.connect(":memory:") as db:
            mod.build(db, records)
            self.assertFalse(mod.search(db, "sidebar", product="nonexistent-product"))
            self.assertTrue(mod.search(db, "sortable", product="dnd-kit", availability="archived-blob-verified"))
            self.assertFalse(mod.search(db, "sortable", product="dnd-kit", availability="link-only"))
        a = mod.audit(records)
        self.assertEqual(sum(r["records"] for r in a["visual_matrix"]), sum(r["kind"] == "visual" for r in records))
        self.assertEqual(a["graph"]["edges"], len(graph["edges"]))

    def test_domain_research_and_coverage_gaps(self):
        records = mod.load_records()
        domain = [r for r in records if r["catalog"] == "domain-research"]
        self.assertEqual({r["record"]["issue"] for r in domain}, set(range(95,102)) | {104,105})
        self.assertTrue(all(r["sources"] for r in domain))
        with sqlite3.connect(":memory:") as db:
            mod.build(db, records)
            self.assertTrue(any(r["catalog"] == "domain-research" for r in mod.search(db, "TextQuoteSelector")))
        fixture = [{"id":"source:x","kind":"source","sources":["https://example.org/x"],"record":{}},
                   {"id":"pattern:y","kind":"pattern","sources":["https://example.org/x"]}]
        self.assertEqual(mod.coverage_gaps(fixture)["source_urls_without_non_source_reference"], [])
        self.assertEqual(mod.coverage_gaps(fixture[:1])["source_urls_without_non_source_reference"], ["https://example.org/x"])

    def test_supplemental_public_catalogs(self):
        rows = mod.load_records()
        by_id = {r["id"]:r for r in rows}
        for namespace,filename,key,domain in mod.SUPPLEMENTAL_CATALOGS:
            members = [r for r in rows if r["catalog"]==namespace]
            self.assertTrue(members,namespace)
            self.assertTrue(all(r["availability"]=="cataloged-synthesis" for r in members))
            self.assertTrue(all(r["record"]["domain"]==domain for r in members))
            self.assertTrue(any(r["catalog"]==namespace+"-sources" for r in rows))
        self.assertEqual(by_id["async-ux:non-blocking-interaction"]["title"],"Non-blocking Interaction")
        self.assertTrue(by_id["ai-product-views:claude-artifact-lifecycle"]["sources"])
        self.assertEqual(by_id["ai-product-views:claude-artifact-lifecycle"]["product"],"Claude")
        with sqlite3.connect(":memory:") as db:
            mod.build(db,rows)
            self.assertTrue(any(r["catalog"]=="space-views" for r in mod.search(db,"organizational contexts",limit=100)))
            self.assertTrue(any(r["catalog"]=="ai-product-views" for r in mod.search(db,"artifact lifecycle",product="Claude",limit=100)))

    def test_product_graph_retrieval(self):
        rows = mod.load_records()
        graph_rows = [r for r in rows if r["catalog"] == "ai-product-graph"]
        self.assertTrue(graph_rows)
        self.assertFalse(any("candidate" in r["record"]["type"] for r in graph_rows))
        self.assertTrue(all(r["product"] for r in graph_rows))
        by_id = {r["id"]: r for r in graph_rows}
        todo = by_id["ai-product-graph:evidence:chatgpt-space:todos"]
        self.assertEqual(todo["availability"], "link-only")
        self.assertIn("not verified", todo["license"])
        with sqlite3.connect(":memory:") as db:
            mod.build(db, rows)
            self.assertTrue(any(r["id"] == todo["id"] for r in mod.search(db, "task list", "visual", product="ChatGPT Space", limit=100)))
            self.assertTrue(mod.search(db, "flashcard review", "flow", product="Gemini Notebook (formerly NotebookLM)", limit=100))
            self.assertTrue(mod.search(db, "canvas debugging", "flow", product="Gemini", limit=100))
