"""Public AI-product target retrieval audit; not independent relevance certification."""
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from production_retrieval_eval import read, score, write, mean

def summarize(capture, scored, labels):
    rows, gold, measured = read(capture), read(labels), read(scored)
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Empty capture or duplicate query ID")
    for field, path in (("capture_sha256", capture), ("labels_sha256", labels)):
        if measured.get(field) != hashlib.sha256(Path(path).read_bytes()).hexdigest():
            raise ValueError("Score provenance mismatch")
    recomputed = score(rows, gold)
    if any(measured.get(k) != v for k, v in recomputed.items()):
        raise ValueError("Score does not match capture and labels")
    if any(h.get("scope") != "public" for r in rows for h in r["hits"]):
        raise ValueError("Non-public hit in public evaluation")
    groups = defaultdict(list)
    for row in measured["cases"]:
        groups[row["id"].split("-", 1)[0]].append(row)
    if set(groups) != {"space", "claude", "grok", "gemini", "notebook", "negative"}:
        raise ValueError("Missing product coverage")
    for name, cases in groups.items():
        if len(cases) != (2 if name == "negative" else 4):
            raise ValueError("Unexpected case count")
        if any(c["negative_case"] != (name == "negative") for c in cases):
            raise ValueError("Mismatched negative case")
    misses = []
    by_id = {r["id"]: r for r in rows}
    for case in measured["cases"]:
        if case["negative_case"] or case["recall_at_20"] == 1:
            continue
        hits = by_id[case["id"]]["hits"][:20]
        found = {h["id"] for h in hits}
        found.update(o.get("hit_id") for h in hits for o in h.get("occurrences", []))
        misses.append({"id": case["id"], "missing_targets": sorted(set(gold[case["id"]]) - found)})
    return {
        "scope": "public five-product target retrieval; same-author annotations, incomplete relevance judgments",
        "independent_annotation": False,
        "ranking_tuned_on_this_set": True,
        "evaluation_class": "development_regression",
        "query_count": len(rows),
        "mean_target_recall_at_20": measured["mean_recall"],
        "mean_labeled_hit_fraction_at_20": measured["mean_precision"],
        "mrr_for_labeled_targets": measured["mrr"],
        "p95_ms": measured["p95_ms"],
        "negative_abstention": measured["negative_abstention"],
        "per_product": {name: {"cases": len(cases),
            "mean_target_recall": mean(c["recall_at_20"] for c in cases),
            "mean_labeled_hit_fraction": mean(c["precision_at_20"] for c in cases),
            "mrr": mean(c["reciprocal_rank"] for c in cases)}
            for name, cases in groups.items() if name != "negative"},
        "missed_targets": misses,
        "quality_certified": False,
        "limitations": ["Targets are not exhaustive relevance annotations.",
                         "A non-target hit may be relevant; labeled-hit fraction is not true precision.",
                         "No independent human annotation, answer grounding, live product inspection or agent comparison.",
                         "If this set is used for ranking changes, record it as development data thereafter."]
    }

if __name__ == "__main__":
    result = summarize(*sys.argv[1:4])
    write(sys.argv[4], result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
