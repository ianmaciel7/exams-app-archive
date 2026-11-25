import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import archive_context as mod
import concept_packs
import research_index


class ArchiveContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = research_index.load_records()
        cls.taxonomy = concept_packs.load_taxonomy()

    def test_resolve_then_retrieve(self):
        resolved = mod.discover("barra lateral", self.records, self.taxonomy)
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(resolved["matches"][0]["id"], "ui.navigation.sidebar")
        out = mod.retrieve("ui.navigation.sidebar", "sidebar screenshots",
                           self.records, self.taxonomy, revision=resolved["snapshot"])
        self.assertEqual(out["status"], "ok")
        self.assertTrue(out["snippets"])
        for entry in out["snippets"]:
            s = entry["snippet"]
            self.assertTrue(s["provenance"]["record_sha256"])
            self.assertTrue(s["breadcrumb"])

    def test_mismatch_and_ambiguity(self):
        out = mod.retrieve("ui.navigation.sidebar", "sidebar",
                           self.records, self.taxonomy, revision="wrong")
        self.assertEqual(out["status"], "snapshot-mismatch")
        self.assertEqual(out["snippets"], [])
        self.assertEqual(mod.discover("side panel and sidebar", self.records, self.taxonomy)["status"], "ambiguous")
        self.assertEqual(mod.discover("pin", self.records, self.taxonomy)["status"], "unresolved")

    def test_scope_budget_and_ranking(self):
        out = mod.retrieve("ui.interaction.reorder", "sortable list",
                           self.records, self.taxonomy, max_bytes=5000, limit=2)
        self.assertLessEqual(len(mod.encode(out).encode("utf-8")) + 1, 5000)
        self.assertLessEqual(len(out["snippets"]), 2)
        self.assertTrue(out["omitted"])
        self.assertEqual(out["scope"], "public-research")
        self.assertTrue(any(s["type"] == "visual" for s in out["snippets"]))
        visual = next(s for s in out["snippets"] if s["type"] == "visual")
        self.assertEqual(visual["snippet"]["id"], "visual:dnd-kit-sortable-list")
        out = mod.retrieve("ui.interaction.reorder", "sortable", self.records, self.taxonomy,
                           product="dnd-kit", max_bytes=6000)
        self.assertTrue(out["snippets"])
        self.assertTrue(all(s["snippet"]["provenance"]["product"] == "dnd-kit" for s in out["snippets"]))

    def test_snapshot_detects_change_and_is_order_independent(self):
        rev = mod.snapshot(self.records, self.taxonomy)
        self.assertEqual(rev, mod.snapshot(list(reversed(self.records)), self.taxonomy))
        changed = [dict(r) for r in self.records]
        changed[0]["record_sha256"] = "changed"
        self.assertNotEqual(rev, mod.snapshot(changed, self.taxonomy))
