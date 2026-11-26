#!/usr/bin/env python3
"""Multimodal semantic ingestion and source coverage audit (#82).

Audits the entire eligible archive universe (public repositories, authenticated
historical bundles/manifests, research catalogs, documents, code/AST, and visual
media) without executing legacy code, mutating bundles, or leaking private content.

Tracks:
  1. Source universe inventory (source_id, revision/ref, MIME type, license,
     authorization scope, and lifecycle state: `located`, `retrieved`,
     `extracted`, `indexed`, `queryable`, `verified`, `partial`, `unavailable`).
  2. Knowledge unit extraction across all modalities:
       - AST / source code (via `scripts/ast_chunker.py` patterns)
       - Documents (requirements, ADRs, contracts, reports via `scripts/document_extractor.py`)
       - Metadata (manifests, GitHub platform metadata, CI/release records, sanitized configs)
       - Visual media (images/screenshots, GIFs/videos with verified vs inferred labels/states)
  3. Traceability graph mapping:
       requirement -> decision -> implementation -> test -> visual_evidence -> version
     plus orphan and duplicate blob detection with original provenance pointers.
  4. Reproducible reports emitted to `reports/SEMANTIC-INGESTION-AUDIT.json`
     and `reports/SEMANTIC-INGESTION-AUDIT.md`.

Zero external dependencies (Python 3.12 stdlib only).
Zero Emoji Policy: NO Unicode emojis [\\U00010000-\\U0010ffff].
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
from pathlib import Path
import re
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ast_chunker  # noqa: E402
import document_extractor  # noqa: E402
import source_registry  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

LIFECYCLE_STATES: tuple[str, ...] = (
    "located",
    "retrieved",
    "extracted",
    "indexed",
    "queryable",
    "verified",
    "partial",
    "unavailable",
)
LIFECYCLE_STATE_SET = frozenset(LIFECYCLE_STATES)

MODALITIES: tuple[str, ...] = (
    "ast_code",
    "document",
    "metadata",
    "media_visual",
)

MIME_OVERRIDES: dict[str, str] = {
    ".ts": "application/typescript",
    ".tsx": "application/typescript+jsx",
    ".mts": "application/typescript",
    ".cts": "application/typescript",
    ".js": "application/javascript",
    ".jsx": "application/javascript+jsx",
    ".mjs": "application/javascript",
    ".cjs": "application/javascript",
    ".py": "text/x-python",
    ".md": "text/markdown",
    ".mdx": "text/mdx",
    ".json": "application/json",
    ".jsonc": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".toml": "application/toml",
    ".html": "text/html",
    ".css": "text/css",
    ".scss": "text/x-scss",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".mp4": "video/mp4",
    ".pdf": "application/pdf",
    ".bundle": "application/x-git-bundle",
}

REQ_ID_RE = re.compile(r"\b(?:REQ|RF|RNF|ISSUE|#)\s*[-:]?\s*(\d{1,5})\b", re.IGNORECASE)
ADR_ID_RE = re.compile(r"\bADR[-_\s]?(\d{1,4})\b", re.IGNORECASE)
SPEC_DECISION_HEADING_RE = re.compile(
    r"(?:decis[aã]o|decision|requisito|requirement|contrato|contract|aceite|acceptance|adr)",
    re.IGNORECASE,
)


def infer_mime_type(path_str: str) -> str:
    ext = Path(path_str).suffix.lower()
    if ext in MIME_OVERRIDES:
        return MIME_OVERRIDES[ext]
    guessed, _ = mimetypes.guess_type(path_str)
    return guessed or "application/octet-stream"


def classify_modality(path_str: str, source_type: str = "") -> str:
    ext = Path(path_str).suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp4", ".drawio", ".excalidraw"}:
        return "media_visual"
    if ext in {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css", ".scss", ".html", ".sql", ".cs"}:
        return "ast_code"
    if ext in {".md", ".mdx", ".txt", ".rst", ".pdf"}:
        return "document"
    if ext in {".json", ".jsonc", ".yaml", ".yml", ".toml"}:
        norm = path_str.replace("\\", "/").lower()
        if any(seg in norm for seg in ("manifest", "inventory", "config/", "reports/", "patterns.json", "sources.json")):
            return "metadata"
        if source_type == "research_catalog":
            return "metadata"
        return "metadata"
    return "metadata"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract_code_units(path: Path, rel_path: str, content: str, blob_sha: str) -> list[dict[str, Any]]:
    ext = path.suffix.lower()
    lang = ast_chunker.LANGUAGE_ALIASES.get(ext)
    if not lang:
        return []
    chunks = ast_chunker.chunk_code(content, language=lang, blob_sha=blob_sha)
    units: list[dict[str, Any]] = []
    for ch in chunks:
        sym = ch.symbol_id or f"{ch.node_type}:{ch.name}:{ch.start_line}"
        units.append(
            {
                "unit_id": f"ast:{rel_path}:{sym}",
                "modality": "ast_code",
                "kind": ch.node_type,
                "name": ch.name,
                "path": rel_path,
                "start_line": ch.start_line,
                "end_line": ch.end_line,
                "chunk_sha": ch.chunk_sha,
                "motion_contracts": len(ch.motion_contracts),
                "observation_status": "verified_static_ast",
            }
        )
    return units


def _extract_document_units(path: Path, rel_path: str, raw: bytes, blob_sha: str) -> list[dict[str, Any]]:
    ext = path.suffix.lower()
    if ext not in {".md", ".mdx", ".markdown", ".txt", ".rst"}:
        return []
    parsed = document_extractor.extract_document_bytes(raw, path=rel_path)
    units: list[dict[str, Any]] = []
    for sec in parsed.get("sections", []):
        title = sec.get("title", "")
        kind = "document_section"
        if ADR_ID_RE.search(title) or ADR_ID_RE.search(rel_path):
            kind = "adr_decision"
        elif SPEC_DECISION_HEADING_RE.search(title):
            kind = "requirement_or_contract"
        pos = sec.get("position", {})
        units.append(
            {
                "unit_id": f"doc:{rel_path}:{sec.get('element_id', title)}",
                "modality": "document",
                "kind": kind,
                "name": title,
                "path": rel_path,
                "start_line": pos.get("start_line", 1),
                "end_line": pos.get("end_line", 1),
                "observation_status": "verified_document_structure",
            }
        )
    return units


def _audit_visual_manifests(root_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Inspect licensed visual libraries distinguishing verified vs inferred observations."""
    visual_units: list[dict[str, Any]] = []
    stats = {
        "total_visual_records": 0,
        "verified_blobs": 0,
        "link_only": 0,
        "sampled_frames_reviewed": 0,
        "uninspected_media": 0,
        "duplicate_blob_groups": 0,
    }
    blobs: dict[str, list[str]] = defaultdict(list)

    vel_manifest = root_dir / "docs/references/visual-evidence-library/manifest.json"
    if vel_manifest.is_file():
        data = json.loads(vel_manifest.read_text(encoding="utf-8"))
        for rec in data.get("records", []):
            stats["total_visual_records"] += 1
            rid = rec.get("id", "")
            status = rec.get("status", "unknown")
            blob_sha = rec.get("blob_sha") or ""
            if blob_sha:
                blobs[blob_sha].append(f"visual-evidence-library:{rid}")
            if status == "archived-blob-verified":
                stats["verified_blobs"] += 1
            elif status == "link-only":
                stats["link_only"] += 1

            seg = rec.get("segment_evidence") or {}
            review_state = seg.get("semantic_review")
            if review_state == "sampled-frames-reviewed":
                stats["sampled_frames_reviewed"] += 1
                obs_status = "verified_sampled_frames"
            elif status == "archived-blob-verified":
                stats["uninspected_media"] += 1
                obs_status = "metadata_declared_not_visually_inspected"
            else:
                stats["uninspected_media"] += 1
                obs_status = "inferred_from_external_link_metadata"

            visual_units.append(
                {
                    "unit_id": f"media:vel:{rid}",
                    "modality": "media_visual",
                    "kind": rec.get("kind", "image"),
                    "title": rec.get("title", ""),
                    "product": rec.get("product"),
                    "license": rec.get("license"),
                    "blob_sha": blob_sha or None,
                    "source_url": rec.get("source_url"),
                    "availability": status,
                    "states": seg.get("states", []),
                    "observations_count": len(seg.get("observations", [])),
                    "keyframes_count": len(seg.get("keyframes", [])),
                    "observation_status": obs_status,
                }
            )

    grok_manifest = root_dir / "docs/references/grok-bot/media/manifest.json"
    if grok_manifest.is_file():
        data = json.loads(grok_manifest.read_text(encoding="utf-8"))
        for asset in data.get("assets", []):
            stats["total_visual_records"] += 1
            blob_sha = asset.get("blob_sha") or ""
            ident = asset.get("path") or asset.get("title", "")
            if blob_sha:
                blobs[blob_sha].append(f"grok-bot:{ident}")
            stats["verified_blobs"] += 1
            stats["uninspected_media"] += 1
            visual_units.append(
                {
                    "unit_id": f"media:grok:{ident}",
                    "modality": "media_visual",
                    "kind": asset.get("kind", "image"),
                    "title": asset.get("title", ""),
                    "product": "grok-bot",
                    "license": asset.get("license"),
                    "blob_sha": blob_sha or None,
                    "source_url": asset.get("source_url"),
                    "availability": "archived-blob-declared",
                    "states": [],
                    "observations_count": 0,
                    "keyframes_count": 0,
                    "observation_status": "metadata_declared_not_visually_inspected",
                }
            )

    dup_groups = {sha: refs for sha, refs in blobs.items() if len(refs) > 1}
    stats["duplicate_blob_groups"] = len(dup_groups)
    stats["duplicate_blobs"] = dup_groups
    return visual_units, stats


