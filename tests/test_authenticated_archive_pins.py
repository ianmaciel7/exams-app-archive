import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import federated_retrieval as fr

def test_missing_actual_digest_and_untrusted_mount_denied():
    for ctx in [
        fr.AuthenticatedArchiveContext(authorized=True,provenance_verified=True,expected_index_checksum="a"*64),
        fr.AuthenticatedArchiveContext(authorized=True,pinned_source_sha="a"*40,documents=[{}]),
        fr.AuthenticatedArchiveContext(authorized=True,provenance_verified=True,pinned_repo="other",allowed_repos=("fixture",)),
    ]:
        assert ctx.validate()

def test_documents_and_ast_reject_absent_wrong_and_unverified_metadata():
    base={"repo":"fixture","ref":"refs/heads/test","commit_sha":"a"*40,
          "title":"synthetic search","name":"synthetic search","path":"fixture.py",
          "content":"synthetic search example","provenance_status":"verified"}
    rows=[base,{**base,"repo":""},{**base,"repo":"other"},
          {**base,"ref":""},{**base,"commit_sha":""},{**base,"commit_sha":"b"*40},
          {**base,"provenance_status":"unverified"},{k:v for k,v in base.items() if k!="provenance_status"}]
    ctx=fr.AuthenticatedArchiveContext(authorized=True,provenance_verified=True,
        allowed_repos=("fixture",),pinned_repo="fixture",pinned_ref="refs/heads/test",
        pinned_source_sha="a"*40,documents=rows,ast_chunks=rows)
    for search in (fr._search_authenticated_documents,fr._search_authenticated_ast):
        hits,audit=search("synthetic search",ctx)
        assert len(hits)==audit.hits==1
        assert hits[0]["provenance"]["commit_sha"]=="a"*40

def test_image_catalog_is_not_recovered_bytes():
    base={"repo":"fixture","ref":"refs/heads/test","commit":"a"*40,
          "path":"synthetic-sidebar.png","screen":"sidebar","blob_sha":"b"*40}
    ctx=fr.AuthenticatedArchiveContext(authorized=True,provenance_verified=True,
        allowed_repos=("fixture",),pinned_repo="fixture",pinned_ref="refs/heads/test",
        pinned_source_sha="a"*40,image_records=[base,{**base,"commit":""},{**base,"repo":"other"},
        {**base,"ref":""},{**base,"blob_sha":"invalid"}])
    hits,_=fr._search_authenticated_images("sidebar",ctx)
    assert len(hits)==1
    assert hits[0]["provenance"]["provenance_status"]=="indexed-not-recovered"
    assert hits[0]["metadata"]["retrieval"]["bytes_verified_in_this_call"] is False
