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

    def test_grouping_normalizes_labels_once_and_tracks_taxonomy_changes(self):
        from unittest.mock import patch
        from copy import deepcopy

        with patch.object(mod, "labels", wraps=mod.labels) as counted:
            concepts, groups = mod.group_records(self.records, self.taxonomy)
            self.assertEqual(counted.call_count, len(concepts))
        for row in self.records:
            if row["kind"] not in {"pattern", "visual"}:
                continue
            for field in [row["title"], *row.get("record", {}).get("keywords", [])]:
                for ident in mod.resolve(field, concepts):
                    self.assertIn(row["id"], groups[ident])
        changed = deepcopy(self.taxonomy)
        sidebar = next(c for c in changed["concepts"] if c["id"] == "ui.navigation.sidebar")
        sidebar["aliases"].append("unique taxonomy test alias")
        self.assertEqual(mod.resolve("unique taxonomy test alias", mod.validate(changed, self.records)),
                         ["ui.navigation.sidebar"])
        self.assertNotIn("ui.navigation.sidebar", mod.resolve("unique taxonomy test alias", concepts))

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

    def test_23_domains_and_backward_compatibility(self):
        by_id = mod.validate(self.taxonomy, self.records)
        concepts, _ = mod.group_records(self.records, self.taxonomy)
        expected_23 = {
            "produto", "concursos", "aprendizagem", "avaliacao", "ia-informacao",
            "workspace", "objetos", "visualizacoes", "design-system", "interacao",
            "motion", "acessibilidade", "responsividade", "ai-native-ux",
            "engenharia", "arquitetura-tecnica", "qualidade", "historico",
            "midia", "referencias-externas", "conhecimento-humano", "operacoes",
            "governanca",
        }
        for domain in sorted(expected_23):
            cid = f"domain.{domain}"
            self.assertIn(cid, by_id)
            self.assertEqual(mod.resolve(cid, concepts), [cid], f"Failed to resolve {cid}")
        pack = mod.build_pack("domain.concursos", self.records, self.taxonomy)
        self.assertEqual(pack["status"], "resolved")
        self.assertEqual(pack["packs"][0]["concept"]["id"], "domain.concursos")
        # Preserve original 15 concepts intact
        original_15 = {
            "ui.navigation", "ui.navigation.sidebar", "ui.navigation.side-panel",
            "ui.navigation.tabs", "ui.collection", "ui.collection.kanban",
            "ui.interaction", "ui.interaction.reorder", "ui.interaction.filter",
            "ui.motion", "ui.ai", "ui.ai.artifact", "ui.visualization",
            "ui.whiteboard", "ui.visual-language",
        }
        self.assertTrue(original_15.issubset(by_id.keys()))
        self.assertEqual(by_id["ui.navigation.sidebar"]["parent"], "ui.navigation")
        self.assertEqual(by_id["ui.navigation.side-panel"]["parent"], "ui.navigation")
        self.assertEqual(by_id["ui.navigation.tabs"]["parent"], "ui.navigation")
        self.assertEqual(by_id["ui.collection.kanban"]["parent"], "ui.collection")
        self.assertEqual(by_id["ui.interaction.reorder"]["parent"], "ui.interaction")
        self.assertEqual(by_id["ui.interaction.filter"]["parent"], "ui.interaction")
        self.assertEqual(by_id["ui.ai.artifact"]["parent"], "ui.ai")

