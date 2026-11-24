#!/usr/bin/env python3
"""Tests for scripts/secrets_gate.py and docs/TOOL-LICENSES-PRIVACY.md (Issue #33)."""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import secrets_gate  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class SecretsGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _run_git(self, *args: str, cwd: Path) -> None:
        subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_detects_all_required_secret_classes_and_never_leaks_raw_values(self):
        synthetic_secrets = {
            "rsa_key.txt": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEAsyntheticKeyBody123456\n",
            "openssh_key.txt": "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmU=\n",
            "ec_key.txt": "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIIsyntheticEcKeyValue123456\n",
            "gh_classic.py": 'TOKEN = "ghp_syntheticTestClassicToken123456789012"\n',
            "gh_pat.ts": 'export const PAT = "github_pat_11SYNTHETIC0000000000_abcdef1234567890ABCD";\n',
            "stripe.env.txt": "STRIPE_KEY=sk_live_syntheticStripeValue9876543210\n",
            "aws.cfg": "aws_access_key_id=AKIASYNTHETIC1234567\naws_secret_access_key=AbCdEfGhIjKlMnOpQrStUvWxYz0123456789+/==\n",
            "google.ts": 'export const FB_KEY = "AIzaSySyntheticGoogleApiKeyValue123456789";\n',
            "db_url.txt": "DATABASE_URL=postgres://adminuser:SyntheticPass987@db.internal:5432/exams\n",
        }
        # Raw values that must NEVER appear anywhere in the generated report JSON
        canary_values = [
            "ghp_syntheticTestClassicToken123456789012",
            "github_pat_11SYNTHETIC0000000000_abcdef1234567890ABCD",
            "sk_live_syntheticStripeValue9876543210",
            "AKIASYNTHETIC1234567",
            "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789+/==",
            "AIzaSySyntheticGoogleApiKeyValue123456789",
            "SyntheticPass987",
        ]

        workspace = self.root / "secrets_ws"
        workspace.mkdir()
        for fname, content in synthetic_secrets.items():
            (workspace / fname).write_text(content, encoding="utf-8")

        report = secrets_gate.scan_target(workspace)
        self.assertTrue(report["blocked"])
        self.assertEqual(report["gate_decision"], "BLOCK")
        found_rules = {f["rule_id"] for f in report["findings"]}
        self.assertTrue(
            {
                "private-key-header",
                "github-token",
                "github-fine-grained-pat",
                "stripe-secret-key",
                "aws-access-key-id",
                "aws-secret-access-key",
                "google-api-key",
                "connection-url-credentials",
            }.issubset(found_rules)
        )

        serialized = json.dumps(report, ensure_ascii=False)
        for canary in canary_values:
            self.assertNotIn(canary, serialized, msg=f"Raw secret leaked into report: {canary}")
        for f in report["findings"]:
            self.assertTrue(f["fingerprint"].startswith("sha256:"))

    def test_sensitive_file_paths_detected_and_example_env_allowed(self):
        ws = self.root / "paths_ws"
        ws.mkdir()
        (ws / ".env").write_text("PORT=3000\n", encoding="utf-8")
        (ws / "tls.pem").write_text("non-secret-cert-placeholder\n", encoding="utf-8")
        (ws / "api.key").write_text("placeholder-key\n", encoding="utf-8")
        (ws / "serviceAccountKey.json").write_text(
            json.dumps({"type": "service_account", "private_key": "synthetic-private-payload-value"}),
            encoding="utf-8",
        )
        # Benign .env.example with placeholder values must pass when scanned in isolation
        clean_dir = self.root / "clean_ws"
        clean_dir.mkdir()
        (clean_dir / ".env.example").write_text(
            "API_KEY=your_api_key_here_placeholder\nDATABASE_URL=postgres://user:placeholder@localhost:5432/app\n",
            encoding="utf-8",
        )

        blocked_report = secrets_gate.scan_target(ws)
        self.assertTrue(blocked_report["blocked"])
        locations = {f["location"] for f in blocked_report["findings"]}
        self.assertIn(".env", locations)
        self.assertIn("tls.pem", locations)
        self.assertIn("api.key", locations)
        self.assertTrue(any(loc.startswith("serviceAccountKey.json") for loc in locations))

        clean_report = secrets_gate.scan_target(clean_dir)
        self.assertFalse(clean_report["blocked"])
        self.assertEqual(clean_report["gate_decision"], "PASS")
        self.assertEqual(clean_report["finding_count"], 0)

    def test_false_positives_and_synthetic_allowlist(self):
        fp_dir = self.root / "fp_ws"
        fp_dir.mkdir()
        # False positives: documentation placeholders, SHA-256 hex hashes, normal identifiers
        (fp_dir / "README.md").write_text(
            "# Example Configuration\n"
            "api_key=example_placeholder_value_123456\n"
            "db_password=changeme_local_dev_password\n"
            "commit_sha=e421ee90123456789abcdef0123456789abcdef0\n"
            "DATABASE_URL=postgres://dev:examplepass@localhost:5432/testdb\n",
            encoding="utf-8",
        )
        report = secrets_gate.scan_target(fp_dir)
        self.assertFalse(report["blocked"], msg=f"Unexpected false positives: {report['findings']}")

        # Synthetic fixture that intentionally resembles a real token, exempted by fingerprint allowlist
        fixture_file = fp_dir / "synthetic_fixture.txt"
        synthetic_tok = "ghp_syntheticFixtureAllowlist1234567890"
        fixture_file.write_text(f"fixture={synthetic_tok}\n", encoding="utf-8")

        unallowed = secrets_gate.scan_target(fp_dir)
        self.assertTrue(unallowed["blocked"])
        fp_hash = unallowed["findings"][0]["fingerprint"]

        allowlist = secrets_gate.GateAllowlist(fingerprints={fp_hash})
        allowed = secrets_gate.scan_target(fp_dir, allowlist=allowlist)
        self.assertFalse(allowed["blocked"])
        self.assertEqual(allowed["finding_count"], 0)

    def test_json_exports_logs_and_rrweb_sanitization(self):
        secret_tok = "ghp_syntheticJsonLeakToken12345678901234"
        stripe_tok = "sk_test_syntheticRrwebSecret1234567890"
        json_path = self.root / "preview-export.json"
        json_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "records": [
                        {
                            "path": "src/auth.ts",
                            "snippet": f"const token = '{secret_tok}';",
                        },
                        {
                            "rrweb_event": {
                                "type": 3,
                                "data": {"text": f"Bearer {stripe_tok}abcdefghij"},
                            }
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        report = secrets_gate.scan_target(json_path)
        self.assertTrue(report["blocked"])
        self.assertNotIn(secret_tok, json.dumps(report))
        self.assertNotIn(stripe_tok, json.dumps(report))

        # Test sanitization of JSON and log files
        sanitized_json = self.root / "preview-export.clean.json"
        exit_code = secrets_gate.main(
            ["sanitize", str(json_path), "--output", str(sanitized_json)]
        )
        self.assertEqual(exit_code, 0)
        cleaned_content = sanitized_json.read_text(encoding="utf-8")
        self.assertNotIn(secret_tok, cleaned_content)
        self.assertNotIn(stripe_tok, cleaned_content)
        self.assertIn("[REDACTED:", cleaned_content)

        # Verify cleaned JSON now passes the gate
        clean_report = secrets_gate.scan_target(sanitized_json)
        self.assertFalse(clean_report["blocked"])

        # Also test plain log sanitization
        log_file = self.root / "worker.log"
        db_url = "postgresql://svc:VerySecretDbPass123@pg.prod.local:5432/core"
        log_file.write_text(f"2026-11-23 INFO connecting to {db_url}\n", encoding="utf-8")
        self.assertTrue(secrets_gate.scan_target(log_file)["blocked"])
        cleaned_log, count = secrets_gate.sanitize_text(log_file.read_text(encoding="utf-8"))
        self.assertEqual(count, 1)
        self.assertNotIn("VerySecretDbPass123", cleaned_log)
        self.assertIn("postgresql://[REDACTED]@pg.prod.local:5432/core", cleaned_log)

    def test_sqlite_synthetic_database_scan(self):
        db_path = self.root / "derived-index.sqlite"
        leaked_aws = "AKIASYNTHETICSQL9999"
        leaked_google = "AIzaSySyntheticSqliteKey1234567890abcdef"
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE content_occurrences (id INTEGER PRIMARY KEY, path TEXT NOT NULL);
                CREATE TABLE content_chunks (id INTEGER PRIMARY KEY, content TEXT NOT NULL);
                """
            )
            conn.execute("INSERT INTO content_occurrences (path) VALUES (?)", (".env.production",))
            conn.execute(
                "INSERT INTO content_chunks (content) VALUES (?)",
                (f"const k1 = '{leaked_aws}';\nconst k2 = '{leaked_google}';",),
            )
            conn.commit()
        finally:
            conn.close()

        report = secrets_gate.scan_target(db_path)
        self.assertTrue(report["blocked"])
        rules = {f["rule_id"] for f in report["findings"]}
        self.assertIn("sqlite-sensitive-path", rules)
        self.assertIn("aws-access-key-id", rules)
        self.assertIn("google-api-key", rules)
        serialized = json.dumps(report)
        self.assertNotIn(leaked_aws, serialized)
        self.assertNotIn(leaked_google, serialized)

    def test_git_bundle_history_scan_and_cli_exit_codes(self):
        repo_work = self.root / "repo_work"
        repo_work.mkdir()
        self._run_git("init", "-q", "-b", "main", str(repo_work), cwd=self.root)
        self._run_git("config", "user.email", "gate@example.invalid", cwd=repo_work)
        self._run_git("config", "user.name", "Gate Test", cwd=repo_work)

        secret_val = "ghp_syntheticGitHistoryToken123456789012"
        (repo_work / "src.ts").write_text(f"export const S = '{secret_val}';\n", encoding="utf-8")
        self._run_git("add", ".", cwd=repo_work)
        self._run_git("commit", "-qm", "add secret", cwd=repo_work)

        # Even if deleted in a later commit, historical blob must be caught in bundle scan
        (repo_work / "src.ts").write_text("export const S = 'clean';\n", encoding="utf-8")
        self._run_git("add", ".", cwd=repo_work)
        self._run_git("commit", "-qm", "remove secret", cwd=repo_work)

        bundle = self.root / "history.bundle"
        self._run_git("bundle", "create", str(bundle), "--all", cwd=repo_work)

        out_json = self.root / "gate-report.json"
        code = secrets_gate.main(["scan", str(bundle), "--output", str(out_json)])
        self.assertEqual(code, 2)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertTrue(report["blocked"])
        self.assertNotIn(secret_val, out_json.read_text(encoding="utf-8"))

    def test_tool_licenses_doc_and_zero_emoji_policy(self):
        required_tools = [
            "Gitleaks",
            "Graphify",
            "Codebase Memory MCP",
            "CocoIndex Code",
            "ast-grep",
            "GitNexus",
            "CodeGraph",
            "QMD",
            "PicoQMD",
            "Docling",
            "PageIndex",
            "sqlite-vec",
            "Repomix",
            "Probe",
            "sqry",
            "SCIP",
            "XERJ",
            "Xberg",
            "OpenDataLoader PDF",
            "Playwright MCP",
            "Chrome DevTools MCP",
            "rrweb",
        ]
        doc_path = ROOT / "docs" / "TOOL-LICENSES-PRIVACY.md"
        self.assertTrue(doc_path.is_file())
        doc_text = doc_path.read_text(encoding="utf-8")
        for tool in required_tools:
            self.assertIn(tool, doc_text, msg=f"Missing required tool in matrix: {tool}")
        self.assertIn("PolyForm Noncommercial", doc_text)
        self.assertIn("AGPL", doc_text)

        # Zero Emoji Policy across all deliverables of issue #33
        for target in (
            ROOT / "scripts" / "secrets_gate.py",
            ROOT / "docs" / "TOOL-LICENSES-PRIVACY.md",
            ROOT / "tests" / "test_secrets_gate.py",
        ):
            content = target.read_text(encoding="utf-8")
            emojis = EMOJI_REGEX.findall(content)
            self.assertEqual(emojis, [], msg=f"Found disallowed emoji in {target}: {emojis}")


if __name__ == "__main__":
    unittest.main()
