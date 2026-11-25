#!/usr/bin/env python3
"""Tests for tripartite Grounded Answer Evaluation (#88)."""
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

import gold_set_benchmark as gsb  # noqa: E402
import grounded_answer_eval as gae  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class GroundedAnswerEvalTests(unittest.TestCase):
    def test_tripartite_evaluation_passes_thresholds_and_preserves_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report = gae.evaluate_all_grounded_answers(
                write_reports=True,
                json_report_path=tmp_path / "GROUNDED-ANSWER-EVAL.json",
                md_report_path=tmp_path / "GROUNDED-ANSWER-EVAL.md",
            )
            self.assertTrue((tmp_path / "GROUNDED-ANSWER-EVAL.json").is_file())
            self.assertTrue((tmp_path / "GROUNDED-ANSWER-EVAL.md").is_file())

        self.assertTrue(report["gate_passed"])
        self.assertEqual(report["total_cases"], 465)

        l1 = report["tripartite_summary"]["layer_1_resolution"]
        l2 = report["tripartite_summary"]["layer_2_ranking"]
        l3 = report["tripartite_summary"]["layer_3_grounding"]
        self.assertGreaterEqual(l1["resolution_rate"], 0.95)
        self.assertGreaterEqual(l2["recall_at_20"], 0.90)
        self.assertGreaterEqual(l3["claim_support_rate"], 0.90)
        self.assertGreaterEqual(l3["citation_accuracy"], 0.90)
        self.assertGreaterEqual(l3["abstention_accuracy"], 0.95)
        self.assertEqual(l3["conflicts_preserved_rate"], 1.0)
        self.assertEqual(l3["hallucination_rate"], 0.0)

        # Verify adversarial cases explicitly
        adv_by_id = {a["case_id"]: a for a in report["adversarial_results"]}
        self.assertTrue(adv_by_id["adv-supersession-adr0002"]["layer_3_grounding"]["conflicts_preserved"])
        self.assertTrue(adv_by_id["adv-conflict-space-vs-workspace"]["layer_3_grounding"]["conflicts_preserved"])
        self.assertTrue(adv_by_id["adv-conflict-pin-tab-vs-sidebar"]["layer_3_grounding"]["conflicts_preserved"])
        self.assertTrue(adv_by_id["adv-inaccessible-private-bundle"]["layer_3_grounding"]["abstention_correct"])
        self.assertEqual(adv_by_id["adv-multihop-design-auth"]["layer_3_grounding"]["requirement_completeness"], 1.0)

    def test_detects_hallucination_despite_perfect_retrieval(self) -> None:
        ctx = gsb._build_corpus_indices()
        try:
            store = gae._build_evidence_store(ctx)
            case = {
                "case_id": "test-hallucination-case",
                "domain": "workspace",
                "case_type": "hallucination_probe",
                "expected_status": "resolved",
                "required_evidence_ids": ["decision:DEC-APP-SHELL-01"],
            }
            retrieval = {
                "resolved_ok": True,
                "recall_at_20": 1.0,
                "precision_at_10": 1.0,
                "mrr": 1.0,
                "retrieved_ids": ["decision:DEC-APP-SHELL-01"],
            }
            # 1. Unsupported fabricated claim even with valid retrieved ID
            bad_answer = {
                "status": "answered",
                "claims": [
                    {
                        "claim_id": "claim:1",
                        "text": "The system deploys Kubernetes pods with Redis Sentinel on port 6379.",
                        "cited_evidence_id": "decision:DEC-APP-SHELL-01",
                        "cited_origin": store["decision:DEC-APP-SHELL-01"].origin_ref,
                        "cited_version_or_sha": store["decision:DEC-APP-SHELL-01"].version_or_sha,
                    }
                ],
                "citations": [
                    {
                        "evidence_id": "decision:DEC-APP-SHELL-01",
                        "origin_ref": store["decision:DEC-APP-SHELL-01"].origin_ref,
                        "version_or_sha": store["decision:DEC-APP-SHELL-01"].version_or_sha,
                        "status": "accepted",
                    }
                ],
                "preserved_conflicts": [],
                "preserved_supersessions": [],
            }
            res = gae.evaluate_grounded_answer(case, retrieval, bad_answer, store)
            self.assertEqual(res["layer_2_ranking"]["recall_at_20"], 1.0)
            self.assertTrue(res["layer_3_grounding"]["hallucination_detected"])
            self.assertFalse(res["layer_3_grounding"]["grounded_pass"])
            self.assertEqual(res["layer_3_grounding"]["claim_support_rate"], 0.0)

            # 2. Answering instead of abstaining on absent/inaccessible evidence
            abs_case = {
                "case_id": "test-abstain-violation",
                "domain": "historico",
                "case_type": "negative_absent",
                "expected_status": "abstain",
            }
            abs_retrieval = {"resolved_ok": True, "recall_at_20": 1.0, "precision_at_10": 1.0, "mrr": 1.0, "retrieved_ids": []}
            res_abs = gae.evaluate_grounded_answer(abs_case, abs_retrieval, bad_answer, store)
            self.assertFalse(res_abs["layer_3_grounding"]["abstention_correct"])
            self.assertTrue(res_abs["layer_3_grounding"]["hallucination_detected"])
            self.assertIn("answered_on_abstention_case", res_abs["layer_3_grounding"]["hallucination_flags"])
        finally:
            ctx["research_db"].close()

    def test_cli_and_zero_emoji_compliance(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "grounded_answer_eval.py"), "--no-write"],
            capture_output=True,
            text=True,
            check=True,
        )
        parsed = json.loads(proc.stdout)
        self.assertTrue(parsed["gate_passed"])
        self.assertTrue(parsed["hallucination_detector_probe"]["hallucination_detected"])

        for p in (
            SCRIPTS_DIR / "grounded_answer_eval.py",
            ROOT / "reports" / "GROUNDED-ANSWER-EVAL.json",
            ROOT / "reports" / "GROUNDED-ANSWER-EVAL.md",
            Path(__file__),
        ):
            self.assertTrue(p.is_file(), f"Missing file {p}")
            self.assertEqual(EMOJI_REGEX.findall(p.read_text(encoding="utf-8")), [], f"Emoji in {p}")


if __name__ == "__main__":
    unittest.main()
