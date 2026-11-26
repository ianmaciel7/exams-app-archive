import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from production_retrieval_eval import run, score

def test_runner_has_no_label_inputs():
    seen = []
    def retrieve(query, **options):
        seen.append((query, options))
        return {"status":"ok","results":[{"id":"a"}]}
    rows = run([{"id":"opaque","query":"example"}], retrieve)
    assert seen == [("example", {"scope":"public","limit":20})]
    assert score(rows, {"opaque":["a"]})["mean_recall"] == 1
    assert score(rows, {"opaque":["b"]})["mean_recall"] == 0
    with pytest.raises(ValueError):
        run([{"id":"opaque","query":"example","expected_status":"ok"}], retrieve)

def test_negative_and_missing_denominators():
    rows = [{"id":"q","hits":[],"unavailable":[],"latency_ms":1}]
    report = score(rows, {"q":[]})
    assert report["mean_recall"] is None
    assert report["mean_precision"] is None
    assert report["cases"][0]["abstained"]


def test_runner_captures_budget_without_exposing_labels():
    seen = []
    def retrieve(query, **options):
        seen.append(options)
        return {"status": "ok", "results": [{"id": "a"}],
                "budget": {"budget_tokens": 8000},
                "omitted_for_budget": [{"id": "b", "reason": "budget_tokens_exceeded"}],
                "available_by_type": {"pattern": 2},
                "gaps": ["budget_truncated:1"]}
    rows = run([{"id": "q", "query": "example"}], retrieve, budget_tokens=8000)
    assert seen == [{"scope": "public", "limit": 20, "budget_tokens": 8000}]
    assert rows[0]["budget"]["budget_tokens"] == 8000
    assert rows[0]["omitted_for_budget"][0]["id"] == "b"
    assert rows[0]["available_by_type"] == {"pattern": 2}
    assert score(rows, {"q": ["b"]})["mean_recall"] == 0
    with pytest.raises(ValueError):
        run([{"id": "q", "query": "example"}], retrieve, budget_tokens=0)


def test_compact_runner_flag_is_opt_in():
    seen = []
    def retrieve(query, **options):
        seen.append(options)
        return {"status": "ok", "results": []}
    run([{"id": "q", "query": "example"}], retrieve, budget_tokens=2000, compact_occurrences=True)
    assert seen == [{"scope": "public", "limit": 20, "budget_tokens": 2000, "compact_occurrences": True}]


def test_relevance_first_runner_flag_is_opt_in():
    seen = []
    def retrieve(query, **options):
        seen.append(options)
        return {"status": "ok", "results": []}
    run([{"id": "q", "query": "example"}], retrieve, budget_tokens=2000,
        compact_occurrences=True, relevance_first=True)
    assert seen == [{"scope": "public", "limit": 20, "budget_tokens": 2000,
                     "compact_occurrences": True, "relevance_first": True}]


def test_runner_context_projection_and_scoring():
    from compare_public_context_payload import compare
    from public_context_payload import audit_digest
    def retrieve(query, **options):
        return {"scope": "public", "snapshot": "a"*64, "status": "ok",
                "results": [{"id": "a", "scope": "public", "evidence_type": "pattern",
                             "title": "Example", "snippet": "Evidence",
                             "occurrences": [{"hit_id": "alias"}]}]}
    rows = run([{"id": "q", "query": "example"}], retrieve, context_budget_tokens=2000)
    assert rows[0]["context_payload"]["audit_sha256"] == audit_digest(rows[0]["audit_response"])
    report = compare(rows, {"q": ["alias"]})
    assert report["projected_score"]["mean_recall"] == 1
    assert report["max_estimated_tokens"] <= 2000
    rows[0]["context_payload"]["audit_sha256"] = "tampered"
    with pytest.raises(ValueError):
        compare(rows, {"q": ["alias"]})
