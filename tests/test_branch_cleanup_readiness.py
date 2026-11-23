#!/usr/bin/env python3
"""Tests that the branch cleanup gate blocks deletion by default."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import branch_cleanup_readiness as b  # noqa: E402


class GateTests(unittest.TestCase):
    def setUp(self):
        self.rows = b.audit_branches()

    def test_nothing_is_deletable_by_default(self):
        self.assertTrue(all(not b.evaluate_safety_gate(r["repo"], r["branch"], self.rows)[0] for r in self.rows))

    def test_infrastructure_and_transfer_branches_blocked(self):
        repo = "ianmaciel7/exams-app-archive"
        for name in ("main", "archive-search-queries", "notes-private-import"):
            self.assertFalse(b.evaluate_safety_gate(repo, name, self.rows)[0], name)

    def test_unknown_branch_blocked(self):
        self.assertFalse(b.evaluate_safety_gate("x/y", "z", self.rows)[0])

    def test_all_branches_classified(self):
        self.assertTrue(all(r["category"] in b.CATEGORIES for r in self.rows))


if __name__ == "__main__":
    unittest.main()
