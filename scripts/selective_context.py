#!/usr/bin/env python3
"""Selective historical context exporter with token budgets, deduplication, and Repomix evaluation.

Implements a deterministic pipeline:
  search -> SHA/path selection -> Git object recovery -> budgeted context preparation

Supports four delivery modes:
  - metadata-only: provenance, commit dates, deduplicated paths/SHAs, and stats only
  - snippet: bounded targeted line ranges around search matches (no full blobs)
  - exact-file: verified full file contents (bounded by file/byte/line/token budgets)
  - context-pack: grouped-by-file context unit (date/ref/SHA/snippet + optional compact
    structural summary via Repomix Tree-sitter or built-in deterministic fallback)

Standard library only for core operation; optional Repomix CLI integration runs offline
in an isolated temporary workspace after strict secret filtering.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import archive_flow  # noqa: E402
import content_index  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parent

VALID_MODES = ("metadata-only", "snippet", "exact-file", "context-pack")
DEFAULT_MODE = "context-pack"

DEFAULT_MAX_FILES = 10
DEFAULT_MAX_BYTES = 64 * 1024
DEFAULT_MAX_LINES = 400
DEFAULT_MAX_TOKENS = 4000
DEFAULT_SNIPPET_LINES = 11

# Reserve space for top-level envelope metadata when enforcing strict token caps.
MIN_TOKEN_BUDGET = 64
MAX_TOKEN_BUDGET = 200_000

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

# Built-in structural extraction regexes used when Repomix is disabled/unavailable
# or for lightweight deterministic compaction in context-pack mode.
_TS_DECL_RE = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?"
    r"(?:function|class|interface|type|enum|const|let)\s+[A-Za-z0-9_$]+"
)
_PY_DECL_RE = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+[A-Za-z0-9_]+")
_MD_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_IMPORT_RE = re.compile(r"^\s*(?:import\s+|from\s+\S+\s+import\s+|export\s+\{)")

# Extra inline secret patterns beyond content_index.SECRET_PATTERNS
_EXTRA_SECRET_PATTERNS = (
    re.compile(r"\b(?:AWS|AZURE|GCP|SUPABASE|FIREBASE)_[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)\s*[:=]\s*[\"']?[^\s\"']{8,}"),
    re.compile(r"-----BEGIN [A-Z0-9 ]*KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


class SelectiveContextError(archive_flow.ArchiveFlowError):
    """Structured error for selective context pipeline operations."""

    code = "selective_context_error"


@dataclass(frozen=True)
class ContextBudget:
    """Configurable upper bounds for context assembly."""

    max_files: int = DEFAULT_MAX_FILES
    max_bytes: int = DEFAULT_MAX_BYTES
    max_lines: int = DEFAULT_MAX_LINES
    max_tokens: int = DEFAULT_MAX_TOKENS

    def validate(self) -> None:
        if self.max_files < 1:
            raise archive_flow.UnsafeInputError("max_files must be >= 1")
        if self.max_bytes < 128:
            raise archive_flow.UnsafeInputError("max_bytes must be >= 128")
        if self.max_lines < 1:
            raise archive_flow.UnsafeInputError("max_lines must be >= 1")
        if self.max_tokens < MIN_TOKEN_BUDGET or self.max_tokens > MAX_TOKEN_BUDGET:
            raise archive_flow.UnsafeInputError(
                f"max_tokens must be between {MIN_TOKEN_BUDGET} and {MAX_TOKEN_BUDGET}"
            )


def estimate_text_tokens(text: str) -> int:
    """Deterministic token estimator (~4 chars per token, matching archive_flow)."""
    if not text:
        return 0
    return (len(text) + 3) // 4


def estimate_json_tokens(obj: object) -> int:
    serialized = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return estimate_text_tokens(serialized)


def is_secret_or_blocked(path: str, text: str | None = None) -> tuple[bool, str | None]:
    """Strict secret check by path and content patterns."""
    try:
        safe = content_index.safe_path(path)
    except ValueError:
        return True, "unsafe_path"

    if content_index.is_secret_path(safe):
        return True, "secret_path"

    lowered = safe.lower()
    if any(
        token in lowered
        for token in (".env", "id_rsa", "id_ed25519", "private_key", "secret_key", "credentials")
    ):
        return True, "secret_path"

    if text is not None:
        if content_index.contains_secret_content(text):
            return True, "secret_content"
        for pattern in _EXTRA_SECRET_PATTERNS:
            if pattern.search(text):
                return True, "secret_content"
    return False, None


def _read_commit_dates(bare_repo: Path, commit_shas: list[str]) -> dict[str, str]:
    """Fetch ISO author dates for commit SHAs in deterministic batch."""
    dates: dict[str, str] = {}
    for sha in dict.fromkeys(commit_shas):
        try:
            safe_sha = content_index.safe_ref(sha)
        except ValueError:
            continue
        try:
            out = content_index.git(bare_repo, "show", "-s", "--format=%aI", safe_sha).strip()
            dates[safe_sha] = out
        except subprocess.CalledProcessError:
            dates[safe_sha] = ""
    return dates


def _date_sort_key(date_str: str, sha: str) -> tuple[str, str]:
    if not date_str:
        return ("", sha)
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            return (dt.astimezone(timezone.utc).isoformat(), sha)
    except ValueError:
        pass
    return (date_str, sha)


def _safe_truncate_text(
    text: str,
    *,
    max_lines: int,
    max_bytes: int,
    max_tokens: int,
) -> tuple[str, bool, list[str]]:
    """Truncate text cleanly on line boundaries so lines, UTF-8 bytes, and tokens stay within limits."""
    if max_lines <= 0 or max_bytes <= 0 or max_tokens <= 0:
        return "", bool(text), ["budget_exhausted"]

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    reasons: list[str] = []
    truncated = False

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True
        reasons.append("max_lines")

    # Narrow line count until both byte and token limits hold.
    max_chars_by_tokens = max_tokens * 4
    kept: list[str] = []
    running_bytes = 0
    running_chars = 0

    for idx, line in enumerate(lines):
        sep_len = 1 if idx > 0 else 0
        line_bytes = len(line.encode("utf-8")) + sep_len
        line_chars = len(line) + sep_len
        if running_bytes + line_bytes > max_bytes:
            truncated = True
            reasons.append("max_bytes")
            break
        if running_chars + line_chars > max_chars_by_tokens:
            truncated = True
            reasons.append("max_tokens")
            break
        kept.append(line)
        running_bytes += line_bytes
        running_chars += line_chars

    if not kept and lines:
        # First line itself exceeded byte/token budget -> slice safely on UTF-8 char boundary.
        first = lines[0]
        limit_chars = max(0, min(max_chars_by_tokens, max_bytes))
        clipped = first[:limit_chars]
        while len(clipped.encode("utf-8")) > max_bytes and clipped:
            clipped = clipped[:-1]
        if clipped:
            kept = [clipped]
        truncated = True
        if "max_bytes" not in reasons and "max_tokens" not in reasons:
            reasons.append("max_tokens")

    return "\n".join(kept), truncated, sorted(set(reasons))


def _structural_outline(text: str, language: str) -> str:
    """Deterministic zero-dependency structural compaction fallback."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    selected: list[str] = []
    seen_idx: set[int] = set()

    def add_line(i: int) -> None:
        if 0 <= i < len(lines) and i not in seen_idx:
            seen_idx.add(i)
            selected.append(f"{i + 1}: {lines[i]}")

    for i, line in enumerate(lines):
        if _IMPORT_RE.match(line):
            add_line(i)
            continue
        if language in {"typescript", "tsx", "javascript", "jsx"} and _TS_DECL_RE.match(line):
            add_line(i)
            # Capture signature closing line if multiline interface/function header.
            if line.rstrip().endswith("{") is False and i + 1 < len(lines):
                add_line(i + 1)
        elif language == "python" and _PY_DECL_RE.match(line):
            add_line(i)
            if i + 1 < len(lines) and lines[i + 1].strip().startswith(('"""', "'''")):
                add_line(i + 1)
        elif language in {"markdown", "mdx"} and _MD_HEADING_RE.match(line):
            add_line(i)
            if i + 1 < len(lines) and lines[i + 1].strip():
                add_line(i + 1)

    if not selected:
        # Fallback to first non-empty lines when no declarations matched.
        for i, line in enumerate(lines[:10]):
            if line.strip():
                add_line(i)
    return "\n".join(selected)


