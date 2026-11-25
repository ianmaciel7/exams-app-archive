#!/usr/bin/env python3
"""Hierarchical and recursive context retriever with strict pre-ranking filters (#86).

LlamaIndex-inspired recursive retriever over native SQLite + Python stdlib structures
(no mandatory LlamaIndex dependency, zero external network calls, zero Unicode emojis):

1. Explicit multi-modal hierarchy modeling:
     - Document: `document` > `section` > `subsection` > `passage`
     - Code:     `module` > `symbol` (class/component) > `member` (method/function/handler)
     - Media:    `asset` > `segment` > `state`
   Preserving parent/child pointers, cross-references (`references`), and `blob_sha` / `record_sha256`.

2. Pre-ranking metadata & security filtering (applied BEFORE candidate generation & ranking,
   AND re-applied on every node visited during recursive expansion):
     - authorization (`authorized`, `scope`: `public` vs `authenticated_archive`)
     - `repo` / `ref`
     - `version`
     - `domain`
     - `license`
     - `provenance_status` (`verified` vs `unverified` / `synthetic` / `not-recovered`)
     - `node_type` / `modality` / `product`

3. Specific-first recursive retrieval:
     - Retrieves the most specific leaf/child nodes matching the query first (`passage`, `member`, `state`,
       or `subsection`/`symbol`/`segment`).
     - Recursively expands parent context, child details, and typed cross-references (`references`)
       when query intent or depth requires structural context.
     - Enforces `depth_limit`, `visited_set`, cycle protection (tracking cyclic edge paths explicitly),
       and strict `budget_tokens`.

4. Compound query decomposition & recombination:
     - Splits compound natural-language questions (e.g., "X e Y", "X and Y", multi-clause questions)
       into deterministic subqueries, retrieves per subquery, and recombines evidence with explicit
       retrieval justification (`retrieval_reason`) and missing-evidence gap reporting.

5. Flat vs Hierarchical-Recursive benchmark comparison:
     - Evaluates flat leaf-only retrieval against recursive hierarchical retrieval across
       business rules, code, architectural decisions, learning (SRS/FSRS), and operations queries.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ast_chunker  # noqa: E402
import document_extractor  # noqa: E402
import domain_ontology  # noqa: E402
import federated_retrieval  # noqa: E402
import search_expansion  # noqa: E402

SCHEMA_VERSION = 1
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

# Canonical hierarchy level definitions & specificity rank (higher = more specific leaf)
DOCUMENT_LEVELS = ("document", "section", "subsection", "passage")
CODE_LEVELS = ("module", "symbol", "member")
MEDIA_LEVELS = ("asset", "segment", "state")

LEVEL_SPECIFICITY: dict[str, int] = {
    "document": 1,
    "section": 2,
    "subsection": 3,
    "passage": 4,
    "module": 1,
    "symbol": 2,
    "member": 3,
    "asset": 1,
    "segment": 2,
    "state": 3,
}

LEVEL_MODALITY: dict[str, str] = {
    "document": "document",
    "section": "document",
    "subsection": "document",
    "passage": "document",
    "module": "code",
    "symbol": "code",
    "member": "code",
    "asset": "media",
    "segment": "media",
    "state": "media",
}

VALID_LEVELS = frozenset(LEVEL_SPECIFICITY.keys())
VALID_EXPANSION_POLICIES = frozenset({"none", "parents", "children", "parents_and_refs", "full"})

DB_SCHEMA = """
PRAGMA journal_mode=DELETE;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS hier_nodes (
    node_id TEXT PRIMARY KEY,
    modality TEXT NOT NULL CHECK(modality IN ('document', 'code', 'media')),
    level TEXT NOT NULL,
    parent_id TEXT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'public',
    repo TEXT NOT NULL DEFAULT '',
    ref TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    domain TEXT NOT NULL DEFAULT '',
    license TEXT NOT NULL DEFAULT '',
    product TEXT NOT NULL DEFAULT '',
    provenance_status TEXT NOT NULL DEFAULT 'verified',
    blob_sha TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS hier_edges (
    src_id TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    relation TEXT NOT NULL CHECK(relation IN ('parent_of', 'child_of', 'references', 'evidenced_by', 'decided_in')),
    PRIMARY KEY (src_id, dst_id, relation)
);
"""


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def estimate_tokens(obj: Any) -> int:
    raw = obj if isinstance(obj, str) else _canonical_json(obj)
    return (len(raw) + 3) // 4 if raw else 0


@dataclass(frozen=True)
class PreRankingFilter:
    """Strict metadata & authorization filter applied BEFORE candidate scoring and during expansion."""

    authorized: bool = False
    allowed_scopes: tuple[str, ...] = ("public",)
    repo: str | None = None
    ref: str | None = None
    version: str | None = None
    domain: str | None = None
    license: str | None = None
    product: str | None = None
    modality: str | None = None
    provenance_statuses: tuple[str, ...] = ("verified",)

    def allows(self, node: "HierarchyNode") -> tuple[bool, str]:
        """Return (allowed, rejection_reason)."""
        # 1. Authorization & scope gate always runs first
        if node.scope not in self.allowed_scopes:
            return False, f"scope_blocked:{node.scope}"
        if node.scope == "authenticated_archive" and not self.authorized:
            return False, "authorization_required"

        # 2. Provenance verification gate
        if self.provenance_statuses and node.provenance_status not in self.provenance_statuses:
            return False, f"provenance_filtered:{node.provenance_status}"

        # 3. Metadata pins (repo, ref, version, domain, license, product, modality)
        if self.repo is not None and node.repo != self.repo:
            return False, f"repo_mismatch:{node.repo}"
        if self.ref is not None and node.ref != self.ref:
            return False, f"ref_mismatch:{node.ref}"
        if self.version is not None and node.version != self.version:
            return False, f"version_mismatch:{node.version}"
        if self.domain is not None and node.domain != self.domain:
            return False, f"domain_mismatch:{node.domain}"
        if self.license is not None and node.license != self.license:
            return False, f"license_mismatch:{node.license}"
        if self.product is not None and node.product.lower() != self.product.lower():
            return False, f"product_mismatch:{node.product}"
        if self.modality is not None and node.modality != self.modality:
            return False, f"modality_mismatch:{node.modality}"

        return True, "ok"


@dataclass
class HierarchyNode:
    """Node in the document/code/media hierarchy with explicit parent/child/reference pointers."""

    node_id: str
    modality: str  # "document" | "code" | "media"
    level: str  # document>section>subsection>passage | module>symbol>member | asset>segment>state
    title: str
    content: str
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    scope: str = "public"
    repo: str = ""
    ref: str = ""
    version: str = ""
    domain: str = ""
    license: str = ""
    product: str = ""
    provenance_status: str = "verified"
    blob_sha: str = ""
    path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.level not in VALID_LEVELS:
            raise ValueError(f"Unsupported hierarchy level {self.level!r}")
        expected_mod = LEVEL_MODALITY[self.level]
        if self.modality != expected_mod:
            raise ValueError(f"Level {self.level!r} belongs to modality {expected_mod!r}, got {self.modality!r}")
        if self.scope not in {"public", "authenticated_archive"}:
            raise ValueError(f"Unsupported scope {self.scope!r}")

    @property
    def specificity(self) -> int:
        return LEVEL_SPECIFICITY[self.level]

    def to_dict(self) -> dict[str, Any]:
        clean_title, _ = domain_ontology.sanitize_untrusted_text(self.title, max_length=240)
        clean_content, _ = domain_ontology.sanitize_untrusted_text(self.content, max_length=1200)
        return {
            "node_id": self.node_id,
            "modality": self.modality,
            "level": self.level,
            "specificity": self.specificity,
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "references": list(self.references),
            "title": clean_title,
            "content": clean_content,
            "scope": self.scope,
            "provenance": {
                "repo": self.repo,
                "ref": self.ref,
                "version": self.version,
                "domain": self.domain,
                "license": self.license,
                "product": self.product,
                "provenance_status": self.provenance_status,
                "blob_sha": self.blob_sha,
                "path": self.path,
            },
            "metadata": self.metadata,
        }


class HierarchicalStore:
    """In-memory and SQLite-backed hierarchical store supporting documents, code ASTs, and visual media."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self.nodes: dict[str, HierarchyNode] = {}
        self.edges: set[tuple[str, str, str]] = set()
        self.conn = conn
        if self.conn is not None:
            self.conn.row_factory = sqlite3.Row
            self.conn.executescript(DB_SCHEMA)

    def add_node(self, node: HierarchyNode) -> None:
        self.nodes[node.node_id] = node
        if node.parent_id:
            self.edges.add((node.parent_id, node.node_id, "parent_of"))
            self.edges.add((node.node_id, node.parent_id, "child_of"))
            if node.parent_id in self.nodes:
                parent = self.nodes[node.parent_id]
                if node.node_id not in parent.children_ids:
                    parent.children_ids.append(node.node_id)
        for cid in node.children_ids:
            self.edges.add((node.node_id, cid, "parent_of"))
            self.edges.add((cid, node.node_id, "child_of"))
        for ref_id in node.references:
            self.edges.add((node.node_id, ref_id, "references"))

        if self.conn is not None:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO hier_nodes (
                        node_id, modality, level, parent_id, title, content, scope,
                        repo, ref, version, domain, license, product, provenance_status,
                        blob_sha, path, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node.node_id, node.modality, node.level, node.parent_id,
                        node.title, node.content, node.scope,
                        node.repo, node.ref, node.version, node.domain,
                        node.license, node.product, node.provenance_status,
                        node.blob_sha, node.path, _canonical_json(node.metadata),
                    ),
                )
                for src, dst, rel in list(self.edges):
                    if src == node.node_id or dst == node.node_id:
                        self.conn.execute(
                            "INSERT OR IGNORE INTO hier_edges (src_id, dst_id, relation) VALUES (?, ?, ?)",
                            (src, dst, rel),
                        )

    def add_reference(self, src_id: str, dst_id: str, relation: str = "references") -> None:
        if relation not in {"parent_of", "child_of", "references", "evidenced_by", "decided_in"}:
            raise ValueError(f"Unsupported relation: {relation}")
        self.edges.add((src_id, dst_id, relation))
        if src_id in self.nodes and relation == "references":
            if dst_id not in self.nodes[src_id].references:
                self.nodes[src_id].references.append(dst_id)
        if self.conn is not None:
            with self.conn:
                self.conn.execute(
                    "INSERT OR IGNORE INTO hier_edges (src_id, dst_id, relation) VALUES (?, ?, ?)",
                    (src_id, dst_id, relation),
                )

    def finalize_links(self) -> None:
        """Back-populate children_ids from parent_id across all registered nodes."""
        for node in self.nodes.values():
            if node.parent_id and node.parent_id in self.nodes:
                parent = self.nodes[node.parent_id]
                if node.node_id not in parent.children_ids:
                    parent.children_ids.append(node.node_id)
                self.edges.add((parent.node_id, node.node_id, "parent_of"))
                self.edges.add((node.node_id, parent.node_id, "child_of"))

    def add_document_from_markdown(
        self,
        text: str,
        *,
        doc_id: str,
        path: str,
        scope: str = "public",
        repo: str = "",
        ref: str = "",
        version: str = "1.0.0",
        domain: str = "arquitetura-tecnica",
        license_name: str = "MIT",
        provenance_status: str = "verified",
    ) -> list[str]:
        """Parse markdown into document > section > subsection > passage hierarchy via document_extractor."""
        extracted = document_extractor.extract_document_bytes(
            text.encode("utf-8"), path=path, repo=repo or "local", ref=ref
        )
        doc_sha = extracted["provenance"]["sha256"]
        doc_title = extracted["metadata"]["title"]
        created: list[str] = []

        root_node = HierarchyNode(
            node_id=doc_id,
            modality="document",
            level="document",
            title=doc_title,
            content=f"Document {doc_title} ({path}) with {extracted['metadata']['section_count']} sections.",
            parent_id=None,
            scope=scope,
            repo=repo,
            ref=ref,
            version=version,
            domain=domain,
            license=license_name,
            provenance_status=provenance_status,
            blob_sha=doc_sha,
            path=path,
            metadata={"document_type": extracted["provenance"]["document_type"]},
        )
        self.add_node(root_node)
        created.append(doc_id)

        sec_id_map: dict[str, str] = {}
        for sec in extracted.get("sections", []):
            raw_eid = sec["element_id"]
            lvl = int(sec.get("level", 1))
            hier_level = "section" if lvl <= 1 else "subsection"
            raw_parent = sec.get("parent_id")
            parent_nid = sec_id_map.get(raw_parent, doc_id) if raw_parent else doc_id
            sec_nid = f"{doc_id}:{raw_eid}"
            sec_id_map[raw_eid] = sec_nid

            # Extract body without heading line if multiple paragraphs exist
            lines = [ln for ln in sec["content"].splitlines() if ln.strip()]
            body_lines = lines[1:] if len(lines) > 1 and lines[0].lstrip().startswith("#") else lines
            summary = body_lines[0] if body_lines else sec["title"]

            self.add_node(
                HierarchyNode(
                    node_id=sec_nid,
                    modality="document",
                    level=hier_level,
                    title=sec["title"],
                    content=summary,
                    parent_id=parent_nid,
                    scope=scope,
                    repo=repo,
                    ref=ref,
                    version=version,
                    domain=domain,
                    license=license_name,
                    provenance_status=provenance_status,
                    blob_sha=sec.get("content_sha256", doc_sha),
                    path=path,
                    metadata={"section_path": sec["section_path"], "position": sec.get("position")},
                )
            )
            created.append(sec_nid)

            # Split body into paragraph passages
            paragraphs = [p.strip() for p in "\n".join(body_lines).split("\n\n") if p.strip()]
            for p_idx, para in enumerate(paragraphs, start=1):
                p_nid = f"{sec_nid}:p{p_idx}"
                self.add_node(
                    HierarchyNode(
                        node_id=p_nid,
                        modality="document",
                        level="passage",
                        title=f"{sec['title']} [passage {p_idx}]",
                        content=para,
                        parent_id=sec_nid,
                        scope=scope,
                        repo=repo,
                        ref=ref,
                        version=version,
                        domain=domain,
                        license=license_name,
                        provenance_status=provenance_status,
                        blob_sha=hashlib.sha256(para.encode("utf-8")).hexdigest(),
                        path=path,
                        metadata={"section_path": sec["section_path"], "passage_index": p_idx},
                    )
                )
                created.append(p_nid)

        self.finalize_links()
        return created

    def add_code_from_source(
        self,
        source_text: str,
        *,
        module_id: str,
        path: str,
        language: str,
        scope: str = "public",
        repo: str = "",
        ref: str = "",
        version: str = "1.0.0",
        domain: str = "engenharia",
        license_name: str = "MIT",
        provenance_status: str = "verified",
    ) -> list[str]:
        """Parse code via ast_chunker into module > symbol > member hierarchy."""
        bsha = ast_chunker.compute_git_blob_sha(source_text)
        chunks = ast_chunker.chunk_code(source_text, language=language, blob_sha=bsha)
        created: list[str] = []

        mod_node = HierarchyNode(
            node_id=module_id,
            modality="code",
            level="module",
            title=Path(path).name,
            content=f"Module {path} ({language}) with {len(chunks)} AST chunks.",
            parent_id=None,
            scope=scope,
            repo=repo,
            ref=ref,
            version=version,
            domain=domain,
            license=license_name,
            provenance_status=provenance_status,
            blob_sha=bsha,
            path=path,
            metadata={"language": language},
        )
        self.add_node(mod_node)
        created.append(module_id)

        symbol_by_name: dict[str, str] = {}
        # First pass: top-level symbols (class, component, interface, function, hook)
        # Second pass: nested members (method, handler, nested hook)
        top_chunks = [c for c in chunks if c.parent_context in {"module", "root", "stylesheet", "fallback"}]
        nested_chunks = [c for c in chunks if c not in top_chunks]

        for ch in top_chunks:
            if ch.node_type == "module":
                continue
            nid = f"{module_id}:{ch.symbol_id or ch.name}"
            symbol_by_name[ch.name] = nid
            self.add_node(
                HierarchyNode(
                    node_id=nid,
                    modality="code",
                    level="symbol",
                    title=f"{ch.name} ({ch.node_type})",
                    content=ch.content,
                    parent_id=module_id,
                    scope=scope,
                    repo=repo,
                    ref=ref,
                    version=version,
                    domain=domain,
                    license=license_name,
                    provenance_status=provenance_status,
                    blob_sha=ch.blob_sha,
                    path=path,
                    metadata={
                        "symbol_id": ch.symbol_id,
                        "node_type": ch.node_type,
                        "start_line": ch.start_line,
                        "end_line": ch.end_line,
                    },
                )
            )
            created.append(nid)

        for ch in nested_chunks:
            parent_key = ch.parent_context.split(".")[-1]
            parent_nid = symbol_by_name.get(parent_key, module_id)
            nid = f"{module_id}:{ch.symbol_id or ch.name}:{ch.chunk_index}"
            self.add_node(
                HierarchyNode(
                    node_id=nid,
                    modality="code",
                    level="member",
                    title=f"{ch.parent_context}.{ch.name} ({ch.node_type})",
                    content=ch.content,
                    parent_id=parent_nid,
                    scope=scope,
                    repo=repo,
                    ref=ref,
                    version=version,
                    domain=domain,
                    license=license_name,
                    provenance_status=provenance_status,
                    blob_sha=ch.blob_sha,
                    path=path,
                    metadata={
                        "symbol_id": ch.symbol_id,
                        "node_type": ch.node_type,
                        "start_line": ch.start_line,
                        "end_line": ch.end_line,
                    },
                )
            )
            created.append(nid)

        # Extract class methods deterministically for TS/JS classes when ast_chunker emits class-level blocks
        if language in {"typescript", "tsx", "javascript", "jsx", "ts", "js"}:
            method_re = re.compile(
                r"^[ \t]*(?:async\s+)?([A-Za-z_$][A-Za-z0-9_$]*)\s*\(([^)]*)\)\s*(?::\s*[^{]+)?\{",
                re.MULTILINE,
            )
            for sym_ch in top_chunks:
                if sym_ch.node_type != "class":
                    continue
                parent_nid = symbol_by_name.get(sym_ch.name, module_id)
                for m_match in method_re.finditer(sym_ch.content):
                    m_name = m_match.group(1)
                    if m_name in {"if", "for", "while", "switch", "catch", "constructor"}:
                        continue
                    start_pos = m_match.start()
                    brace_pos = sym_ch.content.find("{", start_pos)
                    depth = 0
                    end_pos = len(sym_ch.content)
                    for pos in range(brace_pos, len(sym_ch.content)):
                        if sym_ch.content[pos] == "{":
                            depth += 1
                        elif sym_ch.content[pos] == "}":
                            depth -= 1
                            if depth == 0:
                                end_pos = pos + 1
                                break
                    m_body = sym_ch.content[start_pos:end_pos].strip()
                    m_nid = f"{parent_nid}.{m_name}"
                    if m_nid not in self.nodes:
                        self.add_node(
                            HierarchyNode(
                                node_id=m_nid,
                                modality="code",
                                level="member",
                                title=f"{sym_ch.name}.{m_name} (method)",
                                content=m_body,
                                parent_id=parent_nid,
                                scope=scope,
                                repo=repo,
                                ref=ref,
                                version=version,
                                domain=domain,
                                license=license_name,
                                provenance_status=provenance_status,
                                blob_sha=sym_ch.blob_sha,
                                path=path,
                                metadata={
                                    "symbol_id": f"{sym_ch.symbol_id}.{m_name}",
                                    "node_type": "method",
                                    "start_line": sym_ch.start_line,
                                    "end_line": sym_ch.end_line,
                                },
                            )
                        )
                        created.append(m_nid)

        self.finalize_links()
        return created

    def add_media_from_record(
        self,
        record: dict[str, Any],
        *,
        scope: str = "public",
        domain: str = "midia",
    ) -> list[str]:
        """Build asset > segment > state hierarchy from a visual-evidence-library record."""
        asset_id = f"media:{record['id']}"
        provenance_status = "verified" if record.get("status") == "archived-blob-verified" else "unverified"
        asset_node = HierarchyNode(
            node_id=asset_id,
            modality="media",
            level="asset",
            title=record.get("title", record["id"]),
            content=f"{record.get('title', '')} | product={record.get('product', '')} | kind={record.get('kind', '')} | keywords={','.join(record.get('keywords', []))}",
            parent_id=None,
            scope=scope,
            repo=record.get("source_repo", ""),
            ref="",
            version=record.get("source_commit", ""),
            domain=domain,
            license=record.get("license", ""),
            product=record.get("product", ""),
            provenance_status=provenance_status,
            blob_sha=record.get("blob_sha", ""),
            path=record.get("path", ""),
            metadata={"classification": record.get("classification"), "playback": record.get("playback")},
        )
        self.add_node(asset_node)
        created = [asset_id]

        ev = record.get("segment_evidence")
        if isinstance(ev, dict):
            seg = ev.get("segment", {})
            seg_id = f"{asset_id}:segment"
            obs_text = " ".join(ev.get("observations", []))
            self.add_node(
                HierarchyNode(
                    node_id=seg_id,
                    modality="media",
                    level="segment",
                    title=f"{record.get('title', record['id'])} [segment {seg.get('start_seconds', 0)}-{seg.get('end_seconds', 0)}s]",
                    content=f"Pattern: {ev.get('pattern', '')} | Component: {ev.get('component', '')} | Trigger: {ev.get('trigger', '')} | {obs_text}".strip(),
                    parent_id=asset_id,
                    scope=scope,
                    repo=record.get("source_repo", ""),
                    version=record.get("source_commit", ""),
                    domain=domain,
                    license=record.get("license", ""),
                    product=record.get("product", ""),
                    provenance_status=provenance_status,
                    blob_sha=ev.get("source_blob_sha", record.get("blob_sha", "")),
                    path=record.get("path", ""),
                    metadata={"segment": seg, "keyframes": ev.get("keyframes", [])},
                )
            )
            created.append(seg_id)

            for idx, st in enumerate(ev.get("states", []), start=1):
                st_text = st if isinstance(st, str) else _canonical_json(st)
                st_id = f"{seg_id}:state:{idx}"
                self.add_node(
                    HierarchyNode(
                        node_id=st_id,
                        modality="media",
                        level="state",
                        title=f"{record.get('title', record['id'])} [state {idx}]",
                        content=st_text,
                        parent_id=seg_id,
                        scope=scope,
                        repo=record.get("source_repo", ""),
                        version=record.get("source_commit", ""),
                        domain=domain,
                        license=record.get("license", ""),
                        product=record.get("product", ""),
                        provenance_status=provenance_status,
                        blob_sha=ev.get("source_blob_sha", record.get("blob_sha", "")),
                        path=record.get("path", ""),
                        metadata={"state_index": idx},
                    )
                )
                created.append(st_id)

        self.finalize_links()
        return created


