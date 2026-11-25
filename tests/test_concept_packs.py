import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import concept_packs as mod
import research_index


class ConceptPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = research_index.load_records()
        cls.taxonomy = mod.load_taxonomy()

    def test_catalog_and_bilingual(self):
        en = mod.build_pack("sidebar", self.records, self.taxonomy)
        pt = mod.build_pack("barra lateral", self.records, self.taxonomy)
        self.assertEqual(en["packs"], pt["packs"])
        self.assertEqual(en["packs"][0]["concept"]["id"], "ui.navigation.sidebar")
        self.assertEqual(mod.build_pack("painel lateral", self.records, self.taxonomy)["packs"][0]["concept"]["id"], "ui.navigation.side-panel")
        self.assertEqual(mod.build_pack("pin", self.records, self.taxonomy)["status"], "unresolved")
        both = mod.build_pack("side panel and sidebar", self.records, self.taxonomy)
        self.assertEqual(both["status"], "multiple-concepts")
        self.assertEqual({p["concept"]["id"] for p in both["packs"]},
                         {"ui.navigation.side-panel", "ui.navigation.sidebar"})

    def test_cross_catalog_and_budget(self):
        pack = mod.build_pack("reorder", self.records, self.taxonomy, 2)["packs"][0]
        self.assertEqual(set(pack["returned_by_kind"]), {"visual", "pattern"})
        self.assertTrue(pack["truncated"])
        self.assertGreater(pack["record_count"], 2)
        self.assertTrue(all(o["catalog_sha256"] and o["record_sha256"] for b in pack["evidence"] for o in b["occurrences"]))

    def test_exact_blob_dedup(self):
        rows = [{"id": x, "kind": "visual", "title": "Sidebar", "record": {"blob_sha": "a"}} for x in ("one", "two")]
        taxonomy = {"concepts": [{"id": "sidebar", "en": "Sidebar", "pt": "Barra lateral", "parent": None, "aliases": [], "members": ["one", "two"]}]}
        pack = mod.build_pack("sidebar", rows, taxonomy)["packs"][0]
        self.assertEqual(pack["record_count"], 2)
        self.assertEqual(pack["unique_evidence_count"], 1)
        self.assertEqual(len(pack["evidence"][0]["occurrences"]), 2)

    def test_audit_and_hierarchy(self):
        audit = mod.audit(self.records, self.taxonomy)
        self.assertEqual(audit["assigned"] + len(audit["unassigned"]), len(self.records))
        pack = mod.build_pack("navigation", self.records, self.taxonomy)["packs"][0]
        self.assertGreater(pack["record_count"], 4)
        self.assertTrue(all(o["classification"] in {"curated", "lexical-candidate"} for b in pack["evidence"] for o in b["occurrences"]))
