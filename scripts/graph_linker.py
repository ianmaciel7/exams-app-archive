#!/usr/bin/env python3
"""Lightweight multi-repo historical relation graph builder & query engine.

Builds an inert SQLite (and optional JSON) property graph linking repositories,
refs/branches, commits, files, UI/domain components, PRs, issues, images, and
documented architectural/product decisions across historical Git bundles and
preserved platform inventories.

Typed nodes:
  Repo, Ref, Commit, File, Component, PR, Issue, Image, Decision

Typed directed edges:
  MODIFIES, DOCUMENTED_IN, EVIDENCED_BY, SUPERSEDES, IMPORTS, CO_OCCURS_WITH

Every edge records explicit provenance (confidence ``EXTRACTED`` vs ``INFERRED``,
source_ref, commit_sha, validity_status) so historical decisions and cross-repo
impacts can be audited without any external daemon, MCP server, or graph DB.

Standard library only. Zero external dependencies, zero shell interpolation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
import tracemalloc
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import image_catalog  # noqa: E402
import search_expansion  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DB_PATH = ".cache/archive/graph-linker.sqlite"

NODE_TYPES = (
    "Repo",
    "Ref",
    "Commit",
    "File",
    "Component",
    "PR",
    "Issue",
    "Image",
    "Decision",
)
NODE_TYPE_SET = frozenset(NODE_TYPES)

EDGE_TYPES = (
    "MODIFIES",
    "DOCUMENTED_IN",
    "EVIDENCED_BY",
    "SUPERSEDES",
    "IMPORTS",
    "CO_OCCURS_WITH",
)
EDGE_TYPE_SET = frozenset(EDGE_TYPES)

CONFIDENCE_LEVELS = ("EXTRACTED", "INFERRED")
CONFIDENCE_SET = frozenset(CONFIDENCE_LEVELS)

VALIDITY_STATES = (
    "valid_in_commit",
    "superseded_in_later_branch",
    "unverified",
)
VALIDITY_SET = frozenset(VALIDITY_STATES)

IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"})
CODE_EXTENSIONS = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".css", ".scss", ".html"})
DOC_EXTENSIONS = frozenset({".md", ".mdx", ".txt", ".json"})

_TS_IMPORT_RE = re.compile(
    r"""(?:import|export)\s+(?:type\s+)?(?:[\s\S]*?\s+from\s+)?["']([^"']+)["']|require\(\s*["']([^"']+)["']\s*\)""",
    re.MULTILINE,
)
_PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([A-Za-z0-9_.]+)\s+import|import\s+([A-Za-z0-9_.]+))",
    re.MULTILINE,
)
_ISSUE_REF_RE = re.compile(
    r"(?:(?:closes|closed|fixes|fixed|resolves|resolved|refs?|related\s+to|see)\s+)?#(\d+)\b",
    re.IGNORECASE,
)
_IMAGE_REF_RE = re.compile(
    r"!\[[^\]]*\]\(([^)\s]+)\)|([A-Za-z0-9_./-]+\.(?:png|jpg|jpeg|gif|svg|webp))\b",
    re.IGNORECASE,
)
_DECISION_DOC_RE = re.compile(
    r"(?:decis|decision|rationale|spec|design|proposal|adr|architecture|motion|comparacao|mapeamento)",
    re.IGNORECASE,
)
_DECISION_TEXT_RE = re.compile(
    r"(?i)(?:^|\b)(?:decision|decisao|rationale|justificativa|motivo|supersedes|replaces|substitui|adr|why|because)\b"
)
_SHA_HEX_RE = re.compile(r"^[0-9a-f]{7,64}$", re.IGNORECASE)

DB_SCHEMA = """
PRAGMA journal_mode=DELETE;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS graph_nodes (
    node_id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    repo TEXT NOT NULL DEFAULT '',
    ref TEXT NOT NULL DEFAULT '',
    label TEXT NOT NULL,
    path TEXT NOT NULL DEFAULT '',
    commit_sha TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT '',
    validity_status TEXT NOT NULL DEFAULT 'unverified',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS graph_edges (
    edge_id TEXT PRIMARY KEY,
    src_id TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'EXTRACTED',
    repo TEXT NOT NULL DEFAULT '',
    ref TEXT NOT NULL DEFAULT '',
    commit_sha TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT '',
    weight REAL NOT NULL DEFAULT 1.0,
    provenance_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(src_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY(dst_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    UNIQUE(src_id, dst_id, edge_type, commit_sha, ref)
);

CREATE VIRTUAL TABLE IF NOT EXISTS graph_nodes_fts USING fts5(
    node_id UNINDEXED,
    node_type UNINDEXED,
    repo UNINDEXED,
    label,
    path,
    metadata_text,
    tokenize='unicode61'
);

CREATE INDEX IF NOT EXISTS idx_gn_type_repo ON graph_nodes(node_type, repo);
CREATE INDEX IF NOT EXISTS idx_gn_label ON graph_nodes(label);
CREATE INDEX IF NOT EXISTS idx_gn_path ON graph_nodes(path);
CREATE INDEX IF NOT EXISTS idx_gn_ts ON graph_nodes(timestamp);
CREATE INDEX IF NOT EXISTS idx_ge_src ON graph_edges(src_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_ge_dst ON graph_edges(dst_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_ge_type_ts ON graph_edges(edge_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_ge_repo ON graph_edges(repo);
"""


def validate_private_output_path(path: Path, repo_root: Path | None = None) -> Path:
    return image_catalog.validate_private_output_path(path, repo_root=repo_root or REPO_ROOT)


def safe_path(path: str) -> str:
    return image_catalog.safe_path(path)


def open_db(path: Path) -> sqlite3.Connection:
    """Open or initialize the relational graph SQLite store."""
    if str(path) != ":memory:":
        validate_private_output_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(DB_SCHEMA)
    return conn


def _stable_id(prefix: str, *parts: Any) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8", "replace"))
        h.update(b"\x00")
    return f"{prefix}:{h.hexdigest()[:20]}"


def make_node_id(
    node_type: str,
    label: str,
    *,
    repo: str = "",
    ref: str = "",
    path: str = "",
    commit_sha: str = "",
) -> str:
    """Create a deterministic canonical node identifier."""
    if node_type not in NODE_TYPE_SET:
        raise ValueError(f"Unsupported node_type {node_type!r}; expected one of {NODE_TYPES}")
    if node_type == "Repo":
        return f"repo:{label}"
    if node_type == "Component":
        return f"component:{_canonical_component_key(label)}"
    if node_type == "Ref":
        return f"ref:{repo}:{label}"
    if node_type == "Commit":
        return f"commit:{repo}:{commit_sha or label}"
    if node_type == "PR":
        return f"pr:{repo}:{label}"
    if node_type == "Issue":
        return f"issue:{repo}:{label}"
    if node_type == "File":
        return f"file:{repo}:{ref}:{path or label}"
    if node_type == "Image":
        return f"image:{repo}:{path or label}"
    if node_type == "Decision":
        return _stable_id("decision", repo, ref, path or label, commit_sha)
    return _stable_id(node_type.lower(), repo, ref, label, path, commit_sha)


def _canonical_component_key(raw: str) -> str:
    """Normalize a symbol/component identifier across repos and languages."""
    norm = search_expansion.normalize_text(raw)
    norm = re.sub(r"[^a-z0-9]+", "-", norm).strip("-")
    aliases = {
        "barra-lateral": "sidebar",
        "gaveta": "sidebar",
        "app-sidebar": "sidebar",
        "workspace-sidebar": "sidebar",
        "grafo": "graph",
        "simulado": "exam",
        "repeticao-espacada": "fsrs",
    }
    return aliases.get(norm, norm or "unknown")


def infer_component_from_path(path: str, text: str = "") -> str | None:
    """Heuristically extract canonical Component key from path/symbol names."""
    p_low = path.lower()
    stem = Path(path).stem.lower() if path else ""
    combined = f"{p_low} {text.lower()}"
    if any(k in combined for k in ("sidebar", "barra-lateral", "barra lateral", "gaveta")):
        return "Sidebar"
    if any(k in combined for k in ("graph", "grafo")):
        return "GraphCanvas"
    if any(k in combined for k in ("app-shell", "app_shell", "shell")):
        return "AppShell"
    if any(k in combined for k in ("fsrs", "recall", "spaced-repetition", "repeticao")):
        return "FSRS"
    if any(k in combined for k in ("exam", "simulado", "mock-exam", "questao", "question")):
        return "ExamEngine"
    if stem and Path(path).suffix.lower() in CODE_EXTENSIONS and stem not in {"index", "utils", "types", "main"}:
        parts = [seg.capitalize() for seg in re.split(r"[-_.]", stem) if seg]
        if parts:
            return "".join(parts)
    return None


def upsert_node(
    conn: sqlite3.Connection,
    *,
    node_type: str,
    label: str,
    repo: str = "",
    ref: str = "",
    path: str = "",
    commit_sha: str = "",
    timestamp: str = "",
    validity_status: str = "unverified",
    metadata: dict[str, Any] | None = None,
    node_id: str | None = None,
) -> str:
    """Insert or update a typed node and keep its FTS5 shadow entry synced."""
    if node_type not in NODE_TYPE_SET:
        raise ValueError(f"Unsupported node_type: {node_type!r}")
    if validity_status not in VALIDITY_SET:
        raise ValueError(f"Unsupported validity_status: {validity_status!r}")
    nid = node_id or make_node_id(
        node_type,
        label,
        repo=repo,
        ref=ref,
        path=path,
        commit_sha=commit_sha,
    )
    meta = dict(metadata or {})
    meta_json = json.dumps(meta, ensure_ascii=False, sort_keys=True)
    meta_text = " ".join(f"{k}:{v}" for k, v in sorted(meta.items()) if v not in ("", None))

    existing = conn.execute(
        "SELECT timestamp, validity_status, metadata_json FROM graph_nodes WHERE node_id=?",
        (nid,),
    ).fetchone()
    if existing:
        merged_meta = json.loads(existing["metadata_json"] or "{}")
        merged_meta.update(meta)
        meta_json = json.dumps(merged_meta, ensure_ascii=False, sort_keys=True)
        meta_text = " ".join(f"{k}:{v}" for k, v in sorted(merged_meta.items()) if v not in ("", None))
        eff_ts = timestamp or existing["timestamp"]
        eff_val = validity_status if validity_status != "unverified" else existing["validity_status"]
        conn.execute(
            "UPDATE graph_nodes SET label=?, repo=?, ref=?, path=?, commit_sha=?, "
            "timestamp=?, validity_status=?, metadata_json=? WHERE node_id=?",
            (label, repo, ref, path, commit_sha, eff_ts, eff_val, meta_json, nid),
        )
        conn.execute("DELETE FROM graph_nodes_fts WHERE node_id=?", (nid,))
    else:
        conn.execute(
            "INSERT INTO graph_nodes "
            "(node_id, node_type, repo, ref, label, path, commit_sha, timestamp, validity_status, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nid, node_type, repo, ref, label, path, commit_sha, timestamp, validity_status, meta_json),
        )

    conn.execute(
        "INSERT INTO graph_nodes_fts (node_id, node_type, repo, label, path, metadata_text) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (nid, node_type, repo, label, path, meta_text),
    )
    return nid


def upsert_edge(
    conn: sqlite3.Connection,
    *,
    src_id: str,
    dst_id: str,
    edge_type: str,
    confidence: str = "EXTRACTED",
    repo: str = "",
    ref: str = "",
    commit_sha: str = "",
    timestamp: str = "",
    weight: float = 1.0,
    provenance: dict[str, Any] | None = None,
) -> str:
    """Insert or update a typed directed edge with explicit confidence and provenance."""
    if edge_type not in EDGE_TYPE_SET:
        raise ValueError(f"Unsupported edge_type {edge_type!r}; expected one of {EDGE_TYPES}")
    if confidence not in CONFIDENCE_SET:
        raise ValueError(f"Unsupported confidence {confidence!r}; expected one of {CONFIDENCE_LEVELS}")
    prov = dict(provenance or {})
    prov_json = json.dumps(prov, ensure_ascii=False, sort_keys=True)
    eid = _stable_id("edge", src_id, dst_id, edge_type, commit_sha, ref)
    conn.execute(
        "INSERT INTO graph_edges "
        "(edge_id, src_id, dst_id, edge_type, confidence, repo, ref, commit_sha, timestamp, weight, provenance_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(src_id, dst_id, edge_type, commit_sha, ref) DO UPDATE SET "
        "confidence=CASE WHEN excluded.confidence='EXTRACTED' THEN 'EXTRACTED' ELSE graph_edges.confidence END, "
        "timestamp=CASE WHEN excluded.timestamp!='' THEN excluded.timestamp ELSE graph_edges.timestamp END, "
        "weight=MAX(graph_edges.weight, excluded.weight), "
        "provenance_json=excluded.provenance_json",
        (eid, src_id, dst_id, edge_type, confidence, repo, ref, commit_sha, timestamp, float(weight), prov_json),
    )
    return eid


def extract_imports_from_source(path: str, source_text: str) -> list[str]:
    """Deterministically extract imported module/file specifiers from TS/JS/Python code."""
    suffix = Path(path).suffix.lower()
    imports: list[str] = []
    seen: set[str] = set()
    if suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        for m in _TS_IMPORT_RE.finditer(source_text):
            spec = (m.group(1) or m.group(2) or "").strip()
            if spec and spec not in seen:
                seen.add(spec)
                imports.append(spec)
    elif suffix == ".py":
        for m in _PY_IMPORT_RE.finditer(source_text):
            spec = (m.group(1) or m.group(2) or "").strip()
            if spec and spec not in seen:
                seen.add(spec)
                imports.append(spec)
    return imports


def _link_file_to_component(
    conn: sqlite3.Connection,
    *,
    file_id: str,
    path: str,
    repo: str,
    ref: str,
    commit_sha: str,
    timestamp: str,
    hint_text: str = "",
    confidence: str = "EXTRACTED",
) -> str | None:
    comp_name = infer_component_from_path(path, hint_text)
    if not comp_name:
        return None
    comp_id = upsert_node(
        conn,
        node_type="Component",
        label=comp_name,
        repo="multi-repo",
        timestamp=timestamp,
        validity_status="valid_in_commit" if commit_sha else "unverified",
        metadata={"canonical_key": _canonical_component_key(comp_name)},
    )
    upsert_edge(
        conn,
        src_id=file_id,
        dst_id=comp_id,
        edge_type="MODIFIES" if commit_sha else "DOCUMENTED_IN",
        confidence=confidence,
        repo=repo,
        ref=ref,
        commit_sha=commit_sha,
        timestamp=timestamp,
        provenance={"path": path, "component": comp_name},
    )
    return comp_id


def ingest_branch_inventory(
    conn: sqlite3.Connection,
    inventory_path: Path,
    *,
    repo_override: str | None = None,
) -> dict[str, int]:
    """Ingest a branch-file inventory JSON (e.g. inventory/exams-app-branch-files.json)."""
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    repo_name = repo_override or str(payload.get("source") or "exams-app").split("/")[-1]
    counts = {"nodes": 0, "edges": 0, "refs": 0, "files": 0, "images": 0, "decisions": 0}

    with conn:
        repo_id = upsert_node(
            conn,
            node_type="Repo",
            label=repo_name,
            repo=repo_name,
            metadata={"source": payload.get("source", ""), "origin_file": str(inventory_path)},
        )
        counts["nodes"] += 1

        for branch_entry in payload.get("branch_inventories") or []:
            branch = str(branch_entry.get("branch") or "")
            ref = str(branch_entry.get("ref") or f"refs/heads/{branch}")
            head_sha = str(branch_entry.get("sha") or "")
            if not branch:
                continue
            ref_id = upsert_node(
                conn,
                node_type="Ref",
                label=branch,
                repo=repo_name,
                ref=ref,
                commit_sha=head_sha,
                validity_status="valid_in_commit" if head_sha else "unverified",
            )
            upsert_edge(
                conn,
                src_id=ref_id,
                dst_id=repo_id,
                edge_type="DOCUMENTED_IN",
                confidence="EXTRACTED",
                repo=repo_name,
                ref=ref,
                commit_sha=head_sha,
                provenance={"origin_file": str(inventory_path)},
            )
            counts["refs"] += 1

            commit_id = None
            if head_sha:
                commit_id = upsert_node(
                    conn,
                    node_type="Commit",
                    label=head_sha[:12],
                    repo=repo_name,
                    ref=ref,
                    commit_sha=head_sha,
                    validity_status="valid_in_commit",
                )
                upsert_edge(
                    conn,
                    src_id=commit_id,
                    dst_id=ref_id,
                    edge_type="DOCUMENTED_IN",
                    confidence="EXTRACTED",
                    repo=repo_name,
                    ref=ref,
                    commit_sha=head_sha,
                )

            files = branch_entry.get("files") or []
            # Pre-index decision docs & images per directory to link EVIDENCE edges deterministically
            dir_images: dict[str, list[str]] = {}
            dir_decisions: dict[str, list[tuple[str, str]]] = {}

            for f in files:
                fpath = str(f.get("path") or "")
                if not fpath:
                    continue
                try:
                    safe_path(fpath)
                except ValueError:
                    continue
                blob_sha = str(f.get("sha") or "")
                size = int(f.get("size") or 0)
                ext = Path(fpath).suffix.lower()

                if ext in IMAGE_EXTENSIONS:
                    img_id = upsert_node(
                        conn,
                        node_type="Image",
                        label=Path(fpath).name,
                        repo=repo_name,
                        ref=branch,
                        path=fpath,
                        commit_sha=head_sha,
                        validity_status="valid_in_commit" if head_sha else "unverified",
                        metadata={"blob_sha": blob_sha, "size": size},
                    )
                    counts["images"] += 1
                    dir_images.setdefault(str(Path(fpath).parent), []).append(img_id)
                    if commit_id:
                        upsert_edge(
                            conn,
                            src_id=commit_id,
                            dst_id=img_id,
                            edge_type="EVIDENCED_BY",
                            confidence="EXTRACTED",
                            repo=repo_name,
                            ref=branch,
                            commit_sha=head_sha,
                        )
                    _link_file_to_component(
                        conn,
                        file_id=img_id,
                        path=fpath,
                        repo=repo_name,
                        ref=branch,
                        commit_sha=head_sha,
                        timestamp="",
                        confidence="INFERRED",
                    )
                    continue

                file_id = upsert_node(
                    conn,
                    node_type="File",
                    label=Path(fpath).name,
                    repo=repo_name,
                    ref=branch,
                    path=fpath,
                    commit_sha=head_sha,
                    validity_status="valid_in_commit" if head_sha else "unverified",
                    metadata={"blob_sha": blob_sha, "size": size},
                )
                counts["files"] += 1
                if commit_id:
                    upsert_edge(
                        conn,
                        src_id=commit_id,
                        dst_id=file_id,
                        edge_type="MODIFIES",
                        confidence="EXTRACTED",
                        repo=repo_name,
                        ref=branch,
                        commit_sha=head_sha,
                    )
                _link_file_to_component(
                    conn,
                    file_id=file_id,
                    path=fpath,
                    repo=repo_name,
                    ref=branch,
                    commit_sha=head_sha,
                    timestamp="",
                    confidence="EXTRACTED" if ext in CODE_EXTENSIONS else "INFERRED",
                )

                if ext in DOC_EXTENSIONS and _DECISION_DOC_RE.search(fpath):
                    dec_id = upsert_node(
                        conn,
                        node_type="Decision",
                        label=f"Decision doc: {Path(fpath).name}",
                        repo=repo_name,
                        ref=branch,
                        path=fpath,
                        commit_sha=head_sha,
                        validity_status="valid_in_commit" if head_sha else "unverified",
                        metadata={"blob_sha": blob_sha, "source_kind": "inventory_doc"},
                    )
                    counts["decisions"] += 1
                    upsert_edge(
                        conn,
                        src_id=dec_id,
                        dst_id=file_id,
                        edge_type="DOCUMENTED_IN",
                        confidence="EXTRACTED",
                        repo=repo_name,
                        ref=branch,
                        commit_sha=head_sha,
                    )
                    _link_file_to_component(
                        conn,
                        file_id=dec_id,
                        path=fpath,
                        repo=repo_name,
                        ref=branch,
                        commit_sha=head_sha,
                        timestamp="",
                        confidence="INFERRED",
                    )
                    dir_decisions.setdefault(str(Path(fpath).parent), []).append((dec_id, fpath))

            # Connect sibling screenshots in the same review/prototype tree to decision docs
            for img_dir, img_ids in dir_images.items():
                parent_dir = str(Path(img_dir).parent)
                matched_decisions = dir_decisions.get(img_dir, []) + dir_decisions.get(parent_dir, [])
                for dec_id, _dpath in matched_decisions:
                    for img_id in img_ids:
                        upsert_edge(
                            conn,
                            src_id=dec_id,
                            dst_id=img_id,
                            edge_type="EVIDENCED_BY",
                            confidence="INFERRED",
                            repo=repo_name,
                            ref=branch,
                            commit_sha=head_sha,
                            provenance={"reason": "sibling_review_directory"},
                        )
                        counts["edges"] += 1

    return counts


def ingest_notes_platform_inventory(
    conn: sqlite3.Connection,
    notes_dir: Path,
    *,
    repo_name: str = "notes-app",
) -> dict[str, int]:
    """Ingest PRs, issues, and PR file diffs from inventory/notes-app/."""
    counts = {"prs": 0, "issues": 0, "files": 0, "decisions": 0, "edges": 0}
    pulls_file = notes_dir / "source-pulls-2026-11-23.json"
    issues_file = notes_dir / "source-issues-2026-11-23.json"
    platform_dir = notes_dir / "platform"

    with conn:
        repo_id = upsert_node(conn, node_type="Repo", label=repo_name, repo=repo_name)
        pr_by_num: dict[int, str] = {}
        pr_meta: dict[int, dict[str, str]] = {}

        if pulls_file.is_file():
            pulls_data = json.loads(pulls_file.read_text(encoding="utf-8"))
            for entry in pulls_data.get("entries") or []:
                num = int(entry["number"])
                title = str(entry.get("title") or "")
                body = str(entry.get("body") or "")
                created_at = str(entry.get("created_at") or "")
                merged_at = str(entry.get("merged_at") or "")
                head = entry.get("head") or {}
                base = entry.get("base") or {}
                ref = str(head.get("ref") or base.get("ref") or "")
                sha = str(entry.get("merge_commit_sha") or head.get("sha") or "")
                ts = merged_at or created_at

                pr_id = upsert_node(
                    conn,
                    node_type="PR",
                    label=f"PR #{num}: {title[:120]}",
                    repo=repo_name,
                    ref=ref,
                    commit_sha=sha,
                    timestamp=ts,
                    validity_status="valid_in_commit" if sha else "unverified",
                    metadata={
                        "number": num,
                        "state": entry.get("state", ""),
                        "merged_at": merged_at,
                        "html_url": entry.get("html_url", ""),
                    },
                )
                pr_by_num[num] = pr_id
                pr_meta[num] = {"ref": ref, "sha": sha, "ts": ts, "title": title}
                counts["prs"] += 1

                if sha:
                    cid = upsert_node(
                        conn,
                        node_type="Commit",
                        label=sha[:12],
                        repo=repo_name,
                        ref=ref,
                        commit_sha=sha,
                        timestamp=ts,
                        validity_status="valid_in_commit",
                        metadata={"subject": title},
                    )
                    upsert_edge(
                        conn,
                        src_id=cid,
                        dst_id=pr_id,
                        edge_type="DOCUMENTED_IN",
                        confidence="EXTRACTED",
                        repo=repo_name,
                        ref=ref,
                        commit_sha=sha,
                        timestamp=ts,
                    )

                if _DECISION_TEXT_RE.search(f"{title}\n{body}") or any(
                    k in title.lower() for k in ("sidebar", "graph", "capacities", "align")
                ):
                    dec_id = upsert_node(
                        conn,
                        node_type="Decision",
                        label=f"PR #{num}: {title[:100]}",
                        repo=repo_name,
                        ref=ref,
                        path=f"PR#{num}",
                        commit_sha=sha,
                        timestamp=ts,
                        validity_status="valid_in_commit" if sha else "unverified",
                        metadata={"pr_number": num, "title": title},
                    )
                    counts["decisions"] += 1
                    upsert_edge(
                        conn,
                        src_id=dec_id,
                        dst_id=pr_id,
                        edge_type="DOCUMENTED_IN",
                        confidence="EXTRACTED",
                        repo=repo_name,
                        ref=ref,
                        commit_sha=sha,
                        timestamp=ts,
                    )
                    comp = infer_component_from_path("", title)
                    if comp:
                        comp_id = upsert_node(
                            conn,
                            node_type="Component",
                            label=comp,
                            repo="multi-repo",
                            timestamp=ts,
                            validity_status="valid_in_commit" if sha else "unverified",
                            metadata={"canonical_key": _canonical_component_key(comp)},
                        )
                        upsert_edge(
                            conn,
                            src_id=dec_id,
                            dst_id=comp_id,
                            edge_type="MODIFIES",
                            confidence="INFERRED",
                            repo=repo_name,
                            ref=ref,
                            commit_sha=sha,
                            timestamp=ts,
                        )

                for ref_num in _ISSUE_REF_RE.findall(f"{title}\n{body}"):
                    inum = int(ref_num)
                    if inum == num:
                        continue
                    issue_id = upsert_node(
                        conn,
                        node_type="Issue",
                        label=f"Issue #{inum}",
                        repo=repo_name,
                        timestamp=ts,
                    )
                    upsert_edge(
                        conn,
                        src_id=pr_id,
                        dst_id=issue_id,
                        edge_type="DOCUMENTED_IN",
                        confidence="EXTRACTED",
                        repo=repo_name,
                        ref=ref,
                        commit_sha=sha,
                        timestamp=ts,
                    )

        if issues_file.is_file():
            issues_data = json.loads(issues_file.read_text(encoding="utf-8"))
            for entry in issues_data.get("entries") or []:
                num = int(entry["number"])
                if num in pr_by_num:
                    continue
                title = str(entry.get("title") or "")
                ts = str(entry.get("updated_at") or entry.get("created_at") or "")
                issue_id = upsert_node(
                    conn,
                    node_type="Issue",
                    label=f"Issue #{num}: {title[:120]}",
                    repo=repo_name,
                    timestamp=ts,
                    metadata={"number": num, "state": entry.get("state", "")},
                )
                upsert_edge(
                    conn,
                    src_id=issue_id,
                    dst_id=repo_id,
                    edge_type="DOCUMENTED_IN",
                    confidence="EXTRACTED",
                    repo=repo_name,
                    timestamp=ts,
                )
                counts["issues"] += 1

        if platform_dir.is_dir():
            for batch_file in sorted(platform_dir.glob("pr-file-diffs-batch-*.json")):
                batch = json.loads(batch_file.read_text(encoding="utf-8"))
                for rec in batch.get("records") or []:
                    pr_num = int(rec["number"])
                    meta = pr_meta.get(pr_num, {})
                    ref = meta.get("ref", "")
                    sha = meta.get("sha", "")
                    ts = meta.get("ts", "")
                    pr_id = pr_by_num.get(pr_num)
                    changed_file_ids: list[str] = []

                    for f in rec.get("files") or []:
                        fpath = str(f.get("filename") or "")
                        if not fpath:
                            continue
                        try:
                            safe_path(fpath)
                        except ValueError:
                            continue
                        patch = str(f.get("patch") or "")
                        ext = Path(fpath).suffix.lower()
                        if ext in IMAGE_EXTENSIONS:
                            nid = upsert_node(
                                conn,
                                node_type="Image",
                                label=Path(fpath).name,
                                repo=repo_name,
                                ref=ref,
                                path=fpath,
                                commit_sha=sha,
                                timestamp=ts,
                                validity_status="valid_in_commit" if sha else "unverified",
                                metadata={"blob_sha": f.get("sha", ""), "pr_number": pr_num},
                            )
                            if pr_id:
                                upsert_edge(
                                    conn,
                                    src_id=pr_id,
                                    dst_id=nid,
                                    edge_type="EVIDENCED_BY",
                                    confidence="EXTRACTED",
                                    repo=repo_name,
                                    ref=ref,
                                    commit_sha=sha,
                                    timestamp=ts,
                                )
                            _link_file_to_component(
                                conn,
                                file_id=nid,
                                path=fpath,
                                repo=repo_name,
                                ref=ref,
                                commit_sha=sha,
                                timestamp=ts,
                                confidence="INFERRED",
                            )
                            continue

                        fid = upsert_node(
                            conn,
                            node_type="File",
                            label=Path(fpath).name,
                            repo=repo_name,
                            ref=ref,
                            path=fpath,
                            commit_sha=sha,
                            timestamp=ts,
                            validity_status="valid_in_commit" if sha else "unverified",
                            metadata={"blob_sha": f.get("sha", ""), "status": f.get("status", ""), "pr_number": pr_num},
                        )
                        counts["files"] += 1
                        changed_file_ids.append(fid)

                        if pr_id:
                            upsert_edge(
                                conn,
                                src_id=pr_id,
                                dst_id=fid,
                                edge_type="MODIFIES",
                                confidence="EXTRACTED",
                                repo=repo_name,
                                ref=ref,
                                commit_sha=sha,
                                timestamp=ts,
                            )
                            counts["edges"] += 1

                        _link_file_to_component(
                            conn,
                            file_id=fid,
                            path=fpath,
                            repo=repo_name,
                            ref=ref,
                            commit_sha=sha,
                            timestamp=ts,
                            hint_text=patch[:400],
                            confidence="EXTRACTED" if ext in CODE_EXTENSIONS else "INFERRED",
                        )

                        # Deterministic import edge extraction from patch additions
                        added_lines = "\n".join(
                            ln[1:] for ln in patch.splitlines() if ln.startswith("+") and not ln.startswith("+++")
                        )
                        for spec in extract_imports_from_source(fpath, added_lines):
                            target_id = upsert_node(
                                conn,
                                node_type="File",
                                label=Path(spec).name or spec,
                                repo=repo_name,
                                ref=ref,
                                path=spec,
                                commit_sha=sha,
                                timestamp=ts,
                                validity_status="unverified",
                                metadata={"import_specifier": spec},
                            )
                            upsert_edge(
                                conn,
                                src_id=fid,
                                dst_id=target_id,
                                edge_type="IMPORTS",
                                confidence="EXTRACTED",
                                repo=repo_name,
                                ref=ref,
                                commit_sha=sha,
                                timestamp=ts,
                            )
                            counts["edges"] += 1

                    # Record bounded CO_OCCURS_WITH edges for files modified together in the same PR
                    if 2 <= len(changed_file_ids) <= 15:
                        anchor = changed_file_ids[0]
                        for peer in changed_file_ids[1:]:
                            if anchor != peer:
                                upsert_edge(
                                    conn,
                                    src_id=anchor,
                                    dst_id=peer,
                                    edge_type="CO_OCCURS_WITH",
                                    confidence="INFERRED",
                                    repo=repo_name,
                                    ref=ref,
                                    commit_sha=sha,
                                    timestamp=ts,
                                    provenance={"pr_number": pr_num},
                                )
                                counts["edges"] += 1

    return counts


def ingest_archive_sqlite(conn: sqlite3.Connection, archive_db_path: Path) -> dict[str, int]:
    """Ingest commits, refs, changes, and images from an existing archive_index SQLite DB."""
    src = sqlite3.connect(archive_db_path)
    src.row_factory = sqlite3.Row
    counts = {"repos": 0, "commits": 0, "changes": 0, "images": 0}
    try:
        with conn:
            repo_map: dict[int, str] = {}
            for r in src.execute("SELECT id, name, source FROM repositories"):
                repo_map[int(r["id"])] = r["name"]
                upsert_node(conn, node_type="Repo", label=r["name"], repo=r["name"], metadata={"source": r["source"]})
                counts["repos"] += 1

            for r in src.execute("SELECT repo_id, name, sha FROM refs"):
                rname = repo_map.get(int(r["repo_id"]), str(r["repo_id"]))
                upsert_node(
                    conn,
                    node_type="Ref",
                    label=r["name"],
                    repo=rname,
                    ref=r["name"],
                    commit_sha=r["sha"],
                    validity_status="valid_in_commit",
                )

            commit_dates: dict[tuple[str, str], str] = {}
            for c in src.execute("SELECT repo_id, sha, date, subject FROM commits"):
                rname = repo_map.get(int(c["repo_id"]), str(c["repo_id"]))
                commit_dates[(rname, c["sha"])] = c["date"]
                cid = upsert_node(
                    conn,
                    node_type="Commit",
                    label=c["subject"][:120] or c["sha"][:12],
                    repo=rname,
                    commit_sha=c["sha"],
                    timestamp=c["date"],
                    validity_status="valid_in_commit",
                    metadata={"subject": c["subject"]},
                )
                counts["commits"] += 1
                if _DECISION_TEXT_RE.search(c["subject"]):
                    dec_id = upsert_node(
                        conn,
                        node_type="Decision",
                        label=c["subject"][:120],
                        repo=rname,
                        commit_sha=c["sha"],
                        timestamp=c["date"],
                        validity_status="valid_in_commit",
                        metadata={"subject": c["subject"]},
                    )
                    upsert_edge(
                        conn,
                        src_id=dec_id,
                        dst_id=cid,
                        edge_type="DOCUMENTED_IN",
                        confidence="EXTRACTED",
                        repo=rname,
                        commit_sha=c["sha"],
                        timestamp=c["date"],
                    )

            for ch in src.execute("SELECT repo_id, sha, status, path FROM changes"):
                rname = repo_map.get(int(ch["repo_id"]), str(ch["repo_id"]))
                ts = commit_dates.get((rname, ch["sha"]), "")
                fid = upsert_node(
                    conn,
                    node_type="File",
                    label=Path(ch["path"]).name,
                    repo=rname,
                    path=ch["path"],
                    commit_sha=ch["sha"],
                    timestamp=ts,
                    validity_status="valid_in_commit",
                    metadata={"status": ch["status"]},
                )
                cid = make_node_id("Commit", ch["sha"][:12], repo=rname, commit_sha=ch["sha"])
                if conn.execute("SELECT 1 FROM graph_nodes WHERE node_id=?", (cid,)).fetchone():
                    upsert_edge(
                        conn,
                        src_id=cid,
                        dst_id=fid,
                        edge_type="MODIFIES",
                        confidence="EXTRACTED",
                        repo=rname,
                        commit_sha=ch["sha"],
                        timestamp=ts,
                    )
                _link_file_to_component(
                    conn,
                    file_id=fid,
                    path=ch["path"],
                    repo=rname,
                    ref="",
                    commit_sha=ch["sha"],
                    timestamp=ts,
                    confidence="EXTRACTED",
                )
                counts["changes"] += 1

            for im in src.execute("SELECT repo_id, path, blob, commit_sha, kind, bytes FROM images"):
                rname = repo_map.get(int(im["repo_id"]), str(im["repo_id"]))
                ts = commit_dates.get((rname, im["commit_sha"]), "")
                img_id = upsert_node(
                    conn,
                    node_type="Image",
                    label=Path(im["path"]).name,
                    repo=rname,
                    path=im["path"],
                    commit_sha=im["commit_sha"],
                    timestamp=ts,
                    validity_status="valid_in_commit",
                    metadata={"blob": im["blob"], "kind": im["kind"], "bytes": im["bytes"]},
                )
                cid = make_node_id("Commit", im["commit_sha"][:12], repo=rname, commit_sha=im["commit_sha"])
                if conn.execute("SELECT 1 FROM graph_nodes WHERE node_id=?", (cid,)).fetchone():
                    upsert_edge(
                        conn,
                        src_id=cid,
                        dst_id=img_id,
                        edge_type="EVIDENCED_BY",
                        confidence="EXTRACTED",
                        repo=rname,
                        commit_sha=im["commit_sha"],
                        timestamp=ts,
                    )
                _link_file_to_component(
                    conn,
                    file_id=img_id,
                    path=im["path"],
                    repo=rname,
                    ref="",
                    commit_sha=im["commit_sha"],
                    timestamp=ts,
                    confidence="INFERRED",
                )
                counts["images"] += 1
    finally:
        src.close()
    return counts


def link_temporal_supersession(conn: sqlite3.Connection) -> int:
    """Create SUPERSEDES edges across branches/repos for decisions sharing an anchor component or path."""
    rows = conn.execute(
        "SELECT node_id, repo, ref, path, commit_sha, timestamp, label "
        "FROM graph_nodes WHERE node_type='Decision' "
        "ORDER BY CASE WHEN timestamp='' THEN 1 ELSE 0 END, timestamp ASC, node_id ASC"
    ).fetchall()

    groups: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        comp_rows = conn.execute(
            "SELECT n.node_id FROM graph_edges e "
            "JOIN graph_nodes n ON n.node_id=e.dst_id "
            "WHERE e.src_id=? AND n.node_type='Component'",
            (r["node_id"],),
        ).fetchall()
        if comp_rows:
            for c in comp_rows:
                groups.setdefault(c["node_id"], []).append(r)
        elif r["path"]:
            groups.setdefault(f"path:{r['path']}", []).append(r)

    created = 0
    with conn:
        for _key, items in groups.items():
            if len(items) < 2:
                continue
            for idx in range(len(items) - 1):
                older = items[idx]
                newer = items[idx + 1]
                if older["node_id"] == newer["node_id"]:
                    continue
                if older["repo"] == newer["repo"] and older["ref"] == newer["ref"] and older["path"] == newer["path"]:
                    continue
                upsert_edge(
                    conn,
                    src_id=newer["node_id"],
                    dst_id=older["node_id"],
                    edge_type="SUPERSEDES",
                    confidence="INFERRED",
                    repo=newer["repo"],
                    ref=newer["ref"],
                    commit_sha=newer["commit_sha"],
                    timestamp=newer["timestamp"],
                    provenance={"reason": "later_temporal_decision_on_same_component_or_path"},
                )
                if older["validity_status"] if "validity_status" in older.keys() else True:
                    conn.execute(
                        "UPDATE graph_nodes SET validity_status='superseded_in_later_branch' "
                        "WHERE node_id=? AND validity_status='valid_in_commit'",
                        (older["node_id"],),
                    )
                created += 1
    return created


def _resolve_seed_nodes(
    conn: sqlite3.Connection,
    query: str,
    *,
    repo: str | None = None,
    node_types: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Find deterministic seed nodes by exact node_id, component canonical key, or FTS5+PT<->EN."""
    q = (query or "").strip()
    if not q:
        return []

    seeds: dict[str, dict[str, Any]] = {}

    def _add_rows(rows: list[sqlite3.Row], score: float) -> None:
        for r in rows:
            nid = r["node_id"]
            if nid not in seeds:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                d["match_score"] = score
                seeds[nid] = d

    # 1. Direct node_id or canonical component key match
    canon = _canonical_component_key(q)
    sql_direct = "SELECT * FROM graph_nodes WHERE (node_id=? OR lower(label)=lower(?) OR node_id=?)"
    params_direct: list[Any] = [q, q, f"component:{canon}"]
    if repo:
        sql_direct += " AND (repo=? OR repo='multi-repo')"
        params_direct.append(repo)
    _add_rows(conn.execute(sql_direct, params_direct).fetchall(), 1.0)

    # 2. Expanded bilingual FTS5 search across labels, paths, and metadata
    exp = search_expansion.expand_query(q)
    matchers = exp.get("fts_matchers") or []
    for matcher in matchers[:3]:
        sql_fts = (
            "SELECT gn.* FROM graph_nodes_fts fts "
            "JOIN graph_nodes gn ON gn.node_id = fts.node_id "
            "WHERE graph_nodes_fts MATCH ?"
        )
        params_fts: list[Any] = [matcher]
        if repo:
            sql_fts += " AND (gn.repo=? OR gn.repo='multi-repo')"
            params_fts.append(repo)
        if node_types:
            ph = ",".join("?" for _ in node_types)
            sql_fts += f" AND gn.node_type IN ({ph})"
            params_fts.extend(node_types)
        sql_fts += " LIMIT 30"
        try:
            _add_rows(conn.execute(sql_fts, params_fts).fetchall(), 0.8)
        except sqlite3.OperationalError:
            continue

    # 3. Substring fallback on path/label for exact symbols or filenames
    for term in [q, *(exp.get("expanded_terms") or [])[:4]]:
        like_pat = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        sql_like = (
            "SELECT * FROM graph_nodes WHERE (lower(path) LIKE lower(?) ESCAPE '\\' "
            "OR lower(label) LIKE lower(?) ESCAPE '\\')"
        )
        p_like: list[Any] = [like_pat, like_pat]
        if repo:
            sql_like += " AND (repo=? OR repo='multi-repo')"
            p_like.append(repo)
        sql_like += " LIMIT 30"
        _add_rows(conn.execute(sql_like, p_like).fetchall(), 0.6)

    ordered = sorted(
        seeds.values(),
        key=lambda n: (
            -float(n["match_score"]),
            0 if n["node_type"] == "Component" else 1,
            n["repo"],
            n["node_id"],
        ),
    )
    if node_types:
        ordered = [n for n in ordered if n["node_type"] in node_types] or ordered
    return ordered


def query_neighborhood(
    conn: sqlite3.Connection,
    entity: str,
    *,
    hops: int = 2,
    repo: str | None = None,
    edge_types: tuple[str, ...] | None = None,
    target_types: tuple[str, ...] | None = None,
    since: str | None = None,
    until: str | None = None,
    confidence: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Traverse k-hop neighborhood & temporal impact around a node or concept."""
    t0 = time.perf_counter()
    hops = max(1, min(int(hops), 5))
    limit = max(1, min(int(limit), 500))

    seeds = _resolve_seed_nodes(conn, entity, repo=repo)[:max(1, min(10, limit // 3))]
    visited_nodes: dict[str, dict[str, Any]] = {}
    depth_by_node: dict[str, int] = {}
    collected_edges: dict[str, dict[str, Any]] = {}
    queue: deque[tuple[str, int]] = deque()

    for s in seeds:
        sts = s.get("timestamp") or ""
        if since and sts and sts < since and s.get("node_type") != "Component":
            continue
        if until and sts and sts > until and s.get("node_type") != "Component":
            continue
        nid = s["node_id"]
        visited_nodes[nid] = s
        depth_by_node[nid] = 0
        queue.append((nid, 0))

    while queue:
        cur_id, depth = queue.popleft()
        if depth >= hops:
            continue

        sql_edges = "SELECT * FROM graph_edges WHERE (src_id=? OR dst_id=?)"
        params: list[Any] = [cur_id, cur_id]
        if edge_types:
            ph = ",".join("?" for _ in edge_types)
            sql_edges += f" AND edge_type IN ({ph})"
            params.extend(edge_types)
        if confidence:
            sql_edges += " AND confidence=?"
            params.append(confidence)
        if repo:
            sql_edges += " AND (repo=? OR repo='multi-repo' OR repo='')"
            params.append(repo)

        erows = conn.execute(sql_edges, params).fetchall()
        missing_neighbors: list[str] = []
        filtered_edges: list[sqlite3.Row] = []
        for erow in erows:
            ets = erow["timestamp"] or ""
            if since and ets and ets < since:
                continue
            if until and ets and ets > until:
                continue
            filtered_edges.append(erow)
            neighbor_id = erow["dst_id"] if erow["src_id"] == cur_id else erow["src_id"]
            if neighbor_id not in visited_nodes:
                missing_neighbors.append(neighbor_id)

        if missing_neighbors:
            unique_missing = list(dict.fromkeys(missing_neighbors))
            for i in range(0, len(unique_missing), 200):
                chunk = unique_missing[i : i + 200]
                ph = ",".join("?" for _ in chunk)
                for nrow in conn.execute(f"SELECT * FROM graph_nodes WHERE node_id IN ({ph})", chunk):
                    nts = nrow["timestamp"] or ""
                    if since and nts and nts < since and nrow["node_type"] != "Component":
                        continue
                    if until and nts and nts > until and nrow["node_type"] != "Component":
                        continue
                    nd = dict(nrow)
                    nd["metadata"] = json.loads(nd.pop("metadata_json", "{}") or "{}")
                    visited_nodes[nrow["node_id"]] = nd
                    depth_by_node[nrow["node_id"]] = depth + 1
                    if len(visited_nodes) < limit * 3:
                        queue.append((nrow["node_id"], depth + 1))

        for erow in filtered_edges:
            eid = erow["edge_id"]
            if eid not in collected_edges:
                ed = dict(erow)
                ed["provenance"] = json.loads(ed.pop("provenance_json", "{}") or "{}")
                collected_edges[eid] = ed

    # Build grouped view + temporal impact timeline, prioritizing Decision/Image/PR evidence
    type_priority = {
        "Component": 0,
        "Decision": 1,
        "Image": 2,
        "PR": 3,
        "Issue": 4,
        "File": 5,
        "Commit": 6,
        "Ref": 7,
        "Repo": 8,
    }
    nodes_out = []
    for nid, nd in visited_nodes.items():
        if target_types and nd["node_type"] not in target_types and depth_by_node[nid] > 0:
            continue
        item = dict(nd)
        item["hop"] = depth_by_node[nid]
        nodes_out.append(item)

    nodes_out.sort(
        key=lambda n: (
            int(n["hop"]),
            type_priority.get(n["node_type"], 9),
            n["timestamp"] or "9999",
            n["repo"],
            n["label"],
        )
    )
    nodes_out = nodes_out[:limit]
    kept_ids = {n["node_id"] for n in nodes_out}

    edges_out = [
        e for e in collected_edges.values() if e["src_id"] in kept_ids and e["dst_id"] in kept_ids
    ]
    edges_out.sort(key=lambda e: (e["timestamp"] or "9999", e["edge_type"], e["edge_id"]))

    by_type: dict[str, list[dict[str, Any]]] = {}
    repos_touched: set[str] = set()
    for n in nodes_out:
        by_type.setdefault(n["node_type"], []).append(n)
        if n["repo"] and n["repo"] != "multi-repo":
            repos_touched.add(n["repo"])

    temporal_impact = sorted(
        [
            {
                "timestamp": n["timestamp"],
                "repo": n["repo"],
                "ref": n["ref"],
                "node_type": n["node_type"],
                "label": n["label"],
                "path": n["path"],
                "commit_sha": n["commit_sha"],
                "validity_status": n["validity_status"],
            }
            for n in nodes_out
            if n["hop"] > 0 and n["node_type"] in {"Decision", "Image", "PR", "Commit", "File"}
        ],
        key=lambda x: (0 if x["timestamp"] else 1, x["timestamp"] or "9999", x["repo"], x["label"]),
    )

    latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return {
        "query": entity,
        "hops": hops,
        "seed_count": len(seeds),
        "total_nodes": len(nodes_out),
        "total_edges": len(edges_out),
        "repos_touched": sorted(repos_touched),
        "counts_by_node_type": {k: len(v) for k, v in sorted(by_type.items())},
        "latency_ms": latency_ms,
        "seeds": [{"node_id": s["node_id"], "node_type": s["node_type"], "label": s["label"]} for s in seeds],
        "decisions": by_type.get("Decision", []),
        "images": by_type.get("Image", []),
        "prs": by_type.get("PR", []),
        "files": by_type.get("File", []),
        "temporal_impact": temporal_impact,
        "nodes": nodes_out,
        "edges": edges_out,
    }


def export_graph_json(conn: sqlite3.Connection, output_path: Path) -> dict[str, Any]:
    """Export an inert JSON snapshot of nodes and edges (outside site/)."""
    validate_private_output_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nodes = []
    for r in conn.execute("SELECT * FROM graph_nodes ORDER BY node_type, repo, node_id"):
        d = dict(r)
        d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
        nodes.append(d)
    edges = []
    for r in conn.execute("SELECT * FROM graph_edges ORDER BY edge_type, repo, edge_id"):
        d = dict(r)
        d["provenance"] = json.loads(d.pop("provenance_json", "{}") or "{}")
        edges.append(d)
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output": str(output_path), "node_count": len(nodes), "edge_count": len(edges)}


def graph_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return node, edge, confidence, and storage statistics."""
    nodes_by_type = {
        r["node_type"]: r["cnt"]
        for r in conn.execute("SELECT node_type, COUNT(*) AS cnt FROM graph_nodes GROUP BY node_type ORDER BY node_type")
    }
    edges_by_type = {
        r["edge_type"]: r["cnt"]
        for r in conn.execute("SELECT edge_type, COUNT(*) AS cnt FROM graph_edges GROUP BY edge_type ORDER BY edge_type")
    }
    edges_by_conf = {
        r["confidence"]: r["cnt"]
        for r in conn.execute("SELECT confidence, COUNT(*) AS cnt FROM graph_edges GROUP BY confidence")
    }
    repos = [
        r["repo"]
        for r in conn.execute("SELECT DISTINCT repo FROM graph_nodes WHERE repo!='' AND repo!='multi-repo' ORDER BY repo")
    ]
    return {
        "total_nodes": sum(nodes_by_type.values()),
        "total_edges": sum(edges_by_type.values()),
        "nodes_by_type": nodes_by_type,
        "edges_by_type": edges_by_type,
        "edges_by_confidence": edges_by_conf,
        "repositories": repos,
    }


def run_local_benchmark(repo_root: Path | None = None) -> dict[str, Any]:
    """Measure build time, memory peak, SQLite/JSON footprint, and query latency on real repo inventories."""
    root = repo_root or REPO_ROOT
    tracemalloc.start()
    t_build_start = time.perf_counter()

    import tempfile

    with tempfile.TemporaryDirectory(prefix="graph-bench-") as tmp:
        tmp_dir = Path(tmp)
        db_path = tmp_dir / "bench-graph.sqlite"
        json_path = tmp_dir / "bench-graph.json"
        conn = open_db(db_path)
        try:
            inv_exams = root / "inventory" / "exams-app-branch-files.json"
            inv_notes = root / "inventory" / "notes-app"
            ingest_summary: dict[str, Any] = {}
            if inv_exams.is_file():
                ingest_summary["exams_app"] = ingest_branch_inventory(conn, inv_exams, repo_override="exams-app")
            if inv_notes.is_dir():
                ingest_summary["notes_app"] = ingest_notes_platform_inventory(conn, inv_notes, repo_name="notes-app")
            supersedes_count = link_temporal_supersession(conn)
            build_ms = round((time.perf_counter() - t_build_start) * 1000.0, 2)

            stats = graph_stats(conn)
            export_graph_json(conn, json_path)
            sqlite_bytes = db_path.stat().st_size
            json_bytes = json_path.stat().st_size

            sidebar_res = query_neighborhood(conn, "Sidebar", hops=2, limit=200)
            graph_res = query_neighborhood(conn, "GraphCanvas", hops=2, limit=200)
            _cur_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            return {
                "build_ms": build_ms,
                "peak_python_ram_mib": round(peak_mem / (1024 * 1024), 2),
                "sqlite_bytes": sqlite_bytes,
                "sqlite_mib": round(sqlite_bytes / (1024 * 1024), 3),
                "json_bytes": json_bytes,
                "json_mib": round(json_bytes / (1024 * 1024), 3),
                "supersedes_edges_created": supersedes_count,
                "stats": stats,
                "ingest_summary": ingest_summary,
                "sample_queries": {
                    "sidebar": {
                        "latency_ms": sidebar_res["latency_ms"],
                        "total_nodes": sidebar_res["total_nodes"],
                        "total_edges": sidebar_res["total_edges"],
                        "repos_touched": sidebar_res["repos_touched"],
                        "decisions_count": len(sidebar_res["decisions"]),
                        "images_count": len(sidebar_res["images"]),
                    },
                    "graph_canvas": {
                        "latency_ms": graph_res["latency_ms"],
                        "total_nodes": graph_res["total_nodes"],
                        "total_edges": graph_res["total_edges"],
                        "repos_touched": graph_res["repos_touched"],
                        "decisions_count": len(graph_res["decisions"]),
                        "images_count": len(graph_res["images"]),
                    },
                },
            }
        finally:
            conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite graph path (outside site/)")
    sub = ap.add_subparsers(dest="command", required=True)

    p_inv = sub.add_parser("build-inventory", help="Ingest repository inventory/ files into the graph")
    p_inv.add_argument("--inventory-dir", default=str(REPO_ROOT / "inventory"))
    p_inv.add_argument("--export-json", default=None, help="Optional inert JSON export path")

    p_arch = sub.add_parser("ingest-archive", help="Ingest existing archive_index SQLite database")
    p_arch.add_argument("--archive-db", required=True)

    p_q = sub.add_parser("query", help="Query neighborhood and temporal impact for a component/file/concept")
    p_q.add_argument("entity")
    p_q.add_argument("--hops", type=int, default=2)
    p_q.add_argument("--repo", default=None)
    p_q.add_argument("--since", default=None)
    p_q.add_argument("--until", default=None)
    p_q.add_argument("--confidence", choices=CONFIDENCE_LEVELS, default=None)
    p_q.add_argument("--limit", type=int, default=100)

    sub.add_parser("stats", help="Print graph node/edge counts")
    sub.add_parser("benchmark", help="Run reproducible build & query benchmark against local inventory/")

    args = ap.parse_args()
    if args.command == "benchmark":
        print(json.dumps(run_local_benchmark(REPO_ROOT), ensure_ascii=False, indent=2))
        return

    conn = open_db(Path(args.db))
    try:
        if args.command == "build-inventory":
            inv_dir = Path(args.inventory_dir)
            out: dict[str, Any] = {}
            exams_inv = inv_dir / "exams-app-branch-files.json"
            notes_inv = inv_dir / "notes-app"
            if exams_inv.is_file():
                out["exams_app"] = ingest_branch_inventory(conn, exams_inv, repo_override="exams-app")
            if notes_inv.is_dir():
                out["notes_app"] = ingest_notes_platform_inventory(conn, notes_inv, repo_name="notes-app")
            out["supersedes_edges"] = link_temporal_supersession(conn)
            out["stats"] = graph_stats(conn)
            if args.export_json:
                out["json_export"] = export_graph_json(conn, Path(args.export_json))
        elif args.command == "ingest-archive":
            out = ingest_archive_sqlite(conn, Path(args.archive_db))
            out["supersedes_edges"] = link_temporal_supersession(conn)
            out["stats"] = graph_stats(conn)
        elif args.command == "query":
            out = query_neighborhood(
                conn,
                args.entity,
                hops=args.hops,
                repo=args.repo,
                since=args.since,
                until=args.until,
                confidence=args.confidence,
                limit=args.limit,
            )
        else:
            out = graph_stats(conn)
    finally:
        conn.close()

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
