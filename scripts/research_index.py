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
    ("clickup", "ui-ux-research-sources/clickup/pattern-index.json", "patterns", "pattern"),
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

# Discovery leads are source metadata, not patterns, checked screenshots or
# retrieved source bodies. Keep catalog occurrences even when URLs overlap.
DISCOVERY_CATALOGS = (
    ("discovery-1", "discovery-2026-11-25.json", "sources"),
    ("discovery-2", "discovery-2026-11-25-batch-2.json", "sources"),
    ("discovery-3", "discovery-2026-11-25-batch-3.json", "sources"),
    ("visual-discovery", "visual-evidence-discovery-2026-11-25.json", "sources"),
    ("design-md-discovery", "getdesign-public-corpus-2026-11-25.json", "documents"),
)

def discovery_records(base=BASE):
    for namespace, filename, key in DISCOVERY_CATALOGS:
        path = base / "ui-ux-research-sources" / filename
        raw = path.read_bytes()
        doc = json.loads(raw)
        for index, item in enumerate(doc[key]):
            local_id = item.get("id") or item["source_id"]
            url = item["url"]
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None:
                raise ValueError("Invalid discovery source URL")
            projected = dict(item)
            status = item.get("status") or item.get("access_status") or item.get("access")
            projected["status"] = status or "not-established"
            if key == "documents":
                projected["summary"] = item.get("pattern", "")
                projected["description"] = "Independent DESIGN.md analysis; source body not retained in this record."
            yield {"id":namespace+":"+local_id, "record_id":local_id,
                   "catalog":namespace, "kind":"source",
                   "title":item.get("title") or local_id+" DESIGN.md",
                   "catalog_path":"docs/references/ui-ux-research-sources/"+filename,
                   "catalog_sha256":digest(raw),
                   "record_pointer":f"/{key}/{index}",
                   "record_sha256":record_digest(item),
                   "projection_sha256":record_digest(projected),
                   "sources":[url],"date":item.get("recorded_on") or doc.get("recorded_on") or doc.get("date"),
                   "product":item.get("product"),"confidence":status,
                   "license":item.get("license"),"availability":"link-only",
                   "record":projected}


MOTION_CATALOG = "ui-ux-patterns-2026-11-25/visual-motion-evidence.json"
MOTION_GROUPS = ("capacities_visuals", "capacities_references", "motion_demos", "motion_source")


def motion_reference_records(base=BASE):
    """Expose existing evidence pointers, without claiming inspected runtime."""
    path = base / MOTION_CATALOG
    raw = path.read_bytes()
    doc = json.loads(raw)
    for key in MOTION_GROUPS:
        for index, item in enumerate(doc[key]):
            local_id = item.get("id") or item["path"]
            product = "Capacities" if key.startswith("capacities") else "Motion"
            url = item["url"]
            urls = list(dict.fromkeys([url] + ([item["source"]] if item.get("source") else [])))
            if any(urlsplit(u).scheme != "https" or not urlsplit(u).hostname or urlsplit(u).username is not None for u in urls):
                raise ValueError("Invalid motion reference URL")
            projected = dict(item, product=product, reference_type=key)
            projected["domain"] = "motion" if product == "Motion" else "workspace"
            if key == "motion_source":
                projected["source_repo"] = "motiondivision/motion"
                projected["source_commit"] = item["commit"]
                projected["source_path"] = item["upstream_path"]
                projected["local_copy_path"] = "docs/references/ui-ux-patterns-2026-11-25/" + item["path"]
            if key == "capacities_visuals":
                projected["visual_inspection"] = "prior-catalog-reports-seen" if item["status"] == "seen" else "fetch-failed"
            if key == "motion_demos":
                projected["playback"] = "not-recorded"
            yield {"id":"motion-reference:"+key+":"+local_id, "record_id":local_id,
                   "catalog":"motion-reference", "kind":"source",
                   "title":product+" "+Path(local_id).stem.replace("-", " "),
                   "catalog_path":"docs/references/"+MOTION_CATALOG,
                   "catalog_sha256":digest(raw), "record_pointer":f"/{key}/{index}",
                   "record_sha256":record_digest(item), "projection_sha256":record_digest(projected),
                   "sources":urls, "date":doc["date"], "product":product,
                   "confidence":item["status"], "license":item.get("license"),
                   "availability":"source-copy-declared" if key=="motion_source" else "link-only",
                   "record":projected}


