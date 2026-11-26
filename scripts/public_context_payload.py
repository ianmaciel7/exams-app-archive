"""Optional, bounded public model-context projection with a separate audit ledger.

The limit applies to the exact canonical JSON string under a character-count
estimator, not a provider tokenizer or the full conversation. Never send the
complete audit response to a model when using this projection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def estimate_context_tokens(value):
    return (len(canonical_json(value)) + 3) // 4


def audit_digest(audit):
    return hashlib.sha256(canonical_json(audit).encode("utf-8")).hexdigest()


def project_context(audit, *, budget_tokens=2000, max_bytes=None):
    """Keep whole evidence snippets and citation pointers in original order.

    The full, unmodified audit remains with the caller. The projection omits
    verbose metadata deliberately and is NOT a reversible replacement for it.
    No new candidate selection, ranking or source retrieval is performed.
    """
    if type(budget_tokens) is not int or not 128 <= budget_tokens <= 128000:
        raise ValueError("budget_tokens must be an integer between 128 and 128000")
    if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 1):
        raise ValueError("max_bytes must be a positive integer")
    if audit.get("scope") != "public":
        raise ValueError("Context projection is public-only")
    hits = audit.get("results", [])
    if any(hit.get("scope") != "public" for hit in hits):
        raise ValueError("Non-public hit in audit")
    if len({hit["id"] for hit in hits}) != len(hits):
        raise ValueError("Duplicate audit hit identifiers")
    if hits and not audit.get("snapshot"):
        raise ValueError("Missing corpus snapshot for nonempty audit")

    context = {
        "schema": "public-context-v1",
        "scope": "public",
        "snapshot": audit.get("snapshot"),
        "audit_sha256": audit_digest(audit),
        "retrieval_status": audit["status"],
        "retrieval_omitted": len(audit.get("omitted_for_budget", [])),
        "unavailable_sources": len(audit.get("sources_unavailable", [])),
        "projection_omitted": len(hits),
        "results": [],
    }

    def fits(payload):
        serialized = canonical_json(payload)
        return ((len(serialized) + 3) // 4 <= budget_tokens
                and (max_bytes is None or len(serialized.encode("utf-8")) <= max_bytes))

    if not fits(context):
        raise ValueError("Budget cannot fit the minimum context envelope")
    for hit in hits:
        provenance = hit.get("provenance", {})
        metadata = hit.get("metadata", {})
        ids = sorted({o["hit_id"] for o in hit.get("occurrences", [])
                      if o.get("hit_id") and o["hit_id"] != hit["id"]})
        entry = {
            "id": hit["id"],
            "scope": "public",
            "type": hit["evidence_type"],
            "title": hit["title"],
            "snippet": hit["snippet"],
            "provenance_status": provenance.get("provenance_status", "unknown"),
            "sanitized": bool(provenance.get("sanitized", False)),
        }
        if ids:
            entry["occurrence_ids"] = ids
        for key in ("product", "availability", "source_urls"):
            if metadata.get(key):
                entry[key] = metadata[key]
        if metadata.get("source_evidence"):
            # Each pair references the existing source_urls array, avoiding URL
            # repetition. Never keep a claim while stripping its qualifications.
            urls = entry.get("source_urls", [])
            statements = metadata["source_evidence"]
            if any(type(pair[0]) is not int or not 0 <= pair[0] < len(urls)
                   or not isinstance(pair[1], str) or not pair[1]
                   for pair in statements if isinstance(pair, (list, tuple)) and len(pair) == 2) or any(
                       not isinstance(pair, (list, tuple)) or len(pair) != 2 for pair in statements):
                raise ValueError("Invalid source evidence reference")
            entry["source_evidence"] = statements
        pointer = {key: provenance[key] for key in
                   ("repo", "ref", "commit_sha", "path", "blob_sha", "record_sha256")
                   if provenance.get(key)}
        if pointer:
            entry["pointer"] = pointer
        trial = {**context, "results": [*context["results"], entry],
                 "projection_omitted": context["projection_omitted"] - 1}
        if fits(trial):
            context = trial
    # The exact final serialized object, not a sum of per-record estimates.
    assert fits(context)
    return context


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--audit-output", required=True, type=Path,
                        help="New local file for the complete audit; never overwritten.")
    parser.add_argument("--budget-tokens", type=int, default=2000)
    parser.add_argument("--max-context-bytes", type=int)
    parser.add_argument("--retrieval-budget-tokens", type=int, default=2000)
    parser.add_argument("--compact-occurrences", action="store_true")
    parser.add_argument("--relevance-first", action="store_true")
    args = parser.parse_args(argv)
    from federated_retrieval import federated_search
    # Preserve the exact retrieval response, including its accounting and any
    # reversible occurrence encoding. Do not rewrite the audited representation.
    audit = federated_search(args.query, scope="public",
                             budget_tokens=args.retrieval_budget_tokens,
                             compact_occurrences=args.compact_occurrences,
                             relevance_first=args.relevance_first)
    context = project_context(audit, budget_tokens=args.budget_tokens,
                              max_bytes=args.max_context_bytes)
    # Digest refers to exactly these UTF-8 bytes, without a trailing newline.
    with args.audit_output.open("xb") as stream:
        stream.write(canonical_json(audit).encode("utf-8"))
    sys.stdout.write(canonical_json(context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
