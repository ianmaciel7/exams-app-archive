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