def _build_traceability_graph(
    root_dir: Path,
    source_files: list[dict[str, Any]],
    visual_units: list[dict[str, Any]],
) -> dict[str, Any]:
    """Map requirement -> decision -> implementation -> test -> visual_evidence -> version."""
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str, str]] = set()

    def add_node(nid: str, ntype: str, label: str, pointer: str, status: str = "verified") -> None:
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "type": ntype,
                "label": label,
                "pointer": pointer,
                "status": status,
            }

    def add_edge(src: str, tgt: str, etype: str) -> None:
        key = (src, tgt, etype)
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append({"source": src, "target": tgt, "type": etype})

    # Discover implementations & tests from audited files
    scripts_by_stem: dict[str, str] = {}
    tests_by_stem: dict[str, str] = {}
    docs_by_path: list[str] = []

    for rec in source_files:
        p = rec["path"]
        if p.startswith("scripts/") and p.endswith(".py"):
            stem = Path(p).stem
            nid = f"impl:{p}"
            add_node(nid, "implementation", stem, p, rec["lifecycle_state"])
            scripts_by_stem[stem] = nid
        elif p.startswith("tests/") and p.endswith(".py"):
            stem = Path(p).stem
            nid = f"test:{p}"
            add_node(nid, "test", stem, p, rec["lifecycle_state"])
            tests_by_stem[stem] = nid
        elif p.startswith("docs/") and p.endswith(".md"):
            docs_by_path.append(p)
            nid = f"doc:{p}"
            add_node(nid, "decision_or_doc", Path(p).stem, p, rec["lifecycle_state"])

    # Link tests -> implementations by naming convention & imports
    for test_stem, test_nid in tests_by_stem.items():
        short = test_stem[5:] if test_stem.startswith("test_") else test_stem
        if short in scripts_by_stem:
            add_edge(scripts_by_stem[short], test_nid, "VERIFIED_BY_TEST")
        test_path = root_dir / test_nid.split(":", 1)[1]
        if test_path.is_file():
            txt = test_path.read_text(encoding="utf-8", errors="replace")
            for stem, impl_nid in scripts_by_stem.items():
                if re.search(rf"\b{re.escape(stem)}\b", txt):
                    add_edge(impl_nid, test_nid, "VERIFIED_BY_TEST")
            for m in re.findall(r"#(\d{1,4})\b", txt[:600]):
                req_id = f"req:issue-{m}"
                add_node(req_id, "requirement", f"Issue #{m}", f"github:issues/{m}", "located")
                add_edge(req_id, test_nid, "TESTED_FOR")

    # Link scripts -> docs/decisions -> requirements -> versions
    version_id = "version:archive-2026-11-25"
    add_node(version_id, "version", "Archive Snapshot 2026-11-25", "config/source_registry.json", "verified")

    for stem, impl_nid in scripts_by_stem.items():
        add_edge(impl_nid, version_id, "PACKAGED_IN_VERSION")
        script_path = root_dir / impl_nid.split(":", 1)[1]
        if script_path.is_file():
            head = script_path.read_text(encoding="utf-8", errors="replace")[:1500]
            for m in re.findall(r"#(\d{1,4})\b", head):
                req_id = f"req:issue-{m}"
                add_node(req_id, "requirement", f"Issue #{m}", f"github:issues/{m}", "located")
                add_edge(req_id, impl_nid, "IMPLEMENTED_BY")

    # Link docs -> scripts & visual evidence
    for doc_rel in docs_by_path:
        doc_nid = f"doc:{doc_rel}"
        doc_path = root_dir / doc_rel
        if not doc_path.is_file():
            continue
        txt = doc_path.read_text(encoding="utf-8", errors="replace")
        for m in re.findall(r"#(\d{1,4})\b", txt[:2500]):
            req_id = f"req:issue-{m}"
            add_node(req_id, "requirement", f"Issue #{m}", f"github:issues/{m}", "located")
            add_edge(req_id, doc_nid, "SPECIFIED_IN")
        for stem, impl_nid in scripts_by_stem.items():
            if stem in txt:
                add_edge(doc_nid, impl_nid, "GOVERNS_IMPLEMENTATION")
        add_edge(doc_nid, version_id, "RECORDED_IN_VERSION")

    for vu in visual_units:
        vid = vu["unit_id"]
        add_node(vid, "visual_evidence", vu.get("title") or vid, vu.get("source_url") or vid, vu["observation_status"])
        add_edge(vid, version_id, "CAPTURED_IN_VERSION")
        if vu.get("product") == "grok-bot":
            doc_nid = "doc:docs/references/grok-bot/README.md"
            if doc_nid in nodes:
                add_edge(doc_nid, vid, "EVIDENCED_BY")
        elif vid.startswith("media:vel:"):
            doc_nid = "doc:docs/references/visual-evidence-library/README.md"
            if doc_nid in nodes:
                add_edge(doc_nid, vid, "EVIDENCED_BY")

    # Detect orphan nodes (degree 0)
    connected = {e["source"] for e in edges} | {e["target"] for e in edges}
    orphans = sorted(nid for nid in nodes if nid not in connected)

    type_counts = Counter(n["type"] for n in nodes.values())
    return {
        "nodes_count": len(nodes),
        "edges_count": len(edges),
        "node_types": dict(sorted(type_counts.items())),
        "orphan_count": len(orphans),
        "orphans_sample": orphans[:25],
        "edges_sample": edges[:40],
    }