def verify_motion_source_copies(*, base=BASE):
    """Verify only declared licensed local copies; do not execute examples."""
    base = Path(base).resolve()
    parent = base / "ui-ux-patterns-2026-11-25"
    doc = json.loads((base / MOTION_CATALOG).read_bytes())
    errors = []
    checked = 0
    for item in doc["motion_source"]:
        try:
            rel = Path(item["path"])
            if len(rel.parts) != 2 or rel.parts[0] != "motion-source" or rel.suffix not in {".tsx", ".md"}:
                raise ValueError("unapproved motion copy path")
            path = parent / rel
            if path.resolve(strict=True) != path:
                raise ValueError("unsafe motion copy path")
            raw = path.read_bytes()
            blob = hashlib.sha1(f"blob {len(raw)}\x00".encode("ascii") + raw).hexdigest()
            if blob != item["blob_sha"]:
                raise ValueError("blob mismatch")
            if item["license"] != "MIT" or not re.fullmatch(r"[0-9a-f]{40}", item["commit"]):
                raise ValueError("missing declared license or commit pin")
            checked += 1
        except (OSError, ValueError, KeyError) as exc:
            errors.append({"path":item.get("path"),"reason":str(exc)})
    return {"checked":checked,"total":len(doc["motion_source"]),"errors":errors,
            "integrity_passed":not errors,"scope":"local source bytes only; runtime not verified"}


def record_digest(item):
    return digest(json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8"))


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
        def project(item, kind, pointer, product=None):
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
                    "record_sha256":record_digest(item), "record_pointer":pointer,
                    "projection_sha256":record_digest(projected),
                    "sources":list(dict.fromkeys(urls)),
                    "date":item.get("checked_on") or item.get("recorded_on") or item.get("date") or catalog_date,
                    "product":product or item.get("product"),
                    "confidence":item.get("evidence_status") or item.get("evidence") or item.get("classification"),
                    "license":item.get("license"),
                    "availability":"link-only" if kind=="source" else "cataloged-synthesis",
                    "record":projected}
        for index, source in enumerate(doc["sources"]):
            yield project(source,"source",f"/sources/{index}")
        if key=="products":
            for product_index, product in enumerate(doc[key]):
                for index, item in enumerate(product["patterns"]):
                    yield project(item,"pattern",f"/{key}/{product_index}/patterns/{index}",product=product["product"])
        else:
            for index, item in enumerate(doc[key]):
                yield project(item,"pattern",f"/{key}/{index}")


