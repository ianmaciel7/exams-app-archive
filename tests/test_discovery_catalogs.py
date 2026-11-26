import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import research_index as ri

def test_discovery_is_searchable_but_not_validated_evidence():
    rows=list(ri.discovery_records())
    assert len(rows)==231
    assert len({r["id"] for r in rows})==len(rows)
    assert all(r["kind"]=="source" and r["availability"]=="link-only" for r in rows)
    assert ri.verify_record_provenance(rows)["integrity_passed"]
    with sqlite3.connect(":memory:") as db:
        ri.build(db,ri.load_records())
        for query,ident in [("welie","discovery-1:welie"),
                            ("pixlpin","visual-discovery:visual-collector-pixlpin"),
                            ("1win DESIGN","design-md-discovery:1win")]:
            assert any(r["id"]==ident for r in ri.search(db,query,"source",limit=100)),query

def test_discovery_no_invented_media_or_review_status():
    rows=list(ri.discovery_records())
    assert all("visual_review" not in r["record"] for r in rows)
    assert all(r["confidence"] and r["record"]["status"]==r["confidence"] for r in rows)
    assert not any(r["kind"]=="visual" for r in rows)
