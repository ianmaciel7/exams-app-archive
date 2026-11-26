import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_ai_product_budget import compare

def row(budget, hits, omitted=()):
    return {"id": "q", "query": "public question", "snapshot": "same", "hits": [{"id": h, "scope": "public"} for h in hits],
            "budget": {"budget_tokens": budget, "total_tokens": 100}, "omitted_for_budget": [{"id": h} for h in omitted],
            "unavailable": [], "latency_ms": 1}

def test_budget_comparison_identifies_recovery():
    report = compare([row(2000, ["a"], ["b"])], [row(8000, ["a", "b"])], {"q": ["b"]})
    assert report["cases"][0]["recovered_at_expanded_budget"] == ["b"]
    assert report["cases"][0]["missing_target_explicitly_omitted"] == ["b"]
    assert report["default_budget"]["mean_recall"] == 0
    assert report["expanded_budget"]["mean_recall"] == 1

def test_budget_comparison_rejects_snapshot_change():
    a, b = row(2000, []), row(8000, [])
    b["snapshot"] = "changed"
    with pytest.raises(ValueError):
        compare([a], [b], {"q": []})
