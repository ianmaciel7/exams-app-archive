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
    def test_clickup_projection(self):
        records = mod.load_records()
        projected = [r for r in records if r["catalog"] == "clickup"]
        self.assertGreaterEqual(len(projected), 92)
        self.assertTrue(all(r["kind"] == "pattern" and r["product"] == "ClickUp"
                            and r["sources"] and r["record"]["origin"]
                            for r in projected))
        self.assertTrue(all("runtime" in r["confidence"].lower()
                            or r["confidence"] for r in projected))
        self.assertTrue(mod.verify_record_provenance(projected)["integrity_passed"])
        with sqlite3.connect(":memory:") as db:
            mod.build(db, records)
            for query, ident in (("sidebar", None), ("filter draft", "clickup-dashboard-filter-draft"),
                                 ("status template", "clickup-status-template-fork"),
                                 ("archive", "clickup-archive-not-delete")):
                matches = mod.search(db, query, "pattern", product="ClickUp", limit=100)
                self.assertTrue(matches, query)
                if ident:
                    self.assertTrue(any(r["record_id"] == ident for r in matches), query)
            self.assertTrue(mod.search(db, "ClickUp", "source", product="ClickUp", limit=100))

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

    def test_index_membership_detects_and_repairs_drift(self):
        records = [{"id": i, "kind": "pattern", "catalog": "fixture", "title": title}
                   for i, title in (("a", "alpha"), ("b", "beta"), ("c", "gamma"))]
        with sqlite3.connect(":memory:") as db:
            mod.build(db, records)
            self.assertEqual(mod.index_membership(db, records)["membership_percent"], 100)
            db.execute("DELETE FROM research_fts WHERE id='a'")
            db.execute("INSERT INTO research_fts SELECT id,title,body FROM research_fts WHERE id='b'")
            db.execute("UPDATE research SET kind='wrong' WHERE id='c'")
            db.execute("INSERT INTO research_fts VALUES ('orphan','orphan','orphan')")
            failed = mod.index_membership(db, records)
            self.assertFalse(failed["integrity_passed"])
            self.assertEqual(failed["matched_records"], 0)
            self.assertEqual(failed["missing_fts_ids"], ["a"])
            self.assertEqual(failed["duplicate_fts_ids"], ["b"])
            self.assertEqual(failed["stale_metadata_ids"], ["c"])
            self.assertEqual(failed["unexpected_fts_ids"], ["orphan"])
            mod.build(db, records)
            repaired = mod.index_membership(db, records)
            self.assertTrue(repaired["integrity_passed"])
            self.assertEqual(repaired["matched_records"], 3)
            self.assertEqual(repaired["by_catalog"]["fixture"], {"eligible": 3, "matched": 3})
            self.assertEqual(mod.search(db, "alpha")[0]["id"], "a")
            self.assertFalse(mod.search(db, "orphan"))
            self.assertEqual(len(mod.search(db, "beta")), 1)

    def test_real_public_catalog_membership(self):
        records = mod.load_records()
        with sqlite3.connect(":memory:") as db:
            mod.build(db, records)
            measured = mod.coverage(records, db)["index_membership"]
            self.assertTrue(measured["integrity_passed"])
            self.assertEqual(measured["matched_records"], len(records))
            self.assertEqual(sum(c["eligible"] for c in measured["by_catalog"].values()), len(records))
            self.assertEqual(measured["membership_percent"], 100)
            print("PUBLIC_CATALOG_MEMBERSHIP", measured["matched_records"], "/", measured["eligible_records"])

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
        # Legacy issue-backed research and explicit domain-backed research
        # are distinct entry routes. Keep the original issue coverage gate.
        self.assertEqual({r["record"]["issue"] for r in domain if "issue" in r["record"]},
                         set(range(95,102)) | {104,105})
        explicit = [r for r in domain if "issue" not in r["record"]]
        self.assertTrue(all(r["record"].get("domain") in {"arquitetura-tecnica", "historico"}
                            for r in explicit))
        expected = {
            "adr-supersession": ("arquitetura-tecnica", "ADR supersession"),
            "idempotent-background-job": ("arquitetura-tecnica", "idempotent background jobs"),
            "local-first-ownership": ("arquitetura-tecnica", "local first data ownership"),
            "git-bundle-restoration": ("historico", "git bundle restoration"),
            "git-pinned-object-evidence": ("historico", "pinned Git object identity"),
            "prov-derived-artifact-lineage": ("historico", "W3C PROV lineage"),
        }
        by_id = {r["record_id"]: r for r in explicit}
        for ident, (area, query) in expected.items():
            with self.subTest(record=ident):
                row = by_id[ident]
                self.assertEqual(row["record"]["domain"], area)
                self.assertTrue(row["record"]["guardrail"])
                self.assertTrue(row["record"]["tests"])
                self.assertTrue(row["sources"])
        self.assertTrue(all(r["sources"] for r in domain))
        with sqlite3.connect(":memory:") as db:
            mod.build(db, records)
            self.assertTrue(any(r["catalog"] == "domain-research" for r in mod.search(db, "TextQuoteSelector")))
            for ident, (_, query) in expected.items():
                with self.subTest(query=query):
                    self.assertTrue(any(r["id"] == by_id[ident]["id"]
                                        for r in mod.search(db, query, "pattern", limit=100)))
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

    def test_product_view_output_direct_provenance(self):
        # Source coverage is distinct from verified runtime behavior.
        rows = mod.load_records()
        product_rows = [r for r in rows if r["catalog"] == "ai-product-graph"
                        and r["kind"] in {"view", "output", "flow", "contract", "availability", "creation-option"}]
        self.assertGreaterEqual(sum(r["kind"] == "view" for r in product_rows), 41)
        self.assertGreaterEqual(sum(r["kind"] == "output" for r in product_rows), 48)
        for row in product_rows:
            with self.subTest(record=row["id"]):
                self.assertTrue(row["sources"])
                self.assertTrue(row["record"]["source_evidence"])
                for index, status in row["record"]["source_evidence"]:
                    self.assertTrue(0 <= index < len(row["sources"]))
                    self.assertTrue(status)
                self.assertTrue(any(e["relation"] == "supported_by"
                                    and e["node"].startswith("source:")
                                    and e["status"]
                                    for e in row["record"]["relations"]))
        by_id = {r["record_id"]: r for r in product_rows}
        for ident in ("view:chatgpt-space:sites", "view:chatgpt-space:google-drive"):
            with self.subTest(scope=ident):
                self.assertIn("unverified", by_id[ident]["confidence"].lower())
                self.assertTrue(any("Space" in e["status"]
                                    for e in by_id[ident]["record"]["relations"]
                                    if e["relation"] == "supported_by"))
        with sqlite3.connect(":memory:") as db:
            mod.build(db, rows)
            for query, ident in (("Sites", "view:chatgpt-space:sites"),
                                 ("Google Drive", "view:chatgpt-space:google-drive")):
                matches = mod.search(db, query, "view", product="ChatGPT Space", limit=100)
                self.assertTrue(any(r["id"] == by_id[ident]["id"] for r in matches))

    def test_product_contract_and_availability_retrieval(self):
        rows = mod.load_records()
        by_id = {r["id"]: r for r in rows}
        row = by_id["ai-product-graph:contract:notebook-deck-staged-revision"]
        self.assertEqual(row["kind"], "contract")
        self.assertIn("not observed runtime", row["confidence"])
        self.assertTrue(row["sources"])
        self.assertTrue(row["record"]["transitions"])
        self.assertIn("motion timing", row["record"]["unknown"])
        availability = [r for r in rows if r["kind"] == "availability"]
        self.assertGreaterEqual(len(availability), 15)
        self.assertTrue(all(r["sources"] and r["product"] for r in availability))
        with sqlite3.connect(":memory:") as db:
            mod.build(db, rows)
            self.assertTrue(any(r["id"] == row["id"] for r in mod.search(db, "pending deletion", "contract", product="Gemini Notebook (formerly NotebookLM)", limit=100)))
            self.assertTrue(mod.search(db, "motion template", "availability", product="Claude", limit=100))

    def test_creation_option_inventory(self):
        rows = mod.load_records()
        options = [r for r in rows if r["kind"] == "creation-option"]
        self.assertTrue(options)
        self.assertTrue(all(r["sources"] and r["product"] for r in options))
        self.assertEqual(len([r for r in options if r["product"] == "Claude" and r["record"]["category"] == "typed-editor-template"]), 7)
        with sqlite3.connect(":memory:") as db:
            mod.build(db, rows)
            self.assertTrue(mod.search(db, "checklist", "creation-option", product="ChatGPT Space", limit=100))
            self.assertTrue(mod.search(db, "study guide", "creation-option", product="Gemini Notebook (formerly NotebookLM)", limit=100))
