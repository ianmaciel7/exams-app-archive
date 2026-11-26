#!/usr/bin/env python3
"""Unified multidomain federated retrieval over public research and authenticated archive (#81).

Provides a single interface for discovery, query routing, expansion, ranking,
and budgeted fetch across heterogeneous archive subsystems:
  - Public concepts & packs (`scripts/concept_packs.py`, `scripts/archive_context.py`, `scripts/research_index.py`)
  - Multidomain ontology & contextual rules (`scripts/domain_ontology.py`)
  - Factual decisions & glossary (`scripts/knowledge_indexer.py`)
  - Multi-layer evidence graph (`scripts/evidence_graph.py`)
  - Structural AST code chunks & motion contracts (`scripts/ast_chunker.py`)
  - Historical image catalog & visual evidence (`scripts/image_catalog.py`, `scripts/visual_reference_index.py`)
  - Bilingual PT<->EN expansion (`scripts/search_expansion.py`)

Design guarantees:
  - Strict scope isolation BEFORE search and expansion:
      * scope='public' NEVER touches private/historical indexes, bundles, or private ADRs.
      * scope='authenticated_archive' requires explicit authorization (`authorized=True`)
        and verified provenance pins (`repo`, `ref`, `source_sha`, `expected_index_checksum` when specified).
  - Intent-based routing across domains and modalities.
  - Reciprocal Rank Fusion (RRF) combined with deterministic textual BM25 scoring
    plus evidence-type diversity round-robin/interleaving (`code`, `decision`, `requirement`, `test`, `media`, `pattern`, `source`, `concept`).
  - Exact blob deduplication (`blob_sha` / `record_sha256` / `doc_sha256`) retaining all source occurrences.
  - Version/SHA-1/SHA-256 pinning and strict token/byte budget accounting.
  - Auditable ledger of `sources_consulted`, `sources_omitted`, and `sources_unavailable`.
  - Pure Python standard library only; zero network calls; zero Unicode emojis.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import archive_context  # noqa: E402
import ast_chunker  # noqa: E402
import concept_packs  # noqa: E402
import domain_ontology  # noqa: E402
import evidence_graph  # noqa: E402
import image_catalog  # noqa: E402
import knowledge_indexer  # noqa: E402
import research_index  # noqa: E402
import search_expansion  # noqa: E402
import public_lexical_search  # noqa: E402
import source_registry  # noqa: E402

SCHEMA_VERSION = 1
VALID_SCOPES = frozenset({"public", "authenticated_archive"})
VALID_INTENTS = frozenset({
    "auto",
    "concept",
    "code",
    "decision",
    "requirement",
    "test",
    "media",
    "graph",
    "mixed",
})
EVIDENCE_TYPES = (
    "code",
    "decision",
    "requirement",
    "test",
    "media",
    "pattern",
    "source",
    "concept",
)
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")
GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "for", "how", "what", "does", "is",
    "with", "in", "do", "on", "o", "os", "as", "de", "da", "das", "dos", "e", "ou",
    "para", "como", "qual", "que", "em", "um", "uma", "por", "com", "sem", "no", "na",
})

# Intent detection keyword patterns (pure deterministic lexicons, zero LLM)
_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "decision": (
        "adr", "decisao", "decisoes", "decision", "decisions", "rationale", "justificativa",
        "motivo", "why", "porque", "superseded", "arquitetura", "architecture", "rfc",
    ),
    "code": (
        "codigo", "code", "component", "componente", "function", "funcao", "class", "classe",
        "symbol", "simbolo", "ast", "hook", "handler", "tsx", "python", "ts", "impl",
        "implementacao", "implementation", "refatoracao", "refactor", "estado", "state",
    ),
    "requirement": (
        "requisito", "requisitos", "requirement", "requirements", "prd", "spec", "specs",
        "contrato", "contract", "aceite", "acceptance", "regra", "regras", "rule", "rules",
        "escopo", "scope", "edital", "simulado", "questao", "fsrs",
    ),
    "test": (
        "teste", "testes", "test", "tests", "testing", "regressao", "regression", "qa",
        "smoke", "benchmark", "coverage", "cobertura", "validacao", "verify", "assert",
    ),
    "media": (
        "imagem", "imagens", "image", "images", "screenshot", "screenshots", "captura",
        "capturas", "gif", "video", "media", "midia", "visual", "frame", "frames",
        "animation", "animacao", "motion", "svg", "png", "mp4",
    ),
    "graph": (
        "grafo", "graph", "relacao", "relacoes", "relationship", "dependencia", "dependencies",
        "neighborhood", "vizinhanca", "impacto", "impact", "lineage", "traceability",
    ),
    "concept": (
        "conceito", "conceitos", "concept", "concepts", "glossario", "glossary", "ontologia",
        "ontology", "definicao", "definition", "termo", "term", "significado", "meaning",
    ),
}


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: Any) -> str:
    return sha256_text(_canonical_json(obj))


def estimate_tokens(obj: Any) -> int:
    raw = obj if isinstance(obj, str) else _canonical_json(obj)
    return (len(raw) + 3) // 4 if raw else 0


def utf8_bytes(obj: Any) -> int:
    raw = obj if isinstance(obj, str) else _canonical_json(obj)
    return len(raw.encode("utf-8"))


def _tokenize_bm25(text: str) -> list[str]:
    norm = search_expansion.normalize_text(str(text or ""))
    tokens = re.findall(r"[a-z0-9]+", norm)
    return [t for t in tokens if t and t not in STOPWORDS]


def compute_bm25_scores(
    query_terms: list[str],
    documents: list[str],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """Compute deterministic Okapi BM25 scores over a list of document strings."""
    n_docs = len(documents)
    if n_docs == 0 or not query_terms:
        return [0.0] * n_docs

    doc_tokens = [_tokenize_bm25(doc) for doc in documents]
    doc_lens = [len(toks) for toks in doc_tokens]
    avgdl = sum(doc_lens) / float(n_docs) if n_docs else 1.0
    if avgdl <= 0.0:
        avgdl = 1.0

    # Document frequency for query terms
    unique_q = list(dict.fromkeys(query_terms))
    df: dict[str, int] = {term: 0 for term in unique_q}
    tfs: list[Counter[str]] = []
    for toks in doc_tokens:
        counts = Counter(toks)
        tfs.append(counts)
        for term in unique_q:
            if counts.get(term, 0) > 0:
                df[term] += 1

    scores: list[float] = []
    for idx, counts in enumerate(tfs):
        dl = doc_lens[idx]
        score = 0.0
        for term in unique_q:
            tf = counts.get(term, 0)
            if tf <= 0:
                continue
            n_q = df[term]
            idf = math.log(((n_docs - n_q + 0.5) / (n_q + 0.5)) + 1.0)
            denom = tf + k1 * (1.0 - b + b * (dl / avgdl))
            score += idf * ((tf * (k1 + 1.0)) / denom)
        scores.append(round(score, 6))
    return scores


def reciprocal_rank_fusion(
    ranked_lists: dict[str, list[str]],
    *,
    rrf_k: int = 60,
    weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """Fuse multiple source-specific ranked ID lists using Reciprocal Rank Fusion.

    RRF(d) = sum_s weight_s * (1.0 / (rrf_k + rank_s(d)))
    where rank_s(d) is 1-based.
    """
    fused: dict[str, float] = defaultdict(float)
    w_map = weights or {}
    for source_name, id_list in ranked_lists.items():
        w = float(w_map.get(source_name, 1.0))
        seen_in_source: set[str] = set()
        rank_pos = 1
        for item_id in id_list:
            if item_id in seen_in_source:
                continue
            seen_in_source.add(item_id)
            fused[item_id] += w * (1.0 / float(rrf_k + rank_pos))
            rank_pos += 1
    return {k: round(v, 8) for k, v in fused.items()}


def detect_intent(query: str, explicit_intent: str | None = None) -> dict[str, Any]:
    """Classify query intent deterministically across retrieval channels."""
    if explicit_intent is not None:
        cleaned = explicit_intent.strip().lower()
        if cleaned not in VALID_INTENTS:
            raise ValueError(f"Unsupported intent {explicit_intent!r}; expected one of {sorted(VALID_INTENTS)}")
        if cleaned != "auto":
            return {
                "primary": cleaned,
                "matched_intents": [cleaned],
                "scores": {cleaned: 1.0},
                "is_explicit": True,
                "is_compound": False,
            }

    tokens = set(_tokenize_bm25(query))
    norm_q = search_expansion.normalize_text(query)
    scores: dict[str, int] = {}
    for intent_name, kw_tuple in _INTENT_KEYWORDS.items():
        hits = 0
        for kw in kw_tuple:
            if kw in tokens or (len(kw) >= 4 and f" {kw} " in f" {norm_q} "):
                hits += 1
        if hits > 0:
            scores[intent_name] = hits

    if not scores:
        return {
            "primary": "mixed",
            "matched_intents": ["concept", "code", "decision", "requirement", "media"],
            "scores": {},
            "is_explicit": False,
            "is_compound": False,
        }

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    primary = ranked[0][0]
    matched = [name for name, _ in ranked]
    return {
        "primary": primary,
        "matched_intents": matched,
        "scores": {k: float(v) for k, v in ranked},
        "is_explicit": False,
        "is_compound": len(matched) > 1,
    }


def _select_channels_for_intent(intent_info: dict[str, Any], scope: str) -> list[str]:
    """Select which retrieval engines/channels to consult based on intent and scope."""
    matched = set(intent_info.get("matched_intents", []))
    primary = intent_info.get("primary", "mixed")

    if scope == "public":
        # Strict public channels only: never include private/historical SQLite/bundles
        channels = ["ontology", "concept_packs", "public_research", "public_visual"]
        if intent_info.get("scores") and ("code" in matched or primary in {"code", "test", "requirement"}):
            channels.append("public_ast_code")
        return channels

    # authenticated_archive: can access public concept/ontology projections plus authenticated channels
    channels = ["ontology", "knowledge_decisions", "evidence_graph", "ast_code", "image_catalog", "content_archive"]
    if primary == "decision":
        channels = ["knowledge_decisions", "evidence_graph", "ontology", "content_archive"]
    elif primary == "code":
        channels = ["ast_code", "evidence_graph", "content_archive", "ontology", "knowledge_decisions"]
    elif primary == "media":
        channels = ["image_catalog", "evidence_graph", "ontology", "public_visual"]
    elif primary == "requirement":
        channels = ["knowledge_decisions", "ontology", "ast_code", "evidence_graph", "content_archive"]
    elif primary == "test":
        channels = ["ast_code", "content_archive", "evidence_graph", "knowledge_decisions"]
    elif primary == "graph":
        channels = ["evidence_graph", "knowledge_decisions", "ast_code", "ontology"]
    elif primary == "concept":
        channels = ["ontology", "knowledge_decisions", "concept_packs", "evidence_graph"]
    return channels


@dataclass
class SourceAuditEntry:
    source_id: str
    channel: str
    scope: str
    status: str  # "consulted" | "omitted" | "unavailable"
    reason: str
    hits: int = 0
    pinned_version: str = ""
    sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "channel": self.channel,
            "scope": self.scope,
            "status": self.status,
            "reason": self.reason,
            "hits": self.hits,
            "pinned_version": self.pinned_version,
            "sha256": self.sha256,
        }


@dataclass
class AuthenticatedArchiveContext:
    """Explicit authorization and verified provenance context for authenticated_archive queries."""

    authorized: bool = False
    actor: str = ""
    allowed_repos: tuple[str, ...] = ()
    pinned_repo: str | None = None
    pinned_ref: str | None = None
    pinned_source_sha: str | None = None
    expected_index_checksum: str | None = None
    actual_index_checksum: str | None = None
    provenance_verified: bool = False
    knowledge_conn: sqlite3.Connection | None = None
    evidence_conn: sqlite3.Connection | None = None
    content_conn: sqlite3.Connection | None = None
    ast_chunks: list[dict[str, Any]] = field(default_factory=list)
    image_records: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    verified_only: bool = True

    def validate(self) -> list[str]:
        """Return list of authorization/provenance failure reasons (empty if valid)."""
        errors: list[str] = []
        if not self.authorized:
            errors.append("authorization_required: authenticated_archive requires authorized=True")
        if self.pinned_source_sha is not None and not GIT_SHA_RE.fullmatch(self.pinned_source_sha):
            errors.append("invalid_pinned_source_sha: expected 40-64 char hex SHA")
        if self.expected_index_checksum is not None:
            if not SHA256_RE.fullmatch(self.expected_index_checksum):
                errors.append("invalid_expected_index_checksum: expected 64-char hex SHA-256")
            elif self.actual_index_checksum != self.expected_index_checksum:
                errors.append("index_digest_mismatch: actual index checksum does not match expected_index_checksum")
        if self.pinned_repo and self.allowed_repos and self.pinned_repo not in self.allowed_repos:
            errors.append("repo_not_allowed: pinned repository outside authorized set")
        if not self.provenance_verified and not (
            self.expected_index_checksum and self.actual_index_checksum == self.expected_index_checksum
            and SHA256_RE.fullmatch(self.expected_index_checksum)
        ):
            errors.append("unverified_provenance: requires trusted adapter attestation or matching index digest")
        return errors


def _matches_archive_pins(ctx, repo, ref, commit):
    """Missing metadata cannot satisfy an explicit authorization or revision pin."""
    return not (
        (ctx.allowed_repos and repo not in ctx.allowed_repos)
        or (ctx.pinned_repo and repo != ctx.pinned_repo)
        or (ctx.pinned_ref and ref != ctx.pinned_ref)
        or (ctx.pinned_source_sha and commit != ctx.pinned_source_sha)
    )


def _normalize_hit(
    *,
    hit_id: str,
    evidence_type: str,
    source_channel: str,
    source_id: str,
    scope: str,
    title: str,
    snippet: str,
    raw_score: float,
    blob_sha: str = "",
    record_sha256: str = "",
    repo: str = "",
    ref: str = "",
    commit_sha: str = "",
    path: str = "",
    version: str = "",
    license_name: str = "",
    domain: str = "",
    provenance_status: str = "verified",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_title, t_sanitized = domain_ontology.sanitize_untrusted_text(title, max_length=240)
    clean_snippet, s_sanitized = domain_ontology.sanitize_untrusted_text(snippet, max_length=900)
    identity_sha = blob_sha or record_sha256 or sha256_text(f"{source_channel}|{path}|{clean_snippet}")
    occurrence = {
        "hit_id": hit_id,
        "source_channel": source_channel,
        "source_id": source_id,
        "repo": repo,
        "ref": ref,
        "commit_sha": commit_sha,
        "path": path,
        "blob_sha": blob_sha,
        "record_sha256": record_sha256,
        "version": version,
    }
    return {
        "id": hit_id,
        "evidence_type": evidence_type,
        "source_channel": source_channel,
        "source_id": source_id,
        "scope": scope,
        "title": clean_title,
        "snippet": clean_snippet,
        "raw_score": float(raw_score),
        "domain": domain,
        "provenance": {
            "repo": repo,
            "ref": ref,
            "commit_sha": commit_sha,
            "path": path,
            "blob_sha": blob_sha,
            "record_sha256": record_sha256,
            "version": version,
            "license": license_name,
            "provenance_status": provenance_status,
            "sanitized": t_sanitized or s_sanitized,
        },
        "dedup_key": identity_sha,
        "occurrences": [occurrence],
        "metadata": metadata or {},
    }


def _deduplicate_blobs_preserving_occurrences(hits: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Deduplicate hits with identical exact blob/content SHA while retaining every occurrence."""
    by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    dedup_count = 0

    for hit in hits:
        bsha = hit["provenance"].get("blob_sha") or hit["provenance"].get("record_sha256")
        urls = hit.get("metadata", {}).get("source_urls", [])
        # Source entries are pointers, not independent evidence just because
        # the same URL occurs in multiple catalogs. Preserve exact URL identity
        # (including fragment/query), do not merge distinct patterns or media.
        if hit["scope"] == "public" and hit["evidence_type"] == "source" and len(urls) == 1:
            u = urlsplit(urls[0])
            canonical = urlunsplit((u.scheme.lower(), u.netloc.lower(), u.path or "/", u.query, u.fragment))
            key = "public::source-url::" + canonical
        elif bsha and hit["source_channel"] in {"public_ast_code", "ast_code"}:
            # File identity is not chunk identity. Keep different line spans.
            meta = hit.get("metadata", {})
            p = hit["provenance"]
            key = f"{hit['scope']}::{hit['evidence_type']}::{bsha}::{p.get('record_sha256')}::{meta.get('start_line')}::{meta.get('end_line')}"
        elif bsha:
            key = f"{hit['scope']}::{hit['evidence_type']}::{bsha}"
        else:
            key = f"{hit['scope']}::id::{hit['id']}"

        if key not in by_key:
            copied = dict(hit)
            copied["occurrences"] = list(hit.get("occurrences", []))
            by_key[key] = copied
            order.append(key)
        else:
            dedup_count += 1
            existing = by_key[key]
            occurrences = existing["occurrences"] + list(hit.get("occurrences", []))
            # The representative's title, snippet, metadata and provenance must
            # come from the same occurrence. Keep other pointers intact.
            if hit["raw_score"] > existing["raw_score"]:
                by_key[key] = {**hit, "occurrences": occurrences}
            else:
                existing["occurrences"] = occurrences

    return [by_key[k] for k in order], dedup_count


