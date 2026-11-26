import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import federated_retrieval as fr
from check_public_evaluation import gate
from production_retrieval_eval import score

def test_public_code_search_does_not_read_arbitrary_file(tmp_path, monkeypatch):
    private = tmp_path / "private.txt"
    private.write_text("keyboard-secret-token",encoding="utf-8")
    original = Path.read_text
    def guard(self,*args,**kwargs):
        assert self != private, "public retrieval attempted private file read"
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,"read_text",guard)
    hits,_ = fr._search_public_ast_code("keyboard secret",paths=[private])
    assert hits == []

def test_public_code_search_excludes_evaluation_modules():
    candidates = [fr.ROOT_DIR/"scripts"/name for name in
                  ("gold_set_benchmark.py","production_retrieval_eval.py","grounded_answer_eval.py")]
    hits,_ = fr._search_public_ast_code("benchmark gold set",paths=candidates)
    assert hits == []

def test_development_gate_detects_tampering_and_failed_retrieval(tmp_path):
    labels={f"p{i}":[f"record{i}"] for i in range(10)}
    labels["n"]=[]
    rows=[{"id":f"p{i}","hits":[{"id":f"record{i}","scope":"public"}],"unavailable":[],"latency_ms":1} for i in range(10)]
    rows.append({"id":"n","hits":[],"unavailable":[],"latency_ms":1})
    cp,lp,sp=(tmp_path/name for name in ("capture.json","labels.json","score.json"))
    def write_eval():
        cp.write_text(json.dumps(rows),encoding="utf-8")
        lp.write_text(json.dumps(labels),encoding="utf-8")
        result=score(rows,labels)
        result["capture_sha256"]=hashlib.sha256(cp.read_bytes()).hexdigest()
        result["labels_sha256"]=hashlib.sha256(lp.read_bytes()).hexdigest()
        sp.write_text(json.dumps(result),encoding="utf-8")
    write_eval()
    assert gate(cp,lp,sp)["development_regression_gate_passed"]
    bad=json.loads(sp.read_text())
    bad["mean_recall"]=.99
    sp.write_text(json.dumps(bad))
    assert not gate(cp,lp,sp)["development_regression_gate_passed"]
    rows[0]["hits"]=[]
    rows[1]["hits"]=[]
    rows[2]["hits"]=[]
    write_eval()
    assert not gate(cp,lp,sp)["development_regression_gate_passed"]