def decompose_compound_query(query: str) -> list[str]:
    """Split a compound query into atomic subqueries when conjunctions/clauses appear."""
    cleaned = " ".join((query or "").strip().split())
    if not cleaned:
        return []

    # Split on explicit structural separators or strong conjunctions connecting clauses
    parts = re.split(
        r"\s*(?:;|(?:\s+(?:and|e|vs\.?|versus|bem\s+como|al[eé]m\s+de)\s+))\s*",
        cleaned,
        flags=re.IGNORECASE,
    )
    subqueries = [p.strip(" ?.,") for p in parts if p and len(p.strip(" ?.,")) >= 2]
    # Keep decomposition meaningful: avoid splitting a short 2-word noun phrase unless distinct clauses
    if len(subqueries) <= 1:
        return [cleaned]
    return list(dict.fromkeys(subqueries))


def _score_node_bm25_and_specificity(
    query: str,
    nodes: list[HierarchyNode],
) -> list[tuple[HierarchyNode, float, float]]:
    """Score candidate nodes using Okapi BM25 + specific-first bias."""
    if not nodes:
        return []
    exp = search_expansion.expand_query(query, max_tokens=8)
    q_terms = list(
        dict.fromkeys(
            [
                *federated_retrieval._tokenize_bm25(query),
                *[t for e in exp.get("expanded_terms", []) for t in federated_retrieval._tokenize_bm25(e)],
            ]
        )
    )
    docs = [f"{n.title} {n.content} {n.path} {n.domain}" for n in nodes]
    bm25_vals = federated_retrieval.compute_bm25_scores(q_terms, docs)

    max_bm = max(bm25_vals) if bm25_vals else 0.0
    scored: list[tuple[HierarchyNode, float, float]] = []
    for node, bm in zip(nodes, bm25_vals):
        if bm <= 0.0:
            continue
        norm_bm = (bm / max_bm) if max_bm > 0.0 else 0.0
        # Specific-first scoring: normalized lexical match + deterministic specificity tier bonus
        # Ensures leaf nodes (passage/member/state) rank before their containing sections when both match.
        spec_bonus = 0.5 * float(node.specificity)
        total = round(norm_bm + spec_bonus, 6)
        scored.append((node, total, bm))

    scored.sort(key=lambda item: (-item[1], -item[2], -item[0].specificity, item[0].node_id))
    return scored