def _search_ontology(
    query: str,
    *,
    scope: str,
    domain: str | None,
    ontology: domain_ontology.DomainOntology,
) -> tuple[list[dict[str, Any]], SourceAuditEntry]:
    ontology_scope = "public" if scope == "public" else None
    res = ontology.resolve_query(query, domain=domain, scope=ontology_scope, limit=8, min_confidence=0.60)
    hits: list[dict[str, Any]] = []
    for cand in res.get("candidates", []):
        cid = cand["canonical_id"]
        c_scope = cand.get("scope", "public")
        if scope == "public" and c_scope != "public":
            continue
        snippet_parts = [
            f"{cand.get('en', '')} / {cand.get('pt', '')}",
            f"Domain: {cand.get('domain', '')}",
        ]
        if cand.get("properties"):
            snippet_parts.append("Properties: " + ", ".join(cand["properties"][:5]))
        if cand.get("behaviors"):
            snippet_parts.append("Behaviors: " + ", ".join(cand["behaviors"][:5]))
        rec_sha = sha256_obj(cand)
        hits.append(
            _normalize_hit(
                hit_id=f"ontology:{cid}",
                evidence_type="concept",
                source_channel="ontology",
                source_id="config/knowledge-concepts.json",
                scope=c_scope,
                title=f"{cid}: {cand.get('en', cid)}",
                snippet=" | ".join(snippet_parts),
                raw_score=float(cand.get("confidence", 0.7)),
                record_sha256=rec_sha,
                path="scripts/domain_ontology.py",
                version=ontology.version,
                license_name="MIT",
                domain=cand.get("domain", ""),
                provenance_status="verified",
                metadata={
                    "canonical_id": cid,
                    "context_key": cand.get("context_key"),
                    "match_type": cand.get("match_type"),
                    "breadcrumbs": cand.get("breadcrumbs", []),
                    "ambiguous_with": cand.get("ambiguous_with", []),
                    "conflicts_with": cand.get("conflicts_with", []),
                },
            )
        )
    audit = SourceAuditEntry(
        source_id="domain_ontology",
        channel="ontology",
        scope=scope,
        status="consulted",
        reason="Intent-matched multidomain ontology resolution.",
        hits=len(hits),
        pinned_version=ontology.version,
        sha256=sha256_text(ontology.version),
    )
    return hits, audit


