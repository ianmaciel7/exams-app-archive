import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_token_contrast import SPEC, contrast, evaluate

def test_spec_pairs():
    rows = evaluate(SPEC.read_text(encoding="utf-8"))
    assert len(rows) == 46
    assert all(ratio >= minimum for _, ratio, minimum in rows)

def test_mutation_reintroduces_unsafe_text():
    text = SPEC.read_text(encoding="utf-8").replace("#315eb8", "#3f6fce")
    assert any(name == "blue-file" and ratio < minimum for name,ratio,minimum in evaluate(text))

def test_known_extremes():
    assert contrast("#ffffff","#000000") == 21
    assert contrast("#ffffff","#ffffff") == 1
