#!/usr/bin/env python3
"""Tests for context_linker linking code, screenshots, and metadata."""
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))
import context_linker

class ContextLinkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test_context.sqlite"
        self.conn = context_linker.open_db(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_query_history_empty(self):
        timeline = context_linker.query_history(self.conn, "inexistente_123456")
        self.assertEqual(timeline["query"], "inexistente_123456")
        self.assertEqual(timeline["total_files"], 0)
        self.assertEqual(timeline["files"], [])

    def test_zero_emoji_policy(self):
        code = (ROOT / "scripts/context_linker.py").read_text(encoding="utf-8")
        import re
        emojis = re.findall(r"[\U00010000-\U0010ffff]", code)
        self.assertEqual(len(emojis), 0)

if __name__ == "__main__":
    unittest.main()
