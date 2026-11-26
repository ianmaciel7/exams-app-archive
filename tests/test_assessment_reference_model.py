import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from assessment_reference_model import Item, Form, Submission, AssessmentLedger, item_statistics

def test_frozen_item_form_and_original_attempt_survive_regrade():
    ledger=AssessmentLedger()
    old=Item("a",1,"Fictional question","x")
    newer=Item("a",2,"Revised fictional question","y")
    ledger.add_item(old)
    form=Form("f",1,(old,),"original")
    ledger.publish(form)
    sub=Submission("attempt-1","fictional-user",form,(("a","x"),))
    initial=ledger.submit(sub)
    assert initial.marks==(1,)
    assert ledger.submit(sub)==initial
    ledger.add_item(newer)
    with pytest.raises(ValueError):
        ledger.add_item(Item("a",1,"modified","y"))
    with pytest.raises(ValueError):
        ledger.publish(Form("f",1,(newer,),"original"))
    with pytest.raises(ValueError):
        ledger.submit(Submission("attempt-1","fictional-user",form,(("a","y"),)))
    revised=ledger.regrade("attempt-1","corrected",keys={"a":"y"})
    assert revised.marks==(0,)
    assert ledger.results["attempt-1"]==(initial,revised)
    assert ledger.submissions["attempt-1"].form.items==(old,)
    assert ledger.submit(sub)==initial

def test_denominators_and_undefined_metrics():
    rows=[("p1",(1,1)),("p2",(0,0)),("p3",(1,0)),("p1",(0,0))]
    first=item_statistics(rows,0,cohort="fictional cohort A",first_attempt_only=True)
    all_=item_statistics(rows,0,cohort="fictional cohort A",first_attempt_only=False)
    assert first["attempts"]==3 and first["facility"]==pytest.approx(2/3)
    assert all_["attempts"]==4 and all_["facility"]==.5
    assert all_["participants"]==3
    assert item_statistics([("p",(1,0)),("q",(1,1))],0,cohort="constant",first_attempt_only=True)["corrected_item_total_pearson"] is None
    assert item_statistics([],0,cohort="empty",first_attempt_only=True)["facility"] is None
    assert item_statistics([("p",(1,1)),("q",(0,0))],0,cohort="positive",first_attempt_only=True)["corrected_item_total_pearson"]==pytest.approx(1)
