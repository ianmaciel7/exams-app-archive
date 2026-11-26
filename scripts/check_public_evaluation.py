"""Public development regression gate, not a production-quality certification."""
import argparse
import hashlib
import json
from pathlib import Path

# Baseline is the measured 26 Nov 2026 development run, not invented target
# accuracy or a claim of complete corpus relevance. Retain actual denominators.
FLOORS = {"mean_recall": .80, "mean_precision": .48, "negative_abstention": 1.0}

def gate(capture, labels, score):
    import production_retrieval_eval as evaluation
    capture_path, labels_path, score_path = map(Path,(capture,labels,score))
    captured = evaluation.read(capture_path)
    gold = evaluation.read(labels_path)
    supplied = evaluation.read(score_path)
    computed = evaluation.score(captured,gold)
    failures = []
    if not captured or len(captured) != len(gold):
        failures.append("Missing or inconsistent capture")
    for name,path in (("capture_sha256",capture_path),("labels_sha256",labels_path)):
        if supplied.get(name) != hashlib.sha256(path.read_bytes()).hexdigest():
            failures.append("Invalid "+name)
    for key,value in computed.items():
        if supplied.get(key) != value:
            failures.append("Scorer discrepancy: "+key)
    if sum(bool(v) for v in gold.values()) < 10 or sum(not v for v in gold.values()) < 1:
        failures.append("Development dataset coverage below baseline")
    for key,minimum in FLOORS.items():
        metric = computed.get(key)
        if metric is None or metric + 1e-12 < minimum:
            failures.append(f"{key}: {metric} below development baseline {minimum}")
    for row in captured:
        if any(h.get("scope") != "public" for h in row.get("hits",[])):
            failures.append("Non-public result in public evaluation")
    return {"development_regression_gate_passed":not failures,
            "production_quality_status":"NOT_CERTIFIED",
            "independent_holdout":"NOT_RUN",
            "external_agents":"NOT_RUN",
            "failures":failures,
            "baseline":FLOORS}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("capture","labels","score"):
        parser.add_argument(name)
    args=parser.parse_args()
    result=gate(args.capture,args.labels,args.score)
    print(json.dumps(result,indent=2))
    return 0 if result["development_regression_gate_passed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