def _find_repomix_command() -> list[str] | None:
    repomix_bin = shutil.which("repomix")
    if repomix_bin:
        return [repomix_bin]
    return None


def _compact_with_repomix(
    files: dict[str, str],
    *,
    compress: bool = True,
    style: str = "xml",
    timeout: float = 30.0,
) -> dict[str, object]:
    """Run Repomix offline on already-sanitized selected files inside a clean temp directory.

    Never reads secrets or full repository directories; only writes the sanitized
    selected relative paths to an isolated temp dir and extracts per-file blocks.
    """
    for rel_path, body in files.items():
        safe_rel = content_index.safe_path(rel_path)
        blocked, reason = is_secret_or_blocked(safe_rel, body)
        if blocked:
            raise archive_flow.PermissionDeniedError(
                f"Refusing to stage secret/blocked file '{rel_path}': {reason}"
            )

    cmd_base = _find_repomix_command()
    if cmd_base is None:
        return {
            "used": False,
            "reason": "repomix_unavailable",
            "packed_output": "",
            "per_file": {},
            "elapsed_ms": 0.0,
        }
    if not files:
        return {
            "used": False,
            "reason": "no_files",
            "packed_output": "",
            "per_file": {},
            "elapsed_ms": 0.0,
        }

    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="selective-repomix-") as tmp:
        stage_dir = Path(tmp) / "stage"
        stage_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, body in files.items():
            safe_rel = content_index.safe_path(rel_path)
            blocked, reason = is_secret_or_blocked(safe_rel, body)
            if blocked:
                raise archive_flow.PermissionDeniedError(
                    f"Blocked secret before Repomix staging: {safe_rel}",
                    details={"path": safe_rel, "reason": reason},
                )
            dest = stage_dir / safe_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding="utf-8")

        cmd = [
            *cmd_base,
            "--style",
            style,
            "--no-file-summary",
            "--no-directory-structure",
            "--no-gitignore",
            "--no-dot-ignore",
            "--output",
            "-",
        ]
        if compress:
            cmd.append("--compress")
        cmd.append(str(stage_dir))

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            return {
                "used": False,
                "reason": f"repomix_error: {exc}",
                "packed_output": "",
                "per_file": {},
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            }

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        if proc.returncode != 0:
            return {
                "used": False,
                "reason": f"repomix_exit_{proc.returncode}: {proc.stderr.strip()[:200]}",
                "packed_output": "",
                "per_file": {},
                "elapsed_ms": elapsed_ms,
            }

        packed = proc.stdout
        per_file: dict[str, str] = {}
        if style == "xml":
            for match in re.finditer(r'<file path="([^"]+)">\n?(.*?)\n?</file>', packed, re.DOTALL):
                per_file[match.group(1)] = match.group(2).strip()
        return {
            "used": True,
            "reason": "ok",
            "packed_output": packed,
            "per_file": per_file,
            "elapsed_ms": elapsed_ms,
        }


def search_stage(
    query: str,
    *,
    db_path: Path | None = None,
    source: Path | None = None,
    repo: str | None = None,
    ref: str | None = None,
    extension: str | None = None,
    language: str | None = None,
    status: str | None = None,
    limit: int = 30,
    snippet_lines: int = DEFAULT_SNIPPET_LINES,
    match_all: bool = True,
) -> tuple[list[dict], dict[str, int]]:
    """Stage 1: Search FTS5 content index (and optionally build temporary index from source)."""
    if not isinstance(query, str) or not query.strip():
        raise archive_flow.UnsafeInputError("Search query must not be empty")
    if len(query) > 200 or query.lstrip().startswith("-") or any(ord(ch) < 32 for ch in query):
        raise archive_flow.UnsafeInputError("Unsafe search query")

    raw_hits: list[dict] = []
    if db_path is not None and db_path.exists():
        conn = content_index.open_db(db_path)
        try:
            raw_hits = content_index.search(
                conn,
                query,
                repo=repo,
                ref=ref,
                extension=extension,
                language=language,
                status=status,
                limit=limit,
                snippet_lines=snippet_lines,
                match_all=match_all,
            )
            if not raw_hits and match_all:
                raw_hits = content_index.search(
                    conn,
                    query,
                    repo=repo,
                    ref=ref,
                    extension=extension,
                    language=language,
                    status=status,
                    limit=limit,
                    snippet_lines=snippet_lines,
                    match_all=False,
                )
        finally:
            conn.close()
    elif source is not None:
        if not source.exists():
            raise archive_flow.NotFoundError(f"Source repository or bundle not found: {source}")
        with tempfile.TemporaryDirectory(prefix="selective-index-") as tmp:
            temp_db = Path(tmp) / "content.sqlite"
            conn = content_index.open_db(temp_db)
            try:
                repo_name = repo or source.stem or "archive-source"
                content_index.ingest_repo(source, repo_name, conn, all_commits=True)
                raw_hits = content_index.search(
                    conn,
                    query,
                    repo=repo,
                    ref=ref,
                    extension=extension,
                    language=language,
                    status=status,
                    limit=limit,
                    snippet_lines=snippet_lines,
                    match_all=match_all,
                )
                if not raw_hits and match_all:
                    raw_hits = content_index.search(
                        conn,
                        query,
                        repo=repo,
                        ref=ref,
                        extension=extension,
                        language=language,
                        status=status,
                        limit=limit,
                        snippet_lines=snippet_lines,
                        match_all=False,
                    )
            finally:
                conn.close()
    else:
        raise archive_flow.UnsafeInputError("Provide --db or --source")

    safe_hits: list[dict] = []
    blocked_count = 0
    for hit in raw_hits:
        blocked, _reason = is_secret_or_blocked(hit.get("path", ""), hit.get("snippet", ""))
        if blocked:
            blocked_count += 1
            continue
        safe_hits.append(hit)

    return safe_hits, {
        "raw_hits": len(raw_hits),
        "blocked_secret_hits": blocked_count,
        "safe_hits": len(safe_hits),
    }


