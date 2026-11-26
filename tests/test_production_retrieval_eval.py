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
