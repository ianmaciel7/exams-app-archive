"""Public production retrieval evaluation. No private corpus or gold labels in runner."""
import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def run(queries, retrieve, *, budget_tokens=None, compact_occurrences=False):
    if budget_tokens is not None and (not isinstance(budget_tokens, int) or not 128 <= budget_tokens <= 128000):
        raise ValueError("budget_tokens must be between 128 and 128000")
    out = []
    for q in queries:
        if set(q) != {"id", "query"} or not isinstance(q["query"], str):
            raise ValueError("Runner accepts only id and query, never labels or expected metadata")
        start = time.perf_counter()
        options = {"scope": "public", "limit": 20}
        if budget_tokens is not None:
            options["budget_tokens"] = budget_tokens
        if compact_occurrences:
            options["compact_occurrences"] = True
        result = retrieve(q["query"], **options)
        out.append({"id": q["id"], "query": q["query"], "status": result["status"],
                    "hits": result["results"], "snapshot": result.get("snapshot"),
                    "unavailable": result.get("sources_unavailable", []),
                    "budget": result.get("budget", {}),
                    "omitted_for_budget": result.get("omitted_for_budget", []),
                    "available_by_type": result.get("available_by_type", {}),
                    "gaps": result.get("gaps", []),
                    "latency_ms": (time.perf_counter()-start)*1000})
    if len({r["id"] for r in out}) != len(out):
        raise ValueError("Duplicate query IDs")
    return out

def summarize_public_capture(rows):
    """Safe diagnostic for this public-only corpus; no private queries allowed."""
    for row in rows:
        if any(h.get("scope") != "public" for h in row["hits"]):
            raise ValueError("Non-public hit in public capture")
    return [{"id":row["id"],"status":row["status"],"hits":[{"id":h["id"],"channel":h.get("source_channel"),"type":h.get("evidence_type"),"raw_score":h.get("raw_score"),"fused_score":h.get("fused_score")} for h in row["hits"]]} for row in rows]

def score(rows, labels):
    if set(labels) != {row["id"] for row in rows}:
        raise ValueError("Labels and captured queries must match exactly")
    results = []
    for row in rows:
        expected = set(labels[row["id"]])
        actual = list({h["id"]: h for h in row["hits"]}.values())[:20]
        matched = set()
        relevant = 0
        ranks = []
        for rank, hit in enumerate(actual, 1):
            candidates = {hit["id"]} | {o.get("hit_id") for o in hit.get("occurrences", [])}
            found = expected & candidates
            if found:
                matched.update(found)
                relevant += 1
                ranks.append(rank)
        correct = len(matched)
        results.append({"id": row["id"], "expected_count": len(expected), "returned_count": len(actual),
                        "recall_at_20": correct/len(expected) if expected else None,
                        "precision_at_20": relevant/len(actual) if actual else (0.0 if expected else None),
                        "reciprocal_rank": 1/ranks[0] if ranks else (0.0 if expected else None),
                        "abstained": not actual, "negative_case": not expected,
                        "sources_unavailable": row["unavailable"]})
    return {"status": "MEASURED_PUBLIC_RETRIEVAL_ONLY", "cases": results,
            "mean_recall": mean(r["recall_at_20"] for r in results),
            "mean_precision": mean(r["precision_at_20"] for r in results),
            "mrr": mean(r["reciprocal_rank"] for r in results),
            "p50_ms": statistics.median([r["latency_ms"] for r in rows]) if rows else None,
            "p95_ms": sorted(r["latency_ms"] for r in rows)[max(0, __import__("math").ceil(.95*len(rows))-1)] if rows else None,
            "negative_cases": sum(r["negative_case"] for r in results),
            "negative_abstention": mean(float(r["abstained"]) for r in results if r["negative_case"]),
            "limitations": ["No independent annotation attestation", "No claim/citation verification", "No private or agent evaluation"]}

def mean(values):
    valid = [v for v in values if v is not None]
    return statistics.mean(valid) if valid else None

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    runner = sub.add_parser("run")
    runner.add_argument("queries")
    runner.add_argument("output")
    runner.add_argument("--budget-tokens", type=int, default=None)
    runner.add_argument("--compact-occurrences", action="store_true")
    diagnostic = sub.add_parser("diagnostic")
    diagnostic.add_argument("capture")
    scorer = sub.add_parser("score")
    scorer.add_argument("capture")
    scorer.add_argument("labels")
    scorer.add_argument("output")
    args = parser.parse_args()
    if args.mode == "run":
        from federated_retrieval import federated_search
        write(args.output, run(read(args.queries), federated_search, budget_tokens=args.budget_tokens, compact_occurrences=args.compact_occurrences))
    elif args.mode == "diagnostic":
        print(json.dumps(summarize_public_capture(read(args.capture)),indent=2))
    else:
        capture = Path(args.capture)
        result = score(read(capture), read(args.labels))
        result["capture_sha256"] = hashlib.sha256(capture.read_bytes()).hexdigest()
        result["labels_sha256"] = hashlib.sha256(Path(args.labels).read_bytes()).hexdigest()
        write(args.output, result)

if __name__ == "__main__":
    main()
