import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import research_index as ri

def test_platform_records_preserve_scope_and_are_searchable():
    rows=ri.load_records()
    cases=[("questões objetivas","qconcursos-question-workspace"),
           ("simulado personalizado","qconcursos-custom-mock-exam"),
           ("taxa de acerto","tec-observed-item-difficulty"),
           ("study mode","crucial-exams-study-vs-test")]
    ids={i for _,i in cases}
    selected=[r for r in rows if r["catalog"]=="domain-research" and r["record_id"] in ids]
    assert {r["record_id"] for r in selected}==ids
    assert ri.verify_record_provenance(selected)["integrity_passed"]
    assert all(r["record"]["media_status"]=="not-inspected" and r["sources"] for r in selected)
    with sqlite3.connect(":memory:") as db:
        ri.build(db,rows)
        for query,ident in cases:
            assert any(r["record_id"]==ident for r in ri.search(db,query,"pattern",limit=100))