def select_candidates(
    hits: list[dict],
    *,
    deduplicate: bool = True,
    max_files: int = DEFAULT_MAX_FILES,
    commit_dates: dict[str, str] | None = None,
) -> tuple[list[dict], dict[str, int]]:
    """Stage 2: Select and deduplicate SHA/path candidates (Issue #16 + #8 grouped format)."""
    if max_files < 1:
        raise archive_flow.UnsafeInputError("max_files must be >= 1")
    commit_dates = commit_dates or {}

    if not deduplicate:
        selected = []
        for idx, hit in enumerate(hits[:max_files]):
            sha = hit["commit_sha"]
            cdate = commit_dates.get(sha, "")
            selected.append(
                {
                    "selection_id": f"raw-{idx}",
                    "repository": hit["repository"],
                    "path": hit["path"],
                    "ref": hit["ref"],
                    "commit_sha": sha,
                    "commit_date": cdate,
                    "blob_sha": hit["blob_sha"],
                    "language": hit["language"],
                    "extension": hit["extension"],
                    "status": hit["status"],
                    "score": float(hit.get("score", 0.0)),
                    "commits_matched": 1,
                    "first_sha": sha,
                    "last_sha": sha,
                    "history": [
                        {
                            "commit_sha": sha,
                            "date": cdate,
                            "ref": hit["ref"],
                            "status": hit["status"],
                            "blob_sha": hit["blob_sha"],
                        }
                    ],
                    "snippets": [
                        {
                            "start_line": int(hit["start_line"]),
                            "end_line": int(hit["end_line"]),
                            "snippet": hit["snippet"],
                        }
                    ],
                }
            )
        return selected, {
            "input_hits": len(hits),
            "unique_paths": len({(h["repository"], h["path"]) for h in hits}),
            "unique_blobs": len({h["blob_sha"] for h in hits}),
            "deduped_removed": 0,
            "selected_count": len(selected),
            "dropped_by_max_files": max(0, len(hits) - len(selected)),
        }

    # Group by (repository, path) first to aggregate commit timeline (#8),
    # then deduplicate identical blob_sha copies across paths (#16).
    grouped_by_path: dict[tuple[str, str], dict] = {}
    for hit in hits:
        key = (hit["repository"], hit["path"])
        sha = hit["commit_sha"]
        cdate = commit_dates.get(sha, "")
        score = float(hit.get("score", 0.0))
        entry = grouped_by_path.get(key)
        hist_item = {
            "commit_sha": sha,
            "date": cdate,
            "ref": hit["ref"],
            "status": hit["status"],
            "blob_sha": hit["blob_sha"],
        }
        snippet_item = {
            "start_line": int(hit["start_line"]),
            "end_line": int(hit["end_line"]),
            "snippet": hit["snippet"],
        }
        if entry is None:
            grouped_by_path[key] = {
                "repository": hit["repository"],
                "path": hit["path"],
                "ref": hit["ref"],
                "commit_sha": sha,
                "commit_date": cdate,
                "blob_sha": hit["blob_sha"],
                "language": hit["language"],
                "extension": hit["extension"],
                "status": hit["status"],
                "score": score,
                "best_sort": _date_sort_key(cdate, sha),
                "first_sort": _date_sort_key(cdate, sha),
                "last_sort": _date_sort_key(cdate, sha),
                "first_sha": sha,
                "last_sha": sha,
                "history_map": {(sha, hit["ref"], hit["blob_sha"]): hist_item},
                "snippet_map": {
                    (snippet_item["start_line"], snippet_item["end_line"]): snippet_item
                },
            }
        else:
            if score < entry["score"]:
                entry["score"] = score
            sort_k = _date_sort_key(cdate, sha)
            if sort_k < entry["first_sort"]:
                entry["first_sort"] = sort_k
                entry["first_sha"] = sha
            if sort_k >= entry["last_sort"]:
                entry["last_sort"] = sort_k
                entry["last_sha"] = sha
                entry["commit_sha"] = sha
                entry["commit_date"] = cdate
                entry["ref"] = hit["ref"]
                entry["blob_sha"] = hit["blob_sha"]
                entry["status"] = hit["status"]
            entry["history_map"][(sha, hit["ref"], hit["blob_sha"])] = hist_item
            entry["snippet_map"][(snippet_item["start_line"], snippet_item["end_line"])] = snippet_item

    ranked_paths = sorted(
        grouped_by_path.values(),
        key=lambda e: (e["score"], e["repository"], e["path"]),
    )

    # Deduplicate identical blob content across distinct paths (keep highest ranked, record aliases).
    selected: list[dict] = []
    by_blob: dict[str, dict] = {}
    blob_dupes_collapsed = 0

    for item in ranked_paths:
        bsha = item["blob_sha"]
        history_sorted = sorted(
            item["history_map"].values(),
            key=lambda h: _date_sort_key(h["date"], h["commit_sha"]),
        )
        snippets_sorted = sorted(
            item["snippet_map"].values(),
            key=lambda s: (s["start_line"], s["end_line"]),
        )
        existing = by_blob.get(bsha)
        if existing is not None:
            blob_dupes_collapsed += 1
            existing["duplicate_paths"].append(
                {
                    "repository": item["repository"],
                    "path": item["path"],
                    "ref": item["ref"],
                    "commit_sha": item["commit_sha"],
                }
            )
            continue

        candidate = {
            "selection_id": f"sel-{len(selected)}",
            "repository": item["repository"],
            "path": item["path"],
            "ref": item["ref"],
            "commit_sha": item["commit_sha"],
            "commit_date": item["commit_date"],
            "blob_sha": bsha,
            "language": item["language"],
            "extension": item["extension"],
            "status": item["status"],
            "score": round(item["score"], 6),
            "commits_matched": len({h["commit_sha"] for h in history_sorted}),
            "first_sha": item["first_sha"],
            "last_sha": item["last_sha"],
            "history": history_sorted,
            "snippets": snippets_sorted,
            "duplicate_paths": [],
        }
        by_blob[bsha] = candidate
        selected.append(candidate)

    bounded = selected[:max_files]
    return bounded, {
        "input_hits": len(hits),
        "unique_paths": len(grouped_by_path),
        "unique_blobs": len(by_blob),
        "deduped_removed": len(hits) - len(selected),
        "blob_duplicates_collapsed": blob_dupes_collapsed,
        "selected_count": len(bounded),
        "dropped_by_max_files": max(0, len(selected) - len(bounded)),
    }