def _search_public_research_and_concepts(
    query: str,
    *,
    records: list[dict[str, Any]],
    taxonomy: dict[str, Any],
    snapshot_rev: str,
    product: str | None = None,
) -> tuple[list[dict[str, Any]], list[SourceAuditEntry]]:
    """Consult ONLY public research catalogs and concept packs."""
    hits: list[dict[str, Any]] = []
    audits: list[SourceAuditEntry] = []

    # 1. Concept packs resolution
    catalog, groups = concept_packs.group_records(records, taxonomy)
    matched_concepts = concept_packs.resolve(query, catalog)
    pack_hits = 0
    if matched_concepts:
        pack_res = concept_packs.build_pack(query, records, taxonomy, limit=12)
        for pack in pack_res.get("packs", []):
            cid = pack["concept"]["id"]
            for ev in pack.get("evidence", []):
                kind = ev["kind"]
                ev_type = "media" if kind == "visual" else ("pattern" if kind == "pattern" else "source")
                for occ in ev.get("occurrences", []):
                    if product and concept_packs.norm(occ.get("product") or "") != concept_packs.norm(product):
                        continue
                    stmts = occ.get("catalog_statements", {})
                    stmt_text = "; ".join(f"{k}: {v}" for k, v in stmts.items()) or occ.get("title", "")
                    ptr = occ.get("source_pointer", {})
                    hits.append(
                        _normalize_hit(
                            hit_id=f"concept_pack:{cid}:{occ['id']}",
                            evidence_type=ev_type,
                            source_channel="concept_packs",
                            source_id=occ.get("catalog_path", "docs/references"),
                            scope="public",
                            title=occ.get("title", occ["id"]),
                            snippet=stmt_text,
                            raw_score=1.0 if occ.get("classification") == "curated" else 0.75,
                            blob_sha=ptr.get("blob_sha", "") or ev.get("blob_sha") or "",
                            record_sha256=occ.get("record_sha256", ""),
                            repo=ptr.get("source_repo", ""),
                            commit_sha=ptr.get("source_commit", ""),
                            path=ptr.get("source_path") or ptr.get("path") or occ.get("catalog_path", ""),
                            version=snapshot_rev[:16],
                            license_name=occ.get("license") or "",
                            domain="referencias-externas",
                            provenance_status="verified" if occ.get("availability") in {"documented", "archived-blob-verified"} else "unverified",
                            metadata={"concept_id": cid, "classification": occ.get("classification"), "product": occ.get("product"),
                                      "catalog_path": occ.get("catalog_path"), "catalog_sha256": occ.get("catalog_sha256"),
                                      "record_pointer": occ.get("record_pointer"), "projection_sha256": occ.get("projection_sha256"),
                                      "source_urls": occ.get("sources", [])},
                        )
                    )
                    pack_hits += 1

    audits.append(
        SourceAuditEntry(
            source_id="concept_packs",
            channel="concept_packs",
            scope="public",
            status="consulted",
            reason="Public taxonomy concept pack lookup.",
            hits=pack_hits,
            pinned_version=snapshot_rev[:16],
            sha256=snapshot_rev,
        )
    )

    # 2. Field-weighted natural-language ranking; no fixture labels, URL metadata,
    # or per-query expansion fragments treated as independent queries.
    ranked = public_lexical_search.ranked(query, records, product=product, limit=40)
    res_rows = [row for row, _ in ranked]
    lexical_scores = {row["id"]: score for row, score in ranked}
    highest = max(lexical_scores.values(), default=1.0)

    pub_hits = 0
    for idx, row in enumerate(res_rows):
        rec = row.get("record", {})
        kind = row.get("kind", "source")
        ev_type = "media" if kind == "visual" else ("pattern" if kind == "pattern" else "source")
        body_parts = []
        for k in ("definition", "purpose", "anatomy", "behavior", "guardrail", "description", "summary", "principle", "acceptance", "acceptance_tests", "limits", "deliverable", "classification"):
            val = rec.get(k)
            if isinstance(val, str) and val:
                body_parts.append(f"{k}: {val}")
        snippet = "; ".join(body_parts) or row.get("title", "")
        hits.append(
            _normalize_hit(
                hit_id=f"research:{row['id']}",
                evidence_type=ev_type,
                source_channel="public_research",
                source_id=row.get("catalog_path", "docs/references"),
                scope="public",
                title=row.get("title", row["id"]),
                snippet=snippet,
                raw_score=lexical_scores[row["id"]] / highest,
                blob_sha=rec.get("blob_sha", "") if kind == "visual" else "",
                record_sha256=row.get("record_sha256", ""),
                repo=rec.get("source_repo", ""),
                commit_sha=rec.get("source_commit", ""),
                path=rec.get("source_path") or rec.get("path") or row.get("catalog_path", ""),
                version=snapshot_rev[:16],
                license_name=row.get("license") or "",
                domain=rec.get("domain") or "referencias-externas",
                provenance_status="verified" if row.get("availability") in {"documented", "archived-blob-verified"} else "unverified",
                metadata={"catalog": row.get("catalog"), "record_id": row.get("id"), "source_urls": row.get("sources", []), "product": row.get("product"), "availability": row.get("availability"), "catalog_sha256": row.get("catalog_sha256"), "record_pointer": row.get("record_pointer"), "projection_sha256": row.get("projection_sha256")},
            )
        )
        pub_hits += 1

    audits.append(
        SourceAuditEntry(
            source_id="research_index",
            channel="public_research",
            scope="public",
            status="consulted",
            reason="Public approved research catalog field-weighted lexical search.",
            hits=pub_hits,
            pinned_version=snapshot_rev[:16],
            sha256=snapshot_rev,
        )
    )
    return hits, audits


