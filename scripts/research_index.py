#!/usr/bin/env python3
"""Rebuild an offline public research index from explicitly approved catalogs."""
import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/references"
CATALOGS = (
    ("general", "interface-pattern-library/patterns.json", "patterns", "pattern"),
    ("workspace", "ui-ux-patterns-2026-11-25/patterns.json", "patterns", "pattern"),
    ("design-foundations", "ui-ux-research-sources/design-foundations-and-state-transitions-2026-11-25.json", "patterns", "pattern"),
    ("domain-research", "ui-ux-research-sources/domain-research-2026-11-26.json", "patterns", "pattern"),
    ("general-sources", "interface-pattern-library/sources.json", "sources", "source"),
    ("research-sources", "ui-ux-research-sources/sources.json", "sources", "source"),
    ("visual", "visual-evidence-library/manifest.json", "records", "visual"),
    ("grok-assets", "grok-bot/media/manifest.json", "assets", "visual"),
    ("grok-links", "grok-bot/media/manifest.json", "external_media", "visual"),
)
ALIASES = (
    ("barra lateral", "sidebar", "side panel", "sidepanel"),
    ("aba", "tab", "tabs", "abas"),
    ("arrastar", "drag", "dragging", "reorder", "ordenação"),
    ("animação", "animation", "motion", "transição"),
    ("gráfico", "chart", "graph", "visualization"),
    ("vídeo", "video", "recording", "mov", "mp4"),
    ("imagem", "image", "screenshot", "png"),
    ("quadro", "board", "whiteboard", "kanban"),
)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))

# Only explicitly reviewed public catalog files; no recursive scan of archive data.
SUPPLEMENTAL_CATALOGS = (
    ("async-ux", "asynchronous-non-blocking-ux.json", "patterns", "interacao"),
    ("behavioral-ux", "behavioral-ux-quality-2026.json", "patterns", "interacao"),
    ("component-behavior", "component-interaction-behavior-patterns.json", "patterns", "design-system"),
    ("microinteraction", "microinteraction-state-and-polish.json", "patterns", "motion"),
    ("agent-design-system", "agent-ready-design-system-completeness.json", "patterns", "design-system"),
    ("ai-native", "ai-native-product-design.json", "records", "ai-native-ux"),
    ("space-views", "chatgpt-space-views-and-composable-pages-2026-11-26.json", "patterns", "workspace"),
    ("ai-product-views", "ai-product-views-and-artifacts-2026-11-26.json", "products", "ai-native-ux"),
    ("design-activities", "ux-design-activities-2026-11-25.json", "activities", "produto"),
)