def recover_stage(
    source: Path,
    selected: list[dict],
    *,
    mode: str,
    max_file_bytes: int = DEFAULT_MAX_BYTES,
) -> tuple[list[dict], dict[str, int]]:
    """Stage 3: Recover verified Git blobs/lines for selected candidates (with secret gate)."""
    if mode not in VALID_MODES:
        raise archive_flow.UnsafeInputError(f"Unsupported mode: {mode!r}")

    recovered_items: list[dict] = []
    blocked_secrets = 0
    skipped_binary = 0

    with tempfile.TemporaryDirectory(prefix="selective-recover-") as tmp:
        bare_repo, _source_type, _attempts = archive_flow._open_bare_repo_with_retry(
            source, Path(tmp)
        )
        # Fetch commit dates if missing from selection stage.
        missing_date_shas = [
            item["commit_sha"] for item in selected if not item.get("commit_date")
        ]
        dates = _read_commit_dates(bare_repo, missing_date_shas)

        blob_cache: dict[str, tuple[bytes, str]] = {}

        for item in selected:
            safe_rel = archive_flow.validate_path(item["path"])
            full_sha = archive_flow.validate_commit_sha(item["commit_sha"])

            blocked, reason = is_secret_or_blocked(safe_rel)
            if blocked:
                blocked_secrets += 1
                continue

            commit_date = item.get("commit_date") or dates.get(full_sha, "")
            history = []
            for h in item.get("history", []):
                h_copy = dict(h)
                if not h_copy.get("date"):
                    h_copy["date"] = dates.get(h_copy["commit_sha"], "")
                history.append(h_copy)

            base_record = {
                "repository": item["repository"],
                "path": safe_rel,
                "ref": item["ref"],
                "commit_sha": full_sha,
                "commit_date": commit_date,
                "blob_sha": item["blob_sha"],
                "language": item["language"],
                "extension": item["extension"],
                "status": item["status"],
                "score": item["score"],
                "commits_matched": item["commits_matched"],
                "first_sha": item["first_sha"],
                "last_sha": item["last_sha"],
                "history": history,
                "duplicate_paths": item.get("duplicate_paths", []),
                "provenance": f"{item['repository']}@{full_sha}:{safe_rel}",
            }

            if mode == "metadata-only":
                base_record["snippets_meta"] = [
                    {"start_line": s["start_line"], "end_line": s["end_line"]}
                    for s in item.get("snippets", [])
                ]
                recovered_items.append(base_record)
                continue

            # For snippet, exact-file, context-pack: verify blob from Git object store.
            cache_key = f"{full_sha}:{safe_rel}"
            if cache_key not in blob_cache:
                blob_sha, raw_bytes, actual_sha256, _att = archive_flow._read_git_object(
                    bare_repo,
                    full_sha=full_sha,
                    path=safe_rel,
                    expected_blob_sha=item.get("blob_sha") or None,
                    max_bytes=max(max_file_bytes, 1024 * 1024),
                )
                blob_cache[cache_key] = (raw_bytes, actual_sha256)
            else:
                raw_bytes, actual_sha256 = blob_cache[cache_key]

            if content_index.is_binary_bytes(raw_bytes):
                skipped_binary += 1
                continue

            full_text = raw_bytes.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
            blocked, reason = is_secret_or_blocked(safe_rel, full_text)
            if blocked:
                blocked_secrets += 1
                continue

            lines = full_text.split("\n")
            if lines and lines[-1] == "":
                lines.pop()

            base_record["sha256"] = actual_sha256
            base_record["bytes_total"] = len(raw_bytes)
            base_record["lines_total"] = len(lines)
            base_record["full_text"] = full_text
            base_record["snippets"] = item.get("snippets", [])
            recovered_items.append(base_record)

    return recovered_items, {
        "recovered_count": len(recovered_items),
        "blocked_secrets": blocked_secrets,
        "skipped_binary": skipped_binary,
    }


