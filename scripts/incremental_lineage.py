#!/usr/bin/env python3
"""CocoIndex-inspired incremental lineage DAG, memoization, and atomic reconciliation (#87).

Implements deterministic, offline incremental indexing primitives in pure Python stdlib:
  1. Derivation DAG:
       source -> extraction -> chunk -> entity/edge -> index/context
     recording content SHA-256, extractor version, config/policy/taxonomy hashes,
     upstream dependencies, and ACL scope (`public` vs `authenticated_archive`).
  2. Content-addressed memoization:
     - Separates raw byte cache from occurrence/provenance records.
     - Enforces strict scope isolation (a `public` memoization lookup can never
       reuse an `authenticated_archive` artifact, and vice versa).
     - Reuses cached extraction outputs when `(content_sha, fn_name, fn_version,
       config_hash, scope)` match; never recomputes unchanged nodes.
  3. Selective downstream invalidation:
     - Changing a taxonomy hash, policy hash, extractor version, or source file
       invalidates ONLY downstream dependent nodes in the DAG.
     - Distinguishes temporary source unavailability (`source_temporarily_unavailable`)
       from confirmed deletion (`confirmed_removed`), preserving immutable historical
       revisions while reconciling current derived artifacts.
  4. Transactional refresh & atomic snapshot rollback:
     - Uses SQLite transactions + staging snapshots so any mid-refresh failure
       rolls back cleanly to the previous committed snapshot with zero partial state.
  5. Reproducible benchmark comparing Full Rebuild vs Incremental Refresh across
     modification, deletion, rename, taxonomy/extractor bump, and failure/rollback
     scenarios, proving 100% equivalence to a full rebuild.

Zero external dependencies (Python 3.12 stdlib only).
Zero Emoji Policy: NO Unicode emojis [\\U00010000-\\U0010ffff].
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import time
import tracemalloc
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ast_chunker  # noqa: E402
import domain_ontology  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

DAG_STAGES: tuple[str, ...] = (
    "source",
    "extraction",
    "chunk",
    "entity_edge",
    "index_context",
)

DB_SCHEMA = """
PRAGMA journal_mode=DELETE;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    scope TEXT NOT NULL,
    taxonomy_hash TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    extractor_versions_json TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('committed', 'rolled_back', 'failed'))
);

