import json
import shutil
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import research_index as ri

def test_motion_and_capacities_references_preserve_evidence_status():
    rows=list(ri.motion_reference_records())
    assert len(rows)==42
    assert ri.verify_record_provenance(rows)["integrity_passed"]
    assert all(r["kind"]=="source" for r in rows)
    assert sum(r["record"].get("visual_inspection")=="fetch-failed" for r in rows)==3
    assert sum(r["record"].get("playback")=="not-recorded" for r in rows)==10
    assert sum(r["availability"]=="source-copy-declared" for r in rows)==11
    with sqlite3.connect(":memory:") as db:
        ri.build(db,ri.load_records())
        assert any(r["catalog"]=="motion-reference" for r in ri.search(db,"shared layout","source",product="Motion",limit=100))
        assert any(r["catalog"]=="motion-reference" for r in ri.search(db,"small card","source",product="Capacities",limit=100))

def test_source_bytes_and_mutation(tmp_path):
    result=ri.verify_motion_source_copies()
    assert result["checked"]==result["total"]==11 and result["integrity_passed"]
    parent=tmp_path/"ui-ux-patterns-2026-11-25"
    parent.mkdir()
    shutil.copyfile(ri.BASE/ri.MOTION_CATALOG,tmp_path/ri.MOTION_CATALOG)
    shutil.copytree(ri.BASE/"ui-ux-patterns-2026-11-25"/"motion-source",parent/"motion-source")
    (parent/"motion-source"/"Events-whileTap.tsx").write_bytes(b"tampered")
    result=ri.verify_motion_source_copies(base=tmp_path)
    assert not result["integrity_passed"] and result["checked"]==10
