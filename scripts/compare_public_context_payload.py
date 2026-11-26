"""Measure projected context against the captured full audit; offline, no reranking."""
import argparse
import json
from pathlib import Path
from production_retrieval_eval import read, write, score
from public_context_payload import audit_digest, estimate_context_tokens, project_context, canonical_json


def compare(rows, labels, budget_tokens=2000):
    projected_rows = []
    cases = []
    for row in rows:
        context = row["context_payload"]
        audit = row["audit_response"]
        if context["audit_sha256"] != audit_digest(audit):
            raise ValueError("Audit digest mismatch")
        if context != project_context(audit, budget_tokens=budget_tokens):
            raise ValueError("Projection does not match audit")
        size = estimate_context_tokens(context)
        if size > budget_tokens:
            raise ValueError("Projection exceeds budget")
        hits = [{**hit, "occurrences": [{"hit_id": i} for i in hit.get("occurrence_ids", [])]}
                for hit in context["results"]]
        projected_rows.append({**row, "hits": hits})
        cases.append({"id": row["id"], "estimated_tokens": size,
                      "utf8_bytes": len(canonical_json(context).encode("utf-8")),
                      "retained_hits": len(hits), "projection_omitted": context["projection_omitted"]})
    result = score(projected_rows, labels)
    return {"budget_tokens": budget_tokens,
            "estimator": "ceil(canonical JSON characters / 4), not model tokenizer",
            "max_estimated_tokens": max((case["estimated_tokens"] for case in cases), default=0),
            "projection_cases": cases, "projected_score": result,
            "original_score": score(rows, labels),
            "independent_evaluation": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture")
    parser.add_argument("labels")
    parser.add_argument("output")
    args = parser.parse_args()
    report = compare(read(args.capture), read(args.labels))
    write(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
