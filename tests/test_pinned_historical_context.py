import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import authenticated_archive_query as worker


class PinnedHistoricalContextTests(unittest.TestCase):
    def request(self):
        return {"version": 1, "id": "fixture-123", "operation": "concept_context",
                "repo": sorted(worker.ALLOWED)[0], "ref": "refs/heads/example",
                "source_sha": "a" * 40, "expected_index_checksum": "b" * 64,
                "concept_id": "ui.tabs.pin_tab", "query": "togglePin", "limit": 5}

    def test_required_pins(self):
        req = self.request()
        worker.validate(req)
        for key in ("repo", "ref", "source_sha", "expected_index_checksum", "concept_id", "query"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    worker.validate({k: v for k, v in req.items() if k != key})

    def test_bad_checksum(self):
        req = self.request()
        req["expected_index_checksum"] = "wrong"
        with self.assertRaises(ValueError):
            worker.validate(req)
