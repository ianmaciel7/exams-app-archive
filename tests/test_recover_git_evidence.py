import subprocess
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from recover_git_evidence import recover_blob

def test_pinned_recovery_from_actual_git_objects(tmp_path):
    def git(*args):
        return subprocess.run(["git","-C",str(tmp_path),*args],check=True,capture_output=True).stdout.decode().strip()
    git("init")
    git("config","user.name","Archive fixture")
    git("config","user.email","fixture@example.invalid")
    path = tmp_path / "dropdown-expanded.txt"
    path.write_bytes(b"filename is not evidence of an expanded dropdown")
    git("add",".")
    git("commit","-m","original")
    commit = git("rev-parse","HEAD")
    blob = git("rev-parse","HEAD:dropdown-expanded.txt")
    path.unlink()
    git("add","-A")
    git("commit","-m","remove")
    data, proof = recover_blob(tmp_path,commit,path.name,blob)
    assert data.startswith(b"filename")
    assert proof["blob_sha"] == blob
    assert proof["visual_inspection"] == "not_performed"
    with pytest.raises(ValueError):
        recover_blob(tmp_path,commit,path.name,blob,max_bytes=1)
    with pytest.raises(ValueError):
        recover_blob(tmp_path,commit,path.name,"0"*len(blob))
    with pytest.raises(ValueError):
        recover_blob(tmp_path,commit,"../other",blob)
    with pytest.raises(ValueError):
        recover_blob(tmp_path,"HEAD",path.name,blob)
