#!/usr/bin/env python3
"""Tests for PT<->EN search expansion, benchmark metrics, and zero-emoji compliance."""
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

import archive_index  # noqa: E402
import search_benchmark  # noqa: E402
import search_expansion  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class SearchExpansionTests(unittest.TestCase):
    def test_dictionary_version_and_bidirectional_pairs(self):
        stats = search_expansion.dictionary_stats()
        self.assertEqual(stats["version"], search_expansion.DICTIONARY_VERSION)
        self.assertGreaterEqual(stats["group_count"], 30)

        cases = [
            ("grafo", "graph"),
            ("graph", "grafo"),
            ("barra lateral", "sidebar"),
            ("sidebar", "barra lateral"),
            ("simulado", "exam"),
            ("simulado", "mock"),
            ("questão", "question"),
            ("prova", "exam"),
        ]
        for query, expected_synonym in cases:
            expanded = search_expansion.expand_query(query)
            self.assertIn(expected_synonym, expanded["expanded_terms"], f"{query} -> {expanded}")
            self.assertTrue(expanded["fts_matchers"])

    def test_accent_folding_and_phrase_isolation(self):
        res = search_expansion.expand_query("Questão de Barra Lateral")
        self.assertEqual(res["normalized_query"], "questao de barra lateral")
        self.assertIn("barra lateral", res["phrase_matches"])
        self.assertIn("sidebar", res["expanded_terms"])
        self.assertIn("question", res["expanded_terms"])
        # Stopword 'de' should not generate standalone FTS concept groups
        self.assertFalse(any(group == ["de"] for group in res["groups"]))

    def test_empty_query_returns_empty_expansion(self):
        res = search_expansion.expand_query("   ")
        self.assertEqual(res["tokens"], [])
        self.assertEqual(res["expanded_terms"], [])
        self.assertEqual(res["fts_matchers"], [])

    def test_expanded_image_terms_include_slug_variants(self):
        terms = search_expansion.expanded_image_terms("barra lateral")
        self.assertIn("sidebar", terms)
        self.assertIn("barra-lateral", terms)
        self.assertIn("barra_lateral", terms)


class SearchBenchmarkTests(unittest.TestCase):
    def test_ir_metric_calculations(self):
        metrics = search_benchmark.compute_ir_metrics(
            ["d_noise", "d_rel_1", "d_rel_2", "d_noise_2"],
            ("d_rel_1", "d_rel_2", "d_rel_3"),
            k=4,
        )
        self.assertEqual(metrics["precision_at_k"], 0.5)
        self.assertEqual(metrics["recall_at_k"], round(2 / 3, 4))
        self.assertEqual(metrics["mrr"], 0.5)

        miss = search_benchmark.compute_ir_metrics(["d_noise"], ("d_rel_1",), k=4)
        self.assertEqual(miss, {"precision_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0})

    def test_synthetic_benchmark_improves_with_bm25_and_pt_en_expansion(self):
        report = search_benchmark.run_synthetic_benchmark(k=8, repetitions=2)
        summary = report["summary"]

        for key in ("fts5_legacy", "fts5_bm25_16", "fts5_bm25_pt_en", "semantic_proxy_local"):
            self.assertIn(key, summary)
            self.assertGreaterEqual(summary[key]["mean_latency_ms"], 0.0)
            self.assertGreater(summary[key]["mean_response_tokens"], 0.0)

        # #16 (BM25 + kind quotas) outperforms pre-#16 legacy FTS5
        self.assertGreater(
            summary["fts5_bm25_16"]["mean_precision_at_k"],
            summary["fts5_legacy"]["mean_precision_at_k"],
        )
        self.assertGreater(
            summary["fts5_bm25_16"]["mean_recall_at_k"],
            summary["fts5_legacy"]["mean_recall_at_k"],
        )

        # PT<->EN expansion outperforms both BM25 without expansion and semantic proxy
        self.assertGreater(
            summary["fts5_bm25_pt_en"]["mean_recall_at_k"],
            summary["fts5_bm25_16"]["mean_recall_at_k"],
        )
        self.assertGreater(
            summary["fts5_bm25_pt_en"]["mean_precision_at_k"],
            summary["fts5_bm25_16"]["mean_precision_at_k"],
        )
        self.assertGreater(
            summary["fts5_bm25_pt_en"]["mean_recall_at_k"],
            summary["semantic_proxy_local"]["mean_recall_at_k"],
        )
        self.assertEqual(summary["fts5_bm25_pt_en"]["mrr"], 1.0)

    def test_archive_index_search_uses_pt_en_expansion(self):
        docs, _ = search_benchmark.build_synthetic_corpus()
        with tempfile.TemporaryDirectory() as tmp:
            conn, _ = search_benchmark.populate_synthetic_db(Path(tmp) / "bench.sqlite", docs)
            try:
                no_exp = archive_index.search(conn, "prova", limit=8, expand_pt_en=False)
                with_exp = archive_index.search(conn, "prova", limit=8, expand_pt_en=True)
                self.assertEqual(no_exp, [])
                self.assertTrue(any(r["path"] == "src/domain/exams/exam.ts" for r in with_exp))

                grafo_exp = archive_index.search(conn, "grafo", limit=8, kind="file", expand_pt_en=True)
                self.assertTrue(any("graph-canvas.tsx" in r["path"] for r in grafo_exp))
            finally:
                conn.close()

    def test_benchmark_cli_produces_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "bench.json"
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "search_benchmark.py"), "--k", "8", "--repetitions", "1", "--output", str(out_file)],
                capture_output=True,
                text=True,
                check=True,
            )
            parsed = json.loads(proc.stdout)
            self.assertEqual(parsed["mode"], "synthetic_ground_truth")
            self.assertTrue(out_file.is_file())

    def test_report_and_zero_emoji_policy(self):
        report_path = ROOT / "reports" / "SEARCH-BENCHMARK.md"
        self.assertTrue(report_path.is_file())
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("adotar", report_text.lower())
        self.assertIn("fts5", report_text.lower())
        self.assertIn("bm25", report_text.lower())

        files_to_check = [
            SCRIPTS_DIR / "search_expansion.py",
            SCRIPTS_DIR / "search_benchmark.py",
            SCRIPTS_DIR / "archive_index.py",
            report_path,
            Path(__file__),
        ]
        for path in files_to_check:
            content = path.read_text(encoding="utf-8")
            self.assertEqual(EMOJI_REGEX.findall(content), [], f"Found disallowed emoji in {path}")


if __name__ == "__main__":
    unittest.main()