CREATE TABLE IF NOT EXISTS memo_cache (
    cache_key TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    content_sha TEXT NOT NULL,
    fn_name TEXT NOT NULL,
    fn_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    output_sha TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lineage_nodes (
    node_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    stage TEXT NOT NULL CHECK(stage IN ('source', 'extraction', 'chunk', 'entity_edge', 'index_context')),
    scope TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    content_sha TEXT NOT NULL,
    extractor_name TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    output_sha TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active', 'temporarily_unavailable', 'historical_preserved')),
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lineage_edges (
    parent_node_id TEXT NOT NULL,
    child_node_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    PRIMARY KEY (parent_node_id, child_node_id, relation)
);

CREATE TABLE IF NOT EXISTS historical_versions (
    version_key TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    content_sha TEXT NOT NULL,
    scope TEXT NOT NULL,
    first_seen_snapshot TEXT NOT NULL,
    last_seen_snapshot TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
"""


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: Any) -> str:
    return sha256_text(_canonical_json(obj))


@dataclass(frozen=True)
class SourceInput:
    """Declarative input unit entering the incremental derivation pipeline."""

    source_id: str
    path: str
    content: str
    scope: str = "public"  # "public" | "authenticated_archive"
    availability: str = "available"  # "available" | "temporarily_unavailable" | "confirmed_removed"
    language: str | None = None
    content_sha_override: str | None = None

    @property
    def content_sha(self) -> str:
        if self.content_sha_override:
            return self.content_sha_override
        return sha256_text(self.content)


@dataclass
class PipelineConfig:
    """Versioned configuration & extractor registry driving selective invalidation."""

    extractor_versions: dict[str, str] = field(
        default_factory=lambda: {
            "extract": "1.0.0",
            "chunk": "1.0.0",
            "entity_edge": "1.0.0",
            "index_context": "1.0.0",
        }
    )
    taxonomy_version: str = "1.0.0"
    taxonomy_terms: tuple[str, ...] = ("sidebar", "side panel", "tabs", "kanban", "flashcard", "motion")
    policy_version: str = "1.0.0"

    def taxonomy_hash(self) -> str:
        return sha256_obj({"version": self.taxonomy_version, "terms": sorted(self.taxonomy_terms)})

    def policy_hash(self) -> str:
        return sha256_obj({"version": self.policy_version})

    def stage_config_hash(self, stage: str) -> str:
        # Propagate upstream dependency versions transitively along the DAG:
        # extract -> chunk -> entity_edge (also depends on taxonomy) -> index_context.
        if stage == "extract":
            return sha256_obj(
                {
                    "stage": stage,
                    "policy_hash": self.policy_hash(),
                    "fn_version": self.extractor_versions.get("extract", "1.0.0"),
                }
            )
        if stage == "chunk":
            return sha256_obj(
                {
                    "stage": stage,
                    "policy_hash": self.policy_hash(),
                    "upstream_extract": self.extractor_versions.get("extract", "1.0.0"),
                    "fn_version": self.extractor_versions.get("chunk", "1.0.0"),
                }
            )
        if stage == "entity_edge":
            return sha256_obj(
                {
                    "stage": stage,
                    "policy_hash": self.policy_hash(),
                    "taxonomy_hash": self.taxonomy_hash(),
                    "upstream_extract": self.extractor_versions.get("extract", "1.0.0"),
                    "upstream_chunk": self.extractor_versions.get("chunk", "1.0.0"),
                    "fn_version": self.extractor_versions.get("entity_edge", "1.0.0"),
                }
            )
        return sha256_obj(
            {
                "stage": stage,
                "policy_hash": self.policy_hash(),
                "taxonomy_hash": self.taxonomy_hash(),
                "upstream_extract": self.extractor_versions.get("extract", "1.0.0"),
                "upstream_chunk": self.extractor_versions.get("chunk", "1.0.0"),
                "upstream_entity_edge": self.extractor_versions.get("entity_edge", "1.0.0"),
                "fn_version": self.extractor_versions.get("index_context", "1.0.0"),
            }
        )


def open_lineage_db(db_path: Path | str = ":memory:") -> sqlite3.Connection:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(DB_SCHEMA)
    return conn


def build_memo_key(
    *,
    scope: str,
    content_sha: str,
    fn_name: str,
    fn_version: str,
    config_hash: str,
) -> str:
    """Content-addressed memoization key strictly partitioned by ACL scope."""
    material = f"{scope}|{content_sha}|{fn_name}|{fn_version}|{config_hash}"
    return sha256_text(material)


class IncrementalLineageEngine:
    """Manages content-addressed memoization, DAG lineage, transactional refresh, and rollback."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.executescript(DB_SCHEMA)

    def _memo_get(
        self,
        *,
        scope: str,
        content_sha: str,
        fn_name: str,
        fn_version: str,
        config_hash: str,
    ) -> dict[str, Any] | None:
        key = build_memo_key(
            scope=scope,
            content_sha=content_sha,
            fn_name=fn_name,
            fn_version=fn_version,
            config_hash=config_hash,
        )
        row = self.conn.execute(
            "SELECT payload_json FROM memo_cache WHERE cache_key=? AND scope=?",
            (key, scope),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def _memo_put(
        self,
        *,
        scope: str,
        content_sha: str,
        fn_name: str,
        fn_version: str,
        config_hash: str,
        payload: dict[str, Any],
    ) -> str:
        key = build_memo_key(
            scope=scope,
            content_sha=content_sha,
            fn_name=fn_name,
            fn_version=fn_version,
            config_hash=config_hash,
        )
        out_sha = sha256_obj(payload)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO memo_cache
            (cache_key, scope, content_sha, fn_name, fn_version, config_hash, output_sha, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                scope,
                content_sha,
                fn_name,
                fn_version,
                config_hash,
                out_sha,
                _canonical_json(payload),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return out_sha

    def _fn_extract(self, src: SourceInput) -> dict[str, Any]:
        ext = Path(src.path).suffix.lower()
        lang = src.language or ast_chunker.LANGUAGE_ALIASES.get(ext, "text")
        lines = src.content.splitlines()
        return {
            "source_id": src.source_id,
            "path": src.path,
            "language": lang,
            "line_count": len(lines),
            "byte_length": len(src.content.encode("utf-8")),
            "content_sha": src.content_sha,
        }

    def _fn_chunk(self, src: SourceInput, extracted: dict[str, Any]) -> dict[str, Any]:
        lang = extracted["language"]
        if lang in {"python", "typescript", "tsx", "javascript", "jsx", "css", "html"}:
            ast_chunks = ast_chunker.chunk_code(src.content, language=lang, blob_sha=src.content_sha)
            chunks = [
                {
                    "chunk_id": f"{src.content_sha[:12]}:{c.symbol_id or idx}",
                    "name": c.name,
                    "node_type": c.node_type,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "chunk_sha": c.chunk_sha,
                    "text": c.content,
                }
                for idx, c in enumerate(ast_chunks)
            ]
        else:
            chunks = [
                {
                    "chunk_id": f"{src.content_sha[:12]}:doc",
                    "name": Path(src.path).name,
                    "node_type": "document",
                    "start_line": 1,
                    "end_line": max(1, extracted["line_count"]),
                    "chunk_sha": src.content_sha,
                    "text": src.content,
                }
            ]
        return {"chunks": chunks, "chunk_count": len(chunks)}

    def _fn_entity_edge(
        self,
        src: SourceInput,
        chunk_out: dict[str, Any],
        config: PipelineConfig,
    ) -> dict[str, Any]:
        entities: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        terms_lower = [(t, t.lower()) for t in config.taxonomy_terms]
        for ch in chunk_out["chunks"]:
            ent_id = f"ent:{src.scope}:{ch['chunk_id']}"
            entities.append(
                {
                    "entity_id": ent_id,
                    "name": ch["name"],
                    "node_type": ch["node_type"],
                    "source_path": src.path,
                    "content_sha": src.content_sha,
                }
            )
            haystack = f"{ch['name']} {ch['text']}".lower()
            for orig_term, low_term in terms_lower:
                if low_term in haystack:
                    edges.append(
                        {
                            "source": ent_id,
                            "target": f"concept:{orig_term}",
                            "relation": "MENTIONS_CONCEPT",
                            "scope": src.scope,
                        }
                    )
        return {"entities": entities, "edges": edges}

    def _fn_index_context(self, src: SourceInput, graph_out: dict[str, Any]) -> dict[str, Any]:
        concepts = sorted({e["target"] for e in graph_out["edges"]})
        return {
            "context_key": f"{src.scope}::{src.source_id}::{src.path}",
            "source_id": src.source_id,
            "path": src.path,
            "content_sha": src.content_sha,
            "entity_count": len(graph_out["entities"]),
            "edge_count": len(graph_out["edges"]),
            "concepts": concepts,
        }

    def refresh(
        self,
        sources: list[SourceInput],
        config: PipelineConfig | None = None,
        *,
        scope: str = "public",
        incremental: bool = True,
        fail_after_items: int | None = None,
    ) -> dict[str, Any]:
        """Execute transactional refresh over `sources`, returning lineage & memoization metrics.

        If `fail_after_items` is set (for fault-injection testing), simulates a mid-run
        failure and rolls back the entire SQLite transaction atomically.
        """
        cfg = config or PipelineConfig()
        snapshot_id = f"snap-{sha256_obj({'t': time.time_ns(), 'scope': scope})[:16]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        metrics = {
            "mode": "incremental" if incremental else "full_rebuild",
            "snapshot_id": snapshot_id,
            "scope": scope,
            "computed_calls": 0,
            "memo_hits": 0,
            "stage_computed": {s: 0 for s in DAG_STAGES[1:]},
            "stage_memo_hits": {s: 0 for s in DAG_STAGES[1:]},
            "reconciled_removed": 0,
            "temporarily_unavailable_preserved": 0,
            "historical_versions_retained": 0,
        }

        # Filter inputs matching target scope (strict ACL isolation)
        scoped_sources = [s for s in sources if s.scope == scope]

        # Capture previous active nodes before mutation for unavailability / removal reconciliation
        prev_nodes_rows = self.conn.execute(
            "SELECT node_id, source_id, source_path, content_sha, payload_json FROM lineage_nodes WHERE scope=? AND stage='source'",
            (scope,),
        ).fetchall()
        prev_sources_by_key = {(r[1], r[2]): {"node_id": r[0], "content_sha": r[3], "payload": json.loads(r[4])} for r in prev_nodes_rows}

        new_nodes: list[tuple[Any, ...]] = []
        new_edges: list[tuple[str, str, str]] = []
        active_keys: set[tuple[str, str]] = set()
        state_items: list[dict[str, Any]] = []

        try:
            with self.conn:
                if not incremental:
                    # Full rebuild clears memo cache for this scope to force recomputation
                    self.conn.execute("DELETE FROM memo_cache WHERE scope=?", (scope,))

                for idx, src in enumerate(sorted(scoped_sources, key=lambda s: (s.source_id, s.path))):
                    if fail_after_items is not None and idx >= fail_after_items:
                        raise RuntimeError("Simulated interruption during transactional refresh")

                    key = (src.source_id, src.path)
                    if src.availability == "confirmed_removed":
                        metrics["reconciled_removed"] += 1
                        continue

                    if src.availability == "temporarily_unavailable":
                        metrics["temporarily_unavailable_preserved"] += 1
                        prev = prev_sources_by_key.get(key)
                        if prev:
                            # Keep last known active derived state marked temporarily_unavailable
                            active_keys.add(key)
                            src_nid = f"src:{scope}:{src.source_id}:{src.path}"
                            new_nodes.append(
                                (
                                    src_nid,
                                    snapshot_id,
                                    "source",
                                    scope,
                                    src.source_id,
                                    src.path,
                                    prev["content_sha"],
                                    "source_input",
                                    "1.0.0",
                                    cfg.policy_hash(),
                                    prev["content_sha"],
                                    "temporarily_unavailable",
                                    _canonical_json(prev["payload"]),
                                )
                            )
                        continue

                    active_keys.add(key)
                    c_sha = src.content_sha

                    # Stage 0: source node
                    src_nid = f"src:{scope}:{src.source_id}:{src.path}"
                    src_payload = {"source_id": src.source_id, "path": src.path, "content_sha": c_sha}
                    new_nodes.append(
                        (
                            src_nid,
                            snapshot_id,
                            "source",
                            scope,
                            src.source_id,
                            src.path,
                            c_sha,
                            "source_input",
                            "1.0.0",
                            cfg.policy_hash(),
                            c_sha,
                            "active",
                            _canonical_json(src_payload),
                        )
                    )

                    # Stage 1: extraction
                    ext_cfg = cfg.stage_config_hash("extract")
                    ext_ver = cfg.extractor_versions.get("extract", "1.0.0")
                    ext_out = self._memo_get(
                        scope=scope, content_sha=c_sha, fn_name="extract", fn_version=ext_ver, config_hash=ext_cfg
                    ) if incremental else None
                    if ext_out is not None:
                        metrics["memo_hits"] += 1
                        metrics["stage_memo_hits"]["extraction"] += 1
                        ext_out_sha = sha256_obj(ext_out)
                    else:
                        ext_out = self._fn_extract(src)
                        ext_out_sha = self._memo_put(
                            scope=scope,
                            content_sha=c_sha,
                            fn_name="extract",
                            fn_version=ext_ver,
                            config_hash=ext_cfg,
                            payload=ext_out,
                        )
                        metrics["computed_calls"] += 1
                        metrics["stage_computed"]["extraction"] += 1

                    ext_nid = f"ext:{scope}:{src.source_id}:{src.path}"
                    new_nodes.append(
                        (
                            ext_nid, snapshot_id, "extraction", scope, src.source_id, src.path,
                            c_sha, "extract", ext_ver, ext_cfg, ext_out_sha, "active", _canonical_json(ext_out),
                        )
                    )
                    new_edges.append((src_nid, ext_nid, "DERIVES"))

                    # Stage 2: chunk (input identity depends on upstream extraction output_sha; path-independent!)
                    chk_cfg = cfg.stage_config_hash("chunk")
                    chk_ver = cfg.extractor_versions.get("chunk", "1.0.0")
                    chk_out = self._memo_get(
                        scope=scope, content_sha=ext_out_sha, fn_name="chunk", fn_version=chk_ver, config_hash=chk_cfg
                    ) if incremental else None
                    if chk_out is not None:
                        metrics["memo_hits"] += 1
                        metrics["stage_memo_hits"]["chunk"] += 1
                        chk_out_sha = sha256_obj(chk_out)
                    else:
                        chk_out = self._fn_chunk(src, ext_out)
                        chk_out_sha = self._memo_put(
                            scope=scope,
                            content_sha=ext_out_sha,
                            fn_name="chunk",
                            fn_version=chk_ver,
                            config_hash=chk_cfg,
                            payload=chk_out,
                        )
                        metrics["computed_calls"] += 1
                        metrics["stage_computed"]["chunk"] += 1

                    chk_nid = f"chk:{scope}:{src.source_id}:{src.path}"
                    new_nodes.append(
                        (
                            chk_nid, snapshot_id, "chunk", scope, src.source_id, src.path,
                            c_sha, "chunk", chk_ver, chk_cfg, chk_out_sha, "active", _canonical_json(chk_out),
                        )
                    )
                    new_edges.append((ext_nid, chk_nid, "DERIVES"))

                    # Stage 3: entity_edge (depends on chunk output_sha, source occurrence path, AND taxonomy_hash)
                    ee_cfg = sha256_obj(
                        {
                            "stage_cfg": cfg.stage_config_hash("entity_edge"),
                            "source_id": src.source_id,
                            "path": src.path,
                        }
                    )
                    ee_ver = cfg.extractor_versions.get("entity_edge", "1.0.0")
                    ee_out = self._memo_get(
                        scope=scope, content_sha=chk_out_sha, fn_name="entity_edge", fn_version=ee_ver, config_hash=ee_cfg
                    ) if incremental else None
                    if ee_out is not None:
                        metrics["memo_hits"] += 1
                        metrics["stage_memo_hits"]["entity_edge"] += 1
                        ee_out_sha = sha256_obj(ee_out)
                    else:
                        ee_out = self._fn_entity_edge(src, chk_out, cfg)
                        ee_out_sha = self._memo_put(
                            scope=scope,
                            content_sha=chk_out_sha,
                            fn_name="entity_edge",
                            fn_version=ee_ver,
                            config_hash=ee_cfg,
                            payload=ee_out,
                        )
                        metrics["computed_calls"] += 1
                        metrics["stage_computed"]["entity_edge"] += 1

                    ee_nid = f"ee:{scope}:{src.source_id}:{src.path}"
                    new_nodes.append(
                        (
                            ee_nid, snapshot_id, "entity_edge", scope, src.source_id, src.path,
                            c_sha, "entity_edge", ee_ver, ee_cfg, ee_out_sha, "active", _canonical_json(ee_out),
                        )
                    )
                    new_edges.append((chk_nid, ee_nid, "DERIVES"))

                    # Stage 4: index_context (depends on entity_edge output_sha and occurrence path)
                    ic_cfg = sha256_obj(
                        {
                            "stage_cfg": cfg.stage_config_hash("index_context"),
                            "source_id": src.source_id,
                            "path": src.path,
                        }
                    )
                    ic_ver = cfg.extractor_versions.get("index_context", "1.0.0")
                    ic_out = self._memo_get(
                        scope=scope, content_sha=ee_out_sha, fn_name="index_context", fn_version=ic_ver, config_hash=ic_cfg
                    ) if incremental else None
                    if ic_out is not None:
                        metrics["memo_hits"] += 1
                        metrics["stage_memo_hits"]["index_context"] += 1
                        ic_out_sha = sha256_obj(ic_out)
                    else:
                        ic_out = self._fn_index_context(src, ee_out)
                        ic_out_sha = self._memo_put(
                            scope=scope,
                            content_sha=ee_out_sha,
                            fn_name="index_context",
                            fn_version=ic_ver,
                            config_hash=ic_cfg,
                            payload=ic_out,
                        )
                        metrics["computed_calls"] += 1
                        metrics["stage_computed"]["index_context"] += 1

                    ic_nid = f"ic:{scope}:{src.source_id}:{src.path}"
                    new_nodes.append(
                        (
                            ic_nid, snapshot_id, "index_context", scope, src.source_id, src.path,
                            c_sha, "index_context", ic_ver, ic_cfg, ic_out_sha, "active", _canonical_json(ic_out),
                        )
                    )
                    new_edges.append((ee_nid, ic_nid, "DERIVES"))

                    # Preserve immutable historical version record (never deleted on rename/removal)
                    ver_key = f"{scope}:{src.source_id}:{src.path}:{c_sha}"
                    self.conn.execute(
                        """
                        INSERT INTO historical_versions
                        (version_key, source_id, source_path, content_sha, scope, first_seen_snapshot, last_seen_snapshot, payload_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(version_key) DO UPDATE SET last_seen_snapshot=excluded.last_seen_snapshot
                        """,
                        (ver_key, src.source_id, src.path, c_sha, scope, snapshot_id, snapshot_id, _canonical_json(ic_out)),
                    )
                    state_items.append({"context": ic_out, "output_sha": ic_out_sha})

                # Count reconciled removals (keys previously active but absent now)
                removed_keys = set(prev_sources_by_key.keys()) - active_keys
                metrics["reconciled_removed"] += len(removed_keys)

                # Replace current snapshot projection atomically for this scope
                self.conn.execute(
                    "DELETE FROM lineage_edges WHERE parent_node_id IN (SELECT node_id FROM lineage_nodes WHERE scope=?)",
                    (scope,),
                )
                self.conn.execute("DELETE FROM lineage_nodes WHERE scope=?", (scope,))
                self.conn.executemany(
                    """
                    INSERT INTO lineage_nodes
                    (node_id, snapshot_id, stage, scope, source_id, source_path, content_sha,
                     extractor_name, extractor_version, config_hash, output_sha, status, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    new_nodes,
                )
                self.conn.executemany(
                    "INSERT OR IGNORE INTO lineage_edges (parent_node_id, child_node_id, relation) VALUES (?, ?, ?)",
                    new_edges,
                )

                state_hash = sha256_obj(sorted(state_items, key=lambda x: x["context"]["context_key"]))
                self.conn.execute(
                    """
                    INSERT INTO snapshots
                    (snapshot_id, created_at, scope, taxonomy_hash, policy_hash, extractor_versions_json, state_hash, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'committed')
                    """,
                    (
                        snapshot_id,
                        now_iso,
                        scope,
                        cfg.taxonomy_hash(),
                        cfg.policy_hash(),
                        _canonical_json(cfg.extractor_versions),
                        state_hash,
                    ),
                )
        except Exception as exc:
            # Transaction rolled back automatically by `with self.conn:`
            # Record rolled_back audit entry in a separate short transaction
            with self.conn:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO snapshots
                    (snapshot_id, created_at, scope, taxonomy_hash, policy_hash, extractor_versions_json, state_hash, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'rolled_back')
                    """,
                    (
                        snapshot_id,
                        now_iso,
                        scope,
                        cfg.taxonomy_hash(),
                        cfg.policy_hash(),
                        _canonical_json(cfg.extractor_versions),
                        "rolled-back",
                    ),
                )
            return {
                **metrics,
                "status": "rolled_back",
                "error": str(exc),
                "state_hash": self.current_state_hash(scope=scope),
            }

        hist_count = self.conn.execute(
            "SELECT count(*) FROM historical_versions WHERE scope=?", (scope,)
        ).fetchone()[0]
        metrics["historical_versions_retained"] = hist_count
        metrics["status"] = "committed"
        metrics["state_hash"] = self.current_state_hash(scope=scope)
        metrics["dag_nodes"] = len(new_nodes)
        metrics["dag_edges"] = len(new_edges)
        return metrics

    def current_state_hash(self, *, scope: str = "public") -> str:
        """Deterministic hash of current `index_context` outputs for equivalence checks."""
        rows = self.conn.execute(
            "SELECT output_sha, payload_json FROM lineage_nodes WHERE scope=? AND stage='index_context' ORDER BY node_id",
            (scope,),
        ).fetchall()
        material = [{"output_sha": r[0], "payload": json.loads(r[1])} for r in rows]
        return sha256_obj(material)

    def get_active_contexts(self, *, scope: str = "public") -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT payload_json FROM lineage_nodes WHERE scope=? AND stage='index_context' ORDER BY node_id",
            (scope,),
        ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def get_historical_versions(self, *, scope: str = "public") -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT source_id, source_path, content_sha, first_seen_snapshot, last_seen_snapshot FROM historical_versions WHERE scope=? ORDER BY version_key",
            (scope,),
        ).fetchall()
        return [
            {
                "source_id": r[0],
                "source_path": r[1],
                "content_sha": r[2],
                "first_seen_snapshot": r[3],
                "last_seen_snapshot": r[4],
            }
            for r in rows
        ]


def run_benchmark(num_files: int = 24) -> dict[str, Any]:
    """Benchmark Full Rebuild vs Incremental Refresh across realistic mutation scenarios.

    Scenarios measured:
      1. Initial full build
      2. No-op idempotent refresh (0% change)
      3. Single file modification (1/N files changed)
      4. File rename (content SHA unchanged -> downstream extraction/chunk memoized!)
      5. Confirmed file removal (reconciled current projection, historical preserved)
      6. Selective taxonomy update (extract & chunk 100% memoized; entity_edge & index_context recomputed)
      7. Interruption + atomic rollback verification
    """
    base_sources = [
        SourceInput(
            source_id="repo.exams-app",
            path=f"src/components/Widget{i:02d}.tsx",
            content=(
                f"export function Widget{i:02d}() {{\n"
                f"  const label = 'sidebar tab {i}';\n"
                f"  return <div className='duration-200'>{i}</div>;\n"
                f"}}\n"
            ),
            scope="public",
        )
        for i in range(num_files)
    ]

    def _measure(fn: Callable[[], dict[str, Any]]) -> tuple[dict[str, Any], float, int]:
        tracemalloc.start()
        t0 = time.perf_counter()
        res = fn()
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return res, elapsed_ms, peak

    with tempfile.TemporaryDirectory(prefix="lineage-bench-") as td:
        inc_db = open_lineage_db(Path(td) / "inc.sqlite")
        full_db = open_lineage_db(Path(td) / "full.sqlite")
        inc_engine = IncrementalLineageEngine(inc_db)
        full_engine = IncrementalLineageEngine(full_db)
        cfg = PipelineConfig()

        # 1. Initial build
        init_res, init_ms, init_mem = _measure(lambda: inc_engine.refresh(base_sources, cfg, incremental=True))

        # 2. Idempotent no-op
        noop_res, noop_ms, _ = _measure(lambda: inc_engine.refresh(base_sources, cfg, incremental=True))
        full_noop, full_noop_ms, _ = _measure(lambda: full_engine.refresh(base_sources, cfg, incremental=False))

        # 3. Single file edit
        edited = list(base_sources)
        edited[0] = SourceInput(
            source_id="repo.exams-app",
            path=edited[0].path,
            content=edited[0].content + "\n// updated motion\n",
            scope="public",
        )
        edit_res, edit_ms, _ = _measure(lambda: inc_engine.refresh(edited, cfg, incremental=True))
        full_edit, full_edit_ms, _ = _measure(lambda: full_engine.refresh(edited, cfg, incremental=False))

        # 4. File rename (same content SHA -> extract & chunk memoized!)
        renamed = list(edited)
        renamed[1] = SourceInput(
            source_id="repo.exams-app",
            path="src/components/Widget01Renamed.tsx",
            content=renamed[1].content,
            scope="public",
        )
        ren_res, ren_ms, _ = _measure(lambda: inc_engine.refresh(renamed, cfg, incremental=True))
        full_ren, full_ren_ms, _ = _measure(lambda: full_engine.refresh(renamed, cfg, incremental=False))

        # 5. Confirmed deletion
        deleted = renamed[:-1]
        del_res, del_ms, _ = _measure(lambda: inc_engine.refresh(deleted, cfg, incremental=True))
        full_del, full_del_ms, _ = _measure(lambda: full_engine.refresh(deleted, cfg, incremental=False))

        # 6. Taxonomy change (selective downstream invalidation only: entity_edge + index_context)
        tax_cfg = PipelineConfig(
            taxonomy_version="1.1.0",
            taxonomy_terms=cfg.taxonomy_terms + ("motion", "widget"),
        )
        tax_res, tax_ms, _ = _measure(lambda: inc_engine.refresh(deleted, tax_cfg, incremental=True))
        full_tax, full_tax_ms, _ = _measure(lambda: full_engine.refresh(deleted, tax_cfg, incremental=False))

        # 7. Interruption rollback check
        pre_hash = inc_engine.current_state_hash(scope="public")
        rb_res = inc_engine.refresh(
            [
                SourceInput(
                    source_id="repo.exams-app",
                    path="src/components/Broken.tsx",
                    content="export function Broken() { return null; }",
                    scope="public",
                )
            ],
            tax_cfg,
            incremental=True,
            fail_after_items=0,
        )
        post_hash = inc_engine.current_state_hash(scope="public")

        scenarios = [
            {
                "scenario": "noop_idempotent",
                "incremental_ms": noop_ms,
                "full_rebuild_ms": full_noop_ms,
                "incremental_computed_calls": noop_res["computed_calls"],
                "full_computed_calls": full_noop["computed_calls"],
                "memo_hits": noop_res["memo_hits"],
                "work_avoided_ratio": round(
                    1.0 - (noop_res["computed_calls"] / max(1, full_noop["computed_calls"])), 4
                ),
                "equivalent_to_full_rebuild": noop_res["state_hash"] == full_noop["state_hash"],
            },
            {
                "scenario": "single_file_edit",
                "incremental_ms": edit_ms,
                "full_rebuild_ms": full_edit_ms,
                "incremental_computed_calls": edit_res["computed_calls"],
                "full_computed_calls": full_edit["computed_calls"],
                "memo_hits": edit_res["memo_hits"],
                "work_avoided_ratio": round(
                    1.0 - (edit_res["computed_calls"] / max(1, full_edit["computed_calls"])), 4
                ),
                "equivalent_to_full_rebuild": edit_res["state_hash"] == full_edit["state_hash"],
            },
            {
                "scenario": "file_rename",
                "incremental_ms": ren_ms,
                "full_rebuild_ms": full_ren_ms,
                "incremental_computed_calls": ren_res["computed_calls"],
                "full_computed_calls": full_ren["computed_calls"],
                "memo_hits": ren_res["memo_hits"],
                "work_avoided_ratio": round(
                    1.0 - (ren_res["computed_calls"] / max(1, full_ren["computed_calls"])), 4
                ),
                "equivalent_to_full_rebuild": ren_res["state_hash"] == full_ren["state_hash"],
            },
            {
                "scenario": "confirmed_removal",
                "incremental_ms": del_ms,
                "full_rebuild_ms": full_del_ms,
                "incremental_computed_calls": del_res["computed_calls"],
                "full_computed_calls": full_del["computed_calls"],
                "memo_hits": del_res["memo_hits"],
                "work_avoided_ratio": round(
                    1.0 - (del_res["computed_calls"] / max(1, full_del["computed_calls"])), 4
                ),
                "equivalent_to_full_rebuild": del_res["state_hash"] == full_del["state_hash"],
                "historical_versions_retained": del_res["historical_versions_retained"],
            },
            {
                "scenario": "taxonomy_schema_change",
                "incremental_ms": tax_ms,
                "full_rebuild_ms": full_tax_ms,
                "incremental_computed_calls": tax_res["computed_calls"],
                "full_computed_calls": full_tax["computed_calls"],
                "memo_hits": tax_res["memo_hits"],
                "stage_memo_hits": tax_res["stage_memo_hits"],
                "stage_computed": tax_res["stage_computed"],
                "work_avoided_ratio": round(
                    1.0 - (tax_res["computed_calls"] / max(1, full_tax["computed_calls"])), 4
                ),
                "equivalent_to_full_rebuild": tax_res["state_hash"] == full_tax["state_hash"],
            },
            {
                "scenario": "failure_atomic_rollback",
                "status": rb_res["status"],
                "state_preserved_after_rollback": pre_hash == post_hash,
            },
        ]

        inc_db.close()
        full_db.close()

    return {
        "schema_version": 1,
        "corpus_files": num_files,
        "initial_build_ms": init_ms,
        "initial_peak_memory_bytes": init_mem,
        "initial_computed_calls": init_res["computed_calls"],
        "all_scenarios_equivalent_to_full_rebuild": all(
            s.get("equivalent_to_full_rebuild", True) for s in scenarios
        ),
        "rollback_integrity_verified": pre_hash == post_hash,
        "scenarios": scenarios,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    bench = sub.add_parser("benchmark", help="Run full vs incremental lineage benchmark")
    bench.add_argument("--files", type=int, default=24)
    args = parser.parse_args(argv)

    if args.command == "benchmark":
        report = run_benchmark(num_files=args.files)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