def prepare_context(
    recovered_items: list[dict],
    *,
    mode: str = DEFAULT_MODE,
    budget: ContextBudget | None = None,
    use_repomix: bool = False,
    repomix_compress: bool = True,
) -> dict:
    """Stage 4: Assemble budgeted context package with provenance and safe truncation."""
    if mode not in VALID_MODES:
        raise archive_flow.UnsafeInputError(f"Unsupported mode: {mode!r}")
    budget = budget or ContextBudget()
    budget.validate()

    # Optional Repomix structural compaction on non-secret selected texts.
    repomix_meta: dict[str, object] = {
        "requested": use_repomix,
        "used": False,
        "reason": "not_requested",
        "elapsed_ms": 0.0,
    }
    compacted_by_path: dict[str, str] = {}
    if use_repomix and mode == "context-pack" and recovered_items:
        repomix_inputs: dict[str, str] = {}
        for item in recovered_items[: budget.max_files]:
            repomix_inputs[item["path"]] = item.get("full_text", "")
        repomix_res = _compact_with_repomix(
            repomix_inputs,
            compress=repomix_compress,
            style="xml",
        )
        repomix_meta = {
            "requested": True,
            "used": bool(repomix_res["used"]),
            "reason": repomix_res["reason"],
            "elapsed_ms": repomix_res["elapsed_ms"],
        }
        if repomix_res["used"]:
            compacted_by_path = dict(repomix_res.get("per_file", {}))  # type: ignore[arg-type]

    # Reserve deterministic overhead for envelope + outer pipeline metadata fields.
    envelope_reserve_tokens = 140
    remaining_tokens = max(16, budget.max_tokens - envelope_reserve_tokens)
    remaining_bytes = budget.max_bytes
    remaining_lines = budget.max_lines

    delivered_items: list[dict] = []
    truncated_items = 0
    dropped_by_budget = 0

    for item in recovered_items[: budget.max_files]:
        if remaining_tokens <= 8 or remaining_bytes <= 32 or remaining_lines <= 0:
            dropped_by_budget += 1
            continue

        entry: dict = {
            "repository": item["repository"],
            "path": item["path"],
            "ref": item["ref"],
            "commit_sha": item["commit_sha"],
            "commit_date": item["commit_date"],
            "blob_sha": item["blob_sha"],
            "language": item["language"],
            "status": item["status"],
            "commits_matched": item["commits_matched"],
            "first_sha": item["first_sha"],
            "last_sha": item["last_sha"],
            "provenance": item["provenance"],
        }
        if item.get("duplicate_paths"):
            entry["duplicate_paths"] = item["duplicate_paths"]

        if mode == "metadata-only":
            entry["summary"] = (
                f"{item['path']} changed in {item['commits_matched']} commit(s) "
                f"from {item['first_sha'][:10]} to {item['last_sha'][:10]}"
            )
            entry["history"] = item.get("history", [])
            entry["snippets_meta"] = item.get("snippets_meta", [])
            item_tokens = estimate_json_tokens(entry)
            item_bytes = len(json.dumps(entry, ensure_ascii=False).encode("utf-8"))
            if item_tokens > remaining_tokens or item_bytes > remaining_bytes:
                # Try dropping verbose history list to preserve metadata entry within budget.
                entry["history"] = entry["history"][:2]
                entry["truncated"] = True
                item_tokens = estimate_json_tokens(entry)
                item_bytes = len(json.dumps(entry, ensure_ascii=False).encode("utf-8"))
            if item_tokens > remaining_tokens or item_bytes > remaining_bytes:
                dropped_by_budget += 1
                continue
            remaining_tokens -= item_tokens
            remaining_bytes -= item_bytes
            delivered_items.append(entry)
            continue

        entry["sha256"] = item["sha256"]
        entry["bytes_total"] = item["bytes_total"]
        entry["lines_total"] = item["lines_total"]

        if mode == "snippet":
            snippets = item.get("snippets", [])
            raw_body = "\n---\n".join(
                f"# lines {s['start_line']}-{s['end_line']}\n{s['snippet']}"
                for s in snippets
            )
        elif mode == "exact-file":
            raw_body = item.get("full_text", "")
        else:  # context-pack
            snippets = item.get("snippets", [])
            compact_snippets = snippets[:1]
            snippet_block = "\n".join(
                f"[lines {s['start_line']}-{s['end_line']}]\n{s['snippet']}"
                for s in compact_snippets
            )
            if item["path"] in compacted_by_path:
                structure_block = compacted_by_path[item["path"]]
                compaction_method = "repomix-tree-sitter"
            else:
                structure_block = _structural_outline(item.get("full_text", ""), item["language"])
                compaction_method = "builtin-outline"
            entry["compaction"] = compaction_method
            raw_body = (
                f"## {item['path']} ({item['ref']} @ {item['commit_sha'][:12]} | {item['commit_date']})\n"
                f"Changed in {item['commits_matched']} commit(s): {item['first_sha'][:10]}..{item['last_sha'][:10]}\n"
                f"### Structure\n{structure_block}\n"
                f"### Matched Snippets\n{snippet_block}"
            )

        # Account for entry header overhead before truncating content payload.
        header_tokens = estimate_json_tokens(entry) + 16
        avail_tokens = remaining_tokens - header_tokens
        if avail_tokens <= 4:
            dropped_by_budget += 1
            continue

        clipped_body, was_truncated, trunc_reasons = _safe_truncate_text(
            raw_body,
            max_lines=remaining_lines,
            max_bytes=remaining_bytes,
            max_tokens=avail_tokens,
        )
        if not clipped_body:
            dropped_by_budget += 1
            continue

        body_lines = clipped_body.count("\n") + 1
        body_bytes = len(clipped_body.encode("utf-8"))
        body_tokens = estimate_text_tokens(clipped_body)

        entry["content"] = clipped_body
        entry["delivered_lines"] = body_lines
        entry["delivered_bytes"] = body_bytes
        entry["estimated_tokens"] = header_tokens + body_tokens
        entry["truncated"] = was_truncated
        if trunc_reasons:
            entry["truncation_reasons"] = trunc_reasons
        if was_truncated:
            truncated_items += 1

        remaining_lines = max(0, remaining_lines - body_lines)
        remaining_bytes = max(0, remaining_bytes - body_bytes)
        remaining_tokens = max(0, remaining_tokens - entry["estimated_tokens"])
        delivered_items.append(entry)

    def _build_envelope(items_list: list[dict], dropped_count: int) -> dict:
        t_bytes = sum(i.get("delivered_bytes", 0) for i in items_list)
        t_lines = sum(i.get("delivered_lines", 0) for i in items_list)
        t_tokens = sum(estimate_text_tokens(i.get("content", "")) for i in items_list)
        t_trunc = sum(1 for i in items_list if i.get("truncated"))
        env = {
            "ok": True,
            "mode": mode,
            "repomix": repomix_meta,
            "budget": {
                "max_files": budget.max_files,
                "max_bytes": budget.max_bytes,
                "max_lines": budget.max_lines,
                "max_tokens": budget.max_tokens,
            },
            "usage": {
                "files": len(items_list),
                "content_bytes": t_bytes,
                "content_lines": t_lines,
                "content_tokens": t_tokens,
                "truncated_items": t_trunc,
                "dropped_by_budget": dropped_count,
                "total_estimated_tokens": 0,
            },
            "items": items_list,
        }
        est = estimate_json_tokens(env)
        env["usage"]["total_estimated_tokens"] = est
        # Adding digits of `est` can change char length by up to ~5 chars (+2 tokens).
        final_est = estimate_json_tokens(env)
        env["usage"]["total_estimated_tokens"] = final_est
        return env

    result = _build_envelope(delivered_items, dropped_by_budget)
    # Final hard guard so total serialized payload never exceeds budget.max_tokens
    while result["usage"]["total_estimated_tokens"] > budget.max_tokens and delivered_items:
        excess_tokens = result["usage"]["total_estimated_tokens"] - budget.max_tokens
        last = delivered_items[-1]
        if "content" in last and len(last["content"]) > 40 and estimate_text_tokens(last["content"]) > excess_tokens + 8:
            new_tok_limit = max(4, estimate_text_tokens(last["content"]) - excess_tokens - 8)
            clipped, _, reasons = _safe_truncate_text(
                last["content"],
                max_lines=last["delivered_lines"],
                max_bytes=last["delivered_bytes"],
                max_tokens=new_tok_limit,
            )
            if clipped:
                last["content"] = clipped
                last["delivered_lines"] = clipped.count("\n") + 1
                last["delivered_bytes"] = len(clipped.encode("utf-8"))
                last["truncated"] = True
                last["truncation_reasons"] = sorted(set(last.get("truncation_reasons", []) + reasons + ["max_tokens"]))
                result = _build_envelope(delivered_items, dropped_by_budget)
                continue
        delivered_items.pop()
        dropped_by_budget += 1
        result = _build_envelope(delivered_items, dropped_by_budget)
    return result