def _recursive_expand(
    store: HierarchicalStore,
    seeds: list[tuple[HierarchyNode, float, float]],
    *,
    pre_filter: PreRankingFilter,
    depth_limit: int,
    expansion_policy: str,
    budget_tokens: int,
) -> dict[str, Any]:
    """Expand from specific seed nodes through parents, children, and references with cycle protection."""
    visited_set: set[str] = set()
    cycle_detections: list[dict[str, str]] = []
    filtered_during_expansion: list[dict[str, str]] = []
    ordered_results: list[dict[str, Any]] = []
    used_tokens = 0
    budget_truncated: list[str] = []

    queue: deque[tuple[str, int, str, list[str]]] = deque()
    for node, score, bm25_val in seeds:
        if node.node_id in visited_set:
            continue
        visited_set.add(node.node_id)
        item_dict = {
            **node.to_dict(),
            "depth": 0,
            "score": score,
            "bm25_score": bm25_val,
            "retrieval_reason": f"seed_specific_match(level={node.level}, bm25={bm25_val})",
            "lineage_path": [node.node_id],
        }
        tok = estimate_tokens(item_dict)
        if used_tokens + tok <= budget_tokens:
            ordered_results.append(item_dict)
            used_tokens += tok
            queue.append((node.node_id, 0, "seed", [node.node_id]))
        else:
            budget_truncated.append(node.node_id)

    if expansion_policy == "none" or depth_limit <= 0:
        return {
            "items": ordered_results,
            "visited_set": sorted(visited_set),
            "cycles_prevented": cycle_detections,
            "filtered_during_expansion": filtered_during_expansion,
            "budget_truncated": budget_truncated,
            "tokens_used": used_tokens,
        }

    while queue:
        cur_id, depth, _, path_so_far = queue.popleft()
        if depth >= depth_limit:
            continue
        cur_node = store.nodes.get(cur_id)
        if not cur_node:
            continue

        neighbors: list[tuple[str, str]] = []
        if expansion_policy in {"parents", "parents_and_refs", "full"} and cur_node.parent_id:
            neighbors.append((cur_node.parent_id, "parent_context"))
        if expansion_policy in {"children", "full"}:
            for cid in cur_node.children_ids:
                neighbors.append((cid, "child_detail"))
        if expansion_policy in {"parents_and_refs", "full"}:
            for rid in cur_node.references:
                neighbors.append((rid, "cross_reference"))
            for src_id, dst_id, rel in sorted(store.edges):
                if src_id == cur_id and rel in {"references", "evidenced_by", "decided_in"}:
                    neighbors.append((dst_id, rel))

        for next_id, reason_tag in neighbors:
            if next_id in path_so_far:
                cycle_detections.append({
                    "from": cur_id,
                    "to": next_id,
                    "relation": reason_tag,
                    "path": " -> ".join([*path_so_far, next_id]),
                })
                continue
            if next_id in visited_set:
                continue
            next_node = store.nodes.get(next_id)
            if next_node is None:
                continue

            # Re-apply strict pre-ranking filter during recursive expansion!
            allowed, rej_reason = pre_filter.allows(next_node)
            if not allowed:
                visited_set.add(next_id)
                filtered_during_expansion.append({"node_id": next_id, "reason": rej_reason})
                continue

            visited_set.add(next_id)
            new_path = [*path_so_far, next_id]
            item_dict = {
                **next_node.to_dict(),
                "depth": depth + 1,
                "score": round(max(0.05, 0.5 / float(depth + 1)), 4),
                "bm25_score": 0.0,
                "retrieval_reason": f"recursive_{reason_tag}(from={cur_id}, depth={depth + 1})",
                "lineage_path": new_path,
            }
            tok = estimate_tokens(item_dict)
            if used_tokens + tok <= budget_tokens:
                ordered_results.append(item_dict)
                used_tokens += tok
                queue.append((next_id, depth + 1, reason_tag, new_path))
            else:
                budget_truncated.append(next_id)

    return {
        "items": ordered_results,
        "visited_set": sorted(visited_set),
        "cycles_prevented": cycle_detections,
        "filtered_during_expansion": filtered_during_expansion,
        "budget_truncated": budget_truncated,
        "tokens_used": used_tokens,
    }


