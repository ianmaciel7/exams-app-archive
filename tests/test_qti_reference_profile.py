import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from qti_reference_profile import ChoiceItem, export_item, import_item, MAX_BYTES

ITEM=ChoiceItem("fictional_item_v1","Questão fictícia","pt-BR","Qual opção contém A & B?",
                (("a","A & B"),("b","C < D")),"a")

def test_original_text_and_response_roundtrip():
    raw=export_item(ITEM)
    assert b"max-choices=\"1\"" in raw and b"match_correct.xml" in raw
    assert import_item(raw)==ITEM
    assert export_item(import_item(raw))==raw

@pytest.mark.parametrize("mutation",[
    lambda x:x.replace(b'cardinality="single"',b'cardinality="multiple"',1),
    lambda x:x.replace(b'max-choices="1"',b'max-choices="2"'),
    lambda x:x.replace(b'match_correct.xml',b'map_response.xml'),
    lambda x:x.replace(b'</qti-item-body>',b'<qti-extended-text-interaction/></qti-item-body>'),
    lambda x:x.replace(b'</qti-item-body>',b'<qti-rubric-block>extra</qti-rubric-block></qti-item-body>'),
    lambda x:x.replace(b'<qti-value>a</qti-value>',b'<qti-value>unknown</qti-value>'),
    lambda x:b'<!DOCTYPE x [<!ENTITY e "bad">]>'+x,
    lambda x:x.replace(b'encoding=\'utf-8\'',b'encoding=\'iso-8859-1\''),
    lambda x:b' '* (MAX_BYTES+1),
])
def test_unsupported_or_unsafe_inputs_are_rejected(mutation):
    with pytest.raises(ValueError):
        import_item(mutation(export_item(ITEM)))