def product_graph_records(base=BASE):
    """Project the reviewed product graph without treating candidates as evidence."""
    path = base / "interface-pattern-library/ai-product-knowledge-graph.json"
    raw = path.read_bytes()
    doc = json.loads(raw)
    nodes = {n["id"]: n for n in doc["nodes"]}
    if len(nodes) != len(doc["nodes"]):
        raise ValueError("Duplicate product graph node")
    edges = doc["edges"]
    if any(e["from"] not in nodes or e["to"] not in nodes for e in edges):
        raise ValueError("Dangling product graph edge")
    kinds = {"view-or-entry-point": "view", "output": "output",
             "evidence": "visual", "evidence-lead": "visual",
             "documented-flow": "flow",
             "documented-interaction-contract": "contract",
             "documented-availability": "availability",
             "documented-creation-option": "creation-option"}
    owners = {}
    links = {}
    for e in edges:
        links.setdefault(e["from"], []).append(e)
        if nodes[e["from"]]["type"] == "product":
            owners[e["to"]] = nodes[e["from"]]["label"]
    for e in edges:
        if e["relation"] == "illustrated_by" and e["from"] in owners:
            owners[e["to"]] = owners[e["from"]]
    for index, n in enumerate(doc["nodes"]):
        ident = n["id"]
        if n["type"] not in kinds:
            continue
        direct = links.get(ident, [])
        # Only explicit source edges; do not inherit product-level authority.
        urls = [nodes[e["to"]]["url"] for e in direct
                if nodes[e["to"]]["type"] == "source"]
        if any(urlsplit(u).scheme != "https" or not urlsplit(u).hostname
               or urlsplit(u).username is not None for u in urls):
            raise ValueError("Invalid public graph source")
        kind = kinds[n["type"]]
        product = owners.get(ident) or n.get("product")
        related = [{"relation": e["relation"], "node": e["to"],
                    "label": nodes[e["to"]]["label"], "status": e["status"]}
                   for e in direct]
        record = dict(n, product=product, relations=related)
        if kind != "visual":
            # Every projected graph claim (not only views and outputs) retains
            # its direct supporting statements. Visual publisher attribution
            # is a distinct relation and is not converted to claim support.
            unique_urls = list(dict.fromkeys(urls))
            record["source_evidence"] = [
                [unique_urls.index(nodes[e["to"]]["url"]), e["status"]]
                for e in direct if e["relation"] == "supported_by"
                and nodes[e["to"]]["type"] == "source"
            ]
        yield {"id": "ai-product-graph:" + ident, "title": n["label"],
               "kind": kind, "catalog": "ai-product-graph", "record_id": ident,
               "catalog_path": "docs/references/interface-pattern-library/ai-product-knowledge-graph.json",
               "catalog_sha256": digest(raw),
               "record_sha256": record_digest(n), "record_pointer": f"/nodes/{index}",
               "projection_sha256": record_digest(record),
               "sources": list(dict.fromkeys(urls)), "date": doc["reviewed_on"],
               "product": product, "confidence": n.get("evidence_status") or n.get("status") or n.get("classification"),
               "license": n.get("rights"),
               "availability": "link-only" if kind == "visual" else "cataloged-synthesis",
               "record": record}

def load_records(*, base=BASE):
    base = Path(base)
    root = base.parent.parent
    records, seen = [], set()
    general_sources = json.loads((base / "interface-pattern-library/sources.json").read_text(encoding="utf-8"))["sources"]
    source_map = {x["id"]: x["url"] for x in general_sources}
    research_sources = json.loads((base / "ui-ux-research-sources/sources.json").read_text(encoding="utf-8"))["sources"]
    research_map = {x["id"]: x["url"] for x in research_sources}
    maps = {"general": source_map, "design-foundations": source_map, "domain-research": source_map, "clickup": research_map}
    for namespace, rel, key, kind in CATALOGS:
        path = base / rel
        data = path.read_bytes()
        doc = json.loads(data)
        if namespace == "workspace":
            maps[namespace] = doc["sources"]
        for index, item in enumerate(doc[key]):
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
                "catalog_path": str(path.relative_to(root)).replace("\\", "/"),
                "catalog_sha256": digest(data), "sources": list(dict.fromkeys(urls)),
                "date": item.get("checked_on") or item.get("recorded_on") or doc.get("as_of") or doc.get("research_date") or doc.get("archived_on") or doc.get("updated_on") or doc.get("recorded_on"),
                "record_sha256": record_digest(item), "record_pointer": f"/{key}/{index}",
                "projection_sha256": record_digest(item),
                "product": item.get("product"),
                "confidence": item.get("evidence") or item.get("classification") or (item.get("status") if item.get("product") == "ClickUp" else None),
                "license": item.get("license"),
                "availability": item.get("status") if namespace == "visual" else
                    ("archived-blob-declared" if namespace == "grok-assets" else
                     "link-only" if namespace.endswith("sources") or namespace == "grok-links" else "documented"),
                "record": item})
    for row in (*supplemental_records(base), *product_graph_records(base), *discovery_records(base), *motion_reference_records(base)):
        if row["id"] in seen:
            raise ValueError(f"Duplicate id: {row['id']}")
        seen.add(row["id"])
        records.append(row)
    return records

