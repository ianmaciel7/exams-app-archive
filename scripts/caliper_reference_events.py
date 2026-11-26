"""Fictional local Caliper 1.2 AssessmentEvent example, not a sensor or certification."""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from uuid import UUID, uuid5

CONTEXT = "http://purl.imsglobal.org/ctx/caliper/v1p2"
ORIGIN = "https://assessment.example.invalid"
NAMESPACE = UUID("58ee953b-4120-41ce-93ad-dc6ed9b13451")

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",value):
        raise ValueError("expected opaque fictional identifier")
    return value

def timestamp(value):
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware event time required")
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")

@dataclass(frozen=True)
class Attempt:
    participant: str
    assessment: str
    edition: int
    attempt_id: str
    count: int
    started: datetime

    def __post_init__(self):
        for value in (self.participant,self.assessment,self.attempt_id):
            identifier(value)
        if type(self.edition) is not int or self.edition<1 or type(self.count) is not int or self.count<1:
            raise ValueError("positive edition and attempt number required")
        timestamp(self.started)

def event(attempt,action,occurred):
    if action not in {"Started","Submitted"}:
        raise ValueError("unsupported action in narrow profile")
    when=timestamp(occurred)
    if occurred<attempt.started or (action=="Started" and occurred!=attempt.started):
        raise ValueError("invalid lifecycle time")
    actor=f"{ORIGIN}/people/{attempt.participant}"
    assessment=f"{ORIGIN}/assessments/{attempt.assessment}/editions/{attempt.edition}"
    attempt_iri=f"{assessment}/attempts/{attempt.attempt_id}"
    generated={"id":attempt_iri,"type":"Attempt","assignee":actor,"assignable":assessment,
               "count":attempt.count,"startedAtTime":timestamp(attempt.started)}
    if action=="Submitted":
        generated["endedAtTime"]=when
    # Same immutable business event produces the same UUID on retries.
    return {"@context":CONTEXT,"id":"urn:uuid:"+str(uuid5(NAMESPACE,attempt_iri+"/"+action)),
            "type":"AssessmentEvent","profile":"AssessmentProfile",
            "actor":{"id":actor,"type":"Person"},"action":action,
            "object":{"id":assessment,"type":"Assessment"},"generated":generated,
            "eventTime":when,"edApp":ORIGIN}

class LocalEventLedger:
    """Ordered in-memory reference; no network, persistence or exactly-once delivery."""
    def __init__(self):
        self._attempts={}
        self._event_bytes={}

    def record(self,attempt,action,occurred):
        candidate=event(attempt,action,occurred)
        raw=json.dumps(candidate,sort_keys=True,separators=(",",":"))
        ident=candidate["id"]
        if ident in self._event_bytes:
            if self._event_bytes[ident]!=raw:
                raise ValueError("conflicting event retry")
            return False
        key=candidate["generated"]["id"]
        current=self._attempts.get(key)
        if action=="Started":
            if current is not None:
                raise ValueError("attempt already exists")
        elif current != ("Started",attempt):
            raise ValueError("submission requires matching started attempt")
        self._event_bytes[ident]=raw
        self._attempts[key]=(action,attempt)
        return True

    def events(self):
        return [json.loads(raw) for raw in self._event_bytes.values()]