def supplemental_records(base=BASE):
    """Project existing public records without changing their source JSON or hashes.

    Source and pattern occurrences retain namespace, original fields and catalog
    checksum. Cross-indexed patterns do not count as unique discoveries.
    """
    for namespace, filename, key, domain in SUPPLEMENTAL_CATALOGS:
        path = base / "ui-ux-research-sources" / filename
        raw = path.read_bytes()
        doc = json.loads(raw)
        catalog_date = next((doc[k] for k in ("reviewed_on","review_date","recorded_on","date") if doc.get(k)), None)
        source_map = {x["id"]: x["url"] for x in doc["sources"]}
        if len(source_map) != len(doc["sources"]):
            raise ValueError(f"Duplicate source ID in {filename}")
        def project(item, kind, product=None):
            local_id = item["id"]
            title = item.get("title") or item.get("name") or local_id.replace("-", " ")
            ids = list(item.get("source_ids", []))
            if item.get("source_id"):
                ids.append(item["source_id"])
            if any(s not in source_map for s in ids):
                raise ValueError(f"Unresolved source ID in {filename}:{local_id}")
            urls = [source_map[s] for s in ids]
            if item.get("url"):
                urls.append(item["url"])
            if any(urlsplit(u).scheme != "https" or not urlsplit(u).hostname or urlsplit(u).username is not None for u in urls):
                raise ValueError(f"Invalid public URL in {filename}:{local_id}")
            # Do not guess an explicit evidence link where none is declared.
            projected = dict(item)
            if product:
                projected.setdefault("product", product)
            if kind == "pattern":
                projected.setdefault("domain", domain)
            return {"id":namespace + ("-sources" if kind=="source" else "") + ":" + local_id,
                    "title":title,"kind":kind,
                    "catalog":namespace + ("-sources" if kind=="source" else ""),
                    "record_id":local_id,
                    "catalog_path":"docs/references/ui-ux-research-sources/" + filename,
                    "catalog_sha256":digest(raw),
                    "record_sha256":digest(json.dumps(item,ensure_ascii=False,sort_keys=True).encode("utf-8")),
                    "sources":list(dict.fromkeys(urls)),
                    "date":item.get("checked_on") or item.get("recorded_on") or item.get("date") or catalog_date,
                    "product":product or item.get("product"),
                    "confidence":item.get("evidence_status") or item.get("evidence") or item.get("classification"),
                    "license":item.get("license"),
                    "availability":"link-only" if kind=="source" else "cataloged-synthesis",
                    "record":projected}
        for source in doc["sources"]:
            yield project(source,"source")
        if key=="products":
            for product in doc[key]:
                for item in product["patterns"]:
                    yield project(item,"pattern",product=product["product"])
        else:
            for item in doc[key]:
                yield project(item,"pattern")