def _public_git_pin(root, rel, raw):
    """Pin local bytes to the actual checkout, without claiming a remote branch."""
    blob = hashlib.sha1(f"blob {len(raw)}\x00".encode("ascii") + raw).hexdigest()
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, check=True, timeout=5).stdout.decode("ascii").strip()
    try:
        commit = git("rev-parse", "--verify", "HEAD^{commit}")
        committed = git("rev-parse", "--verify", commit + ":" + rel)
        if committed == blob:
            return commit, blob, "verified"
    except (OSError, subprocess.SubprocessError, UnicodeError):
        pass
    return "", blob, "local-unpinned"


def _search_public_ast_code(
    query: str,
    *,
    paths: list[Path] | None = None,
) -> tuple[list[dict[str, Any]], SourceAuditEntry]:
    """Search public repository scripts/tests via AST chunker (no private bundles)."""
    # Explicit public code corpus. Never accept arbitrary local files, private
    # paths, evaluation runners, fixture labels, or symlinks escaping the root.
    approved = (
        "archive_context.py", "archive_index.py", "ast_chunker.py",
        "component_catalog.py", "concept_packs.py", "domain_ontology.py",
        "evidence_graph.py", "federated_retrieval.py", "graph_linker.py",
        "image_catalog.py", "public_lexical_search.py", "research_index.py",
        "search_expansion.py", "source_registry.py", "visual_reference_index.py",
    )
    approved_paths = {ROOT_DIR / "scripts" / name for name in approved}
    if paths is None:
        target_files = sorted(approved_paths)
    else:
        # Check lexical path and resolved path before opening any file.
        target_files = []
        for path in paths:
            candidate = Path(path)
            if not candidate.is_absolute():
                candidate = ROOT_DIR / candidate
            if candidate in approved_paths and candidate.resolve() == candidate:
                target_files.append(candidate)
    target_files = [p for p in target_files if p.resolve() == p]

    exp = search_expansion.expand_query(query, max_tokens=6)
    terms = set(_tokenize_bm25(query))
    for t in exp.get("expanded_terms", []):
        terms.update(_tokenize_bm25(t))

    hits: list[dict[str, Any]] = []
    for fpath in target_files:
        if not fpath.is_file():
            continue
        rel = fpath.relative_to(ROOT_DIR).as_posix() if fpath.is_relative_to(ROOT_DIR) else fpath.name
        try:
            raw = fpath.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lang = ast_chunker.normalize_language(fpath.suffix)
        commit_sha, bsha, provenance_status = _public_git_pin(ROOT_DIR, rel, raw)
        chunks = ast_chunker.chunk_code(text, language=lang, blob_sha=bsha)
        for ch in chunks:
            ch_tokens = set(_tokenize_bm25(f"{ch.name} {ch.parent_context} {ch.content}"))
            overlap = len(terms & ch_tokens)
            if overlap == 0:
                continue
            ev_type = "test" if rel.startswith("tests/") or "test_" in ch.name else "code"
            hits.append(
                _normalize_hit(
                    hit_id=f"ast:{rel}:{ch.symbol_id or ch.chunk_index}",
                    evidence_type=ev_type,
                    source_channel="public_ast_code",
                    source_id="local.code-and-tests",
                    scope="public",
                    title=f"{rel} :: {ch.name} ({ch.node_type})",
                    snippet=ch.content[:500],
                    raw_score=float(overlap) / max(1.0, float(len(terms))),
                    blob_sha=ch.blob_sha,
                    record_sha256=sha256_text(ch.content),
                    repo="ianmaciel7/exams-app-archive",
                    ref=commit_sha,
                    commit_sha=commit_sha,
                    path=rel,
                    version=ch.extractor_version,
                    license_name="MIT",
                    domain="qualidade" if ev_type == "test" else "engenharia",
                    provenance_status=provenance_status,
                    metadata={
                        "node_type": ch.node_type,
                        "symbol_id": ch.symbol_id,
                        "parent_context": ch.parent_context,
                        "start_line": ch.start_line,
                        "end_line": ch.end_line,
                    },
                )
            )

    hits.sort(key=lambda h: (-h["raw_score"], h["id"]))
    hits = hits[:16]
    audit = SourceAuditEntry(
        source_id="local.code-and-tests",
        channel="public_ast_code",
        scope="public",
        status="consulted",
        reason="Public repository AST structural code/test search.",
        hits=len(hits),
        pinned_version=ast_chunker.EXTRACTOR_VERSION,
    )
    return hits, audit


def _search_authenticated_decisions(
    query: str,
    auth_ctx: AuthenticatedArchiveContext,
) -> tuple[list[dict[str, Any]], SourceAuditEntry]:
    if auth_ctx.knowledge_conn is None:
        return [], SourceAuditEntry(
            source_id="knowledge_indexer",
            channel="knowledge_decisions",
            scope="authenticated_archive",
            status="unavailable",
            reason="knowledge_conn not mounted in AuthenticatedArchiveContext.",
        )

    conn = auth_ctx.knowledge_conn
    hits: list[dict[str, Any]] = []
    res = knowledge_indexer.query_knowledge(conn, query, verified_only=auth_ctx.verified_only)

    if res.get("is_adr") and res.get("decision"):
        dec = res["decision"]
        if dec.get("status") != "not-recovered":
            hits.append(
                _normalize_hit(
                    hit_id=f"decision:{dec['decision_id']}",
                    evidence_type="decision",
                    source_channel="knowledge_decisions",
                    source_id="knowledge_indexer",
                    scope="authenticated_archive",
                    title=f"{dec['decision_id']}: {dec.get('title', '')}",
                    snippet=f"{dec.get('motivation', '')} | {dec.get('consequences', '')}",
                    raw_score=1.0,
                    blob_sha=dec.get("blob_sha") or "",
                    record_sha256=sha256_obj(dec),
                    repo=dec.get("source_repo") or "",
                    ref=dec.get("source_ref") or "",
                    commit_sha=dec.get("commit_sha") or "",
                    path=dec.get("path") or "",
                    version=dec.get("valid_from_ref") or "",
                    domain="arquitetura-tecnica",
                    provenance_status=dec.get("provenance_status", "verified"),
                    metadata={"status": dec.get("status"), "verified": dec.get("verified", False)},
                )
            )

    for group in res.get("candidate_groups", []):
        cid = group["concept_id"]
        hits.append(
            _normalize_hit(
                hit_id=f"glossary:{cid}",
                evidence_type="concept",
                source_channel="knowledge_decisions",
                source_id="knowledge_indexer",
                scope="authenticated_archive",
                title=f"{cid}: {group.get('canonical_term_en', '')} / {group.get('canonical_term_pt', '')}",
                snippet=group.get("description") or "",
                raw_score=0.9,
                blob_sha=group.get("implementation_sha") or "",
                record_sha256=sha256_obj(group),
                path=group.get("implementation_file") or "",
                domain="conhecimento-humano",
                provenance_status=group.get("provenance_status", "verified"),
                metadata={"matched_terms": group.get("matched_terms", []), "verified": group.get("verified", False)},
            )
        )
        for dec in group.get("applicable_decisions", []):
            hits.append(
                _normalize_hit(
                    hit_id=f"decision:{dec['decision_id']}",
                    evidence_type="decision",
                    source_channel="knowledge_decisions",
                    source_id="knowledge_indexer",
                    scope="authenticated_archive",
                    title=f"{dec['decision_id']}: {dec.get('title', '')}",
                    snippet=f"{dec.get('motivation', '')} | {dec.get('consequences', '')}",
                    raw_score=0.85,
                    blob_sha=dec.get("blob_sha") or "",
                    record_sha256=sha256_obj(dec),
                    ref=dec.get("valid_from_ref") or "",
                    path=dec.get("path") or "",
                    domain="arquitetura-tecnica",
                    provenance_status=dec.get("provenance_status", "verified"),
                    metadata={"status": dec.get("status"), "verified": dec.get("verified", False)},
                )
            )

    # Also query FTS5 knowledge_fts directly with expanded terms for broader recall
    exp = search_expansion.expand_query(query, max_tokens=6)
    terms = [t for t in exp.get("tokens", []) if t not in STOPWORDS]
    if not terms:
        terms = _tokenize_bm25(query)
    if terms:
        # Build safe OR query over normalized terms
        expanded = []
        for t in terms[:4]:
            expanded.append(t)
            for peer in search_expansion.TOKEN_SYNONYMS.get(t, ())[:2]:
                if " " not in peer:
                    expanded.append(peer)
        match_expr = " OR ".join(f'"{t}"' for t in dict.fromkeys(expanded))
        try:
            rows = conn.execute(
                "SELECT entity_type, entity_id, title, content FROM knowledge_fts WHERE knowledge_fts MATCH ? LIMIT 15",
                (match_expr,),
            ).fetchall()
            for r in rows:
                etype = r["entity_type"]
                eid = r["entity_id"]
                if etype == "decision":
                    drow = conn.execute("SELECT * FROM decision_records WHERE decision_id=?", (eid,)).fetchone()
                    if not drow:
                        continue
                    prov_st = drow["provenance_status"]
                    is_ver = prov_st == "verified" and not bool(drow["is_synthetic"]) and knowledge_indexer.validate_git_sha(drow["blob_sha"])
                    if auth_ctx.verified_only and not is_ver:
                        continue
                    hits.append(
                        _normalize_hit(
                            hit_id=f"decision:{eid}",
                            evidence_type="decision",
                            source_channel="knowledge_decisions",
                            source_id="knowledge_indexer",
                            scope="authenticated_archive",
                            title=f"{eid}: {drow['title']}",
                            snippet=f"{drow['motivation'] or ''} | {drow['consequences'] or ''}",
                            raw_score=0.8,
                            blob_sha=drow["blob_sha"] or "",
                            record_sha256=sha256_text(f"{eid}|{drow['title']}|{drow['motivation']}"),
                            repo=drow["source_repo"] or "",
                            ref=drow["source_ref"] or "",
                            commit_sha=drow["commit_sha"] or "",
                            path=drow["path"] or "",
                            version=drow["valid_from_ref"] or "",
                            domain="arquitetura-tecnica",
                            provenance_status=prov_st,
                            metadata={"status": drow["status"], "verified": is_ver},
                        )
                    )
        except sqlite3.OperationalError:
            pass

    return hits, SourceAuditEntry(
        source_id="knowledge_indexer",
        channel="knowledge_decisions",
        scope="authenticated_archive",
        status="consulted",
        reason="Authenticated ADR and disambiguated glossary index search.",
        hits=len(hits),
        pinned_version=knowledge_indexer.INDEXER_VERSION,
    )


