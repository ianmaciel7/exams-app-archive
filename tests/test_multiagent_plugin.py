#!/usr/bin/env python3
"""Contract tests for the shared, private, four-client Exams Archive plugin (stdlib only)."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "exams-archive-native"
LEGACY = ROOT / "plugins" / "exams-archive"

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

class MultiAgentPluginTests(unittest.TestCase):
    def test_manifests_share_identity_and_version(self):
        paths = ["plugin.json",".codex-plugin/plugin.json",".claude-plugin/plugin.json",".antigravity-plugin/plugin.json"]
        manifests = [json.loads((PLUGIN / p).read_text(encoding="utf-8")) for p in paths]
        self.assertEqual({m["name"] for m in manifests}, {"exams-archive-native"})
        self.assertRegex(manifests[0]["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual({m["version"] for m in manifests}, {manifests[0]["version"]})
        self.assertEqual(manifests[0]["$schema"], "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        self.assertEqual(manifests[3]["$schema"], "https://antigravity.google/schemas/v1/plugin.json")
        self.assertTrue(manifests[2]["description"])
    def test_marketplaces_use_canonical_folder(self):
        codex=load(".agents/plugins/marketplace.json")
        claude=load(".claude-plugin/marketplace.json")
        self.assertEqual(len(codex["plugins"]),1)
        self.assertEqual(len(claude["plugins"]),1)
        self.assertEqual(codex["plugins"][0]["source"]["path"],"./plugins/exams-archive-native")
        self.assertEqual(claude["plugins"][0]["source"],"./plugins/exams-archive-native")
        self.assertEqual(codex["plugins"][0]["name"],claude["plugins"][0]["name"])
        self.assertTrue((ROOT / claude["plugins"][0]["source"]).is_dir())
    def test_skills_have_matching_frontmatter(self):
        skills=list((PLUGIN / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skills),6)
        for path in skills:
            data=path.read_text(encoding="utf-8")
            self.assertEqual(data.splitlines()[0],"---",path)
            m=next((line[6:].strip() for line in data.splitlines() if line.startswith("name: ")),None)
            self.assertIsNotNone(m,path)
            self.assertEqual(m,path.parent.name,path)
            self.assertIn("description:",data)
    def test_fts5_script_is_preserved_identically(self):
        new=(PLUGIN / "scripts/archive_query.py").read_bytes()
        old=(LEGACY / "scripts/archive_query.py").read_bytes()
        self.assertEqual(new,old,"Do not silently rewrite the historical FTS5 CLI")
        self.assertIn(b"def read_db(",new)
        self.assertIn(b"gzip_sha256",new)
        self.assertIn(b"component_catalog",new)
        self.assertTrue((PLUGIN / "skills/component-explorer/SKILL.md").is_file())
    def test_private_archive_remains_separate(self):
        self.assertTrue((LEGACY / "plugin.json").is_file())
        self.assertTrue((ROOT / "manifests").exists())
        self.assertFalse((PLUGIN / "reports").exists())
        self.assertFalse((PLUGIN / "inventory").exists())
    def test_sync_contract_exists(self):
        self.assertTrue((PLUGIN/"skills/sync-bridge/SKILL.md").is_file())
        registry=load("plugins/exams-archive-native/.sync-state.json")
        self.assertEqual(registry["plugin_id"],"plugins_6b04aaa9fd848191a24525011f76e2bb")

if __name__ == "__main__":
    unittest.main()