def load_records():
    records, seen = [], set()
    general_sources = json.loads((BASE / "interface-pattern-library/sources.json").read_text(encoding="utf-8"))["sources"]
    source_map = {x["id"]: x["url"] for x in general_sources}
    maps = {"general": source_map, "design-foundations": source_map, "domain-research": source_map}
    for namespace, rel, key, kind in CATALOGS:
        path = BASE / rel
        data = path.read_bytes()
        doc = json.loads(data)
        if namespace == "workspace":
            maps[namespace] = doc["sources"]
        for item in doc[key]:
            title = item.get("title") or item.get("name")
            if not title:
                raise ValueError(f"Missing title in {rel}")
            local_id = item.get("id") or digest(json.dumps(item, sort_keys=True).encode())[:20]
            ident = namespace + ":" + local_id
            if ident in seen:
                raise ValueError(f"Duplicate id: {ident}")
            seen.add(ident)
            source_ids = item.get("source_ids", [])
            urls = [maps.get(namespace, {}).get(s) for s in source_ids]
            if any(u is None for u in urls):
                raise ValueError(f"Unresolved source id: {ident}")
            direct = item.get("source_url") or item.get("url")
            if direct:
                urls.append(direct)
            if any(urlsplit(u).scheme != "https" or not urlsplit(u).hostname or urlsplit(u).username is not None for u in urls):
                raise ValueError(f"Non-HTTPS source: {ident}")
            records.append({"id": ident, "title": title, "kind": kind,
                "catalog": namespace, "record_id": local_id,
                "catalog_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "catalog_sha256": digest(data), "sources": list(dict.fromkeys(urls)),
                "date": item.get("checked_on") or item.get("recorded_on") or doc.get("as_of") or doc.get("research_date") or doc.get("archived_on") or doc.get("updated_on") or doc.get("recorded_on"),
                "record_sha256": digest(json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")),
                "product": item.get("product"),
                "confidence": item.get("evidence") or item.get("classification"),
                "license": item.get("license"),
                "availability": item.get("status") if namespace == "visual" else
                    ("archived-blob-declared" if namespace == "grok-assets" else
                     "link-only" if namespace.endswith("sources") or namespace == "grok-links" else "documented"),
                "record": item})
    for row in supplemental_records():
        if row["id"] in seen:
            raise ValueError(f"Duplicate id: {row['id']}")
        seen.add(row["id"])
        records.append(row)
    return records

def build(db, records):
    """Reconcile the explicit catalog snapshot, preserving unchanged FTS rows.

    The complete snapshot is authoritative: removed records cannot survive a
    rebuild. Changes to the serialized payload (including provenance) update
    the FTS entry atomically with its metadata.
    """
    incoming = {}
    for row in records:
        ident = row["id"]
        if ident in incoming:
            raise ValueError(f"Duplicate id: {ident}")
        incoming[ident] = (row, json.dumps(row, ensure_ascii=False, sort_keys=True))
    db.executescript("""
    CREATE TABLE IF NOT EXISTS research(id TEXT PRIMARY KEY, kind TEXT NOT NULL, catalog TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE VIRTUAL TABLE IF NOT EXISTS research_fts USING fts5(id UNINDEXED, title, body, tokenize='unicode61 remove_diacritics 2');
    """)
    previous = dict(db.execute("SELECT id, payload FROM research"))
    removed = sorted(previous.keys() - incoming.keys())
    changed = sorted(ident for ident, (_, payload) in incoming.items()
                     if previous.get(ident) != payload)
    added = sum(ident not in previous for ident in changed)
    with db:
        for ident in removed:
            db.execute("DELETE FROM research_fts WHERE id=?", (ident,))
            db.execute("DELETE FROM research WHERE id=?", (ident,))
        for ident in changed:
            row, payload = incoming[ident]
            db.execute("DELETE FROM research_fts WHERE id=?", (ident,))
            db.execute("INSERT OR REPLACE INTO research VALUES (?,?,?,?)",
                       (ident, row["kind"], row["catalog"], payload))
            db.execute("INSERT INTO research_fts VALUES (?,?,?)", (ident, row["title"], payload))
    return {"added": added, "updated": len(changed) - added,
            "removed": len(removed), "unchanged": len(incoming) - len(changed)}

def query_expr(query):
    tokens = re.findall(r"[\w]+", normalized(query))
    if len(tokens) > 12:
        raise ValueError("At most twelve terms")
    clauses = []
    for token in tokens:
        synonyms = {token}
        for group in ALIASES:
            words = {normalized(x) for x in group}
            if token in words:
                synonyms.update(words)
        clauses.append("(" + " OR ".join('"' + t + '"' for t in sorted(synonyms)) + ")")
    return " AND ".join(clauses)

def search(db, query, kind=None, limit=20, *, product=None, source=None,
           availability=None, confidence=None, since=None, until=None):
    match = query_expr(query)
    if not match:
        return []
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1..100")
    sql = """SELECT r.payload FROM research_fts JOIN research r ON r.id=research_fts.id
        WHERE research_fts MATCH ? AND (? IS NULL OR r.kind=?)"""
    args = [match, kind, kind]
    for field, value in (("product", product), ("availability", availability), ("confidence", confidence)):
        if value is not None:
            sql += f" AND lower(json_extract(r.payload, '$.{field}')) = lower(?)"
            args.append(value)
    if source is not None:
        sql += " AND EXISTS (SELECT 1 FROM json_each(r.payload, '$.sources') WHERE value=?)"
        args.append(source)
    for op, value in ((">=", since), ("<=", until)):
        if value is not None:
            sql += f" AND json_extract(r.payload, '$.date') {op} ?"
            args.append(value)
    sql += " ORDER BY bm25(research_fts,0,4,1), r.id LIMIT ?"
    return [json.loads(r[0]) for r in db.execute(sql, (*args, limit))]


def coverage(records):
    counts = Counter(r["catalog"] for r in records)
    return {"records": len(records), "catalogs": dict(counts),
            "scope": "explicit public research catalogs only; historical and private index not included"}


def provenance_graph(records):
    """Exact URL relations only; no inferred equivalence."""
    nodes, edges = {}, []
    for r in records:
        ident = r["id"]
        nodes[ident] = {"id": ident, "type": r["kind"], "title": r["title"],
                        "catalog_path": r.get("catalog_path"), "catalog_sha256": r.get("catalog_sha256")}
        for url in sorted(set(r.get("sources", []))):
            target = "url:" + digest(url.encode("utf-8"))
            nodes[target] = {"id": target, "type": "source_url", "url": url}
            edges.append({"source": ident, "target": target, "type": "cites",
                          "confidence": "explicit_catalog_link"})
    return {"nodes": sorted(nodes.values(), key=lambda n: n["id"]),
            "edges": sorted(edges, key=lambda e: (e["source"], e["target"])),
            "scope": "explicit public catalog citations; not historical decisions or verified live links"}


def coverage_gaps(records):
    """Report explicit public-catalog relations only, never inferred evidence coverage."""
    referenced = {url for r in records if r["kind"] != "source" for url in r.get("sources", [])}
    source_rows = [r for r in records if r["kind"] == "source"]
    source_urls = {url for r in source_rows for url in r.get("sources", [])}
    missing = sorted(source_urls - referenced)
    domains = Counter(str(r.get("record", {}).get("issue")) for r in records
                      if r.get("catalog") == "domain-research")
    return {
        "unique_source_urls": len(source_urls),
        "source_urls_with_non_source_reference": len(source_urls & referenced),
        "source_urls_without_non_source_reference": missing,
        "missing_source_status_ids": sorted(r["id"] for r in source_rows
                                            if not r.get("record", {}).get("status")),
        "patterns_without_source_ids_or_urls": sorted(r["id"] for r in records
                                                      if r["kind"] == "pattern" and not r.get("sources")),
        "domain_research_by_issue": dict(sorted(domains.items())),
        "visual_content_inspection": "not assessed by catalog audit",
        "live_url_verification": "not performed",
        "historical_private_coverage": "not assessed",
    }

def audit(records):
    visual = Counter()
    gaps = Counter()
    for r in records:
        item = r.get("record", {})
        if r["kind"] == "visual":
            visual[(r.get("product") or "unknown", item.get("kind") or "unknown",
                    r.get("availability") or "unknown")] += 1
        for field in ("product", "date", "confidence", "license"):
            if not r.get(field):
                gaps[field] += 1
        if not r.get("sources"):
            gaps["sources"] += 1
    graph = provenance_graph(records)
    with sqlite3.connect(":memory:") as db:
        build(db, records)
        queries = {q: len(search(db, q, limit=20)) for q in
                   ("side panel", "wall", "shared layout", "agent mascot", "generative UI", "vídeo", "kanban")}
    return {**coverage(records), "knowledge_coverage_gaps": coverage_gaps(records), "unknown_metadata_counts": dict(gaps),
            "visual_matrix": [{"product": p, "modality": k, "availability": a, "records": n}
                              for (p,k,a),n in sorted(visual.items())],
            "graph": {"nodes": len(graph["nodes"]), "edges": len(graph["edges"])},
            "query_hit_counts_top20": queries,
            "limitations": ["Hit counts are not precision or recall.",
                            "Media status is declared by catalogs, not checked here.",
                            "Unknown metadata is not evidence of absence.",
                            "No live-link, private-data or historical restoration validation."]}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--kind", choices=["pattern","source","visual"])
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--db", default=":memory:")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--audit", action="store_true")
    p.add_argument("--graph", action="store_true")
    for name in ("product", "source", "availability", "confidence", "since", "until"):
        p.add_argument("--" + name)
    args = p.parse_args()
    records = load_records()
    with sqlite3.connect(args.db) as db:
        build(db,records)
        if args.audit:
            out = audit(records)
        elif args.graph:
            out = provenance_graph(records)
        elif args.coverage:
            out = coverage(records)
        else:
            out = search(db, args.query, args.kind, args.limit, product=args.product,
                         source=args.source, availability=args.availability,
                         confidence=args.confidence, since=args.since, until=args.until)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