def verify_record_provenance(records, *, root=ROOT, require_complete=False):
    """Recheck exact public catalog bytes, original JSON location and projection.

    No arbitrary filesystem paths: the approved catalog registry is authoritative.
    This is local content integrity, not verification of upstream claims.
    """
    root = Path(root).resolve()
    allowed = {"docs/references/" + rel for _, rel, _, _ in CATALOGS}
    allowed.update("docs/references/ui-ux-research-sources/" + name
                   for _, name, _, _ in SUPPLEMENTAL_CATALOGS)
    allowed.update("docs/references/ui-ux-research-sources/" + name
                   for _, name, _ in DISCOVERY_CATALOGS)
    allowed.add("docs/references/" + MOTION_CATALOG)
    allowed.add("docs/references/interface-pattern-library/ai-product-knowledge-graph.json")
    cache = {}
    errors = []
    checked = 0
    seen = set()
    # Rebuild expected projection from the source catalogs, never trust a
    # caller-supplied projection digest as the expected value.
    try:
        for path in allowed:
            candidate = root / path
            if candidate.resolve(strict=True) != candidate:
                raise ValueError("unsafe catalog path")
        expected = {r["id"]: r for r in load_records(base=root / "docs/references")}
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        return {"checked": 0, "total": len(records), "errors": [{"reason": str(exc)}],
                "integrity_passed": False, "scope": "local public catalog content only"}
    for row in records:
        ident = row.get("id", "")
        path = row.get("catalog_path")
        try:
            if ident in seen:
                raise ValueError("duplicate record identity")
            seen.add(ident)
            if path not in allowed:
                raise ValueError("unapproved catalog")
            if path not in cache:
                file = (root / path).resolve(strict=True)
                if not file.is_relative_to(root) or file != root / path:
                    raise ValueError("unsafe catalog path")
                raw = file.read_bytes()
                cache[path] = (digest(raw), json.loads(raw))
            checksum, doc = cache[path]
            if row.get("catalog_sha256") != checksum:
                raise ValueError("catalog checksum mismatch")
            pointer = row.get("record_pointer", "")
            if not re.fullmatch(r"/[a-zA-Z_]+/[0-9]+(?:/[a-zA-Z_]+/[0-9]+)?", pointer):
                raise ValueError("invalid record pointer")
            original = doc
            for part in pointer[1:].split("/"):
                original = original[int(part)] if isinstance(original, list) else original[part]
            if not isinstance(original, dict) or record_digest(original) != row.get("record_sha256"):
                raise ValueError("original record checksum mismatch")
            if record_digest(row["record"]) != row.get("projection_sha256"):
                raise ValueError("projection checksum mismatch")
            if ident not in expected or row != expected[ident]:
                raise ValueError("record differs from regenerated canonical projection")
            checked += 1
        except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
            errors.append({"record": ident, "reason": str(exc)})
    if require_complete:
        errors.extend({"record": ident, "reason": "missing canonical record"}
                      for ident in sorted(set(expected) - seen))
    return {"checked": checked, "total": len(records), "errors": errors,
            "integrity_passed": not errors, "scope": "local public catalog content only",
            "expected_records": len(expected), "complete_snapshot_required": require_complete}


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
    previous = {ident: (kind, catalog, payload) for ident, kind, catalog, payload in
                db.execute("SELECT id, kind, catalog, payload FROM research")}
    fts_rows = {}
    for ident, title, body in db.execute("SELECT id, title, body FROM research_fts"):
        fts_rows.setdefault(ident, []).append((title, body))
    removed = sorted(previous.keys() - incoming.keys())
    orphaned_fts = fts_rows.keys() - incoming.keys()
    changed = sorted(ident for ident, (row, payload) in incoming.items()
                     if previous.get(ident) != (row["kind"], row["catalog"], payload)
                     or fts_rows.get(ident) != [(row["title"], payload)])
    added = sum(ident not in previous for ident in changed)
    with db:
        for ident in orphaned_fts:
            db.execute("DELETE FROM research_fts WHERE id IS ?", (ident,))
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