def _search_authenticated_graph(
    query: str,
    auth_ctx: AuthenticatedArchiveContext,
) -> tuple[list[dict[str, Any]], SourceAuditEntry]:
    if auth_ctx.evidence_conn is None:
        return [], SourceAuditEntry(
            source_id="evidence_graph",
            channel="evidence_graph",
            scope="authenticated_archive",
            status="unavailable",
            reason="evidence_conn not mounted in AuthenticatedArchiveContext.",
        )

    conn = auth_ctx.evidence_conn
    hits: list[dict[str, Any]] = []
    # Resolve candidate entities from query tokens + expanded terms
    exp = search_expansion.expand_query(query, max_tokens=6)
    probes = [query] + [t for t in exp.get("expanded_terms", [])[:6] if t != query]
    seen_node_ids: set[str] = set()

    for probe in probes:
        bundle = evidence_graph.traverse_evidence_graph(
            conn, probe, hops=2, token_budget=4000, repo=auth_ctx.pinned_repo
        )
        eb = bundle.get("evidence_bundle", {})
        layer_map = (
            ("component", "code"),
            ("files", "code"),
            ("symbols", "code"),
            ("handlers", "code"),
            ("state", "code"),
            ("motion", "media"),
            ("docs_and_adrs", "decision"),
            ("screenshots", "media"),
        )
        for layer_key, ev_type in layer_map:
            for node in eb.get(layer_key, []):
                nid = node["node_id"]
                if nid in seen_node_ids:
                    continue
                seen_node_ids.add(nid)
                if auth_ctx.pinned_repo and node.get("repo") and node["repo"] != auth_ctx.pinned_repo:
                    continue
                meta = node.get("metadata", {})
                hits.append(
                    _normalize_hit(
                        hit_id=f"graph:{nid}",
                        evidence_type=ev_type,
                        source_channel="evidence_graph",
                        source_id="evidence_graph",
                        scope="authenticated_archive",
                        title=f"{node['node_type']}: {node['label']}",
                        snippet=json.dumps(meta, ensure_ascii=False)[:400] if meta else node.get("path", ""),
                        raw_score=0.85 if node["node_type"] in {"Component", "Decision"} else 0.72,
                        blob_sha=meta.get("blob_sha", ""),
                        record_sha256=sha256_obj(node),
                        repo=node.get("repo", ""),
                        ref=node.get("ref", ""),
                        commit_sha=node.get("commit_sha", ""),
                        path=node.get("path", ""),
                        domain="engenharia" if ev_type == "code" else "midia",
                        provenance_status="verified" if node.get("validity_status") != "unverified" else "unverified",
                        metadata={"node_type": node["node_type"], "layer": layer_key, "graph_meta": meta},
                    )
                )

    return hits, SourceAuditEntry(
        source_id="evidence_graph",
        channel="evidence_graph",
        scope="authenticated_archive",
        status="consulted",
        reason="Multi-layer evidence graph traversal across code, state, motion, decisions, and screenshots.",
        hits=len(hits),
    )


def _search_authenticated_ast(
    query: str,
    auth_ctx: AuthenticatedArchiveContext,
) -> tuple[list[dict[str, Any]], SourceAuditEntry]:
    if not auth_ctx.ast_chunks:
        return [], SourceAuditEntry(
            source_id="ast_chunker",
            channel="ast_code",
            scope="authenticated_archive",
            status="unavailable",
            reason="ast_chunks not provided in AuthenticatedArchiveContext.",
        )

    exp = search_expansion.expand_query(query, max_tokens=6)
    q_terms = set(_tokenize_bm25(query))
    for t in exp.get("expanded_terms", []):
        q_terms.update(_tokenize_bm25(t))

    hits: list[dict[str, Any]] = []
    for item in auth_ctx.ast_chunks:
        repo = item.get("repo", "")
        ref = item.get("ref", "")
        if not _matches_archive_pins(auth_ctx, repo, ref, item.get("commit_sha", "")):
            continue
        if auth_ctx.verified_only and item.get("provenance_status") != "verified":
            continue
        content = item.get("content", "")
        name = item.get("name", "")
        path = item.get("path", "")
        tokens = set(_tokenize_bm25(f"{path} {name} {item.get('parent_context', '')} {content}"))
        overlap = len(q_terms & tokens)
        if overlap == 0:
            continue
        is_test = "test" in path.lower() or name.lower().startswith("test_") or ".spec." in path.lower()
        ev_type = "test" if is_test else "code"
        hits.append(
            _normalize_hit(
                hit_id=f"auth_ast:{repo}:{path}:{item.get('symbol_id') or name}",
                evidence_type=ev_type,
                source_channel="ast_code",
                source_id="ast_chunker",
                scope="authenticated_archive",
                title=f"{path} :: {name} ({item.get('node_type', 'symbol')})",
                snippet=content[:600],
                raw_score=float(overlap) / max(1.0, float(len(q_terms))),
                blob_sha=item.get("blob_sha", ""),
                record_sha256=item.get("chunk_sha") or sha256_text(content),
                repo=repo,
                ref=ref,
                commit_sha=item.get("commit_sha", ""),
                path=path,
                version=item.get("extractor_version", ast_chunker.EXTRACTOR_VERSION),
                domain="qualidade" if is_test else "engenharia",
                provenance_status=item.get("provenance_status", "unverified"),
                metadata={
                    "node_type": item.get("node_type"),
                    "symbol_id": item.get("symbol_id"),
                    "parent_context": item.get("parent_context"),
                    "start_line": item.get("start_line"),
                    "end_line": item.get("end_line"),
                },
            )
        )

    return hits, SourceAuditEntry(
        source_id="ast_chunker",
        channel="ast_code",
        scope="authenticated_archive",
        status="consulted",
        reason="Authenticated historical AST chunk search.",
        hits=len(hits),
        pinned_version=ast_chunker.EXTRACTOR_VERSION,
    )