def run_pipeline(
    query: str,
    *,
    source: Path,
    db_path: Path | None = None,
    repo: str | None = None,
    ref: str | None = None,
    extension: str | None = None,
    language: str | None = None,
    status: str | None = None,
    mode: str = DEFAULT_MODE,
    deduplicate: bool = True,
    use_repomix: bool = False,
    repomix_compress: bool = True,
    search_limit: int = 40,
    snippet_lines: int = DEFAULT_SNIPPET_LINES,
    budget: ContextBudget | None = None,
) -> dict:
    """End-to-end selective context export pipeline."""
    t0 = time.perf_counter()
    budget = budget or ContextBudget()
    budget.validate()
    if mode not in VALID_MODES:
        raise archive_flow.UnsafeInputError(f"Unsupported mode: {mode!r}")

    hits, search_stats = search_stage(
        query,
        db_path=db_path,
        source=source,
        repo=repo,
        ref=ref,
        extension=extension,
        language=language,
        status=status,
        limit=search_limit,
        snippet_lines=snippet_lines,
    )

    commit_dates: dict[str, str] = {}
    if hits:
        with tempfile.TemporaryDirectory(prefix="selective-dates-") as tmp:
            bare_repo, _, _ = archive_flow._open_bare_repo_with_retry(source, Path(tmp))
            commit_dates = _read_commit_dates(
                bare_repo, [h["commit_sha"] for h in hits]
            )

    selected, selection_stats = select_candidates(
        hits,
        deduplicate=deduplicate,
        max_files=budget.max_files,
        commit_dates=commit_dates,
    )

    recovered, recovery_stats = recover_stage(
        source,
        selected,
        mode=mode,
        max_file_bytes=budget.max_bytes,
    )

    packaged = prepare_context(
        recovered,
        mode=mode,
        budget=budget,
        use_repomix=use_repomix,
        repomix_compress=repomix_compress,
    )
    packaged["query"] = query
    packaged["deduplicate"] = deduplicate
    packaged["pipeline"] = {
        "search": search_stats,
        "selection": selection_stats,
        "recovery": recovery_stats,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }
    packaged["usage"]["total_estimated_tokens"] = estimate_json_tokens(packaged)
    while packaged["usage"]["total_estimated_tokens"] > budget.max_tokens and packaged["items"]:
        excess = packaged["usage"]["total_estimated_tokens"] - budget.max_tokens
        last = packaged["items"][-1]
        if "content" in last and estimate_text_tokens(last["content"]) > excess + 12:
            new_tok = max(4, estimate_text_tokens(last["content"]) - excess - 12)
            clipped, _, reasons = _safe_truncate_text(
                last["content"],
                max_lines=last["delivered_lines"],
                max_bytes=last["delivered_bytes"],
                max_tokens=new_tok,
            )
            if clipped:
                last["content"] = clipped
                last["delivered_lines"] = clipped.count("\n") + 1
                last["delivered_bytes"] = len(clipped.encode("utf-8"))
                last["truncated"] = True
                last["truncation_reasons"] = sorted(
                    set(last.get("truncation_reasons", []) + reasons + ["max_tokens"])
                )
                packaged["usage"]["content_bytes"] = sum(
                    i.get("delivered_bytes", 0) for i in packaged["items"]
                )
                packaged["usage"]["content_lines"] = sum(
                    i.get("delivered_lines", 0) for i in packaged["items"]
                )
                packaged["usage"]["content_tokens"] = sum(
                    estimate_text_tokens(i.get("content", "")) for i in packaged["items"]
                )
                packaged["usage"]["truncated_items"] = sum(
                    1 for i in packaged["items"] if i.get("truncated")
                )
                packaged["usage"]["total_estimated_tokens"] = estimate_json_tokens(packaged)
                continue
        packaged["items"].pop()
        packaged["usage"]["files"] = len(packaged["items"])
        packaged["usage"]["dropped_by_budget"] += 1
        packaged["usage"]["content_bytes"] = sum(
            i.get("delivered_bytes", 0) for i in packaged["items"]
        )
        packaged["usage"]["content_lines"] = sum(
            i.get("delivered_lines", 0) for i in packaged["items"]
        )
        packaged["usage"]["content_tokens"] = sum(
            estimate_text_tokens(i.get("content", "")) for i in packaged["items"]
        )
        packaged["usage"]["truncated_items"] = sum(
            1 for i in packaged["items"] if i.get("truncated")
        )
        packaged["usage"]["total_estimated_tokens"] = estimate_json_tokens(packaged)
    packaged["usage"]["total_estimated_tokens"] = estimate_json_tokens(packaged)
    return packaged


