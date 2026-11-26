"""Fictional timed assessment state contract, using caller-supplied trusted time.
No database, browser, transport, production authentication or timer service.
"""
from dataclasses import dataclass, replace
from enum import Enum

class Phase(str, Enum):
    ACTIVE="active"
    CONFIRMING="confirming"
    SUBMITTED="submitted"
    EXPIRED="expired"

@dataclass(frozen=True)
class Attempt:
    id: str
    items: tuple[str,...]
    deadline: int
    last_seen: int
    phase: Phase=Phase.ACTIVE
    answers: tuple[tuple[str,str],...]=()
    flagged: tuple[str,...]=()
    cursor: int=0
    finalized_at: int|None=None

def start(ident, items, now, duration):
    if (not ident or not items or len(set(items))!=len(items) or
        any(not isinstance(i,str) or not i for i in items) or
        type(now) is not int or type(duration) is not int or duration<=0):
        raise ValueError("invalid attempt configuration")
    return Attempt(ident,tuple(items),now+duration,now)

def tick(a,now):
    if type(now) is not int or now<a.last_seen:
        raise ValueError("trusted time must not move backwards")
    if a.phase in {Phase.SUBMITTED,Phase.EXPIRED}:
        return a
    if now>=a.deadline:
        return replace(a,phase=Phase.EXPIRED,finalized_at=a.deadline,last_seen=now)
    return replace(a,last_seen=now)

def dispatch(a,event,now,*,item=None,value=None):
    a=tick(a,now)
    if a.phase in {Phase.SUBMITTED,Phase.EXPIRED}:
        # Late events must not change the sealed response snapshot.
        return a
    if event in {"resume","tick"}:
        return a
    if a.phase==Phase.CONFIRMING:
        if event=="cancel":
            return replace(a,phase=Phase.ACTIVE)
        if event=="submit":
            return replace(a,phase=Phase.SUBMITTED,finalized_at=now)
        if event=="finish":
            return a
        raise ValueError("confirmation must be resolved first")
    if event=="finish":
        return replace(a,phase=Phase.CONFIRMING)
    if event=="navigate":
        if item not in a.items:
            raise ValueError("unknown item")
        return replace(a,cursor=a.items.index(item))
    if event in {"answer","flag"}:
        if item!=a.items[a.cursor]:
            raise ValueError("event does not match current item")
        if event=="answer":
            answers=dict(a.answers)
            if value is None:
                answers.pop(item,None)
            elif isinstance(value,str) and value:
                answers[item]=value
            else:
                raise ValueError("invalid answer")
            return replace(a,answers=tuple((i,answers[i]) for i in a.items if i in answers))
        flags=set(a.flagged)
        if type(value) is not bool:
            raise ValueError("explicit flag value required")
        if value:
            flags.add(item)
        else:
            flags.discard(item)
        return replace(a,flagged=tuple(i for i in a.items if i in flags))
    raise ValueError("illegal event")

def view(a):
    answered=dict(a.answers)
    return {"phase":a.phase.value,"remaining":0 if a.phase==Phase.EXPIRED else max(0,a.deadline-a.last_seen),
            "can_edit":a.phase==Phase.ACTIVE,"answered":len(answered),
            "unanswered":len(a.items)-len(answered),"flagged":len(a.flagged),
            "item_states":[{"id":i,"answered":i in answered,"flagged":i in a.flagged,
                            "current":n==a.cursor} for n,i in enumerate(a.items)]}
