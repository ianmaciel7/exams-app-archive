import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from knowledge_coverage_audit import audit, canonical_url

def row(id,kind,urls,**item):
    return {"id":id,"kind":kind,"sources":urls,"record":item}

def test_explicit_links_and_unknowns():
    url="https://example.org/a"
    result=audit([row("s","source",[url]),row("p","pattern",[url],issue=95,tests="proposed"),
                  row("v","visual",["https://example.org/b"],states=["open"],status="link-only")],
                 {"concepts":[{"id":"domain.workspace","members":["v"]}]})
    assert len(result["domains"])==23
    assert result["domains"]["concursos"]["patterns"]==1
    assert result["domains"]["concursos"]["declared_tests"]==1
    assert result["domains"]["workspace"]["inspected_visual_records"]==0
    assert result["records"][1]["visual_inspection"]=="not_established"
    assert result["sources"][0]["metadata_missing"]
    assert result["gap_counts"]["unregistered_reference_url"]==1
    assert result["integrity_passed"]

def test_removed_member_fails_integrity():
    result=audit([],{"concepts":[{"id":"domain.workspace","members":["missing"]}]})
    assert not result["integrity_passed"]
    assert result["gap_counts"]["dangling_concept_member"]==1
    assert result["gap_counts"]["domain_without_explicit_links"]==23

def test_url_normalization_does_not_merge_sections_or_query():
    assert canonical_url("https://EXAMPLE.org:443/a?x=1#b")=="https://example.org/a?x=1#b"
    assert canonical_url("https://example.org/a#x")!=canonical_url("https://example.org/a#y")

def test_source_only_domain_is_not_missing_or_validated():
    result=audit([row("s","source",["https://example.org/a"])],
                 {"concepts":[{"id":"domain.historico","members":["s"]}]})
    assert result["domains"]["historico"]["coverage_status"]=="source_links_only"
    assert result["domains"]["historico"]["source_urls"]==1
    assert result["domains"]["historico"]["patterns"]==0
    assert result["gap_counts"]["domain_with_source_links_only"]==1


def test_unlinked_source_triage_is_exhaustive_without_fabricating_links():
    a, b, c, d, e, linked = ["https://example.org/" + x for x in "abcdef"]
    rows = [
        row("design-md-discovery:a", "source", [a]),
        row("discovery-1:a", "source", [a]),
        row("general-sources:a", "source", [a]),
        row("discovery-2:b", "source", [b]),
        row("component-behavior-sources:b", "source", [b]),
        row("motion-reference:c", "source", [c]),
        row("component-behavior-sources:d", "source", [d]),
        row("general-sources:e", "source", [e]),
        row("general-sources:f", "source", [linked]),
        row("pattern:f", "pattern", [linked]),
    ]
    result = audit(rows, {"concepts": []})
    triage = result["unlinked_source_triage"]
    assert triage["counts"] == {
        "design_md_inventory": 1, "discovery_inventory": 1,
        "motion_reference": 1, "specialized_catalog": 1, "general_registry": 1,
    }
    assert result["gap_counts"]["unlinked_source"] == 5
    assert {x["url"] for x in triage["sources"]} == {a, b, c, d, e}
    assert len(triage["sources"][0]["source_ids"]) == 3
    assert result["integrity_passed"]
