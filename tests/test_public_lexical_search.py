import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from public_lexical_search import ranked, adequate_hit

def item(id, title, aliases=(), **data):
    return {"id":id,"title":title,"record":{"aliases":list(aliases),**data}}

def test_natural_language_and_bilingual_terms():
    records = [item("a","Document navigation and keyboard shortcuts", ["navegacao","teclado"]),
               item("b","Keyboard hardware", ["teclado"]),
               item("c","Unrelated")]
    assert ranked("Como usar navegação por teclado?",records)[0][0]["id"] == "a"
    assert not ranked("What is the serial number of my kitchen oven?",records)

def test_metadata_cannot_match():
    rows = [item("a","Unrelated")]
    rows[0]["catalog_path"] = "password-keyboard-shortcuts"
    assert not ranked("keyboard shortcuts",rows)

def test_multiple_concepts_and_aliases():
    rows = [item("a","Save filters",["guardar","criterios"]),
            item("b","Save files")]
    assert ranked("guardar criterios",rows)[0][0]["id"] == "a"
    assert not adequate_hit("keyboard shortcuts",{"title":"keyboard hardware","snippet":""})
