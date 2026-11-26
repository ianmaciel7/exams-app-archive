"""Resolve a public archive concept, then retrieve scoped, versioned snippets.

Context7-style interface over existing research records. No network, new
database, model inference, or historical/private lookup.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json

import concept_packs as concepts
import research_index

SCHEMA = 1
SCOPE = "public-research"
FIELDS = ("definition", "purpose", "anatomy", "behavior", "accessibility",
          "guardrail", "description", "summary", "keywords", "kind")
STOP = frozenset("a an the and or of to for how what does is with in do on "
                 "o a os as de da do das dos e ou para como qual que em um uma".split())


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def snapshot(records, taxonomy):
    material = {"schema": SCHEMA, "taxonomy": taxonomy,
                "records": sorted((r["id"], research_index.record_digest(r)) for r in records)}
    return hashlib.sha256(encode(material).encode("utf-8")).hexdigest()


def words(value):
    return set(concepts.norm(value).split()) - STOP


def discover(query, records, taxonomy):
    catalog, groups = concepts.group_records(records, taxonomy)
    matches = concepts.resolve(query, catalog)
    rows = []
    for ident in matches:
        item = catalog[ident]
        ids = {rid for child in concepts.descendants(ident, catalog) for rid in groups[child]}
        rows.append({"id": ident, "title": item["en"], "title_pt": item["pt"],
                     "parent": item["parent"], "aliases": item["aliases"],
                     "records": len(ids)})
    return {"schema": SCHEMA, "scope": SCOPE, "snapshot": snapshot(records, taxonomy),
            "status": "unresolved" if not rows else "ambiguous" if len(rows) > 1 else "resolved",
            "matches": rows}


def make_snippet(row, concept_id, membership):
    record = row.get("record", {})
    statements = {}
    for key in FIELDS:
        value = record.get(key)
        if isinstance(value, str) and value:
            statements[key] = value
        elif key == "keywords" and isinstance(value, list):
            statements[key] = [v for v in value if isinstance(v, str)]
    pointer = {k: record[k] for k in ("source_repo", "source_commit", "source_path", "path",
               "blob_sha", "duration_seconds", "playback") if k in record}
    return {"id": row["id"], "type": row["kind"], "title": row["title"],
            "breadcrumb": [concept_id, row["catalog"], row["title"]],
            "membership": membership, "statements": statements,
            "provenance": {"catalog_path": row["catalog_path"],
                           "catalog_sha256": row["catalog_sha256"],
                           "record_sha256": row["record_sha256"],
                           "record_pointer": row.get("record_pointer"),
                           "projection_sha256": row.get("projection_sha256"),
                           "urls": row.get("sources", []), "product": row.get("product"),
                           "date": row.get("date"), "confidence": row.get("confidence"),
                           "license": row.get("license"), "availability": row.get("availability"),
                           "pointer": pointer}}


def rank(snippet, terms, product):
    title = words(snippet["title"])
    body = words(encode(snippet["statements"]))
    p = snippet["provenance"]
    # Deterministic contextual lexical rank; no claim of vector similarity.
    return (4 * len(title & terms) + 2 * len(body & terms)
            + (3 if product and concepts.norm(p.get("product") or "") == concepts.norm(product) else 0)
            + (1 if snippet["membership"] == "curated" else 0))


def retrieve(concept_id, query, records, taxonomy, *, revision=None, product=None,
             limit=12, max_bytes=12000):
    if not 1 <= limit <= 50 or not 1024 <= max_bytes <= 64000:
        raise ValueError("limit must be 1..50 and max_bytes 1024..64000")
    catalog, groups = concepts.group_records(records, taxonomy)
    rev = snapshot(records, taxonomy)
    out = {"schema": SCHEMA, "scope": SCOPE, "concept_id": concept_id,
           "snapshot": rev, "status": "ok", "snippets": [], "available_by_type": {},
           "returned_by_type": {}, "missing_types": [], "omitted": 0,
           "limitations": ["Public research only; no historical code or private ADRs.",
                           "Catalog statements are not independently verified product behavior.",
                           "Snapshot identifies input content, not a product version."]}
    def size():
        return len(encode(out).encode("utf-8")) + 1
    if concept_id not in catalog:
        raise ValueError("unknown concept ID; call resolve first")
    if revision is not None and revision != rev:
        out["status"] = "snapshot-mismatch"
        out["limitations"].append("Requested snapshot not loaded; no fallback to another revision.")
        if size() > max_bytes:
            raise ValueError("budget too small for response metadata")
        return out
    membership = {}
    for child in sorted(concepts.descendants(concept_id, catalog)):
        for rid, classification in groups[child].items():
            if membership.get(rid) != "curated":
                membership[rid] = classification
    terms = words(query)
    for label in concepts.labels(catalog[concept_id]):
        terms -= words(label)
    rows = []
    for row in records:
        if row["id"] not in membership:
            continue
        if product and concepts.norm(row.get("product") or "") != concepts.norm(product):
            continue
        snippet = make_snippet(row, concept_id, membership[row["id"]])
        rows.append(snippet)
    # Deduplicate exact blobs, but retain each source occurrence. Distinct
    # revisions or merely similar content are never merged by title.
    buckets = {}
    for s in rows:
        blob = s["provenance"]["pointer"].get("blob_sha") if s["type"] == "visual" else None
        key = ("blob", blob) if blob else ("record", s["id"])
        buckets.setdefault(key, []).append(s)
    by_type = defaultdict(list)
    for group in buckets.values():
        group.sort(key=lambda s: (-rank(s, terms, product), s["id"]))
        first = group[0]
        score = rank(first, terms, product)
        bucket = {"type": first["type"], "score": score, "snippet": first,
                  "other_occurrences": group[1:]}
        by_type[first["type"]].append(bucket)
    for entries in by_type.values():
        entries.sort(key=lambda b: (-b["score"], b["snippet"]["id"]))
    out["available_by_type"] = {k: len(v) for k, v in sorted(by_type.items())}
    out["missing_types"] = sorted({"pattern", "visual"} - set(by_type))
    out["omitted"] = len(buckets)
    if not buckets:
        out["status"] = "no-evidence"
    if size() > max_bytes:
        raise ValueError("budget too small for response metadata")
    while any(by_type.values()) and len(out["snippets"]) < limit:
        for kind in sorted(by_type):
            if not by_type[kind] or len(out["snippets"]) >= limit:
                continue
            candidate = by_type[kind].pop(0)
            out["snippets"].append(candidate)
            out["returned_by_type"] = dict(Counter(s["type"] for s in out["snippets"]))
            out["omitted"] = len(buckets) - len(out["snippets"])
            if size() > max_bytes:
                out["snippets"].pop()
                out["returned_by_type"] = dict(Counter(s["type"] for s in out["snippets"]))
                out["omitted"] = len(buckets) - len(out["snippets"])
    if not out["snippets"] and buckets:
        out["status"] = "budget-exhausted"
    if size() > max_bytes:
        raise ValueError("budget too small for final response")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("query")
    docs = sub.add_parser("context")
    docs.add_argument("concept_id")
    docs.add_argument("query")
    docs.add_argument("--snapshot")
    docs.add_argument("--product")
    docs.add_argument("--limit", type=int, default=12)
    docs.add_argument("--max-bytes", type=int, default=12000)
    args = p.parse_args()
    records = research_index.load_records()
    taxonomy = concepts.load_taxonomy()
    if args.command == "resolve":
        result = discover(args.query, records, taxonomy)
    else:
        result = retrieve(args.concept_id, args.query, records, taxonomy,
                          revision=args.snapshot, product=args.product,
                          limit=args.limit, max_bytes=args.max_bytes)
    print(encode(result))


if __name__ == "__main__":
    main()
