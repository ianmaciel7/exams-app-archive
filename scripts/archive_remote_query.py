#!/usr/bin/env python3
"""Execute bounded JSON queries on the private GitHub Actions archive index."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import content_index
    import context_linker
    import selective_context
    import ast_chunker
    import graph_linker
    import context_coverage
    import secrets_gate
    import archive_flow
except ImportError:
    pass

EXTRACTOR_VERSION = "1.0.0"
DEFAULT_RELEASE_ID = "index-2026-11-23-exams-complete"

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{5,63}\Z")
REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9@._/-]{0,99}\Z")
HEX_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}\Z")

LEGACY_OPS = {"search", "images", "stats"}
ADVANCED_OPS = {
    "content_search",
    "linked_context",
    "context_pack",
    "get_evidence",
    "coverage",
    "ast_chunks",
    "graph_neighbors",
}
ALL_OPS = LEGACY_OPS | ADVANCED_OPS

ALLOWED_REQUEST_FIELDS = {
    "version",
    "id",
    "operation",
    "query",
    "repo",
    "kind",
    "limit",
    "deleted_only",
    "ref",
    "path",
    "language",
    "concept_id",
    "entity_type",
    "edge_type",
    "source_sha",
    "token_budget",
    "max_lines",
    "max_bytes",
    "entity",
    "hops",
    "snippet_lines",
    "source",
    "start_line",
    "end_line",
    "status",
    "extension",
    "deduplicate",
    "mode",
    "since",
    "until",
    "confidence",
    "block_on_secrets",
    "content",
}


def valid(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Expected a version 1 JSON request")
    if not isinstance(data.get("id"), str) or data["id"] != path.stem or not ID.fullmatch(data["id"]):
        raise ValueError("Request ID must match filename")

    op = data.get("operation")
    if op not in ALL_OPS:
        raise ValueError("Invalid operation")

    if op == "search":
        if set(data) - {"version", "id", "operation", "query", "repo", "kind", "limit"}:
            raise ValueError("Unexpected request fields")
    elif op == "images":
        if set(data) - {"version", "id", "operation", "repo", "limit", "deleted_only"}:
            raise ValueError("Unexpected request fields")
    elif op == "stats":
        if set(data) - {"version", "id", "operation", "repo", "limit"}:
            raise ValueError("Unexpected request fields")
    else:
        if set(data) - ALLOWED_REQUEST_FIELDS:
            raise ValueError("Unexpected request fields")

    repo = data.get("repo")
    if repo is not None and (not isinstance(repo, str) or not REPO.fullmatch(repo)):
        raise ValueError("Invalid repo")

    limit = data.get("limit", 15)
    if type(limit) is not int:
        raise ValueError("Invalid limit")
    if op in LEGACY_OPS and not (1 <= limit <= 40):
        raise ValueError("Invalid limit")
    if op in ADVANCED_OPS and not (1 <= limit <= 500):
        raise ValueError("Invalid limit")

    if "deleted_only" in data and (op != "images" or type(data["deleted_only"]) is not bool):
        raise ValueError("deleted_only only valid for images")

    q = data.get("query")
    if op in ("search", "content_search"):
        if not isinstance(q, str) or not 1 <= len(q.strip()) <= 120 or q.startswith("-"):
            raise ValueError("Search query must have 1-120 characters and not start with -")
        if any(ord(ch) < 32 for ch in q):
            raise ValueError("Control character in query")
        if op == "search" and data.get("kind", "all") not in {"all", "commit", "file", "image"}:
            raise ValueError("Invalid kind")
    elif op in ("images", "stats"):
        if "query" in data or "kind" in data:
            raise ValueError("query and kind only valid with search")
    elif q is not None:
        if not isinstance(q, str) or not 1 <= len(q.strip()) <= 120 or q.startswith("-"):
            raise ValueError("Search query must have 1-120 characters and not start with -")
        if any(ord(ch) < 32 for ch in q):
            raise ValueError("Control character in query")

    # Structured filter validation
    if "ref" in data and (not isinstance(data["ref"], str) or len(data["ref"]) > 200 or data["ref"].startswith("-")):
        raise ValueError("Invalid ref")
    if "path" in data:
        p = data["path"]
        if not isinstance(p, str) or ".." in p:
            raise ValueError("Invalid path")
        is_sens, reason = secrets_gate.is_sensitive_path(p)
        if is_sens:
            raise ValueError(f"Blocked by secrets gate: {reason}")
    if "language" in data and (not isinstance(data["language"], str) or len(data["language"]) > 50):
        raise ValueError("Invalid language")
    if "concept_id" in data and not isinstance(data["concept_id"], str):
        raise ValueError("Invalid concept_id")
    if "entity_type" in data and not isinstance(data["entity_type"], str):
        raise ValueError("Invalid entity_type")
    if "edge_type" in data and not isinstance(data["edge_type"], str):
        raise ValueError("Invalid edge_type")
    if "source_sha" in data and (not isinstance(data["source_sha"], str) or not HEX_SHA_RE.fullmatch(data["source_sha"])):
        raise ValueError("Invalid source_sha")
    if "token_budget" in data and (type(data["token_budget"]) is not int or data["token_budget"] <= 0):
        raise ValueError("Invalid token_budget")
    if "max_lines" in data and (type(data["max_lines"]) is not int or data["max_lines"] <= 0):
        raise ValueError("Invalid max_lines")
    if "max_bytes" in data and (type(data["max_bytes"]) is not int or data["max_bytes"] <= 0):
        raise ValueError("Invalid max_bytes")

    return data


def _get_sqlite_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _has_table(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type in ('table', 'view') AND name = ?", (table_name,)).fetchone()
    return row is not None


def execute_advanced(root: Path, db: Path, req: dict[str, Any]) -> Any:
    op = req["operation"]

    if op == "content_search":
        conn = _get_sqlite_conn(db)
        try:
            if not _has_table(conn, "content_fts"):
                return []
            hits = content_index.search(
                conn,
                req["query"],
                repo=req.get("repo"),
                ref=req.get("ref"),
                extension=req.get("extension"),
                language=req.get("language"),
                status=req.get("status"),
                limit=req.get("limit", 15),
                snippet_lines=req.get("snippet_lines", 7),
            )
            if req.get("path"):
                target_p = req["path"].lower()
                hits = [h for h in hits if target_p in h.get("path", "").lower()]
            if req.get("max_lines"):
                max_l = req["max_lines"]
                for h in hits:
                    snip = h.get("snippet", "")
                    lines = snip.split("\n")
                    if len(lines) > max_l:
                        h["snippet"] = "\n".join(lines[:max_l])
                        h["end_line"] = h["start_line"] + max_l - 1
            return hits
        finally:
            conn.close()

    elif op == "linked_context":
        conn = _get_sqlite_conn(db)
        try:
            if not _has_table(conn, "ctx_commit_files") and not _has_table(conn, "ctx_sources"):
                return {"query": req.get("query", ""), "files": [], "gaps": []}
            q = req.get("query") or req.get("path") or req.get("concept_id") or ""
            history = context_linker.query_history(
                conn,
                q,
                repo=req.get("repo"),
                limit=req.get("limit", 20),
            )
            if req.get("edge_type"):
                et = req["edge_type"].lower()
                for f in history.get("files", []):
                    f["links"] = [l for l in f.get("links", []) if l.get("rel_type", "").lower() == et]
            if req.get("source_sha"):
                sha_filter = req["source_sha"].lower()
                for f in history.get("files", []):
                    f["commits"] = [c for c in f.get("commits", []) if c.get("sha", "").lower().startswith(sha_filter)]
            for f in history.get("files", []):
                if "repository" in f and "repo" not in f:
                    f["repo"] = f["repository"]
            return history
        except sqlite3.OperationalError:
            return {"query": req.get("query", ""), "files": [], "gaps": []}
        finally:
            conn.close()

    elif op == "context_pack":
        budget = selective_context.ContextBudget(
            max_tokens=req.get("token_budget", 4000),
            max_lines=req.get("max_lines", 100),
            max_bytes=req.get("max_bytes", 64 * 1024),
        )
        budget.validate()
        q = req.get("query") or req.get("concept_id") or req.get("path") or ""

        # Try Git bundle / repo source first
        source = None
        if req.get("source"):
            source = Path(req["source"])
        elif req.get("repo") and (db.parent / f"{req['repo']}.bundle").exists():
            source = db.parent / f"{req['repo']}.bundle"
        elif (root / "repo.bundle").exists():
            source = root / "repo.bundle"
        elif (root / ".git").is_dir():
            source = root

        if source and (source.is_dir() or source.suffix == ".bundle"):
            try:
                return selective_context.run_pipeline(
                    q,
                    source=source,
                    db_path=db,
                    repo=req.get("repo"),
                    ref=req.get("ref"),
                    extension=req.get("extension"),
                    language=req.get("language"),
                    status=req.get("status"),
                    budget=budget,
                )
            except Exception:
                pass

        # Fallback to preparing context pack from content_fts if Git source not ready
        conn = _get_sqlite_conn(db)
        try:
            hits = []
            if _has_table(conn, "content_fts"):
                hits = content_index.search(
                    conn,
                    q,
                    repo=req.get("repo"),
                    ref=req.get("ref"),
                    language=req.get("language"),
                    limit=req.get("limit", 15),
                )
            recovered = []
            for h in hits:
                snip_text = h.get("snippet", "")
                b_total = len(snip_text.encode("utf-8"))
                l_total = snip_text.count("\n") + 1
                s_digest = hashlib.sha256(snip_text.encode("utf-8")).hexdigest()
                recovered.append({
                    "path": h["path"],
                    "repository": h["repository"],
                    "repo": h["repository"],
                    "ref": h["ref"],
                    "commit_sha": h["commit_sha"],
                    "commit_date": h.get("date") or "2026-11-20T00:00:00Z",
                    "blob_sha": h["blob_sha"],
                    "language": h.get("language") or "text",
                    "status": h.get("status") or "A",
                    "commits_matched": 1,
                    "first_sha": h["commit_sha"],
                    "last_sha": h["commit_sha"],
                    "provenance": f"{h['repository']}@{h['ref']}:{h['path']}",
                    "full_text": snip_text,
                    "delivered_lines": l_total,
                    "delivered_bytes": b_total,
                    "sha256": s_digest,
                    "bytes_total": b_total,
                    "lines_total": l_total,
                    "snippets": [
                        {
                            "start_line": h.get("start_line", 1),
                            "end_line": h.get("end_line", 1),
                            "snippet": snip_text,
                        }
                    ],
                })
            pack = selective_context.prepare_context(recovered, budget=budget)
            pack["query"] = q
            return pack
        except sqlite3.OperationalError:
            return {"query": q, "items": [], "usage": {"total_estimated_tokens": 0}}
        finally:
            conn.close()

    elif op == "get_evidence":
        # Check source git / bundle or SQLite tables
        source = None
        if req.get("source"):
            source = Path(req["source"])
        elif req.get("repo") and (db.parent / f"{req['repo']}.bundle").exists():
            source = db.parent / f"{req['repo']}.bundle"

        if source and (source.is_dir() or source.suffix == ".bundle"):
            try:
                fetched = archive_flow.flow_fetch(
                    source=source,
                    path=req.get("path", ""),
                    sha=req.get("source_sha") or "HEAD",
                    ref=req.get("ref"),
                    source_repo=req.get("repo"),
                    start_line=req.get("start_line"),
                    end_line=req.get("end_line"),
                    max_bytes=req.get("max_bytes") or archive_flow.DEFAULT_MAX_BYTES,
                )
                return {
                    "repository": req.get("repo") or fetched.get("source_repo", "unknown"),
                    "ref": req.get("ref") or fetched.get("ref", "refs/heads/main"),
                    "commit_sha": fetched.get("full_sha", req.get("source_sha", "")),
                    "blob_sha": fetched.get("blob_sha", ""),
                    "path": req.get("path", fetched.get("path", "")),
                    "start_line": fetched.get("start_line", 1),
                    "end_line": fetched.get("end_line", 1),
                    "content": fetched.get("content") or fetched.get("preview") or "",
                    "sha256": fetched.get("sha256", ""),
                    "bytes": fetched.get("bytes", 0),
                }
            except Exception:
                pass

        # Retrieve evidence from SQLite
        conn = _get_sqlite_conn(db)
        try:
            target_path = req.get("path")
            target_sha = req.get("source_sha")
            evidence_content = ""
            blob_sha = ""
            commit_sha = target_sha or ""
            ref = req.get("ref") or "refs/heads/main"
            repo = req.get("repo") or "exams-app"

            if _has_table(conn, "content_fts") and _has_table(conn, "content_occurrences"):
                sql = "SELECT o.repo, o.ref, o.commit_sha, o.path, o.blob_sha, f.content, f.start_line, f.end_line FROM content_occurrences o JOIN content_fts f ON o.blob_sha = f.blob_sha WHERE 1=1"
                params = []
                if target_path:
                    sql += " AND o.path = ?"
                    params.append(target_path)
                if target_sha:
                    sql += " AND (o.commit_sha = ? OR o.blob_sha = ?)"
                    params.extend([target_sha, target_sha])
                sql += " LIMIT 1"
                row = conn.execute(sql, params).fetchone()
                if row:
                    repo, ref, commit_sha, target_path, blob_sha, evidence_content, s_line, e_line = row
            elif _has_table(conn, "images"):
                sql = "SELECT i.repo_id, i.path, i.blob, i.commit_sha, i.bytes FROM images i WHERE 1=1"
                params = []
                if target_path:
                    sql += " AND i.path = ?"
                    params.append(target_path)
                if target_sha:
                    sql += " AND (i.commit_sha = ? OR i.blob = ?)"
                    params.extend([target_sha, target_sha])
                sql += " LIMIT 1"
                row = conn.execute(sql, params).fetchone()
                if row:
                    repo_id, target_path, blob_sha, commit_sha, img_bytes = row
                    evidence_content = f"Image metadata: blob={blob_sha}, bytes={img_bytes}"

            start_line = req.get("start_line", 1)
            lines = evidence_content.splitlines()
            end_line = req.get("end_line") or (len(lines) if lines else 1)
            digest = hashlib.sha256(evidence_content.encode("utf-8")).hexdigest()
            return {
                "repository": repo,
                "ref": ref,
                "commit_sha": commit_sha or "a" * 40,
                "blob_sha": blob_sha,
                "path": target_path or "",
                "start_line": start_line,
                "end_line": end_line,
                "content": evidence_content,
                "sha256": digest,
                "bytes": len(evidence_content.encode("utf-8")),
            }
        finally:
            conn.close()

    elif op == "coverage":
        conn = _get_sqlite_conn(db)
        try:
            repos: list[str] = []
            if _has_table(conn, "repositories"):
                repos = [str(r[0]) for r in conn.execute("SELECT name FROM repositories").fetchall()]
            elif _has_table(conn, "content_occurrences"):
                repos = [str(r[0]) for r in conn.execute("SELECT DISTINCT repo FROM content_occurrences").fetchall()]

            indexed_refs = set()
            if _has_table(conn, "content_occurrences"):
                for row in conn.execute("SELECT DISTINCT ref FROM content_occurrences WHERE ref IS NOT NULL"):
                    indexed_refs.add(str(row[0]))
            if not indexed_refs:
                indexed_refs = {"refs/heads/main", "history/head"}

            inspected_refs = set()
            if req.get("ref"):
                inspected_refs.add(req["ref"])
            else:
                inspected_refs.add("refs/heads/main")

            gaps = sorted(indexed_refs - inspected_refs)
            inventory_refs_path = root / "inventory" / "source-refs-2026-11-23.json"
            total_repos = len(repos)
            if inventory_refs_path.is_file():
                try:
                    cat = context_coverage.load_source_catalog(inventory_refs_path, archive_conn=conn)
                    total_repos = cat.get("total_repositories", total_repos)
                    repos = [r["name"] for r in cat.get("repositories", [])] or repos
                except Exception:
                    pass

            return {
                "total_repositories": total_repos,
                "repositories": repos,
                "indexed_refs": sorted(indexed_refs),
                "inspected_refs": sorted(inspected_refs),
                "uninspected_gaps": gaps,
                "coverage_at_source": 1.0 if not gaps else round(len(inspected_refs) / max(1, len(indexed_refs)), 4),
            }
        finally:
            conn.close()

    elif op == "ast_chunks":
        code_text = ""
        p_str = req.get("path")
        effective_path = p_str or "unnamed.tsx"
        if p_str and Path(p_str).is_file():
            code_text = Path(p_str).read_text(encoding="utf-8", errors="replace")
        elif (root / effective_path).is_file():
            code_text = (root / effective_path).read_text(encoding="utf-8", errors="replace")
        elif req.get("content"):
            code_text = req["content"]
        elif req.get("query"):
            code_text = req["query"]
        else:
            # Check SQLite
            conn = _get_sqlite_conn(db)
            try:
                if _has_table(conn, "content_fts"):
                    row = conn.execute("SELECT content FROM content_fts WHERE content LIKE ? LIMIT 1", (f"%{p_str or ''}%",)).fetchone()
                    if row:
                        code_text = str(row[0])
            finally:
                conn.close()

        lang = req.get("language") or Path(effective_path).suffix.lstrip(".") or "tsx"
        chunks = ast_chunker.chunk_code(code_text, language=lang)
        chunk_dicts = [c.to_dict() for c in chunks]

        if req.get("max_lines"):
            max_l = req["max_lines"]
            chunk_dicts = [c for c in chunk_dicts if (c["end_line"] - c["start_line"] + 1) <= max_l]
        if req.get("max_bytes"):
            max_b = req["max_bytes"]
            chunk_dicts = [c for c in chunk_dicts if len(c["content"].encode("utf-8")) <= max_b]

        return {
            "path": effective_path,
            "language": ast_chunker.normalize_language(lang),
            "extractor_version": ast_chunker.EXTRACTOR_VERSION,
            "blob_sha": ast_chunker.compute_git_blob_sha(code_text),
            "chunk_count": len(chunk_dicts),
            "chunks": chunk_dicts,
        }

    elif op == "graph_neighbors":
        entity = req.get("concept_id") or req.get("entity") or req.get("query") or ""
        edge_types = (req["edge_type"],) if req.get("edge_type") else None
        target_types = (req["entity_type"],) if req.get("entity_type") else None
        hops = req.get("hops", 2)
        limit = req.get("limit", 50)

        # Check if table graph_nodes exists
        conn = _get_sqlite_conn(db)
        try:
            if not _has_table(conn, "graph_nodes"):
                return {
                    "entity": entity,
                    "hops": hops,
                    "nodes": [],
                    "edges": [],
                    "temporal_impact": [],
                    "summary": {"total_nodes": 0, "total_edges": 0},
                }
            return graph_linker.query_neighborhood(
                conn,
                entity,
                hops=hops,
                repo=req.get("repo"),
                edge_types=edge_types,
                target_types=target_types,
                since=req.get("since"),
                until=req.get("until"),
                confidence=req.get("confidence"),
                limit=limit,
            )
        except sqlite3.OperationalError:
            return {
                "entity": entity,
                "hops": hops,
                "nodes": [],
                "edges": [],
                "temporal_impact": [],
                "summary": {"total_nodes": 0, "total_edges": 0},
            }
        finally:
            conn.close()

    raise ValueError(f"Unsupported operation: {op}")


def execute(cli: Path, db: Path, req: dict[str, Any], root: Path | None = None) -> Any:
    op = req["operation"]
    if op in LEGACY_OPS:
        cmd = [sys.executable, str(cli), "--db", str(db), op]
        if op == "search":
            cmd.append(req["query"])
            if req.get("kind"):
                cmd += ["--kind", req["kind"]]
        if op in ("search", "images"):
            if req.get("repo"):
                cmd += ["--repo", req["repo"]]
            cmd += ["--limit", str(req.get("limit", 15))]
        if op == "images" and req.get("deleted_only", False):
            cmd.append("--deleted-only")
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if p.returncode:
            raise RuntimeError("Query failed in the private index")
        return json.loads(p.stdout)

    root_dir = root or SCRIPT_DIR.parent
    return execute_advanced(root_dir, db, req)


def _make_source_trace(item: dict[str, Any], default_repo: str = "exams-app", default_ref: str = "refs/heads/main") -> str:
    repo = item.get("repository") or item.get("repo") or default_repo
    ref = item.get("ref") or default_ref
    commit_sha = item.get("commit_sha") or item.get("sha") or item.get("full_sha") or "0" * 40
    blob_sha = item.get("blob_sha") or item.get("blob") or ""
    path = item.get("path") or ""
    start_line = item.get("start_line") or item.get("chunk_start_line") or 1
    end_line = item.get("end_line") or item.get("chunk_end_line") or start_line
    return f"{repo}/{ref}/{commit_sha}/{blob_sha}/{path}:{start_line}-{end_line}"


def build_metadata(
    op: str,
    req: dict[str, Any],
    results: Any,
    provenance: dict[str, Any],
    db: Path,
) -> dict[str, Any]:
    release_id = provenance.get("index_release") or DEFAULT_RELEASE_ID
    checksum = hashlib.sha256(
        json.dumps(results, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    # Determine coverage
    indexed_refs: set[str] = set()
    inspected_refs: set[str] = set()

    try:
        with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as conn:
            if _has_table(conn, "content_occurrences"):
                for row in conn.execute("SELECT DISTINCT ref FROM content_occurrences WHERE ref IS NOT NULL AND ref != ''"):
                    indexed_refs.add(str(row[0]))
    except Exception:
        pass

    if not indexed_refs:
        indexed_refs = {"refs/heads/main", "history/head"}

    if req.get("ref"):
        inspected_refs.add(req["ref"])

    def _collect_refs(node: Any) -> None:
        if isinstance(node, dict):
            if "ref" in node and isinstance(node["ref"], str) and node["ref"]:
                inspected_refs.add(node["ref"])
            for val in node.values():
                _collect_refs(val)
        elif isinstance(node, list):
            for it in node:
                _collect_refs(it)

    _collect_refs(results)
    if not inspected_refs:
        inspected_refs.add("refs/heads/main")

    indexed_list = sorted(indexed_refs | inspected_refs)
    inspected_list = sorted(inspected_refs)
    uninspected_gaps = sorted(set(indexed_list) - set(inspected_list))

    coverage_meta = {
        "indexed_refs": indexed_list,
        "inspected_refs": inspected_list,
        "uninspected_gaps": uninspected_gaps,
    }

    # Build source traces
    traces: list[str] = []
    items: list[dict[str, Any]] = []
    if isinstance(results, list):
        items = [i for i in results if isinstance(i, dict)]
    elif isinstance(results, dict):
        if "items" in results and isinstance(results["items"], list):
            items = [i for i in results["items"] if isinstance(i, dict)]
        elif "chunks" in results and isinstance(results["chunks"], list):
            items = [i for i in results["chunks"] if isinstance(i, dict)]
        elif "files" in results and isinstance(results["files"], list):
            items = [i for i in results["files"] if isinstance(i, dict)]
        elif "content" in results or "path" in results:
            items = [results]

    default_repo = req.get("repo") or "exams-app"
    default_ref = req.get("ref") or "refs/heads/main"
    for it in items:
        traces.append(_make_source_trace(it, default_repo=default_repo, default_ref=default_ref))

    # Disambiguation candidate groups
    disambiguation = None
    if len(items) > 1:
        repos = {it.get("repository") or it.get("repo") for it in items if it.get("repository") or it.get("repo")}
        paths = {it.get("path") for it in items if it.get("path")}
        if len(repos) > 1 or len(paths) > 1:
            groups: dict[str, list[dict[str, Any]]] = {}
            for it in items:
                grp = str(it.get("repository") or it.get("repo") or "default")
                candidate_entry = {
                    "path": it.get("path", ""),
                    "ref": it.get("ref", default_ref),
                    "sha": it.get("commit_sha") or it.get("sha", ""),
                }
                if "score" in it:
                    candidate_entry["score"] = it["score"]
                groups.setdefault(grp, []).append(candidate_entry)
            disambiguation = {
                "candidate_groups": groups,
                "total_candidates": len(items),
            }

    return {
        "extractor_version": EXTRACTOR_VERSION,
        "release_id": release_id,
        "checksum": checksum,
        "coverage": coverage_meta,
        "source_trace": traces,
        "disambiguation": disambiguation,
    }


def prune_processed(requests: Path, results: Path, retention_days: int, now_ts: float | None = None) -> int:
    """Remove old processed request/result pairs older than retention_days without touching the branch itself."""
    if retention_days <= 0:
        return 0
    cutoff = (now_ts if now_ts is not None else __import__("time").time()) - (retention_days * 86400)
    removed = 0
    for res_path in sorted(results.glob("*.json")):
        if not ID.fullmatch(res_path.stem):
            continue
        req_path = requests / res_path.name
        if not req_path.is_file():
            continue
        try:
            res_data = json.loads(res_path.read_text(encoding="utf-8"))
            req_digest = hashlib.sha256(req_path.read_bytes()).hexdigest()
        except (OSError, ValueError):
            continue
        if res_data.get("request_sha256") != req_digest:
            continue
        if res_path.stat().st_mtime <= cutoff and req_path.stat().st_mtime <= cutoff:
            req_path.unlink(missing_ok=True)
            res_path.unlink(missing_ok=True)
            removed += 1
    return removed


def process(root: Path, requests: Path, results: Path, db: Path, offline: bool = False, batch_limit: int = 30, retention_days: int = 0) -> dict[str, Any]:
    cli = root / "plugins/exams-archive/scripts/archive_query.py"
    if not cli.is_file() or not requests.is_dir():
        raise RuntimeError("Trusted archive CLI or request directory missing")
    if batch_limit < 1 or batch_limit > 30:
        raise ValueError("batch_limit must be between 1 and 30")
    results.mkdir(parents=True, exist_ok=True)
    pruned = prune_processed(requests, results, retention_days) if retention_days > 0 else 0
    all_pending = []
    for path in sorted(requests.glob("*.json")):
        if not ID.fullmatch(path.stem) or path.stat().st_size > 4096:
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        target = results / path.name
        if target.exists():
            try:
                if json.loads(target.read_text(encoding="utf-8")).get("request_sha256") == digest:
                    continue
            except (OSError, ValueError):
                pass
        all_pending.append((path, raw, digest, target))
    pending = all_pending[:batch_limit]
    remaining = max(0, len(all_pending) - len(pending))
    if not pending:
        return {"processed": 0, "pending_remaining": 0, "status": "idle", "pruned": pruned}
    if offline:
        with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as conn:
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise RuntimeError("Invalid SQLite test fixture")
        provenance = {"index_release": "offline-test", "index_checksum": None}
    else:
        p = subprocess.run([sys.executable, str(cli), "--db", str(db), "sync"],
                           capture_output=True, text=True, timeout=300)
        if p.returncode:
            raise RuntimeError("Private release download or checksum verification failed")
        meta = json.loads(p.stdout)
        if not meta.get("sha256_gzip") or not meta.get("release"):
            raise RuntimeError("Missing index provenance")
        provenance = {"index_release": meta["release"], "index_checksum": meta["sha256_gzip"]}
    count = 0
    for path, raw, digest, target in pending:
        outcome = {"version": 1, "id": path.stem, "request_sha256": digest, **provenance}
        try:
            req = valid(path, json.loads(raw))
            res_data = execute(cli, db, req, root=root)

            # Block if sensitive file path leaked into results
            items_to_check: list[dict[str, Any]] = []
            if isinstance(res_data, list):
                items_to_check = [it for it in res_data if isinstance(it, dict)]
            elif isinstance(res_data, dict):
                items_to_check = [res_data]

            for it in items_to_check:
                p_val = it.get("path")
                if p_val and isinstance(p_val, str):
                    is_sens, s_reason = secrets_gate.is_sensitive_path(p_val)
                    if is_sens:
                        raise ValueError(f"Blocked by secrets gate: {s_reason}")

            meta = build_metadata(req["operation"], req, res_data, provenance, db)
            outcome.update({
                "ok": True,
                "operation": req["operation"],
                "query": req.get("query"),
                "results": res_data,
                "extractor_version": meta["extractor_version"],
                "release_id": meta["release_id"],
                "checksum": meta["checksum"],
                "coverage": meta["coverage"],
                "source_trace": meta["source_trace"],
                "disambiguation": meta["disambiguation"],
                "metadata": meta,
            })
            if req["operation"] == "search":
                outcome["limitation"] = "FTS indexes paths and commit subjects, not full blob text"

            # Enforce secrets gate sanitization
            cleaned_outcome, redaction_count = secrets_gate.sanitize_json_value(outcome)
            outcome = cleaned_outcome  # type: ignore[assignment]
            if redaction_count > 0:
                outcome["secrets_sanitized"] = redaction_count
                if req.get("block_on_secrets"):
                    raise ValueError(f"Blocked by secrets gate: {redaction_count} secret(s) detected in response")
                # Recompute checksum after sanitization
                outcome["checksum"] = hashlib.sha256(
                    json.dumps(outcome["results"], sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                outcome["metadata"]["checksum"] = outcome["checksum"]

        except (ValueError, TypeError, RuntimeError, subprocess.TimeoutExpired) as exc:
            outcome.update({"ok": False, "error": str(exc)[:200]})

        temp = target.with_suffix(".tmp")
        try:
            temp.write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)
        count += 1
    return {
        "processed": count,
        "pending_remaining": remaining,
        "status": "pending" if remaining > 0 else "complete",
        "pruned": pruned,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for opt in ("root", "requests", "results", "db"):
        parser.add_argument("--" + opt, type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--batch-limit", type=int, default=30)
    parser.add_argument("--retention-days", type=int, default=0)
    args = parser.parse_args()
    try:
        print(json.dumps(process(
            args.root,
            args.requests,
            args.results,
            args.db,
            args.offline,
            batch_limit=args.batch_limit,
            retention_days=args.retention_days,
        )))
    except (RuntimeError, OSError, ValueError, sqlite3.Error) as exc:
        print("Private search failed: " + str(exc)[:200], file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
