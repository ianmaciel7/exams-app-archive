import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from federated_retrieval import _normalize_hit, _deduplicate_blobs_preserving_occurrences

def hit(id,url,score,kind="source"):
    return _normalize_hit(hit_id=id,evidence_type=kind,source_channel="public_research",
                          source_id=id,scope="public",title=id,snippet=id,raw_score=score,
                          path=id,record_sha256=id,metadata={"source_urls":[url]})

def test_same_url_retains_occurrences_and_representative():
    a=hit("a","https://example.org/a",.5)
    b=hit("b","https://EXAMPLE.org/a",.8)
    rows,count=_deduplicate_blobs_preserving_occurrences([a,b])
    assert count==1 and len(rows)==1
    assert rows[0]["id"]==rows[0]["title"]==rows[0]["provenance"]["path"]=="b"
    assert {o["hit_id"] for o in rows[0]["occurrences"]}=={"a","b"}

def test_distinct_patterns_or_sections_not_collapsed():
    a=hit("a","https://example.org/a#x",.5)
    b=hit("b","https://example.org/a#y",.8)
    c=hit("c","https://example.org/a#x",.5,"pattern")
    d=hit("d","https://example.org/a#x",.5,"pattern")
    rows,count=_deduplicate_blobs_preserving_occurrences([a,b,c,d])
    assert count==0 and len(rows)==4
