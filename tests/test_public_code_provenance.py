import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import federated_retrieval as fr

def test_pin_exact_bytes_and_dirty_worktree(tmp_path):
    def git(*args):
        return subprocess.check_output(["git","-C",str(tmp_path),*args]).decode().strip()
    git("init")
    git("config","user.name","Fixture")
    git("config","user.email","fixture@example.invalid")
    path=tmp_path/"source.py"
    raw=b"def example():\r\n    return 1\r\n"
    path.write_bytes(raw)
    git("add","source.py")
    git("commit","-m","fixture")
    commit,blob,status=fr._public_git_pin(tmp_path,"source.py",raw)
    assert commit==git("rev-parse","HEAD")
    assert blob==git("rev-parse","HEAD:source.py")
    assert status=="verified"
    commit,blob,status=fr._public_git_pin(tmp_path,"source.py",b"changed")
    assert not commit and status=="local-unpinned"

def test_distinct_ast_chunks_from_same_blob_are_not_collapsed():
    def hit(id,line,score):
        return fr._normalize_hit(hit_id=id,evidence_type="code",source_channel="public_ast_code",
            source_id="local",scope="public",title=id,snippet=id,raw_score=score,
            blob_sha="same-file",record_sha256="same-text",metadata={"start_line":line,"end_line":line+1})
    rows,count=fr._deduplicate_blobs_preserving_occurrences([hit("a",1,.5),hit("b",10,.7),hit("c",1,.8)])
    assert count==1
    assert {r["id"] for r in rows}=={"b","c"}
    assert {o["hit_id"] for o in next(r for r in rows if r["id"]=="c")["occurrences"]}=={"a","c"}
