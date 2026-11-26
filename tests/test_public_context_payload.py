import copy
import hashlib
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from public_context_payload import (audit_digest, canonical_json,
                                    estimate_context_tokens, project_context)


def hit(ident, text="Estado de progresso"):
    return {"id": ident, "scope": "public", "evidence_type": "pattern",
            "title": "Study", "snippet": text,
            "provenance": {"path": "docs/reference.json", "record_sha256": "a"*64,
                           "provenance_status": "verified"},
            "metadata": {"source_urls": ["https://example.org/reference"],
                         "availability": "documented", "product": "fictional"},
            "occurrences": [{"hit_id": ident}, {"hit_id": ident+"-alias"}]}


def audit(*hits):
    return {"scope": "public", "status": "ok", "snapshot": "b"*64,
            "results": list(hits), "omitted_for_budget": [{"id": "missing"}],
            "sources_unavailable": [{"id": "unavailable"}],
            "sources_consulted": [{"details": "x"*10000}]}


def test_projection_exact_envelope_and_audit_integrity():
    raw = audit(hit("a"), hit("b", "á"*900), hit("c"))
    before = copy.deepcopy(raw)
    payload = project_context(raw, budget_tokens=400, max_bytes=1600)
    assert raw == before
    assert payload["audit_sha256"] == hashlib.sha256(canonical_json(raw).encode()).hexdigest()
    assert payload["audit_sha256"] == audit_digest(raw)
    assert estimate_context_tokens(payload) <= 400
    assert len(canonical_json(payload).encode("utf-8")) <= 1600
    assert [h["id"] for h in payload["results"]] == ["a", "c"]
    assert payload["projection_omitted"] == 1
    assert payload["retrieval_omitted"] == 1
    assert payload["unavailable_sources"] == 1
    assert payload["results"][0]["occurrence_ids"] == ["a-alias"]
    assert payload["results"][0]["pointer"]["record_sha256"] == "a"*64
    assert payload["results"][0]["source_urls"] == ["https://example.org/reference"]
    assert payload["results"][0]["snippet"] == raw["results"][0]["snippet"]
    assert "sources_consulted" not in payload


def test_projection_fails_closed_and_preserves_empty_status():
    raw = audit(hit("a"))
    with pytest.raises(ValueError):
        project_context({**raw, "scope": "authenticated_archive"})
    with pytest.raises(ValueError):
        project_context(audit({**hit("b"), "scope": "authenticated_archive"}))
    with pytest.raises(ValueError):
        project_context(audit(hit("x"), hit("x")))
    with pytest.raises(ValueError):
        project_context({**raw, "snapshot": None})
    with pytest.raises(ValueError):
        project_context(raw, max_bytes=1)
    with pytest.raises(ValueError):
        project_context(raw, budget_tokens=True)
    empty = project_context({"scope": "public", "status": "no-evidence", "results": []})
    assert empty["results"] == []
    assert empty["retrieval_status"] == "no-evidence"
    assert empty["projection_omitted"] == 0


def test_projection_limits_include_all_serialized_fields():
    raw = audit(*(hit(str(i), "dados "*100) for i in range(20)))
    for budget in (128, 200, 500, 2000):
        p = project_context(raw, budget_tokens=budget)
        assert estimate_context_tokens(p) <= budget
        assert len(p["results"]) + p["projection_omitted"] == 20
        assert all(h["snippet"] == raw["results"][int(h["id"])]["snippet"] for h in p["results"])


def test_projection_preserves_source_qualifications_or_omits_whole_claim():
    h = hit("scope", "Example only")
    h["metadata"]["source_evidence"] = [[0, "Official example; runtime untested."]]
    raw = audit(h)
    projected = project_context(raw, budget_tokens=2000)
    assert projected["results"][0]["source_evidence"] == h["metadata"]["source_evidence"]
    assert projected["results"][0]["source_urls"] == h["metadata"]["source_urls"]
    assert estimate_context_tokens(projected) <= 2000
    smaller = project_context(raw, budget_tokens=128)
    assert not smaller["results"] and smaller["projection_omitted"] == 1
    h["metadata"]["source_evidence"] = [[1, "invalid index"]]
    with pytest.raises(ValueError):
        project_context(raw)
