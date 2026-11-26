import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import research_index as ri

def test_every_original_record_and_projection_recoverable():
    rows=ri.load_records()
    result=ri.verify_record_provenance(rows)
    assert result["integrity_passed"], result["errors"]
    assert result["checked"]==len(rows)
    assert any(r["record_sha256"]!=r["projection_sha256"] for r in rows)
    assert all(r["record_pointer"].startswith("/") for r in rows)

def test_original_projection_pointer_and_catalog_tampering_fail():
    row=next(r for r in ri.load_records() if r["catalog"]=="ai-product-graph")
    for key,value in [("record_sha256","0"*64),("catalog_sha256","0"*64),
                      ("record_pointer","/nodes/999999"),
                      ("catalog_path","../private.json")]:
        changed={**row,key:value}
        assert not ri.verify_record_provenance([changed])["integrity_passed"]
    changed=copy.deepcopy(row)
    changed["record"]["label"]="tampered"
    assert not ri.verify_record_provenance([changed])["integrity_passed"]
