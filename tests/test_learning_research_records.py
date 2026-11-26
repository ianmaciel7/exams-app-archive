import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import research_index as ri

def test_learning_evidence_index_and_source_identity():
    rows=ri.load_records()
    expected={"interleaving-material-similarity","explanatory-feedback-content","retrieval-transfer-outcomes"}
    selected=[r for r in rows if r["catalog"]=="domain-research" and r["record_id"] in expected]
    assert {r["record_id"] for r in selected}==expected
    assert ri.verify_record_provenance(selected)["integrity_passed"]
    assert all(r["record"]["evidence_status"]=="abstract-reviewed" and r["sources"] for r in selected)
    with sqlite3.connect(":memory:") as db:
        ri.build(db,rows)
        for query,record in [("interleaving","interleaving-material-similarity"),("explanatory feedback","explanatory-feedback-content"),("retrieval practice transfer","retrieval-transfer-outcomes")]:
            assert any(r["record_id"]==record for r in ri.search(db,query,"pattern",limit=100))