def _verify_bundle_recovery_coverage(root_dir: Path, registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Verify that unavailable/retired GitHub origins have immutable bundle manifests recorded."""
    rows: list[dict[str, Any]] = []
    for src in registry.get("sources", []):
        if src.get("adapter") != "git_bundle" and not src.get("bundle_fallback"):
            continue
        manifest_ref = src.get("manifest_ref")
        manifest_exists = bool(manifest_ref and (root_dir / manifest_ref).is_file())
        bundle_info = src.get("bundle_asset") or src.get("bundle_fallback") or {}
        has_sha256 = bool(bundle_info.get("sha256"))
        rows.append(
            {
                "source_id": src["source_id"],
                "repo": src.get("repo"),
                "scope": src["scope"],
                "origin_status": src["origin_status"],
                "manifest_ref": manifest_ref,
                "manifest_present": manifest_exists,
                "bundle_sha256_pinned": has_sha256,
                "pinned_refs_count": len(src.get("pinned_refs", [])),
                "recovery_verified_in_manifest": manifest_exists and (has_sha256 or src["scope"] == "authenticated_archive"),
                "operational_index_separated": True,
            }
        )
    return rows


def run_audit(
    *,
    registry: dict[str, Any] | None = None,
    registry_path: Path | None = None,
    workspace_root: Path | None = None,
    authorized_scopes: set[str] | None = None,
    max_units_per_file: int = 200,
) -> dict[str, Any]:
    """Run full multimodal semantic ingestion and coverage audit across registry sources."""
    root_dir = workspace_root or ROOT_DIR
    reg = registry if registry is not None else source_registry.load_registry(registry_path)
    auth_scopes = authorized_scopes or {"public"}

    source_summaries: list[dict[str, Any]] = []
    file_inventory: list[dict[str, Any]] = []
    excluded_samples: list[dict[str, Any]] = []
    traceable_samples: list[dict[str, Any]] = []
    backlog_gaps: list[dict[str, Any]] = []

    lifecycle_counts: Counter[str] = Counter()
    modality_counts: Counter[str] = Counter()
    mime_counts: Counter[str] = Counter()
    unit_modality_counts: Counter[str] = Counter()
    knowledge_units_total = 0

    for src in reg["sources"]:
        sid = src["source_id"]
        adapter = src["adapter"]
        scope = src["scope"]
        is_auth = scope in auth_scopes or not src.get("authorization_required", False)
        dr = source_registry.dry_run(sid, registry=reg, workspace_root=root_dir, authorized=is_auth)

        src_files_included = 0
        src_files_excluded = 0
        src_units = 0
        src_states: Counter[str] = Counter()

        if adapter != "local_fs":
            # Remote or offline bundle source: check origin status & manifest availability
            manifest_ref = src.get("manifest_ref")
            manifest_ok = bool(manifest_ref and (root_dir / manifest_ref).is_file())
            if src["origin_status"] in {"historical_unavailable", "private_authenticated"} and not is_auth:
                state = "unavailable"
                backlog_gaps.append(
                    {
                        "source_id": sid,
                        "gap_type": "authorization_or_bundle_restore_required",
                        "detail": f"Source '{sid}' ({src['origin_status']}) requires authenticated bundle restoration locally; not indexed publicly.",
                    }
                )
            elif manifest_ok:
                state = "partial"
                backlog_gaps.append(
                    {
                        "source_id": sid,
                        "gap_type": "bundle_blobs_not_mounted_locally",
                        "detail": f"Manifest '{manifest_ref}' is verified locally; full Git objects live in release bundle.",
                    }
                )
            else:
                state = "located"
            src_states[state] += 1
            lifecycle_counts[state] += 1
            source_summaries.append(
                {
                    "source_id": sid,
                    "context_key": src["context_key"],
                    "adapter": adapter,
                    "scope": scope,
                    "license": src["license"],
                    "origin_status": src["origin_status"],
                    "pinned_refs_count": len(src.get("pinned_refs", [])),
                    "files_evaluated": dr["summary"]["total_evaluated"],
                    "files_included": 0,
                    "files_excluded": dr["summary"]["excluded"],
                    "knowledge_units": 0,
                    "lifecycle_states": dict(src_states),
                }
            )
            continue

        rel_root = src.get("root_path", ".")
        base = (root_dir / rel_root).resolve()

        for dec in dr["decisions"]:
            rel_in_src = dec["target"]
            full_rel = (
                (Path(rel_root) / rel_in_src).as_posix()
                if rel_root not in {".", ""}
                else rel_in_src
            )
            while full_rel.startswith("./"):
                full_rel = full_rel[2:]

            if not dec["included"]:
                src_files_excluded += 1
                if len(excluded_samples) < 30:
                    excluded_samples.append(
                        {
                            "source_id": sid,
                            "path": full_rel,
                            "reason_code": dec["reason_code"],
                            "reason_detail": dec["reason_detail"],
                        }
                    )
                continue

            file_path = base / rel_in_src
            if not file_path.is_file():
                lifecycle_counts["unavailable"] += 1
                src_states["unavailable"] += 1
                continue

            src_files_included += 1
            mime = infer_mime_type(full_rel)
            modality = classify_modality(full_rel, src["source_type"])
            mime_counts[mime] += 1
            modality_counts[modality] += 1

            raw = file_path.read_bytes()
            sha256 = _sha256_bytes(raw)
            units: list[dict[str, Any]] = []
            state = "retrieved"

            if modality == "ast_code":
                text = raw.decode("utf-8", errors="replace")
                units = _extract_code_units(file_path, full_rel, text, sha256)[:max_units_per_file]
                state = "verified" if units else "extracted"
            elif modality == "document":
                if file_path.suffix.lower() == ".pdf":
                    # Check native PDF extractability without guessing OCR
                    pdf_res = document_extractor.extract_document_bytes(raw, path=full_rel)
                    if pdf_res.get("uninterpreted_pages"):
                        state = "partial"
                        backlog_gaps.append(
                            {
                                "source_id": sid,
                                "gap_type": "pdf_ocr_needed",
                                "detail": f"PDF '{full_rel}' has image-only pages requiring offline OCR.",
                            }
                        )
                    else:
                        state = "extracted"
                    units = [
                        {
                            "unit_id": f"pdf:{full_rel}:p{s.get('page', 1)}",
                            "modality": "document",
                            "kind": "pdf_section",
                            "name": s.get("title", ""),
                            "observation_status": "verified_native_pdf_stream",
                        }
                        for s in pdf_res.get("sections", [])[:max_units_per_file]
                    ]
                else:
                    units = _extract_document_units(file_path, full_rel, raw, sha256)[:max_units_per_file]
                    state = "verified" if units else "extracted"
            elif modality == "metadata":
                try:
                    parsed_json = json.loads(raw.decode("utf-8"))
                    top_keys = list(parsed_json.keys())[:10] if isinstance(parsed_json, dict) else ["array"]
                    units = [
                        {
                            "unit_id": f"meta:{full_rel}",
                            "modality": "metadata",
                            "kind": "structured_metadata",
                            "keys": top_keys,
                            "observation_status": "verified_json_schema",
                        }
                    ]
                    state = "queryable" if "references" in full_rel or "config/" in full_rel else "indexed"
                except (UnicodeDecodeError, json.JSONDecodeError):
                    state = "extracted"
            elif modality == "media_visual":
                state = "indexed"
                units = [
                    {
                        "unit_id": f"media:file:{full_rel}",
                        "modality": "media_visual",
                        "kind": "binary_media_file",
                        "bytes": len(raw),
                        "observation_status": "blob_sha256_verified_not_visually_inspected",
                    }
                ]

            src_units += len(units)
            knowledge_units_total += len(units)
            unit_modality_counts[modality] += len(units)
            src_states[state] += 1
            lifecycle_counts[state] += 1

            record_entry = {
                "source_id": sid,
                "path": full_rel,
                "sha256": sha256,
                "bytes": len(raw),
                "mime_type": mime,
                "modality": modality,
                "license": src["license"],
                "scope": scope,
                "lifecycle_state": state,
                "knowledge_units": len(units),
            }
            file_inventory.append(record_entry)
            if len(traceable_samples) < 25 and units:
                traceable_samples.append(
                    {
                        **record_entry,
                        "sample_unit": units[0],
                    }
                )

        source_summaries.append(
            {
                "source_id": sid,
                "context_key": src["context_key"],
                "adapter": adapter,
                "scope": scope,
                "license": src["license"],
                "origin_status": src["origin_status"],
                "pinned_refs_count": len(src.get("pinned_refs", [])),
                "files_evaluated": dr["summary"]["total_evaluated"],
                "files_included": src_files_included,
                "files_excluded": src_files_excluded,
                "knowledge_units": src_units,
                "lifecycle_states": dict(sorted(src_states.items())),
            }
        )

    visual_units, visual_stats = _audit_visual_manifests(root_dir)
    # Manifest records are distinct from binary-file units. Reconcile counts without
    # implying unique media objects or semantic review of their contents.
    local_units_total = knowledge_units_total
    unit_modality_counts["media_visual"] += len(visual_units)
    knowledge_units_total += len(visual_units)
    if sum(unit_modality_counts.values()) != knowledge_units_total:
        raise ValueError("Knowledge unit modality accounting mismatch")
    if visual_stats["uninspected_media"] > 0:
        backlog_gaps.append(
            {
                "source_id": "local.visual-evidence-library",
                "gap_type": "visual_semantic_inspection_incomplete",
                "detail": (
                    f"{visual_stats['uninspected_media']} visual media records lack human/sampled-frame "
                    "semantic inspection; never infer UI behavior from filename alone."
                ),
            }
        )

    traceability = _build_traceability_graph(root_dir, file_inventory, visual_units)
    bundle_recovery = _verify_bundle_recovery_coverage(root_dir, reg)

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry_version": reg.get("registry_version"),
        "registry_hash": source_registry.compute_registry_hash(reg),
        "egress_policy": reg["global_policies"]["egress_policy"],
        "lifecycle_vocabulary": list(LIFECYCLE_STATES),
        "summary": {
            "total_sources": len(source_summaries),
            "files_included": len(file_inventory),
            "files_excluded": sum(s["files_excluded"] for s in source_summaries),
            "knowledge_units_total": knowledge_units_total,
            "local_file_units": local_units_total,
            "visual_manifest_units": len(visual_units),
            "unit_count_semantics": "file units plus manifest records; not unique semantic concepts",
            "by_lifecycle_state": dict(sorted(lifecycle_counts.items())),
            "by_modality_files": dict(sorted(modality_counts.items())),
            "by_modality_units": dict(sorted(unit_modality_counts.items())),
            "mime_types_count": len(mime_counts),
            "top_mime_types": dict(mime_counts.most_common(15)),
        },
        "visual_media_audit": visual_stats,
        "traceability_graph": traceability,
        "bundle_recovery_verification": bundle_recovery,
        "sources": source_summaries,
        "traceable_samples": traceable_samples,
        "excluded_samples": excluded_samples,
        "backlog_gaps": backlog_gaps,
    }


def render_markdown_report(audit: dict[str, Any]) -> str:
    """Render deterministic Markdown audit report (Zero Emoji Policy enforced)."""
    s = audit["summary"]
    vis = audit["visual_media_audit"]
    tg = audit["traceability_graph"]
    lines = [
        "# Semantic Ingestion & Source Coverage Audit (#82)",
        "",
        f"- Generated at: `{audit['generated_at']}`",
        f"- Registry version: `{audit['registry_version']}` (`{audit['registry_hash'][:16]}`)",
        f"- Egress policy: `{audit['egress_policy']}`",
        "",
        "## 1. Universe Coverage Summary",
        "",
        f"- Registered sources: **{s['total_sources']}**",
        f"- Local eligible files audited: **{s['files_included']}** (excluded by policy: **{s['files_excluded']}**)",
        f"- Accounted units (local file units + visual manifest records): **{s['knowledge_units_total']}**",
        f"- Local file units: **{s.get('local_file_units', 'not separated')}**; visual manifest records: **{s.get('visual_manifest_units', 'not separated')}**. Counts are not unique concepts or visually inspected images.",
        f"- Distinct MIME types observed: **{s['mime_types_count']}**",
        "",
        "### Lifecycle State Distribution",
        "",
        "| Lifecycle State | Count |",
        "|---|---:|",
    ]
    for state in LIFECYCLE_STATES:
        lines.append(f"| `{state}` | {s['by_lifecycle_state'].get(state, 0)} |")

    lines.extend(
        [
            "",
            "### Modality Coverage",
            "",
            "| Modality | Files | Knowledge Units |",
            "|---|---:|---:|",
        ]
    )
    for mod in MODALITIES:
        lines.append(
            f"| `{mod}` | {s['by_modality_files'].get(mod, 0)} | {s['by_modality_units'].get(mod, 0)} |"
        )

    lines.extend(
        [
            "",
            "## 2. Visual Media Audit (Verified vs Inferred)",
            "",
            f"- Total visual catalog records: **{vis['total_visual_records']}**",
            f"- Verified local blobs (`archived-blob-verified` / declared): **{vis['verified_blobs']}**",
            f"- Link-only external references: **{vis['link_only']}**",
            f"- Sampled frames reviewed (`sampled-frames-reviewed`): **{vis['sampled_frames_reviewed']}**",
            f"- Uninspected visual records (not inferred from filenames): **{vis['uninspected_media']}**",
            f"- Duplicate blob groups (deduplicated by `blob_sha`): **{vis['duplicate_blob_groups']}**",
            "",
            "## 3. Traceability Graph (Requirement -> Decision -> Implementation -> Test -> Visual -> Version)",
            "",
            f"- Total graph nodes: **{tg['nodes_count']}**",
            f"- Total graph edges: **{tg['edges_count']}**",
            f"- Orphan nodes detected: **{tg['orphan_count']}**",
            "",
            "| Node Type | Count |",
            "|---|---:|",
        ]
    )
    for ntype, cnt in tg["node_types"].items():
        lines.append(f"| `{ntype}` | {cnt} |")

    lines.extend(
        [
            "",
            "## 4. Source Inventory & Bundle Recovery",
            "",
            "| Source ID | Adapter | Scope | Origin Status | Files Included | Files Excluded | Units |",
            "|---|---|---|---|---:|---:|---:|",
        ]
    )
    for src in audit["sources"]:
        lines.append(
            f"| `{src['source_id']}` | `{src['adapter']}` | `{src['scope']}` | "
            f"`{src['origin_status']}` | {src['files_included']} | {src['files_excluded']} | {src['knowledge_units']} |"
        )

    lines.extend(["", "## 5. Backlog of Coverage Gaps", ""])
    for gap in audit["backlog_gaps"]:
        lines.append(f"- **[{gap['source_id']}] `{gap['gap_type']}`**: {gap['detail']}")

    text = "\n".join(lines) + "\n"
    if EMOJI_REGEX.search(text):
        raise ValueError("Zero Emoji Policy violated in audit report")
    return text


def write_reports(
    audit: dict[str, Any],
    *,
    json_path: Path | None = None,
    md_path: Path | None = None,
) -> tuple[Path, Path]:
    jpath = json_path or (ROOT_DIR / "reports" / "SEMANTIC-INGESTION-AUDIT.json")
    mpath = md_path or (ROOT_DIR / "reports" / "SEMANTIC-INGESTION-AUDIT.md")
    jpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.parent.mkdir(parents=True, exist_ok=True)

    json_payload = json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
    if EMOJI_REGEX.search(json_payload):
        raise ValueError("Zero Emoji Policy violated in JSON audit report")
    md_payload = render_markdown_report(audit)

    jpath.write_text(json_payload, encoding="utf-8")
    mpath.write_text(md_payload, encoding="utf-8")
    return jpath, mpath


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=ROOT_DIR / "reports" / "SEMANTIC-INGESTION-AUDIT.json")
    parser.add_argument("--md-out", type=Path, default=ROOT_DIR / "reports" / "SEMANTIC-INGESTION-AUDIT.md")
    parser.add_argument("--include-authenticated", action="store_true")
    args = parser.parse_args(argv)

    scopes = {"public", "authenticated_archive"} if args.include_authenticated else {"public"}
    audit = run_audit(registry_path=args.registry, authorized_scopes=scopes)
    jpath, mpath = write_reports(audit, json_path=args.json_out, md_path=args.md_out)
    print(
        json.dumps(
            {
                "ok": True,
                "json_report": str(jpath.relative_to(ROOT_DIR)) if jpath.is_relative_to(ROOT_DIR) else str(jpath),
                "md_report": str(mpath.relative_to(ROOT_DIR)) if mpath.is_relative_to(ROOT_DIR) else str(mpath),
                "summary": audit["summary"],
                "traceability_graph": {
                    "nodes": audit["traceability_graph"]["nodes_count"],
                    "edges": audit["traceability_graph"]["edges_count"],
                    "orphans": audit["traceability_graph"]["orphan_count"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