def retrieve_hierarchical(
    store: HierarchicalStore,
    query: str,
    *,
    pre_filter: PreRankingFilter | None = None,
    depth_limit: int = 2,
    expansion_policy: str = "parents_and_refs",
    budget_tokens: int = 2500,
    seed_limit: int = 4,
    decompose_compound: bool = True,
) -> dict[str, Any]:
    """Retrieve hierarchical context with pre-ranking filtering, specific-first seeding,
    and bounded recursive expansion.
    """
    if expansion_policy not in VALID_EXPANSION_POLICIES:
        raise ValueError(f"Unsupported expansion_policy {expansion_policy!r}")
    if depth_limit < 0 or depth_limit > 6:
        raise ValueError("depth_limit must be between 0 and 6")
    if budget_tokens < 64:
        raise ValueError("budget_tokens must be >= 64")

    pf = pre_filter or PreRankingFilter()
    clean_query, sanitized = domain_ontology.sanitize_untrusted_text(query, max_length=240)
    if not clean_query or clean_query == "[sanitized-untrusted-directive]":
        return {
            "schema_version": SCHEMA_VERSION,
            "query": clean_query,
            "status": "invalid-query",
            "subqueries": [],
            "results": [],
            "gaps": ["empty_or_sanitized_query"],
            "pre_filter_stats": {"total_nodes": len(store.nodes), "eligible_nodes": 0, "rejected_nodes": 0},
            "visited_set": [],
            "cycles_prevented": [],
            "tokens_used": 0,
            "budget_tokens": budget_tokens,
            "sanitized_query": sanitized,
        }

    # Step 1: Apply pre-ranking filters BEFORE candidate generation & scoring
    eligible_nodes: list[HierarchyNode] = []
    rejected_counts: dict[str, int] = defaultdict(int)
    for node in store.nodes.values():
        allowed, reason = pf.allows(node)
        if allowed:
            eligible_nodes.append(node)
        else:
            rejected_counts[reason] += 1

    # Step 2: Decompose compound queries if requested
    subqueries = decompose_compound_query(clean_query) if decompose_compound else [clean_query]
    per_subquery_budget = max(64, budget_tokens // max(1, len(subqueries)))

    combined_items: list[dict[str, Any]] = []
    seen_combined: set[str] = set()
    all_visited: set[str] = set()
    all_cycles: list[dict[str, str]] = []
    all_filtered_exp: list[dict[str, str]] = []
    all_truncated: list[str] = []
    subquery_summaries: list[dict[str, Any]] = []
    gaps: list[str] = []
    total_tokens = 0

    for subq in subqueries:
        scored_seeds = _score_node_bm25_and_specificity(subq, eligible_nodes)[:seed_limit]
        if not scored_seeds:
            gaps.append(f"no_evidence_for_subquery:{subq}")
            subquery_summaries.append({"subquery": subq, "seeds": 0, "retrieved": 0, "gap": True})
            continue

        remaining_budget = max(0, budget_tokens - total_tokens)
        sub_budget = min(per_subquery_budget, remaining_budget) if len(subqueries) > 1 else remaining_budget
        exp_res = _recursive_expand(
            store,
            scored_seeds,
            pre_filter=pf,
            depth_limit=depth_limit,
            expansion_policy=expansion_policy,
            budget_tokens=sub_budget if sub_budget > 0 else remaining_budget,
        )
        all_visited.update(exp_res["visited_set"])
        all_cycles.extend(exp_res["cycles_prevented"])
        all_filtered_exp.extend(exp_res["filtered_during_expansion"])
        all_truncated.extend(exp_res["budget_truncated"])

        sub_added = 0
        for item in exp_res["items"]:
            nid = item["node_id"]
            if nid in seen_combined:
                continue
            item_tok = estimate_tokens(item)
            if total_tokens + item_tok > budget_tokens:
                all_truncated.append(nid)
                continue
            item["matched_subquery"] = subq
            seen_combined.add(nid)
            combined_items.append(item)
            total_tokens += item_tok
            sub_added += 1

        subquery_summaries.append({
            "subquery": subq,
            "seeds": len(scored_seeds),
            "retrieved": sub_added,
            "gap": sub_added == 0,
        })

    if not combined_items and not gaps:
        gaps.append("no_matching_evidence_after_pre_filter")
    if all_truncated:
        gaps.append(f"budget_truncated:{len(set(all_truncated))}")

    return {
        "schema_version": SCHEMA_VERSION,
        "query": clean_query,
        "status": "ok" if combined_items else "no-evidence",
        "expansion_policy": expansion_policy,
        "depth_limit": depth_limit,
        "subqueries": subquery_summaries,
        "results": combined_items,
        "gaps": gaps,
        "pre_filter_stats": {
            "total_nodes": len(store.nodes),
            "eligible_nodes": len(eligible_nodes),
            "rejected_nodes": len(store.nodes) - len(eligible_nodes),
            "rejection_reasons": dict(sorted(rejected_counts.items())),
        },
        "visited_set": sorted(all_visited),
        "cycles_prevented": all_cycles,
        "filtered_during_expansion": all_filtered_exp,
        "budget_truncated": sorted(set(all_truncated)),
        "tokens_used": total_tokens,
        "budget_tokens": budget_tokens,
        "sanitized_query": sanitized,
    }


def retrieve_flat(
    store: HierarchicalStore,
    query: str,
    *,
    pre_filter: PreRankingFilter | None = None,
    limit: int = 4,
    budget_tokens: int = 2500,
) -> dict[str, Any]:
    """Baseline flat retrieval (no hierarchy traversal, no parent/reference expansion, no decomposition)."""
    return retrieve_hierarchical(
        store,
        query,
        pre_filter=pre_filter,
        depth_limit=0,
        expansion_policy="none",
        budget_tokens=budget_tokens,
        seed_limit=limit,
        decompose_compound=False,
    )


def build_benchmark_store() -> tuple[HierarchicalStore, list[dict[str, Any]]]:
    """Build a deterministic multidomain hierarchical corpus (business rules, code, ADRs, learning, ops)
    and gold evaluation queries comparing flat vs recursive retrieval.
    """
    store = HierarchicalStore()

    # 1. Business rules & concursos (Document > Section > Subsection > Passage)
    business_md = (
        "# Regras de Negocio do Simulado\n\n"
        "## Modo Prova e Gabarito\n\n"
        "### Restricao de Exibicao de Gabarito\n\n"
        "Durante o modo prova cronometrado, o gabarito comentado fica oculto ate a submissao final.\n\n"
        "Apos a entrega do simulado, o sistema libera a correcao detalhada por banca e disciplina.\n"
    )
    store.add_document_from_markdown(
        business_md,
        doc_id="doc:regras-simulado",
        path="docs/produto/regras-simulado.md",
        scope="public",
        repo="ianmaciel7/exams-app",
        ref="refs/heads/main",
        version="1.0.0",
        domain="concursos",
        license_name="MIT",
    )

    # 2. Architectural Decision (Document > Section > Passage) linked to Code
    adr_md = (
        "# ADR-0012 Desacoplamento de Abas e Sidebar\n\n"
        "## Decisao\n\n"
        "Manter abas fixadas em AppHeaderTabs e entidades fixadas em AppSidebarOverview com persistencia isolada.\n\n"
        "## Consequencias\n\n"
        "Evita conflito de estado entre tabs abertas e atalhos globais na barra lateral.\n"
    )
    store.add_document_from_markdown(
        adr_md,
        doc_id="doc:adr-0012",
        path="docs/adr/0012-abas-sidebar.md",
        scope="public",
        repo="ianmaciel7/exams-app",
        ref="refs/heads/main",
        version="1.0.0",
        domain="arquitetura-tecnica",
        license_name="MIT",
    )

    # 3. Code (Module > Symbol > Member)
    tsx_code = (
        "export class AppHeaderTabs {\n"
        "  togglePin(tabId: string) {\n"
        "    return { tabId, pinned: true };\n"
        "  }\n"
        "}\n"
        "export class FSRSScheduler {\n"
        "  computeNextInterval(stability: number, difficulty: number) {\n"
        "    return Math.max(1, Math.round(stability * (11 - difficulty)));\n"
        "  }\n"
        "}\n"
    )
    store.add_code_from_source(
        tsx_code,
        module_id="code:workspace-core",
        path="src/workspace/core.ts",
        language="ts",
        scope="public",
        repo="ianmaciel7/exams-app",
        ref="refs/heads/main",
        version="1.0.0",
        domain="aprendizagem",
        license_name="MIT",
    )

    # 4. Operations / Backup runbook (Document > Section > Passage)
    ops_md = (
        "# Runbook de Backup e Restauracao\n\n"
        "## Verificacao de Integridade\n\n"
        "Validar SHA-256 dos pacotes criptografados antes de autorizar limpeza de branches.\n"
    )
    store.add_document_from_markdown(
        ops_md,
        doc_id="doc:ops-backup",
        path="docs/ops/backup-runbook.md",
        scope="public",
        repo="ianmaciel7/exams-app",
        ref="refs/heads/main",
        version="1.0.0",
        domain="operacoes",
        license_name="MIT",
    )

    # Cross-reference from AppHeaderTabs member to ADR-0012 decision
    for nid in list(store.nodes):
        if "togglePin" in nid:
            store.add_reference(nid, "doc:adr-0012", relation="decided_in")
            # Also link back to test cycle protection
            store.add_reference("doc:adr-0012", nid, relation="references")

    gold_queries = [
        {
            "id": "q_business_rule",
            "category": "business_rule",
            "query": "Quando o gabarito comentado fica oculto?",
            "expected_nodes": ["doc:regras-simulado:sec-0003:p1", "doc:regras-simulado:sec-0003"],
        },
        {
            "id": "q_code_and_decision",
            "category": "code_and_decision",
            "query": "togglePin",
            "expected_nodes": [
                "code:workspace-core:typescript:AppHeaderTabs.togglePin",
                "code:workspace-core:typescript:AppHeaderTabs",
                "doc:adr-0012",
            ],
        },
        {
            "id": "q_learning_fsrs",
            "category": "learning",
            "query": "computeNextInterval stability difficulty",
            "expected_nodes": [
                "code:workspace-core:typescript:FSRSScheduler.computeNextInterval",
                "code:workspace-core:typescript:FSRSScheduler",
            ],
        },
        {
            "id": "q_compound_ops_and_rules",
            "category": "operations",
            "query": "Validar SHA-256 dos pacotes e gabarito comentado oculto",
            "expected_nodes": ["doc:ops-backup:sec-0002:p1", "doc:regras-simulado:sec-0003:p1"],
        },
    ]
    return store, gold_queries


def compare_flat_vs_recursive(
    store: HierarchicalStore | None = None,
    queries: list[dict[str, Any]] | None = None,
    *,
    budget_tokens: int = 2500,
) -> dict[str, Any]:
    """Compare flat retrieval vs hierarchical recursive retrieval on recall and structural coverage."""
    if store is None or queries is None:
        store, queries = build_benchmark_store()

    pf = PreRankingFilter(authorized=False, allowed_scopes=("public",))
    flat_recalls: list[float] = []
    rec_recalls: list[float] = []
    per_query: list[dict[str, Any]] = []

    for q in queries:
        expected = set(q["expected_nodes"])
        flat_res = retrieve_flat(store, q["query"], pre_filter=pf, limit=2, budget_tokens=budget_tokens)
        rec_res = retrieve_hierarchical(
            store, q["query"], pre_filter=pf, depth_limit=2, expansion_policy="parents_and_refs", budget_tokens=budget_tokens, seed_limit=2
        )

        flat_ids = {r["node_id"] for r in flat_res["results"]}
        rec_ids = {r["node_id"] for r in rec_res["results"]}

        flat_recall = len(expected & flat_ids) / float(len(expected))
        rec_recall = len(expected & rec_ids) / float(len(expected))
        flat_recalls.append(flat_recall)
        rec_recalls.append(rec_recall)

        per_query.append({
            "id": q["id"],
            "category": q["category"],
            "expected_count": len(expected),
            "flat_recall": round(flat_recall, 4),
            "recursive_recall": round(rec_recall, 4),
            "flat_retrieved": len(flat_ids),
            "recursive_retrieved": len(rec_ids),
            "cycles_prevented": len(rec_res["cycles_prevented"]),
        })

    n = float(len(queries)) or 1.0
    return {
        "schema_version": SCHEMA_VERSION,
        "queries_evaluated": len(queries),
        "flat_mean_recall": round(sum(flat_recalls) / n, 4),
        "recursive_mean_recall": round(sum(rec_recalls) / n, 4),
        "recall_gain": round((sum(rec_recalls) - sum(flat_recalls)) / n, 4),
        "per_query": per_query,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--benchmark", action="store_true", help="Compare flat vs recursive retrieval")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--budget-tokens", type=int, default=2500)
    args = parser.parse_args(argv)

    if args.benchmark or not args.query:
        out = compare_flat_vs_recursive(budget_tokens=args.budget_tokens)
    else:
        store, _ = build_benchmark_store()
        out = retrieve_hierarchical(
            store, args.query, depth_limit=args.depth, budget_tokens=args.budget_tokens
        )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
