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

def run(queries, retrieve):
    out = []
    for q in queries:
        if set(q) != {"id", "query"} or not isinstance(q["query"], str):
            raise ValueError("Runner accepts only id and query, never labels or expected metadata")
        start = time.perf_counter()
        result = retrieve(q["query"], scope="public", limit=20)
        out.append({"id": q["id"], "query": q["query"], "status": result["status"],
                    "hits": result["results"], "snapshot": result.get("snapshot"),
                    "unavailable": result.get("sources_unavailable", []),
                    "latency_ms": (time.perf_counter()-start)*1000})
    if len({r["id"] for r in out}) != len(out):
        raise ValueError("Duplicate query IDs")
    return out

def score(rows, labels):
    if set(labels) != {row["id"] for row in rows}:
        raise ValueError("Labels and captured queries must match exactly")
    results = []
    for row in rows:
        expected = set(labels[row["id"]])
        actual = list(dict.fromkeys(h["id"] for h in row["hits"]))[:20]
        correct = len(expected.intersection(actual))
        results.append({"id": row["id"], "expected_count": len(expected), "returned_count": len(actual),
                        "recall_at_20": correct/len(expected) if expected else None,
                        "precision_at_20": correct/len(actual) if actual else None,
                        "abstained": not actual, "negative_case": not expected,
                        "sources_unavailable": row["unavailable"]})
    return {"status": "MEASURED_PUBLIC_RETRIEVAL_ONLY", "cases": results,
            "mean_recall": mean(r["recall_at_20"] for r in results),
            "mean_precision": mean(r["precision_at_20"] for r in results),
            "p50_ms": statistics.median([r["latency_ms"] for r in rows]) if rows else None,
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
    scorer = sub.add_parser("score")
    scorer.add_argument("capture")
    scorer.add_argument("labels")
    scorer.add_argument("output")
    args = parser.parse_args()
    if args.mode == "run":
        from federated_retrieval import federated_search
        write(args.output, run(read(args.queries), federated_search))
    else:
        capture = Path(args.capture)
        result = score(read(capture), read(args.labels))
        result["capture_sha256"] = hashlib.sha256(capture.read_bytes()).hexdigest()
        result["labels_sha256"] = hashlib.sha256(Path(args.labels).read_bytes()).hexdigest()
        write(args.output, result)

if __name__ == "__main__":
    main()
