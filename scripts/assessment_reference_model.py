"""Original, fictional assessment reference model. Not QTI/IRT certification."""
from dataclasses import dataclass
from math import sqrt
from collections import defaultdict

@dataclass(frozen=True)
class Item:
    bank_id: str
    version: int
    prompt: str
    key: str

@dataclass(frozen=True)
class Form:
    id: str
    edition: int
    items: tuple[Item, ...]
    policy: str

@dataclass(frozen=True)
class Submission:
    attempt: str
    participant: str
    form: Form
    responses: tuple[tuple[str, str], ...]

@dataclass(frozen=True)
class Result:
    attempt: str
    policy: str
    marks: tuple[int, ...]
    revision: int

class AssessmentLedger:
    def __init__(self):
        self.bank = {}
        self.forms = {}
        self.submissions = {}
        self.results = {}

    def add_item(self, item):
        key = (item.bank_id, item.version)
        if key in self.bank and self.bank[key] != item:
            raise ValueError("immutable item version")
        self.bank[key] = item

    def publish(self, form):
        if not form.items or len({i.bank_id for i in form.items}) != len(form.items):
            raise ValueError("empty or duplicate items")
        if any(self.bank.get((i.bank_id, i.version)) != i for i in form.items):
            raise ValueError("unknown item version")
        key = (form.id, form.edition)
        if key in self.forms and self.forms[key] != form:
            raise ValueError("immutable published form")
        self.forms[key] = form

    def submit(self, submission):
        existing = self.submissions.get(submission.attempt)
        if existing is not None:
            if existing != submission:
                raise ValueError("conflicting retry")
            return self.results[submission.attempt][0]
        form = submission.form
        if self.forms.get((form.id, form.edition)) != form:
            raise ValueError("unpublished form")
        responses = dict(submission.responses)
        if len(responses) != len(submission.responses) or set(responses) - {i.bank_id for i in form.items}:
            raise ValueError("invalid response identity")
        result = Result(submission.attempt, form.policy,
                        tuple(int(responses.get(i.bank_id) == i.key) for i in form.items), 1)
        self.submissions[submission.attempt] = submission
        self.results[submission.attempt] = (result,)
        return result

    def regrade(self, attempt, policy, *, keys):
        sub = self.submissions[attempt]
        history = self.results[attempt]
        if policy in {r.policy for r in history}:
            raise ValueError("grading policy revision already used")
        if set(keys) != {i.bank_id for i in sub.form.items}:
            raise ValueError("complete grading keys required")
        answers = dict(sub.responses)
        result = Result(attempt, policy,
                        tuple(int(answers.get(i.bank_id) == keys[i.bank_id]) for i in sub.form.items),
                        len(history)+1)
        self.results[attempt] = (*history, result)
        return result

def item_statistics(rows, item_index, *, cohort, first_attempt_only):
    """Rows ordered by submission time: (participant, marks). Corrected item-total
    Pearson correlation uses total of *other* items. No model/calibration claims."""
    if not cohort:
        raise ValueError("explicit cohort required")
    selected = []
    seen = set()
    for person, marks in rows:
        if len(marks) <= item_index or item_index < 0 or any(m not in (0,1) for m in marks):
            raise ValueError("invalid dichotomous response matrix")
        if first_attempt_only and person in seen:
            continue
        seen.add(person)
        selected.append(marks)
    if len({len(m) for m in selected}) > 1:
        raise ValueError("mixed form lengths")
    n = len(selected)
    x = [m[item_index] for m in selected]
    y = [sum(m)-m[item_index] for m in selected]
    facility = sum(x)/n if n else None
    correlation = None
    if n >= 2:
        dx = [v-sum(x)/n for v in x]
        dy = [v-sum(y)/n for v in y]
        denominator = sqrt(sum(v*v for v in dx)*sum(v*v for v in dy))
        if denominator:
            correlation = sum(a*b for a,b in zip(dx,dy))/denominator
    return {"cohort":cohort, "attempt_scope":"first" if first_attempt_only else "all",
            "attempts":n,"participants":len(seen),"facility":facility,
            "corrected_item_total_pearson":correlation,
            "scope":"fictional descriptive CTT example; not calibrated difficulty, validity or IRT"}