def _build_synthetic_benchmark_repo(root: Path) -> tuple[Path, Path, Path]:
    """Create a realistic multi-language synthetic Git repo + FTS5 DB for reproducible benchmarking."""
    work = root / "bench_repo"
    work.mkdir(parents=True, exist_ok=True)

    def git_cmd(*args: str) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=work,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return proc.stdout

    git_cmd("init", "-q", "-b", "main")
    git_cmd("config", "user.email", "bench@example.invalid")
    git_cmd("config", "user.name", "Benchmark Suite")

    (work / "src" / "components" / "ui").mkdir(parents=True, exist_ok=True)
    (work / "src" / "domain").mkdir(parents=True, exist_ok=True)
    (work / "src" / "unrelated").mkdir(parents=True, exist_ok=True)
    (work / "docs").mkdir(parents=True, exist_ok=True)

    # 1. TypeScript component with multiple historical versions (simulates #16 14x sidebar repeats)
    ts_base = "\n".join(
        [
            "import React, { useState } from 'react';",
            "import { PanelHeader } from './panel-header';",
            "",
            "export interface SidebarConfig {",
            "  collapsed: boolean;",
            "  widthPx: number;",
            "  theme: 'light' | 'dark';",
            "}",
            "",
            "export interface SidebarItem {",
            "  id: string;",
            "  label: string;",
            "  route: string;",
            "}",
            "",
            "export function computeSidebarWidth(config: SidebarConfig): number {",
            "  if (config.collapsed) {",
            "    return 64;",
            "  }",
            "  const clamped = Math.max(180, Math.min(420, config.widthPx));",
            "  // Layout padding compensation for docked panels",
        ]
        + [f"  const slot_{i} = 'slot-{i}';" for i in range(1, 55)]
        + [
            "  return clamped;",
            "}",
            "",
            "export function SidebarNavigation({ items, config }: { items: SidebarItem[]; config: SidebarConfig }) {",
            "  const [collapsed, setCollapsed] = useState(config.collapsed);",
            "  const width = computeSidebarWidth({ ...config, collapsed });",
            "  return (",
            '    <aside data-panel="capacities-sidebar" style={{ width }}>',
            "      <PanelHeader title=\"Navigation\" onToggle={() => setCollapsed((v) => !v)} />",
            "      <ul>{items.map((it) => <li key={it.id}>{it.label}</li>)}</ul>",
            "    </aside>",
            "  );",
            "}",
        ]
    )

    # 2. Python backend helper
    py_text = "\n".join(
        [
            '"""Sidebar state persistence and FSRS deck grouping."""',
            "from dataclasses import dataclass",
            "",
            "@dataclass",
            "class SidebarState:",
            "    collapsed: bool",
            "    active_deck: str",
            "    pinned_ids: list[str]",
            "",
            "def normalize_sidebar_state(raw: dict) -> SidebarState:",
            "    collapsed = bool(raw.get('collapsed', False))",
            "    deck = str(raw.get('active_deck', 'all')).strip() or 'all'",
            "    pinned = [str(x) for x in raw.get('pinned_ids', []) if str(x)]",
            "    # Keep deterministic ordering for snapshots",
        ]
        + [f"    _pad_{i} = {i}" for i in range(1, 45)]
        + [
            "    return SidebarState(collapsed=collapsed, active_deck=deck, pinned_ids=sorted(set(pinned)))",
            "",
            "def summarize_sidebar_badges(state: SidebarState) -> dict[str, int]:",
            "    return {'pinned_count': len(state.pinned_ids), 'collapsed': int(state.collapsed)}",
        ]
    )

    # 3. Markdown specification
    md_text = "\n".join(
        [
            "# Capacities Sidebar Architecture",
            "",
            "## Decision Record",
            "The sidebar component exposes `computeSidebarWidth` and `SidebarNavigation`.",
            "Historical commits refined collapsed rail width from 48px to 64px.",
            "",
            "## Requirements",
        ]
        + [f"- Requirement item {i}: preserve deterministic layout and keyboard focus." for i in range(1, 20)]
    )

    # 4. Unrelated modules in repo to measure selective search vs full-repo packing
    for mod_idx in range(1, 8):
        unrelated_body = "\n".join(
            [f"// Unrelated module {mod_idx}"]
            + [f"export const UNRELATED_{mod_idx}_{j} = 'value-{j}';" for j in range(1, 45)]
        )
        (work / "src" / "unrelated" / f"module_{mod_idx}.ts").write_text(
            unrelated_body, encoding="utf-8"
        )

    # 5. Duplicate blob copied across legacy path (tests blob deduplication)
    (work / "src" / "components" / "ui" / "sidebar.tsx").write_text(ts_base, encoding="utf-8")
    (work / "src" / "components" / "ui" / "sidebar.legacy.tsx").write_text(ts_base, encoding="utf-8")
    (work / "src" / "domain" / "sidebar_state.py").write_text(py_text, encoding="utf-8")
    (work / "docs" / "SIDEBAR-SPEC.md").write_text(md_text, encoding="utf-8")
    # Secret file that must never leak into benchmark exports
    (work / ".env").write_text("API_SECRET=sk_test_syntheticBenchSecret9999999\n", encoding="utf-8")

    git_cmd("add", ".")
    git_cmd("commit", "-qm", "feat: initial sidebar implementation")

    # Add multiple historical revisions of sidebar.tsx across commits + branches
    for rev in range(1, 6):
        updated_ts = ts_base.replace("return 64;", f"return {64 + rev * 2}; // rev {rev}")
        (work / "src" / "components" / "ui" / "sidebar.tsx").write_text(updated_ts, encoding="utf-8")
        git_cmd("add", "src/components/ui/sidebar.tsx")
        git_cmd("commit", "-qm", f"refactor(sidebar): width revision {rev}")

    git_cmd("checkout", "-qb", "feature/sidebar-compact")
    (work / "src" / "components" / "ui" / "sidebar.tsx").write_text(
        ts_base.replace("widthPx: number;", "widthPx: number;\n  compactMode?: boolean;"),
        encoding="utf-8",
    )
    git_cmd("add", "src/components/ui/sidebar.tsx")
    git_cmd("commit", "-qm", "feat(sidebar): compactMode option")
    git_cmd("checkout", "-q", "main")

    bare = root / "bench.git"
    subprocess.run(["git", "clone", "--mirror", "-q", str(work), str(bare)], check=True)

    db_path = root / "bench.sqlite"
    conn = content_index.open_db(db_path)
    try:
        content_index.ingest_repo(bare, "exams-app-bench", conn, all_commits=True)
    finally:
        conn.close()
    return work, bare, db_path


