import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from offsite_export_and_restore import safe_name, verify_file


class OffsiteExportTests(unittest.TestCase):
    def test_asset_names(self):
        self.assertEqual(safe_name("notes-app-all-refs.bundle"), "notes-app-all-refs.bundle")
        for name in ("../secret", "a/b", "..", "a\\b", "*"):
            with self.assertRaises(ValueError):
                safe_name(name)

    def test_sha_and_size_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.bundle"
            p.write_bytes(b"example")
            record = {"bytes": 7, "sha256": hashlib.sha256(b"example").hexdigest()}
            verify_file(p, record)
            p.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify_file(p, record)
            p.unlink()
            with self.assertRaises(ValueError):
                verify_file(p, record)
