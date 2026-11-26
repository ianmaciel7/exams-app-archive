"""Compare two label-blind retrieval captures; budget experiment, not an independent holdout."""
import argparse
import json
from production_retrieval_eval import read, score, write

def ids(row):
    return {v for h in row["hits"] for v in [h["id"], *(o.get("hit_id") for o in h.get("occurrences", []))] if v}

def compare(default, expanded, labels):
    a, b = ({r["id"]: r for r in rows} for rows in (default, expanded))
    if len(a) != len(default) or len(b) != len(expanded) or set(a) != set(b) or set(a) != set(labels):
        raise ValueError("Mismatched query sets")
    if not a:
        raise ValueError("Empty captures")
    cases = []
    for ident, left in a.items():
        right = b[ident]
        if left["query"] != right["query"] or not left.get("snapshot") or left["snapshot"] != right.get("snapshot"):
            raise ValueError("Query or snapshot changed: " + ident)
        if left.get("budget", {}).get("budget_tokens") != 2000 or right.get("budget", {}).get("budget_tokens") != 8000:
            raise ValueError("Unexpected budget: " + ident)
        if any(h.get("scope") != "public" for row in (left, right) for h in row["hits"]):
            raise ValueError("Non-public hit")
        expected = set(labels[ident])
        missing = expected - ids(left)
        recovered = missing & ids(right)
        omitted = {h["id"] for h in left.get("omitted_for_budget", [])}
        cases.append({"id": ident, "default_hits": len(left["hits"]), "expanded_hits": len(right["hits"]),
                      "missing_at_default": sorted(missing), "recovered_at_expanded_budget": sorted(recovered),
                      "missing_at_both": sorted(missing - recovered),
                      "lost_at_expanded_budget": sorted((expected & ids(left)) - ids(right)),
                      "missing_target_explicitly_omitted": sorted(missing & omitted),
                      "default_budget_omissions": len(left.get("omitted_for_budget", [])),
                      "default_reported_tokens": left["budget"].get("total_tokens"),
                      "expanded_reported_tokens": right["budget"].get("total_tokens")})
    def metrics(rows):
        result = score(rows, labels)
        return {k: result[k] for k in ("mean_recall", "mean_precision", "mrr", "p95_ms", "negative_abstention")}
    return {"scope": "development regression; budget sensitivity, same snapshot",
            "default_budget": metrics(default), "expanded_budget": metrics(expanded), "cases": cases,
            "limitations": ["Named targets only; precision field is labeled-hit fraction.",
                            "A target absent from explicit omissions may have been deduplicated, filtered, or ranked below the candidate limit.",
                            "Expanded budget does not prove ranking quality at production budget.",
                            "Reported tokens are engine estimates; latency is not a controlled performance comparison.",
                            "No independent relevance annotation."]}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("default", "expanded", "labels", "output"):
        parser.add_argument(name)
    args = parser.parse_args()
    result = compare(read(args.default), read(args.expanded), read(args.labels))
    write(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
