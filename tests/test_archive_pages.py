#!/usr/bin/env python3
"""Tests for the GitHub Pages public shell and offline explorer security gates."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
WORKFLOW_PATH = ROOT / ".github/workflows/archive-pages.yml"

ALLOWLIST = {"index.html", "style.css", "app.js", ".nojekyll", "llms.txt", "files.html", "files.js"}
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class ArchivePagesTests(unittest.TestCase):
    def test_allowlist_contents_exist(self):
        for name in ALLOWLIST:
            target = SITE_DIR / name
            self.assertTrue(target.is_file(), f"Missing required allowlisted file: {name}")

    def test_zero_emoji_policy(self):
        for name in ["index.html", "style.css", "app.js", "files.html", "files.js"]:
            content = (SITE_DIR / name).read_text(encoding="utf-8")
            emojis = EMOJI_REGEX.findall(content)
            self.assertEqual(len(emojis), 0, f"Found emojis in site/{name}: {emojis}")

    def test_js_syntax(self):
        res = subprocess.run(["node", "--check", str(SITE_DIR / "app.js")],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Syntax error in site/app.js: {res.stderr}")

    def test_research_public_projection(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "research.json"
            result = subprocess.run(["python", str(ROOT / "scripts/export_public_research.py"), str(target)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(data["scope"], "public research metadata only")
            self.assertEqual(data["audit"]["records"], len(data["records"]))
            self.assertTrue(all(r["catalog_path"].startswith("docs/references/") for r in data["records"]))
            self.assertTrue(all("record" not in r and "content" not in r for r in data["records"]))
            self.assertTrue(all(url.startswith("https://") for r in data["records"] for url in r["sources"]))
        result = subprocess.run(["node", "--check", str(SITE_DIR / "research.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_files_js_syntax(self):
        res = subprocess.run(["node", "--check", str(SITE_DIR / "files.js")], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_content_security_policy_and_landmarks(self):
        html = (SITE_DIR / "index.html").read_text(encoding="utf-8")
        self.assertIn("Content-Security-Policy", html)
        self.assertIn("default-src 'none'", html)
        self.assertIn("connect-src 'self'", html)
        self.assertIn("script-src 'self'", html)
        self.assertIn('role="status"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('class="skip-link"', html)

    def test_packaging_gate_rejects_private_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            website = temp_path / "website"
            website.mkdir()

            for name in ALLOWLIST:
                shutil.copy2(SITE_DIR / name, website / name)

            # Legitimate packaging has exactly 7 files
            packaged_files = [p.name for p in website.iterdir()]
            self.assertEqual(set(packaged_files), ALLOWLIST)

            # Gate fails if any non-allowlist or sensitive file is added
            leak_files = [
                ("archive.bundle", b"git-bundle-binary-bytes"),
                ("full-index.sqlite", b"SQLite format 3\x00"),
                ("private.archive-browser.json", b'{"version":1,"records":[]}'),
                ("req-01.json", b'{"query":"secret"}'),
                (".env", b"GH_TOKEN=ghp_dummysecretvalue1234567890"),
                ("id_rsa", b"-----BEGIN OPENSSH PRIVATE KEY-----\ntest\n-----END OPENSSH PRIVATE KEY-----")
            ]
            for filename, content in leak_files:
                leak_target = website / filename
                leak_target.write_bytes(content)
                self.assertNotEqual(
                    len(list(website.iterdir())),
                    7,
                    f"Directory should reject or detect extra file {filename}"
                )
                leak_target.unlink()

    def test_synthetic_export_schema_compatibility(self):
        synthetic = {
            "version": 1,
            "exported_at": "2026-11-23T20:00:00Z",
            "records": [
                {
                    "repository": "exams-app-antigo-2",
                    "kind": "commit",
                    "sha": "a" * 40,
                    "path": "",
                    "summary": "Implementacao do grafo de questoes",
                    "deleted": False
                },
                {
                    "repository": "exams-app",
                    "kind": "file",
                    "sha": "b" * 40,
                    "path": "src/components/Sidebar.tsx",
                    "summary": "src/components/Sidebar.tsx",
                    "deleted": False
                },
                {
                    "repository": "exams-app-old",
                    "kind": "image",
                    "sha": "c" * 40,
                    "path": "docs/screenshots/canvas-v1.png",
                    "summary": "docs/screenshots/canvas-v1.png",
                    "bytes": 10240,
                    "deleted": True
                }
            ]
        }
        raw = json.dumps(synthetic)
        data = json.loads(raw)
        self.assertEqual(data["version"], 1)
        self.assertEqual(len(data["records"]), 3)
        for r in data["records"]:
            self.assertIn(r["kind"], ["commit", "file", "image"])
            self.assertEqual(len(r["sha"]), 40)
            self.assertIsInstance(r["deleted"], bool)


if __name__ == "__main__":
    unittest.main()
