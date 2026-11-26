import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import archive_context as ac
import concept_packs as cp
import research_index as ri

def test_snapshot_changes_if_projection_changes():
    rows=ri.load_records()
    taxonomy=cp.load_taxonomy()
    row=next(r for r in rows if r["catalog"]=="ai-product-graph")
    changed=copy.deepcopy(row)
    changed["record"]["description"]="altered projection"
    assert ac.snapshot([row],taxonomy)!=ac.snapshot([changed],taxonomy)

def test_snippets_and_packs_preserve_original_record_locator():
    rows=ri.load_records()
    taxonomy=cp.load_taxonomy()
    pack=cp.build_pack("sidebar",rows,taxonomy)["packs"][0]
    by_id={r["id"]:r for r in rows}
    for bucket in pack["evidence"]:
        for occ in bucket["occurrences"]:
            row=by_id[occ["id"]]
            snippet=ac.make_snippet(row,"ui.navigation.sidebar",occ["classification"])
            for key in ("catalog_sha256","record_sha256","record_pointer","projection_sha256"):
                assert occ[key]==row[key]==snippet["provenance"][key]
