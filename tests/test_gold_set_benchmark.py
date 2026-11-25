#!/usr/bin/env python3
"""Tests for multidomain Gold Set Benchmark (#78)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import domain_ontology  # noqa: E402
import gold_set_benchmark as gsb  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class GoldSetBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = gsb.load_gold_set()

    def test_gold_set_has_460_queries_across_23_domains_and_deterministic_splits(self) -> None:
        self.assertEqual(self.dataset["total_domains"], 23)
        self.assertEqual(self.dataset["queries_per_domain"], 20)
        self.assertEqual(self.dataset["total_queries"], 460)
        self.assertEqual(len(self.dataset["queries"]), 460)
        self.assertEqual(self.dataset["splits"], {"dev": 345, "holdout": 115})

        per_domain: dict[str, list[dict]] = {}
        for q in self.dataset["queries"]:
            per_domain.setdefault(q["domain"], []).append(q)

        self.assertEqual(set(per_domain.keys()), set(domain_ontology.REQUIRED_23_DOMAINS))
        for dom, items in per_domain.items():
            self.assertEqual(len(items), 20, f"Domain {dom} does not have 20 queries")
            dev_count = sum(1 for i in items if i["split"] == "dev")
            holdout_count = sum(1 for i in items if i["split"] == "holdout")
            self.assertEqual(dev_count, 15, f"Domain {dom} dev count != 15")
            self.assertEqual(holdout_count, 5, f"Domain {dom} holdout count != 5")

        # Verify query variety (PT/EN, NL, camelCase, snake_case, typo, ambiguous, negative, multi-hop, media/code/decision)
        qtypes = {q["query_type"] for q in self.dataset["queries"]}
        for required_type in (
            "pt_canonical",
            "en_canonical",
            "natural_language_pt",
            "natural_language_en",
            "technical_term",
            "camel_case",
            "snake_case",
            "typo",
            "ambiguous",
            "negative_absent",
            "negative_unavailable",
            "multi_hop",
            "modality_code",
            "modality_decision",
            "modality_media",
        ):
            self.assertIn(required_type, qtypes)

        # Negative queries distinguish absence vs unavailability
        neg_reasons = {
            q["negative_reason"]
            for q in self.dataset["queries"]
            if q["expected_status"] == "abstain"
        }
        self.assertEqual(neg_reasons, {"absent_in_corpus", "unavailable_private_scope"})

        # Deterministic regeneration produces identical dataset SHA-256
        regen = gsb.generate_gold_set_queries()
        self.assertEqual(regen["dataset_sha256"], self.dataset["dataset_sha256"])

    def test_evaluate_gold_set_meets_thresholds_and_outperforms_ablations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report = gsb.evaluate_gold_set(
                write_reports=True,
                json_report_path=tmp_path / "GOLD-SET-BENCHMARK.json",
                md_report_path=tmp_path / "GOLD-SET-BENCHMARK.md",
            )
            self.assertTrue((tmp_path / "GOLD-SET-BENCHMARK.json").is_file())
            self.assertTrue((tmp_path / "GOLD-SET-BENCHMARK.md").is_file())

        self.assertTrue(report["gate_passed"])
        ov = report["overall"]
        self.assertGreaterEqual(ov["resolution_rate"], 0.95)
        self.assertGreaterEqual(ov["recall_at_20"], 0.90)
        self.assertGreaterEqual(ov["precision_at_10"], 0.85)
        self.assertGreater(ov["mrr"], 0.90)
        self.assertGreater(ov["ndcg_at_10"], 0.90)
        self.assertGreaterEqual(ov["p95_latency_ms"], 0.0)
        self.assertGreater(ov["mean_tokens"], 0.0)
        self.assertGreater(ov["mean_bytes"], 0.0)

        # Holdout split also meets thresholds independently
        holdout = report["splits"]["holdout"]
        self.assertEqual(holdout["count"], 115)
        self.assertGreaterEqual(holdout["resolution_rate"], 0.95)
        self.assertGreaterEqual(holdout["recall_at_20"], 0.90)
        self.assertGreaterEqual(holdout["precision_at_10"], 0.85)

        # Every single one of the 23 domains meets thresholds
        for dom in domain_ontology.REQUIRED_23_DOMAINS:
            dm = report["by_domain"][dom]
            self.assertGreaterEqual(dm["resolution_rate"], 0.95, f"{dom} resolution_rate")
            self.assertGreaterEqual(dm["recall_at_20"], 0.90, f"{dom} recall@20")
            self.assertGreaterEqual(dm["precision_at_10"], 0.85, f"{dom} precision@10")

        # Full federated outperforms ablations
        abl = report["ablations"]
        self.assertGreater(abl["full_federated"]["recall_at_20"], abl["ablation_no_pt_en"]["recall_at_20"])
        self.assertGreater(abl["ablation_no_pt_en"]["recall_at_20"], abl["ablation_lexical_only"]["recall_at_20"])

    def test_cli_and_zero_emoji_compliance(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "gold_set_benchmark.py"), "--no-write"],
            capture_output=True,
            text=True,
            check=True,
        )
        parsed = json.loads(proc.stdout)
        self.assertEqual(parsed["total_queries"], 460)
        self.assertTrue(parsed["gate_passed"])

        for p in (
            ROOT / "config" / "gold_set_benchmark.json",
            SCRIPTS_DIR / "gold_set_benchmark.py",
            ROOT / "reports" / "GOLD-SET-BENCHMARK.json",
            ROOT / "reports" / "GOLD-SET-BENCHMARK.md",
            Path(__file__),
        ):
            self.assertTrue(p.is_file(), f"Missing file {p}")
            self.assertEqual(EMOJI_REGEX.findall(p.read_text(encoding="utf-8")), [], f"Emoji in {p}")


if __name__ == "__main__":
    unittest.main()