def index_membership(db, records):
    """Compare canonical projected records with actual SQLite metadata and FTS rows.

    This measures exact stored membership, not retrieval relevance, media inspection
    or coverage of external/private sources. Do not use catalog counts as index counts.
    """
    expected = {}
    for row in records:
        if row["id"] in expected:
            raise ValueError(f"Duplicate id: {row['id']}")
        expected[row["id"]] = row
    metadata = {ident: (kind, catalog, payload) for ident, kind, catalog, payload in
                db.execute("SELECT id, kind, catalog, payload FROM research")}
    fts = {}
    for ident, title, body in db.execute("SELECT id, title, body FROM research_fts"):
        fts.setdefault(ident, []).append((title, body))
    missing_metadata, missing_fts, stale_metadata, stale_fts, matched = [], [], [], [], []
    duplicates = [ident for ident, rows in fts.items() if len(rows) != 1]
    by_catalog = {}
    for ident, row in expected.items():
        counts = by_catalog.setdefault(row["catalog"], {"eligible": 0, "matched": 0})
        counts["eligible"] += 1
        payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
        meta_ok = metadata.get(ident) == (row["kind"], row["catalog"], payload)
        fts_ok = fts.get(ident) == [(row["title"], payload)]
        if not meta_ok:
            (missing_metadata if ident not in metadata else stale_metadata).append(ident)
        if not fts_ok:
            (missing_fts if ident not in fts else stale_fts).append(ident)
        if meta_ok and fts_ok:
            matched.append(ident)
            counts["matched"] += 1
    extras_meta = set(metadata) - set(expected)
    extras_fts = set(fts) - set(expected)
    def ordered(values):
        return sorted(values, key=lambda v: (v is not None, str(v)))
    return {
        "scope": "explicit public catalog projection; excludes historical/private and unregistered sources",
        "eligible_records": len(expected),
        "matched_records": len(matched),
        "membership_percent": 100 * len(matched) / len(expected) if expected else None,
        "by_catalog": dict(sorted(by_catalog.items())),
        "missing_metadata_ids": ordered(missing_metadata),
        "missing_fts_ids": ordered(missing_fts),
        "stale_metadata_ids": ordered(stale_metadata),
        "stale_fts_ids": ordered(stale_fts),
        "duplicate_fts_ids": ordered(duplicates),
        "unexpected_metadata_ids": ordered(extras_meta),
        "unexpected_fts_ids": ordered(extras_fts),
        "integrity_passed": bool(expected) and len(matched) == len(expected)
                            and not extras_meta and not extras_fts,
    }


def coverage(records, db=None):
    counts = Counter(r["catalog"] for r in records)
    result = {"records": len(records), "catalogs": dict(counts),
              "scope": "explicit public research catalogs only; historical and private index not included"}
    if db is not None:
        result["index_membership"] = index_membership(db, records)
    return result


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
        measured_coverage = coverage(records, db)
        queries = {q: len(search(db, q, limit=20)) for q in
                   ("side panel", "wall", "shared layout", "agent mascot", "generative UI", "vídeo", "kanban")}
    return {**measured_coverage, "knowledge_coverage_gaps": coverage_gaps(records), "unknown_metadata_counts": dict(gaps),
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
    p.add_argument("--kind", choices=["pattern","source","visual","view","output","flow","contract","availability","creation-option"])
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--db", default=":memory:")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--verify-index", action="store_true", help="Audit an existing database without rebuilding it")
    p.add_argument("--audit", action="store_true")
    p.add_argument("--graph", action="store_true")
    for name in ("product", "source", "availability", "confidence", "since", "until"):
        p.add_argument("--" + name)
    args = p.parse_args()
    records = load_records()
    if args.verify_index:
        if args.db == ":memory:" or not Path(args.db).is_file():
            p.error("--verify-index requires an existing --db file")
        with sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True) as db:
            out = index_membership(db, records)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        raise SystemExit(0 if out["integrity_passed"] else 1)
    with sqlite3.connect(args.db) as db:
        build(db,records)
        if args.audit:
            out = audit(records)
        elif args.graph:
            out = provenance_graph(records)
        elif args.coverage:
            out = coverage(records, db)
        else:
            out = search(db, args.query, args.kind, args.limit, product=args.product,
                         source=args.source, availability=args.availability,
                         confidence=args.confidence, since=args.since, until=args.until)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