def _search_authenticated_images(
    query: str,
    auth_ctx: AuthenticatedArchiveContext,
) -> tuple[list[dict[str, Any]], SourceAuditEntry]:
    if not auth_ctx.image_records:
        return [], SourceAuditEntry(
            source_id="image_catalog",
            channel="image_catalog",
            scope="authenticated_archive",
            status="unavailable",
            reason="image_records not provided in AuthenticatedArchiveContext.",
        )

    exp_terms = search_expansion.expanded_image_terms(query, max_terms=10) if hasattr(search_expansion, "expanded_image_terms") else []
    q_terms = set(_tokenize_bm25(query))
    for t in exp_terms:
        q_terms.update(_tokenize_bm25(t))

    hits: list[dict[str, Any]] = []
    for img in auth_ctx.image_records:
        repo = img.get("repo") or img.get("origin") or ""
        ref = img.get("ref") or (img.get("refs")[0] if img.get("refs") else "")
        commit = img.get("commit") or img.get("commit_sha") or ""
        if not _matches_archive_pins(auth_ctx, repo, ref, commit):
            continue
        # A catalog entry identifies a candidate, not freshly recovered bytes.
        if auth_ctx.verified_only and not GIT_SHA_RE.fullmatch(img.get("blob_sha") or ""):
            continue
        path = img.get("path", "")
        screen = img.get("screen", "")
        refs = " ".join(img.get("refs", [])) if isinstance(img.get("refs"), list) else str(img.get("ref", ""))
        haystack = f"{path} {screen} {refs} {img.get('status', '')}"
        tokens = set(_tokenize_bm25(haystack))
        overlap = len(q_terms & tokens)
        if overlap == 0:
            continue
        hits.append(
            _normalize_hit(
                hit_id=f"img:{repo}:{path}:{img.get('blob_sha', '')[:12]}",
                evidence_type="media",
                source_channel="image_catalog",
                source_id="image_catalog",
                scope="authenticated_archive",
                title=f"{Path(path).name} ({img.get('status', 'present')})",
                snippet=f"Indexed path: {path} | Filename-derived screen label: {screen} | Format: {img.get('format', '')} | Dimensions: {img.get('dimensions')} | Visual content not inspected by retrieval.",
                raw_score=float(overlap) / max(1.0, float(len(q_terms))),
                blob_sha=img.get("blob_sha") or "",
                record_sha256=img.get("sha256") or sha256_obj(img),
                repo=repo,
                ref=img.get("ref") or (img.get("refs")[0] if img.get("refs") else ""),
                commit_sha=img.get("commit") or img.get("commit_sha") or "",
                path=path,
                domain="midia",
                provenance_status="indexed-not-recovered" if GIT_SHA_RE.fullmatch(img.get("blob_sha") or "") else "unverified",
                metadata={"deleted": bool(img.get("deleted")), "bytes": img.get("bytes"), "dimensions": img.get("dimensions"), "visual_inspection": "not_performed_by_retrieval", "screen_label_origin": "filename", "verified_states": [], "retrieval": {"method": "authorized_local_git_blob" if img.get("blob_sha") else "unavailable", "bytes_verified_in_this_call": False, "branch_freshness": "not_checked"}},
            )
        )

    return hits, SourceAuditEntry(
        source_id="image_catalog",
        channel="image_catalog",
        scope="authenticated_archive",
        status="consulted",
        reason="Authenticated historical image catalog search.",
        hits=len(hits),
    )


def _search_authenticated_documents(
    query: str,
    auth_ctx: AuthenticatedArchiveContext,
) -> tuple[list[dict[str, Any]], SourceAuditEntry]:
    if not auth_ctx.documents:
        return [], SourceAuditEntry(
            source_id="authenticated_documents",
            channel="content_archive",
            scope="authenticated_archive",
            status="unavailable",
            reason="documents not mounted in AuthenticatedArchiveContext.",
        )

    exp = search_expansion.expand_query(query, max_tokens=6)
    q_terms = set(_tokenize_bm25(query))
    for t in exp.get("expanded_terms", []):
        q_terms.update(_tokenize_bm25(t))

    hits: list[dict[str, Any]] = []
    for doc in auth_ctx.documents:
        repo = doc.get("repo", "")
        ref = doc.get("ref", "")
        if not _matches_archive_pins(auth_ctx, repo, ref, doc.get("commit_sha", "")):
            continue
        if auth_ctx.verified_only and doc.get("provenance_status") != "verified":
            continue
        text = doc.get("content", "") or doc.get("text", "")
        title = doc.get("title", "") or doc.get("path", "")
        tokens = set(_tokenize_bm25(f"{title} {doc.get('path', '')} {text}"))
        overlap = len(q_terms & tokens)
        if overlap == 0:
            continue
        ev_type = doc.get("evidence_type") or ("requirement" if any(k in title.lower() or k in text.lower() for k in ("req", "requisito", "spec", "prd", "aceite")) else "decision")
        hits.append(
            _normalize_hit(
                hit_id=f"doc:{repo}:{doc.get('path', '')}:{doc.get('element_id', title)}",
                evidence_type=ev_type,
                source_channel="content_archive",
                source_id="authenticated_documents",
                scope="authenticated_archive",
                title=title,
                snippet=text[:600],
                raw_score=float(overlap) / max(1.0, float(len(q_terms))),
                blob_sha=doc.get("blob_sha", ""),
                record_sha256=doc.get("doc_sha256") or sha256_text(text),
                repo=repo,
                ref=ref,
                commit_sha=doc.get("commit_sha", ""),
                path=doc.get("path", ""),
                version=doc.get("version", ""),
                domain=doc.get("domain", "produto"),
                provenance_status=doc.get("provenance_status", "unverified"),
                metadata={"element_id": doc.get("element_id")},
            )
        )

    return hits, SourceAuditEntry(
        source_id="authenticated_documents",
        channel="content_archive",
        scope="authenticated_archive",
        status="consulted",
        reason="Authenticated historical requirements/content search.",
        hits=len(hits),
    )


