import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from caliper_reference_events import Attempt, LocalEventLedger, event, CONTEXT

START=datetime(2026,1,1,12,tzinfo=timezone(timedelta(hours=-3)))
ATTEMPT=Attempt("fictional-person","fictional-exam",1,"a1",1,START)

def test_started_and_submitted_share_attempt_but_not_event_identity():
    ledger=LocalEventLedger()
    assert ledger.record(ATTEMPT,"Started",START)
    assert not ledger.record(ATTEMPT,"Started",START)
    end=START+timedelta(minutes=10)
    assert ledger.record(ATTEMPT,"Submitted",end)
    assert not ledger.record(ATTEMPT,"Submitted",end)
    started,submitted=ledger.events()
    assert started["@context"]==CONTEXT
    assert started["eventTime"]=="2026-01-01T15:00:00.000Z"
    assert submitted["generated"]["endedAtTime"]=="2026-01-01T15:10:00.000Z"
    assert started["generated"]["id"]==submitted["generated"]["id"]
    assert started["id"]!=submitted["id"]
    assert submitted["generated"]["count"]==1
    assert "score" not in submitted and "score" not in submitted["generated"]
    with pytest.raises(ValueError,match="conflicting"):
        ledger.record(ATTEMPT,"Submitted",end+timedelta(seconds=1))

def test_reject_out_of_order_wrong_attempt_and_unsafe_identifiers():
    ledger=LocalEventLedger()
    with pytest.raises(ValueError,match="matching started"):
        ledger.record(ATTEMPT,"Submitted",START)
    ledger.record(ATTEMPT,"Started",START)
    other=Attempt("different-person","fictional-exam",1,"a1",1,START)
    with pytest.raises(ValueError):
        ledger.record(other,"Submitted",START)
    with pytest.raises(ValueError):
        event(ATTEMPT,"Submitted",START-timedelta(seconds=1))
    with pytest.raises(ValueError):
        event(ATTEMPT,"Submitted",START.replace(tzinfo=None))
    with pytest.raises(ValueError):
        event(ATTEMPT,"Graded",START)
    with pytest.raises(ValueError):
        Attempt("email@example.invalid","fictional-exam",1,"a2",2,START)
    assert len(ledger.events())==1

def test_distinct_attempt_and_version_ids():
    e=event(ATTEMPT,"Started",START)
    for other in (Attempt("fictional-person","fictional-exam",1,"a2",2,START),
                  Attempt("fictional-person","fictional-exam",2,"a1",1,START)):
        assert event(other,"Started",START)["id"]!=e["id"]
