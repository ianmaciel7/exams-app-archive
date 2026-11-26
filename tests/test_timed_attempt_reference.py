import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from timed_attempt_reference import start, dispatch, view, Phase

def test_confirm_cancel_submit_retry_and_orthogonal_flags():
    a=start("demo",("a","b"),100,20)
    a=dispatch(a,"answer",101,item="a",value="choice1")
    a=dispatch(a,"flag",102,item="a",value=True)
    assert view(a)["item_states"][0]=={"id":"a","answered":True,"flagged":True,"current":True}
    a=dispatch(a,"navigate",103,item="b")
    a=dispatch(a,"finish",104)
    assert a.phase==Phase.CONFIRMING and not view(a)["can_edit"]
    with pytest.raises(ValueError):
        dispatch(a,"answer",104,item="b",value="choice2")
    a=dispatch(a,"cancel",105)
    assert a.phase==Phase.ACTIVE and view(a)["unanswered"]==1
    a=dispatch(a,"finish",106)
    a=dispatch(a,"submit",107)
    assert a.phase==Phase.SUBMITTED and a.finalized_at==107
    assert dispatch(a,"submit",108)==a
    assert dispatch(a,"answer",109,item="b",value="late")==a

def test_deadline_wins_over_confirmation_and_reconnect():
    a=start("demo",("a",),100,20)
    a=dispatch(a,"answer",110,item="a",value="choice")
    confirming=dispatch(a,"finish",119)
    expired=dispatch(confirming,"submit",120)
    assert expired.phase==Phase.EXPIRED and expired.finalized_at==120
    assert expired.answers==a.answers and view(expired)["remaining"]==0
    assert dispatch(a,"resume",150).phase==Phase.EXPIRED
    assert dispatch(expired,"cancel",151)==expired

def test_invalid_events_and_clear_answer():
    a=start("demo",("a","b"),100,20)
    for event,kwargs in [("submit",{}),("navigate",{"item":"z"}),("answer",{"item":"b","value":"x"})]:
        with pytest.raises(ValueError):
            dispatch(a,event,101,**kwargs)
    a=dispatch(a,"answer",102,item="a",value="x")
    a=dispatch(a,"answer",103,item="a",value=None)
    assert view(a)["answered"]==0
    with pytest.raises(ValueError):
        dispatch(a,"tick",102)
    with pytest.raises(ValueError):
        start("demo",("a","a"),100,20)