def _interleave_by_evidence_type(
    ranked_hits: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Interleave ranked results across distinct evidence types to preserve multimodal diversity."""
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for h in ranked_hits:
        by_type[h["evidence_type"]].append(h)

    ordered: list[dict[str, Any]] = []
    # Order types by highest top RRF+BM25 score first, then round-robin
    type_order = sorted(
        by_type.keys(),
        key=lambda t: (-by_type[t][0]["fused_score"], t),
    )
    while len(ordered) < limit and any(by_type.values()):
        for etype in type_order:
            if by_type[etype] and len(ordered) < limit:
                ordered.append(by_type[etype].pop(0))
    return ordered


def _enforce_budget(
    candidates: list[dict[str, Any]],
    *,
    envelope_base: dict[str, Any],
    budget_tokens: int,
    max_bytes: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Add results in rank order while strictly respecting budget_tokens and max_bytes."""
    kept: list[dict[str, Any]] = []
    omitted_budget: list[dict[str, Any]] = []

    base_tokens = estimate_tokens(envelope_base)
    base_bytes = utf8_bytes(envelope_base)
    # Reserve compact metadata overhead (capped at 25% of budget_tokens if envelope is verbose)
    reserved_tokens = min(base_tokens, max(32, budget_tokens // 4))
    used_tokens = reserved_tokens
    used_bytes = base_bytes

    for item in candidates:
        item_tokens = estimate_tokens(item)
        item_bytes = utf8_bytes(item)
        over_tokens = (used_tokens + item_tokens) > budget_tokens
        over_bytes = (max_bytes is not None) and ((used_bytes + item_bytes) > max_bytes)
        if over_tokens or over_bytes:
            omitted_budget.append({
                "id": item["id"],
                "evidence_type": item["evidence_type"],
                "source_channel": item["source_channel"],
                "reason": "budget_tokens_exceeded" if over_tokens else "max_bytes_exceeded",
                "item_tokens": item_tokens,
            })
            continue
        kept.append(item)
        used_tokens += item_tokens
        used_bytes += item_bytes

    accounting = {
        "budget_tokens": budget_tokens,
        "envelope_tokens": base_tokens,
        "reserved_metadata_tokens": reserved_tokens,
        "results_tokens": max(0, used_tokens - reserved_tokens),
        "total_tokens": used_tokens,
        "remaining_tokens": max(0, budget_tokens - used_tokens),
        "total_bytes": used_bytes,
        "max_bytes": max_bytes,
    }
    return kept, omitted_budget, accounting


def federated_search(
    query: str,
    scope: str = "public",
    budget_tokens: int = 2000,
    intent: str | None = None,
    *,
    domain: str | None = None,
    product: str | None = None,
    limit: int = 16,
    max_bytes: int | None = None,
    auth_context: AuthenticatedArchiveContext | None = None,
    public_records: list[dict[str, Any]] | None = None,
    public_taxonomy: dict[str, Any] | None = None,
    public_code_paths: list[Path] | None = None,
    ontology: domain_ontology.DomainOntology | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Unified federated search entrypoint across public research and authenticated historical archive.

    Strict invariants:
      - scope='public' NEVER accesses private/historical channels, even if auth_context is passed.
      - scope='authenticated_archive' fails closed unless auth_context.validate() passes.
      - Combines channel rankings via RRF + textual Okapi BM25 + diversity interleaving.
      - Deduplicates identical blobs while preserving all occurrences and pinned SHA-1/SHA-256.
      - Returns auditable lists of consulted, omitted, and unavailable sources plus gap diagnostics.
    """
    if scope not in VALID_SCOPES:
        raise ValueError(f"Unsupported scope {scope!r}; expected 'public' or 'authenticated_archive'")
    if not isinstance(budget_tokens, int) or budget_tokens < 128 or budget_tokens > 128000:
        raise ValueError("budget_tokens must be an integer between 128 and 128000")
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    clean_query, query_sanitized = domain_ontology.sanitize_untrusted_text(query, max_length=240)
    if not clean_query or clean_query == "[sanitized-untrusted-directive]":
        return {
            "schema_version": SCHEMA_VERSION,
            "query": clean_query,
            "scope": scope,
            "status": "invalid-query",
            "intent": detect_intent("", intent),
            "results": [],
            "gaps": ["empty_or_sanitized_query"],
            "sources_consulted": [],
            "sources_omitted": [],
            "sources_unavailable": [],
            "budget": {"budget_tokens": budget_tokens, "total_tokens": 0, "remaining_tokens": budget_tokens},
            "sanitized_query": query_sanitized,
        }

    intent_info = detect_intent(clean_query, intent)
    selected_channels = _select_channels_for_intent(intent_info, scope)

    audits_consulted: list[dict[str, Any]] = []
    audits_omitted: list[dict[str, Any]] = []
    audits_unavailable: list[dict[str, Any]] = []

    # Registry awareness for reporting historical unavailable / scope-blocked sources
    reg = registry if registry is not None else source_registry.load_registry()
    reg_hash = source_registry.compute_registry_hash(reg)

    # Strict scope isolation gate BEFORE any retrieval or expansion
    if scope == "public":
        if auth_context is not None:
            audits_omitted.append(
                SourceAuditEntry(
                    source_id="authenticated_archive",
                    channel="authenticated_archive",
                    scope="authenticated_archive",
                    status="omitted",
                    reason="scope='public' strictly isolates and blocks access to private/historical archive channels.",
                ).to_dict()
            )
        for src in reg.get("sources", []):
            if src.get("scope") == "authenticated_archive":
                audits_omitted.append(
                    SourceAuditEntry(
                        source_id=src["source_id"],
                        channel=src.get("adapter", "git_bundle"),
                        scope="authenticated_archive",
                        status="omitted",
                        reason="Isolated by public scope policy before search and expansion.",
                    ).to_dict()
                )
    else:
        # scope == "authenticated_archive"
        if auth_context is None:
            return {
                "schema_version": SCHEMA_VERSION,
                "query": clean_query,
                "scope": scope,
                "status": "authorization-denied",
                "intent": intent_info,
                "results": [],
                "gaps": ["authorization_required: AuthenticatedArchiveContext is missing"],
                "sources_consulted": [],
                "sources_omitted": [],
                "sources_unavailable": [
                    SourceAuditEntry(
                        source_id="authenticated_archive",
                        channel="authenticated_archive",
                        scope="authenticated_archive",
                        status="unavailable",
                        reason="authorization_required: missing AuthenticatedArchiveContext",
                    ).to_dict()
                ],
                "registry_hash": reg_hash,
                "budget": {"budget_tokens": budget_tokens, "total_tokens": 0, "remaining_tokens": budget_tokens},
                "sanitized_query": query_sanitized,
            }
        auth_errors = auth_context.validate()
        if auth_errors:
            return {
                "schema_version": SCHEMA_VERSION,
                "query": clean_query,
                "scope": scope,
                "status": "authorization-denied",
                "intent": intent_info,
                "results": [],
                "gaps": auth_errors,
                "sources_consulted": [],
                "sources_omitted": [],
                "sources_unavailable": [
                    SourceAuditEntry(
                        source_id="authenticated_archive",
                        channel="authenticated_archive",
                        scope="authenticated_archive",
                        status="unavailable",
                        reason="; ".join(auth_errors),
                    ).to_dict()
                ],
                "registry_hash": reg_hash,
                "budget": {"budget_tokens": budget_tokens, "total_tokens": 0, "remaining_tokens": budget_tokens},
                "sanitized_query": query_sanitized,
            }

    ont = ontology if ontology is not None else domain_ontology.DomainOntology()
    raw_hits: list[dict[str, Any]] = []
    channel_rankings: dict[str, list[str]] = defaultdict(list)

    def _record_channel(ch_hits: list[dict[str, Any]], audit: SourceAuditEntry) -> None:
        if scope == "authenticated_archive" and audit.channel != "ontology":
            before = len(ch_hits)
            ch_hits = [hit for hit in ch_hits if _matches_archive_pins(
                auth_context, hit["provenance"].get("repo"), hit["provenance"].get("ref"),
                hit["provenance"].get("commit_sha"))]
            audit.hits = len(ch_hits)
            if before != len(ch_hits):
                audit.reason += f" Excluded {before-len(ch_hits)} hits with missing or mismatched scope pins."
        if audit.status == "consulted":
            audits_consulted.append(audit.to_dict())
        elif audit.status == "omitted":
            audits_omitted.append(audit.to_dict())
        else:
            audits_unavailable.append(audit.to_dict())
        raw_hits.extend(ch_hits)

    # Execute consulted channels
    if "ontology" in selected_channels:
        h, a = _search_ontology(clean_query, scope=scope, domain=domain, ontology=ont)
        _record_channel(h, a)
    else:
        audits_omitted.append(SourceAuditEntry("domain_ontology", "ontology", scope, "omitted", "Not routed for intent.").to_dict())

    if scope == "public":
        records = public_records if public_records is not None else research_index.load_records()
        taxonomy = public_taxonomy if public_taxonomy is not None else concept_packs.load_taxonomy()
        rev = archive_context.snapshot(records, taxonomy)
        pub_hits, pub_audits = _search_public_research_and_concepts(
            clean_query, records=records, taxonomy=taxonomy, snapshot_rev=rev, product=product
        )
        raw_hits.extend(pub_hits)
        for pa in pub_audits:
            audits_consulted.append(pa.to_dict())

        if "public_ast_code" in selected_channels:
            h, a = _search_public_ast_code(clean_query, paths=public_code_paths)
            _record_channel(h, a)
        else:
            audits_omitted.append(SourceAuditEntry("local.code-and-tests", "public_ast_code", "public", "omitted", "Not routed for intent.").to_dict())

        # Audit that private authenticated channels were strictly omitted
        for priv_ch in ("knowledge_decisions", "evidence_graph", "image_catalog", "content_archive"):
            audits_omitted.append(
                SourceAuditEntry(
                    source_id=priv_ch,
                    channel=priv_ch,
                    scope="authenticated_archive",
                    status="omitted",
                    reason="Strict public scope isolation: private index not consulted.",
                ).to_dict()
            )
    else:
        assert auth_context is not None
        snapshot_pin = auth_context.expected_index_checksum or auth_context.actual_index_checksum or auth_context.pinned_source_sha or reg_hash
        rev = snapshot_pin

        if "knowledge_decisions" in selected_channels:
            h, a = _search_authenticated_decisions(clean_query, auth_context)
            _record_channel(h, a)
        else:
            audits_omitted.append(SourceAuditEntry("knowledge_indexer", "knowledge_decisions", scope, "omitted", "Not routed for intent.").to_dict())

        if "evidence_graph" in selected_channels:
            h, a = _search_authenticated_graph(clean_query, auth_context)
            _record_channel(h, a)
        else:
            audits_omitted.append(SourceAuditEntry("evidence_graph", "evidence_graph", scope, "omitted", "Not routed for intent.").to_dict())

        if "ast_code" in selected_channels:
            h, a = _search_authenticated_ast(clean_query, auth_context)
            _record_channel(h, a)
        else:
            audits_omitted.append(SourceAuditEntry("ast_chunker", "ast_code", scope, "omitted", "Not routed for intent.").to_dict())

        if "image_catalog" in selected_channels:
            h, a = _search_authenticated_images(clean_query, auth_context)
            _record_channel(h, a)
        else:
            audits_omitted.append(SourceAuditEntry("image_catalog", "image_catalog", scope, "omitted", "Not routed for intent.").to_dict())

        if "content_archive" in selected_channels:
            h, a = _search_authenticated_documents(clean_query, auth_context)
            _record_channel(h, a)
        else:
            audits_omitted.append(SourceAuditEntry("authenticated_documents", "content_archive", scope, "omitted", "Not routed for intent.").to_dict())

        # Record any offline/unavailable historical origins from registry
        for src in reg.get("sources", []):
            if src.get("origin_status") == "historical_unavailable":
                audits_unavailable.append(
                    SourceAuditEntry(
                        source_id=src["source_id"],
                        channel=src.get("adapter", "git_bundle"),
                        scope=src["scope"],
                        status="unavailable",
                        reason="Remote GitHub origin historical_unavailable; relies on restored local bundles.",
                        pinned_version=str(src.get("pinned_revisions", {})),
                    ).to_dict()
                )

    # Exact blob deduplication retaining all occurrences
    deduped_hits, dedup_count = _deduplicate_blobs_preserving_occurrences(raw_hits)

    if scope == "public":
        deduped_hits = [hit for hit in deduped_hits
                        if hit["source_channel"] == "public_research"
                        or public_lexical_search.adequate_hit(clean_query, hit)]

    # Public candidate selection and reranking must use the same bilingual
    # concepts. Exclude provenance paths/domain labels from relevance text.
    if scope == "public":
        doc_texts = [" ".join((h["title"], h["snippet"],
                              str(h.get("metadata", {}).get("product") or "")))
                     for h in deduped_hits]
        bm25_scores = public_lexical_search.grouped_bm25(clean_query, doc_texts)
    else:
        # Compute BM25 over deduped items with PT<->EN expanded query terms
        exp = search_expansion.expand_query(clean_query, max_tokens=8)
        bm25_terms = list(dict.fromkeys([*_tokenize_bm25(clean_query), *[_t for e in exp.get("expanded_terms", []) for _t in _tokenize_bm25(e)]]))
        doc_texts = [f"{h['title']} {h['snippet']} {h['provenance'].get('path', '')} {h.get('domain', '')}" for h in deduped_hits]
        bm25_scores = compute_bm25_scores(bm25_terms, doc_texts)

    for idx, h in enumerate(deduped_hits):
        h["bm25_score"] = bm25_scores[idx]

    # Build per-channel ranked lists + BM25 global list for RRF
    for ch_name in sorted({h["source_channel"] for h in deduped_hits}):
        ch_items = [h for h in deduped_hits if h["source_channel"] == ch_name]
        ch_items.sort(key=lambda x: (-x["raw_score"], -x["bm25_score"], x["id"]))
        channel_rankings[ch_name] = [x["id"] for x in ch_items]

    bm25_ranked = sorted(deduped_hits, key=lambda x: (-x["bm25_score"], -x["raw_score"], x["id"]))
    channel_rankings["bm25_textual"] = [x["id"] for x in bm25_ranked if x["bm25_score"] > 0.0]

    rrf_scores = reciprocal_rank_fusion(channel_rankings, rrf_k=60)
    max_bm25 = max(bm25_scores) if bm25_scores and max(bm25_scores) > 0 else 1.0

    for h in deduped_hits:
        norm_bm25 = h["bm25_score"] / max_bm25
        rrf_val = rrf_scores.get(h["id"], 0.0)
        h["rrf_score"] = rrf_val
        h["fused_score"] = round(rrf_val + 0.015 * norm_bm25 + 0.005 * h["raw_score"], 8)

    deduped_hits.sort(key=lambda x: (-x["fused_score"], x["id"]))

    # Diversity interleaving across evidence types
    diversified = _interleave_by_evidence_type(deduped_hits, limit=limit)

    # Identify evidence type gaps for the detected intent
    present_types = {h["evidence_type"] for h in diversified}
    expected_by_intent = {
        "decision": {"decision", "code"},
        "code": {"code", "test"},
        "requirement": {"requirement", "decision", "code"},
        "test": {"test", "code"},
        "media": {"media"},
        "graph": {"code", "decision", "media"},
        "concept": {"concept"},
        "mixed": {"concept", "code", "decision", "media"},
    }
    expected_types = expected_by_intent.get(intent_info["primary"], {"concept"})
    if scope == "public":
        # Public scope does not claim private historical code/decisions
        expected_types = expected_types & {"concept", "pattern", "source", "media", "code", "test"}
    missing_evidence_types = sorted(expected_types - present_types)

    gaps: list[str] = []
    if not diversified:
        gaps.append("no_matching_evidence_found")
    if missing_evidence_types:
        gaps.append("missing_evidence_types:" + ",".join(missing_evidence_types))
    if audits_unavailable:
        gaps.append("unavailable_sources:" + ",".join(a["source_id"] for a in audits_unavailable))

    envelope_meta = {
        "schema_version": SCHEMA_VERSION,
        "query": clean_query,
        "scope": scope,
        "snapshot": rev,
        "registry_hash": reg_hash,
        "intent": intent_info,
        "ranking_method": "rrf_bm25_diversity",
        "deduplicated_occurrences": dedup_count,
        "available_by_type": dict(sorted(Counter(h["evidence_type"] for h in deduped_hits).items())),
        "missing_evidence_types": missing_evidence_types,
        "gaps": gaps,
        "sources_consulted": audits_consulted,
        "sources_omitted": audits_omitted,
        "sources_unavailable": audits_unavailable,
    }

    kept, omitted_budget, budget_accounting = _enforce_budget(
        diversified,
        envelope_base=envelope_meta,
        budget_tokens=budget_tokens,
        max_bytes=max_bytes,
    )

    if omitted_budget:
        gaps.append(f"budget_truncated:{len(omitted_budget)}")

    status = "ok" if kept else ("budget-exhausted" if diversified else "no-evidence")

    return {
        **envelope_meta,
        "status": status,
        "returned_by_type": dict(sorted(Counter(h["evidence_type"] for h in kept).items())),
        "results": kept,
        "omitted_for_budget": omitted_budget,
        "budget": budget_accounting,
        "sanitized_query": query_sanitized,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Search query")
    parser.add_argument("--scope", choices=["public", "authenticated_archive"], default="public")
    parser.add_argument("--budget-tokens", type=int, default=2000)
    parser.add_argument("--intent", choices=sorted(VALID_INTENTS), default=None)
    parser.add_argument("--domain", default=None)
    parser.add_argument("--product", default=None)
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--max-bytes", type=int, default=None)
    args = parser.parse_args(argv)

    result = federated_search(
        args.query,
        scope=args.scope,
        budget_tokens=args.budget_tokens,
        intent=args.intent,
        domain=args.domain,
        product=args.product,
        limit=args.limit,
        max_bytes=args.max_bytes,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
