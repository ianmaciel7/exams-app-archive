#!/usr/bin/env python3
"""Rebuild an offline public research index from explicitly approved catalogs."""
import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/references"
CATALOGS = (
    ("general", "interface-pattern-library/patterns.json", "patterns", "pattern"),
    ("workspace", "ui-ux-patterns-2026-11-25/patterns.json", "patterns", "pattern"),
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

def load_records():
    records, seen = [], set()
    general_sources = json.loads((BASE / "interface-pattern-library/sources.json").read_text(encoding="utf-8"))["sources"]
    maps = {"general": {x["id"]: x["url"] for x in general_sources}}
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
            if any(not u.startswith("https://") for u in urls):
                raise ValueError(f"Non-HTTPS source: {ident}")
            records.append({"id": ident, "title": title, "kind": kind,
                "catalog": namespace, "record_id": local_id,
                "catalog_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "catalog_sha256": digest(data), "sources": list(dict.fromkeys(urls)),
                "availability": item.get("status") if namespace == "visual" else
                    ("archived-blob-declared" if namespace == "grok-assets" else
                     "link-only" if namespace.endswith("sources") or namespace == "grok-links" else "documented"),
                "record": item})
    return records

def build(db, records):
    db.executescript("""
    DROP TABLE IF EXISTS research_fts;
    DROP TABLE IF EXISTS research;
    CREATE TABLE research(id TEXT PRIMARY KEY, kind TEXT NOT NULL, catalog TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE VIRTUAL TABLE research_fts USING fts5(id UNINDEXED, title, body, tokenize='unicode61 remove_diacritics 2');
    """)
    for row in records:
        payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
        db.execute("INSERT INTO research VALUES (?,?,?,?)", (row["id"],row["kind"],row["catalog"],payload))
        db.execute("INSERT INTO research_fts VALUES (?,?,?)", (row["id"],row["title"],payload))
    db.commit()

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

def search(db, query, kind=None, limit=20):
    match = query_expr(query)
    if not match:
        return []
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1..100")
    sql = """SELECT r.payload FROM research_fts JOIN research r ON r.id=research_fts.id
        WHERE research_fts MATCH ? AND (? IS NULL OR r.kind=?)
        ORDER BY bm25(research_fts,0,4,1), r.id LIMIT ?"""
    return [json.loads(r[0]) for r in db.execute(sql, (match,kind,kind,limit))]

def coverage(records):
    counts = {}
    for r in records:
        counts[r["catalog"]] = counts.get(r["catalog"], 0) + 1
    return {"records":len(records),"catalogs":counts,
            "scope":"explicit public research catalogs only; historical and private index not included"}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--kind", choices=["pattern","source","visual"])
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--db", default=":memory:")
    p.add_argument("--coverage", action="store_true")
    args = p.parse_args()
    records = load_records()
    with sqlite3.connect(args.db) as db:
        build(db,records)
        out = coverage(records) if args.coverage else search(db,args.query,args.kind,args.limit)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