def run_benchmark(*, include_repomix: bool = True) -> dict:
    """Run synthetic benchmark measuring token savings across deduplication, modes, and Repomix."""
    with tempfile.TemporaryDirectory(prefix="selective-bench-") as tmp:
        root = Path(tmp)
        work, bare, db_path = _build_synthetic_benchmark_repo(root)

        budget = ContextBudget(max_files=40, max_bytes=256 * 1024, max_lines=4000, max_tokens=100_000)
        query = "sidebar"

        # Baseline 1: Full raw repository dump (excluding .git and .env)
        raw_repo_texts = {}
        for p in sorted(work.rglob("*")):
            if not p.is_file() or ".git" in p.parts:
                continue
            rel = p.relative_to(work).as_posix()
            txt = p.read_text(encoding="utf-8", errors="replace")
            blocked, _ = is_secret_or_blocked(rel, txt)
            if blocked:
                continue
            raw_repo_texts[rel] = txt
        full_repo_tokens = estimate_text_tokens("\n".join(raw_repo_texts.values()))

        # Scenario A: No deduplication, exact-file delivery
        no_dedup = run_pipeline(
            query,
            source=bare,
            db_path=db_path,
            mode="exact-file",
            deduplicate=False,
            search_limit=40,
            budget=budget,
        )

        # Scenario B: With path/blob deduplication, exact-file delivery
        with_dedup_exact = run_pipeline(
            query,
            source=bare,
            db_path=db_path,
            mode="exact-file",
            deduplicate=True,
            search_limit=40,
            budget=budget,
        )

        # Scenario C: With deduplication, metadata-only mode
        metadata_only = run_pipeline(
            query,
            source=bare,
            db_path=db_path,
            mode="metadata-only",
            deduplicate=True,
            search_limit=40,
            budget=budget,
        )

        # Scenario D: With deduplication, snippet mode
        snippet_mode = run_pipeline(
            query,
            source=bare,
            db_path=db_path,
            mode="snippet",
            deduplicate=True,
            search_limit=40,
            budget=budget,
        )

        # Scenario E: Context-pack with built-in structural compaction (no Repomix)
        ctx_builtin = run_pipeline(
            query,
            source=bare,
            db_path=db_path,
            mode="context-pack",
            deduplicate=True,
            use_repomix=False,
            search_limit=40,
            budget=budget,
        )

        # Scenario F: Context-pack with Repomix (--compress Tree-sitter) if requested/available
        ctx_repomix = None
        repomix_whole_repo = None
        if include_repomix:
            ctx_repomix = run_pipeline(
                query,
                source=bare,
                db_path=db_path,
                mode="context-pack",
                deduplicate=True,
                use_repomix=True,
                repomix_compress=True,
                search_limit=40,
                budget=budget,
            )
            repomix_whole = _compact_with_repomix(raw_repo_texts, compress=True, style="xml")
            repomix_whole_repo = {
                "used": repomix_whole["used"],
                "reason": repomix_whole["reason"],
                "elapsed_ms": repomix_whole["elapsed_ms"],
                "tokens": estimate_text_tokens(str(repomix_whole["packed_output"])),
            }

        def summarize(label: str, res: dict) -> dict:
            return {
                "scenario": label,
                "files": res["usage"]["files"],
                "content_lines": res["usage"]["content_lines"],
                "content_bytes": res["usage"]["content_bytes"],
                "content_tokens": res["usage"]["content_tokens"],
                "total_estimated_tokens": res["usage"]["total_estimated_tokens"],
                "elapsed_ms": res["pipeline"]["elapsed_ms"],
                "repomix_used": res["repomix"]["used"],
            }

        rows = [
            summarize("exact_no_dedup", no_dedup),
            summarize("exact_with_dedup", with_dedup_exact),
            summarize("metadata_only", metadata_only),
            summarize("snippet", snippet_mode),
            summarize("context_pack_builtin", ctx_builtin),
        ]
        if ctx_repomix is not None:
            rows.append(summarize("context_pack_repomix", ctx_repomix))

        t_no_dedup = no_dedup["usage"]["total_estimated_tokens"]
        t_dedup = with_dedup_exact["usage"]["total_estimated_tokens"]
        t_snippet = snippet_mode["usage"]["total_estimated_tokens"]
        t_builtin = ctx_builtin["usage"]["total_estimated_tokens"]
        c_dedup = with_dedup_exact["usage"]["content_tokens"]
        c_snippet = snippet_mode["usage"]["content_tokens"]
        c_builtin = ctx_builtin["usage"]["content_tokens"]

        dedup_savings_pct = round(100.0 * (1.0 - (t_dedup / max(1, t_no_dedup))), 2)
        snippet_savings_pct = round(100.0 * (1.0 - (t_snippet / max(1, t_no_dedup))), 2)
        builtin_savings_pct = round(100.0 * (1.0 - (t_builtin / max(1, t_no_dedup))), 2)
        builtin_content_vs_exact_pct = round(100.0 * (1.0 - (c_builtin / max(1, c_dedup))), 2)

        repomix_savings_vs_no_dedup_pct = None
        repomix_content_vs_exact_pct = None
        selective_content_vs_repomix_whole_repo_pct = None
        if ctx_repomix is not None:
            t_rmx = ctx_repomix["usage"]["total_estimated_tokens"]
            c_rmx = ctx_repomix["usage"]["content_tokens"]
            repomix_savings_vs_no_dedup_pct = round(
                100.0 * (1.0 - (t_rmx / max(1, t_no_dedup))), 2
            )
            repomix_content_vs_exact_pct = round(
                100.0 * (1.0 - (c_rmx / max(1, c_dedup))), 2
            )
            if repomix_whole_repo and repomix_whole_repo["tokens"] > 0:
                selective_content_vs_repomix_whole_repo_pct = round(
                    100.0 * (1.0 - (c_snippet / repomix_whole_repo["tokens"])), 2
                )

        return {
            "ok": True,
            "query": query,
            "full_repo_raw_tokens": full_repo_tokens,
            "repomix_whole_repo": repomix_whole_repo,
            "scenarios": rows,
            "comparisons": {
                "dedup_vs_no_dedup_savings_pct": dedup_savings_pct,
                "snippet_vs_no_dedup_savings_pct": snippet_savings_pct,
                "context_pack_builtin_vs_no_dedup_savings_pct": builtin_savings_pct,
                "context_pack_repomix_vs_no_dedup_savings_pct": repomix_savings_vs_no_dedup_pct,
                "context_pack_builtin_content_vs_exact_pct": builtin_content_vs_exact_pct,
                "context_pack_repomix_content_vs_exact_pct": repomix_content_vs_exact_pct,
                "selective_snippet_content_vs_repomix_whole_repo_pct": selective_content_vs_repomix_whole_repo_pct,
            },
        }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p_exp = sub.add_parser("export", help="Run selective context export pipeline")
    p_exp.add_argument("query", help="Search query")
    p_exp.add_argument("--source", type=Path, required=True, help="Bare repo, workdir, or .bundle")
    p_exp.add_argument("--db", type=Path, default=None, help="Optional pre-built content_index SQLite")
    p_exp.add_argument("--repo", default=None, help="Logical repo filter")
    p_exp.add_argument("--ref", default=None, help="Git ref or branch filter")
    p_exp.add_argument("--ext", default=None, help="File extension filter")
    p_exp.add_argument("--lang", default=None, help="Language filter")
    p_exp.add_argument("--status", default=None, help="Status filter (ref-head, deleted, commit)")
    p_exp.add_argument("--mode", choices=VALID_MODES, default=DEFAULT_MODE)
    p_exp.add_argument("--no-dedup", action="store_true", help="Disable path/blob deduplication")
    p_exp.add_argument("--use-repomix", action="store_true", help="Enable optional Repomix Tree-sitter compaction")
    p_exp.add_argument("--no-repomix-compress", action="store_true", help="Disable Repomix --compress flag")
    p_exp.add_argument("--search-limit", type=int, default=40)
    p_exp.add_argument("--snippet-lines", type=int, default=DEFAULT_SNIPPET_LINES)
    p_exp.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    p_exp.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    p_exp.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    p_exp.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)

    p_bench = sub.add_parser("benchmark", help="Run synthetic token-economy benchmark")
    p_bench.add_argument("--no-repomix", action="store_true", help="Skip Repomix comparison")
    return ap


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "benchmark":
        result = run_benchmark(include_repomix=not args.no_repomix)
    else:
        budget = ContextBudget(
            max_files=args.max_files,
            max_bytes=args.max_bytes,
            max_lines=args.max_lines,
            max_tokens=args.max_tokens,
        )
        result = run_pipeline(
            args.query,
            source=args.source,
            db_path=args.db,
            repo=args.repo,
            ref=args.ref,
            extension=args.ext,
            language=args.lang,
            status=args.status,
            mode=args.mode,
            deduplicate=not args.no_dedup,
            use_repomix=args.use_repomix,
            repomix_compress=not args.no_repomix_compress,
            search_limit=args.search_limit,
            snippet_lines=args.snippet_lines,
            budget=budget,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except archive_flow.ArchiveFlowError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        err = SelectiveContextError(str(exc), code="invalid_input")
        print(json.dumps(err.to_dict(), ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
