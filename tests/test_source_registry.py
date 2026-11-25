#!/usr/bin/env python3
"""Unit tests for declarative source registry and policy enforcement (#84)."""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import source_registry as sr  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class SourceRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = sr.load_registry()

    def test_valid_registry_schema_and_adapters(self) -> None:
        self.assertEqual(sr.validate_registry_schema(self.registry), [])
        self.assertEqual(self.registry["global_policies"]["egress_policy"], "offline-local-only")
        self.assertFalse(self.registry["global_policies"]["external_third_party_upload"])

        adapters = {s["adapter"] for s in self.registry["sources"]}
        self.assertEqual(adapters, {"github_api", "local_fs", "git_bundle"})

        scopes = {s["scope"] for s in self.registry["sources"]}
        self.assertEqual(scopes, {"public", "authenticated_archive"})

        # Legacy config consolidation parity check
        legacy = json.loads((ROOT / "config" / "public-catalog-sources.json").read_text(encoding="utf-8"))
        exported = sr.export_legacy_public_policy(self.registry)
        self.assertEqual(exported["repositories"], legacy["repositories"])
        self.assertEqual(exported["historical_unavailable"], legacy["historical_unavailable"])

    def test_exclusion_and_authorization_precedence_over_inclusion(self) -> None:
        src_public = sr.get_source(self.registry, "local.code-and-tests")
        # Even if path matches scripts/** include rule, secrets/env/node_modules MUST be blocked.
        candidates = [
            "scripts/valid_module.py",
            "scripts/.env",
            "scripts/.env.local",
            "scripts/node_modules/pkg/index.js",
            "scripts/secrets/api_key.json",
            "scripts/service-account.json",
            "scripts/private.pem",
            "scripts/user_password_helper.py",
        ]
        run = sr.dry_run("local.code-and-tests", registry=self.registry, candidates=candidates, authorized=True)
        by_target = {d["target"]: d for d in run["decisions"]}

        self.assertTrue(by_target["scripts/valid_module.py"]["included"])
        self.assertEqual(by_target["scripts/valid_module.py"]["precedence_stage"], "source_include")

        for blocked in candidates[1:]:
            self.assertFalse(by_target[blocked]["included"], f"Expected exclusion for {blocked}")
            self.assertEqual(by_target[blocked]["precedence_stage"], "global_security_exclude")
            self.assertTrue(by_target[blocked]["reason_detail"])

        # Authenticated archive source MUST fail closed when authorized=False even for valid code paths
        unauth_run = sr.dry_run(
            "bundle.exams-app-old",
            registry=self.registry,
            candidates=["src/components/Sidebar.tsx"],
            authorized=False,
        )
        self.assertFalse(unauth_run["decisions"][0]["included"])
        self.assertEqual(unauth_run["decisions"][0]["precedence_stage"], "authorization")
        self.assertEqual(unauth_run["decisions"][0]["reason_code"], "authorization_required")

        # Authorized access permits valid non-secret paths in authenticated archive
        auth_run = sr.dry_run(
            "bundle.exams-app-old",
            registry=self.registry,
            candidates=["src/components/Sidebar.tsx", "src/.env.production"],
            authorized=True,
        )
        self.assertTrue(auth_run["decisions"][0]["included"])
        self.assertFalse(auth_run["decisions"][1]["included"])

    def test_pinned_revisions_and_size_limit_enforcement(self) -> None:
        exams = sr.get_source(self.registry, "repo.exams-app")
        self.assertIn("refs/heads/main", exams["pinned_revisions"])
        self.assertEqual(len(exams["pinned_revisions"]["refs/heads/main"]), 40)

        dec_ok = sr.evaluate_file_policy(
            exams,
            "src/Sidebar.tsx",
            global_policies=self.registry["global_policies"],
            byte_size=4096,
        )
        self.assertTrue(dec_ok.included)

        dec_big = sr.evaluate_file_policy(
            exams,
            "src/HugeBundle.tsx",
            global_policies=self.registry["global_policies"],
            byte_size=10_000_000,
        )
        self.assertFalse(dec_big.included)
        self.assertEqual(dec_big.reason_code, "exceeds_max_bytes")

    def test_rejects_invalid_registry_configurations(self) -> None:
        bad_egress = json.loads(json.dumps(self.registry))
        bad_egress["global_policies"]["external_third_party_upload"] = True
        self.assertTrue(sr.validate_registry_schema(bad_egress))

        bad_notes = json.loads(json.dumps(self.registry))
        for s in bad_notes["sources"]:
            if s["source_id"] == "bundle.notes-app":
                s["scope"] = "public"
                s["authorization_required"] = False
        self.assertTrue(sr.validate_registry_schema(bad_notes))

        bad_sha = json.loads(json.dumps(self.registry))
        bad_sha["sources"][0]["pinned_revisions"]["refs/heads/main"] = "not-a-sha"
        self.assertTrue(sr.validate_registry_schema(bad_sha))

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text(json.dumps(bad_egress), encoding="utf-8")
            with self.assertRaises(sr.RegistryValidationError):
                sr.load_registry(p)

    def test_controlled_new_source_and_url_policy(self) -> None:
        extended = json.loads(json.dumps(self.registry))
        extended["sources"].append(
            {
                "source_id": "local.adr-contracts",
                "context_key": "public::arquitetura-tecnica::local.adr-contracts",
                "title": "Architecture Contracts",
                "source_type": "documentation_corpus",
                "adapter": "local_fs",
                "scope": "public",
                "authorization_required": False,
                "origin_status": "online",
                "license": "MIT",
                "root_path": "docs",
                "pinned_refs": ["HEAD"],
                "pinned_revisions": {},
                "preserve_history": True,
                "freshness_policy": {"mode": "incremental_content_hash", "ttl_hours": 48},
                "include_paths": ["**/*.md"],
                "exclude_paths": ["**/drafts/**"],
                "include_extensions": [".md"],
                "exclude_extensions": [".env"],
                "include_urls": ["https://docs.example.org/*"],
                "exclude_urls": ["https://docs.example.org/private/*"],
            }
        )
        self.assertEqual(sr.validate_registry_schema(extended), [])

        new_src = sr.get_source(extended, "local.adr-contracts")
        self.assertTrue(sr.evaluate_url_policy(new_src, "https://docs.example.org/adr-1").included)
        self.assertFalse(sr.evaluate_url_policy(new_src, "https://docs.example.org/private/token").included)
        self.assertFalse(sr.evaluate_url_policy(new_src, "http://insecure.example.org/adr").included)

    def test_coverage_inspection_and_zero_emoji(self) -> None:
        cov = sr.inspect_coverage(registry=self.registry)
        self.assertEqual(cov["total_sources"], len(self.registry["sources"]))
        self.assertIn("local_fs", cov["by_adapter"])
        self.assertIn("git_bundle", cov["by_adapter"])
        self.assertIn("github_api", cov["by_adapter"])

        script_txt = (SCRIPTS_DIR / "source_registry.py").read_text(encoding="utf-8")
        cfg_txt = (ROOT / "config" / "source_registry.json").read_text(encoding="utf-8")
        self.assertFalse(EMOJI_REGEX.search(script_txt))
        self.assertFalse(EMOJI_REGEX.search(cfg_txt))
        self.assertFalse(EMOJI_REGEX.search(json.dumps(cov, ensure_ascii=False)))


if __name__ == "__main__":
    unittest.main()
