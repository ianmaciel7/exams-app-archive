"""Regression coverage for the public App Shell taxonomy index."""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import concept_packs
import research_index


class AppShellTaxonomyTests(unittest.TestCase):
    def test_curated_records_and_bilingual_resolution(self):
        rows = research_index.load_records()
        shells = {r["id"]: r for r in rows
                  if r["catalog"] == "general"
                  and r["record"].get("family") == "app-shell-taxonomy"}
        taxonomy = concept_packs.load_taxonomy()
        concepts = concept_packs.validate(taxonomy, rows)
        concept = concepts["ui.layout.app-shell"]
        self.assertGreaterEqual(len(shells), 18)
        self.assertEqual(set(concept["members"]), set(shells))
        for alias in ("tipos de app shell", "app shell taxonomy", "app shell", "app-shell", "shell de aplicação"):
            self.assertEqual(concept_packs.resolve(alias, concepts), [concept["id"]])
        self.assertTrue(all(r["sources"] and r["confidence"] for r in shells.values()))
        self.assertTrue(research_index.verify_record_provenance(list(shells.values()))["integrity_passed"])
        with sqlite3.connect(":memory:") as db:
            research_index.build(db, rows)
            for query, ident in (
                ("colunas flexíveis", "general:shell.flexible-column"),
                ("painel auxiliar", "general:shell.supporting-pane"),
                ("múltiplas janelas", "general:shell.multi-window"),
                ("list detail detail", "general:shell.list-detail-detail"),
            ):
                matches = research_index.search(db, query, "pattern", limit=100)
                self.assertIn(ident, {row["id"] for row in matches}, query)
