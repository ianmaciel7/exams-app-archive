"""Concept grouping over the existing public research projection (no second index)."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import re
import unicodedata

import research_index

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / "config/knowledge-concepts.json"


def norm(value):
    return " ".join(re.findall(r"\w+", "".join(
        c for c in unicodedata.normalize("NFKD", str(value).casefold())
        if not unicodedata.combining(c))))


def load_taxonomy():
    return json.loads(TAXONOMY.read_text(encoding="utf-8"))


def validate(taxonomy, records):
    concepts = taxonomy["concepts"]
    by_id = {c["id"]: c for c in concepts}
    if len(by_id) != len(concepts):
        raise ValueError("duplicate concept ID")
    record_ids = {r["id"] for r in records}
    for c in concepts:
        if set(c["members"]) - record_ids:
            raise ValueError("unknown member in " + c["id"])
        seen = {c["id"]}
        parent = c["parent"]
        while parent is not None:
            if parent not in by_id or parent in seen:
                raise ValueError("unknown parent or cycle: " + c["id"])
            seen.add(parent)
            parent = by_id[parent]["parent"]
    return by_id


def labels(concept):
    return {norm(s) for s in [concept["id"], concept["en"], concept["pt"], *concept["aliases"]] if norm(s)}


def resolve(query, concepts):
    q = norm(query)
    if not q:
        return []
    exact = [c["id"] for c in concepts.values() if q in labels(c)]
    if exact:
        return sorted(exact)
    matches = [(len(term.split()), c["id"]) for c in concepts.values()
               for term in labels(c) if " " + term + " " in " " + q + " "]
    if not matches:
        return []
    # Keep equally specific concepts, rather than arbitrarily choosing one.
    best = max(n for n, _ in matches)
    return sorted({ident for n, ident in matches if n == best})


def group_records(records, taxonomy):
    concepts = validate(taxonomy, records)
    groups = defaultdict(dict)
    for c in concepts.values():
        for ident in c["members"]:
            groups[c["id"]][ident] = "curated"
    for row in records:
        # Do not classify by source URL, full serialized metadata or arbitrary body
        # text; those routinely create false cross-topic matches.
        if row["kind"] not in {"pattern", "visual"}:
            continue
        item = row.get("record", {})
        fields = [row["title"], *item.get("keywords", [])]
        for field in fields:
            for ident in resolve(field, concepts):
                groups[ident].setdefault(row["id"], "lexical-candidate")
    return concepts, groups


def descendants(ident, concepts):
    result = {ident}
    while True:
        expanded = result | {c["id"] for c in concepts.values() if c["parent"] in result}
        if expanded == result:
            return result
        result = expanded


def build_pack(query, records, taxonomy, limit=20):
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1..100")
    concepts, groups = group_records(records, taxonomy)
    selected = resolve(query, concepts)
    indexed = {r["id"]: r for r in records}
    packs = []
    for ident in selected:
        members = {}
        for child in sorted(descendants(ident, concepts)):
            for rid, confidence in groups[child].items():
                entry = members.setdefault(rid, {"concepts": [], "classification": confidence})
                entry["concepts"].append(child)
                if confidence == "curated":
                    entry["classification"] = confidence
        # Exact visual blobs only; different screenshots, products or revisions
        # must remain distinct. Retain every occurrence and source pointer.
        buckets = {}
        for rid, membership in sorted(members.items()):
            r = indexed[rid]
            blob = r.get("record", {}).get("blob_sha") if r["kind"] == "visual" else None
            key = ("blob", blob) if blob else ("id", rid)
            bucket = buckets.setdefault(key, {"kind": r["kind"], "occurrences": []})
            bucket["occurrences"].append({
                "id": rid, "title": r["title"], "product": r.get("product"),
                "date": r.get("date"), "availability": r.get("availability"),
                "source_confidence": r.get("confidence"), "license": r.get("license"),
                "catalog_path": r.get("catalog_path"), "catalog_sha256": r.get("catalog_sha256"),
                "record_sha256": r.get("record_sha256"), "sources": r.get("sources", []),
                **membership})
        # Round-robin evidence kinds so one modality cannot consume the budget.
        kinds = defaultdict(list)
        for bucket in buckets.values():
            kinds[bucket["kind"]].append(bucket)
        for entries in kinds.values():
            entries.sort(key=lambda b: (not any(o["classification"] == "curated" for o in b["occurrences"]), b["occurrences"][0]["id"]))
        counts = {k: len(v) for k, v in sorted(kinds.items())}
        ordered = []
        while any(kinds.values()) and len(ordered) < limit:
            for kind in sorted(kinds):
                if kinds[kind] and len(ordered) < limit:
                    ordered.append(kinds[kind].pop(0))
        c = concepts[ident]
        packs.append({"concept": {k: c[k] for k in ("id", "en", "pt", "parent")},
                      "record_count": len(members), "unique_evidence_count": len(buckets),
                      "available_by_kind": counts, "returned_by_kind": dict(Counter(b["kind"] for b in ordered)),
                      "missing_kinds": sorted({"pattern", "visual"} - set(counts)),
                      "truncated": len(ordered) < len(buckets), "evidence": ordered})
    return {"schema_version": 1, "scope": "public research only",
            "query": query, "status": "unresolved" if not selected else ("multiple-concepts" if len(selected) > 1 else "resolved"),
            "packs": packs, "limitations": ["Lexical candidates require review; membership is not proof of behavior.",
            "Historical code, ADRs and private evidence are not included.", "Media availability is catalog-declared."]}


def audit(records, taxonomy):
    concepts, groups = group_records(records, taxonomy)
    assigned = {rid for g in groups.values() for rid in g}
    return {"schema_version": 1, "scope": "public research only", "concepts": len(concepts),
            "records": len(records), "assigned": len(assigned),
            "unassigned": [{"id": r["id"], "kind": r["kind"], "title": r["title"]} for r in records if r["id"] not in assigned],
            "memberships": {k: dict(Counter(v.values())) for k, v in sorted(groups.items())}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    records = research_index.load_records()
    taxonomy = load_taxonomy()
    out = audit(records, taxonomy) if args.audit else build_pack(args.query, records, taxonomy, args.limit)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
