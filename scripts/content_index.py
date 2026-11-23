#!/usr/bin/env python3
"""Historical Git content FTS5 index: Git remains authoritative; SQLite is rebuildable.

Indexes deduplicated text/code blobs into deterministic line-bounded chunks using
SQLite FTS5, supporting bare repositories and local Git bundles.
Standard library only. No embeddings, no model inference, no shell interpolation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MAX_FILE_BYTES = 256 * 1024
DEFAULT_CHUNK_LINES = 40
DEFAULT_OVERLAP_LINES = 5
DEFAULT_MAX_CHUNK_CHARS = 8000
DEFAULT_SNIPPET_LINES = 7

LANGUAGE_BY_EXT: dict[str, str] = {
    ".ts": "typescript",
    ".tsx": "tsx",
    ".mts": "typescript",
    ".cts": "typescript",
    ".js": "javascript",
    ".jsx": "jsx",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".py": "python",
    ".pyi": "python",
    ".md": "markdown",
    ".mdx": "mdx",
    ".txt": "text",
    ".rst": "rst",
    ".json": "json",
    ".jsonc": "jsonc",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".xml": "xml",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".ps1": "powershell",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".svelte": "svelte",
    ".vue": "vue",
    ".graphql": "graphql",
    ".gql": "graphql",
}

IGNORED_FILENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lockb",
    "poetry.lock",
    "cargo.lock",
}

SECRET_EXTENSIONS = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
    ".kdbx",
    ".crt",
    ".cer",
    ".der",
    ".ppk",
    ".ovpn",
    ".age",
    ".gpg",
    ".asc",
    ".secret",
    ".secrets",
    ".env",
}

SECRET_FILENAMES = {
    ".env",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".dockercfg",
    ".htpasswd",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
    "service-account.json",
    "serviceaccountkey.json",
    "google-services.json",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    "secrets.toml",
    "master.key",
}

SECRET_DIR_PARTS = {"secrets", ".ssh", ".aws", ".gnupg"}

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-(?:proj-|live-|test-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{24,}\b"),
    re.compile(
        r"(?i)\b(?:api_key|apikey|secret_key|private_key|access_token|auth_token|client_secret|db_password)"
        r"\s*[:=]\s*[\"']?(?!example|placeholder|your_|dummy|test_|changeme|xxxx|<)[A-Za-z0-9/+=._:-]{16,}[\"']?"
    ),
    re.compile(r"\b(?:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis)://[^:\s/]+:[^@\s]{6,}@"),
)

DB_SCHEMA = """
PRAGMA journal_mode=DELETE;
CREATE TABLE IF NOT EXISTS content_repositories (
    repo TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    indexed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS content_blobs (
    blob_sha TEXT PRIMARY KEY,
    bytes INTEGER NOT NULL,
    line_count INTEGER NOT NULL,
    language TEXT NOT NULL,
    chunk_count INTEGER NOT NULL,
    indexed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS content_skipped_blobs (
    blob_sha TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    bytes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS content_chunks (
    id INTEGER PRIMARY KEY,
    blob_sha TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    content TEXT NOT NULL,
    UNIQUE(blob_sha, chunk_index)
);
CREATE TABLE IF NOT EXISTS content_occurrences (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    ref TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    path TEXT NOT NULL,
    extension TEXT NOT NULL,
    language TEXT NOT NULL,
    blob_sha TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ref-head',
    UNIQUE(repo, ref, commit_sha, path, blob_sha, status)
);
CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
    content,
    blob_sha UNINDEXED,
    chunk_id UNINDEXED,
    start_line UNINDEXED,
    end_line UNINDEXED,
    language UNINDEXED,
    tokenize='unicode61'
);
CREATE INDEX IF NOT EXISTS idx_content_occ_blob ON content_occurrences(blob_sha);
CREATE INDEX IF NOT EXISTS idx_content_occ_repo_ref ON content_occurrences(repo, ref);
CREATE INDEX IF NOT EXISTS idx_content_occ_ext ON content_occurrences(extension);
CREATE INDEX IF NOT EXISTS idx_content_occ_commit_path ON content_occurrences(commit_sha, path);
CREATE INDEX IF NOT EXISTS idx_content_chunks_blob ON content_chunks(blob_sha);
CREATE VIEW IF NOT EXISTS content_entries AS
SELECT
    o.repo,
    o.ref,
    o.commit_sha,
    o.path,
    o.extension,
    c.start_line,
    c.end_line,
    o.language,
    o.blob_sha,
    o.status,
    c.content
FROM content_occurrences o
JOIN content_chunks c ON c.blob_sha = o.blob_sha;
"""


def safe_ref(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise ValueError("commit SHA must be full-length hexadecimal")
    return value


def safe_path(path: str) -> str:
    parts = Path(path).parts
    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or ".." in parts
        or path.startswith("-")
        or "\x00" in path
        or ":" in path
    ):
        raise ValueError("unsafe path")
    return path


def normalize_extension(ext: str) -> str:
    cleaned = ext.strip().lower()
    if not cleaned:
        return ""
    return cleaned if cleaned.startswith(".") else "." + cleaned


def detect_language(path: str) -> tuple[str, str] | None:
    p = Path(path)
    name_lower = p.name.lower()
    if name_lower in IGNORED_FILENAMES:
        return None
    if name_lower.endswith(".min.js") or name_lower.endswith(".min.css"):
        return None
    ext = p.suffix.lower()
    lang = LANGUAGE_BY_EXT.get(ext)
    if not lang:
        return None
    return ext, lang


def is_secret_path(path: str) -> bool:
    p = Path(path)
    parts_lower = [part.lower() for part in p.parts]
    name_lower = p.name.lower()
    if name_lower == ".env" or name_lower.startswith(".env."):
        return True
    if name_lower in SECRET_FILENAMES or name_lower.startswith("firebase-adminsdk"):
        return True
    if p.suffix.lower() in SECRET_EXTENSIONS:
        return True
    if any(part in SECRET_DIR_PARTS for part in parts_lower[:-1]):
        return True
    return False


def is_binary_bytes(raw: bytes) -> bool:
    if not raw:
        return False
    sample = raw[:8192]
    if b"\x00" in sample or b"\x00" in raw:
        return True
    control_count = sum(1 for b in sample if b < 32 and b not in (9, 10, 11, 12, 13))
    if len(sample) > 0 and (control_count / len(sample)) > 0.10:
        return True
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def contains_secret_content(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def chunk_text(
    text: str,
    *,
    chunk_lines: int = DEFAULT_CHUNK_LINES,
    overlap_lines: int = DEFAULT_OVERLAP_LINES,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> list[tuple[int, int, str]]:
    if chunk_lines < 1:
        raise ValueError("chunk_lines must be >= 1")
    if overlap_lines < 0 or overlap_lines >= chunk_lines:
        raise ValueError("overlap_lines must be >= 0 and < chunk_lines")
    if max_chunk_chars < 64:
        raise ValueError("max_chunk_chars must be >= 64")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or all(not line.strip() for line in lines):
        return []

    chunks: list[tuple[int, int, str]] = []
    n = len(lines)
    idx = 0
    while idx < n:
        end = min(idx + chunk_lines, n)
        selected: list[str] = []
        total_chars = 0
        for pos in range(idx, end):
            line = lines[pos]
            if len(line) > max_chunk_chars:
                line = line[:max_chunk_chars]
            added = len(line) + (1 if selected else 0)
            if selected and total_chars + added > max_chunk_chars:
                end = pos
                break
            selected.append(line)
            total_chars += added
        start_line = idx + 1
        end_line = idx + len(selected)
        chunks.append((start_line, end_line, "\n".join(selected)))
        if end_line >= n:
            break
        step = max(1, (end_line - idx) - overlap_lines)
        idx += step
    return chunks


def git(repo: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", f"--git-dir={repo}", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout if binary else result.stdout.decode("utf-8", "replace")


def git_stream(repo: Path, *args: str):
    proc = subprocess.Popen(
        ["git", f"--git-dir={repo}", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None and proc.stderr is not None
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
        err = proc.stderr.read()
    finally:
        proc.stdout.close()
        proc.stderr.close()
    code = proc.wait()
    if code:
        raise RuntimeError(f"git returned {code}: {err[:1200]}")


def read_blobs_batch(repo: Path, blob_shas: list[str]) -> dict[str, bytes]:
    if not blob_shas:
        return {}
    out: dict[str, bytes] = {}
    proc = subprocess.Popen(
        ["git", f"--git-dir={repo}", "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
    payload = ("\n".join(blob_shas) + "\n").encode("ascii")
    proc.stdin.write(payload)
    proc.stdin.close()
    try:
        while True:
            header_raw = proc.stdout.readline()
            if not header_raw:
                break
            header = header_raw.decode("ascii", "replace").rstrip("\n")
            parts = header.split()
            if len(parts) < 2:
                continue
            sha = parts[0]
            if parts[1] == "missing":
                continue
            if len(parts) < 3:
                continue
            obj_type = parts[1]
            size = int(parts[2])
            data = proc.stdout.read(size)
            proc.stdout.read(1)  # trailing LF
            if obj_type == "blob" and len(data) == size:
                out[sha] = data
        err = proc.stderr.read().decode("utf-8", "replace")
    finally:
        proc.stdout.close()
        proc.stderr.close()
    code = proc.wait()
    if code:
        raise RuntimeError(f"git cat-file --batch returned {code}: {err[:1200]}")
    return out


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(DB_SCHEMA)
    return conn


def _resolve_bare_repo(source_path: Path, temp_root: Path) -> tuple[Path, str]:
    if source_path.is_file():
        bare = temp_root / "mirror.git"
        subprocess.run(
            ["git", "clone", "--mirror", "--quiet", str(source_path), str(bare)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return bare, str(source_path)
    if source_path.is_dir():
        if (source_path / "HEAD").exists():
            return source_path, str(source_path)
        if (source_path / ".git").is_dir() and (source_path / ".git" / "HEAD").exists():
            return source_path / ".git", str(source_path)
    raise ValueError(f"Expected a bare Git repository or bundle file: {source_path}")


def _collect_candidates(
    bare_repo: Path,
    *,
    include_deleted: bool,
    all_commits: bool,
    max_file_bytes: int,
) -> tuple[list[dict], dict[str, int]]:
    stats = {
        "skipped_unsafe": 0,
        "skipped_extension": 0,
        "skipped_secret_path": 0,
        "skipped_size": 0,
    }
    candidates: list[dict] = []
    seen_occ: set[tuple[str, str, str, str, str]] = set()

    def consider(ref: str, commit_sha: str, path: str, blob_sha: str, size: int | None, status: str) -> None:
        try:
            safe_path(path)
            safe_ref(commit_sha)
        except ValueError:
            stats["skipped_unsafe"] += 1
            return
        if is_secret_path(path):
            stats["skipped_secret_path"] += 1
            return
        lang_info = detect_language(path)
        if lang_info is None:
            stats["skipped_extension"] += 1
            return
        if size is not None and size > max_file_bytes:
            stats["skipped_size"] += 1
            return
        ext, lang = lang_info
        key = (ref, commit_sha, path, blob_sha, status)
        if key in seen_occ:
            return
        seen_occ.add(key)
        candidates.append(
            {
                "ref": ref,
                "commit_sha": commit_sha,
                "path": path,
                "extension": ext,
                "language": lang,
                "blob_sha": blob_sha,
                "status": status,
            }
        )

    refs: list[tuple[str, str]] = []
    for line in git_stream(bare_repo, "for-each-ref", "--format=%(refname)%09%(objectname)"):
        if "\t" not in line:
            continue
        refname, obj_sha = line.split("\t", 1)
        if not (
            refname.startswith("refs/heads/")
            or refname.startswith("refs/pull/")
            or refname.startswith("refs/tags/")
        ):
            continue
        try:
            resolved = git(bare_repo, "rev-parse", f"{refname}^{{commit}}").strip()
            safe_ref(resolved)
        except (subprocess.CalledProcessError, ValueError):
            resolved = obj_sha
        refs.append((refname, resolved))

    for refname, commit_sha in refs:
        try:
            for line in git_stream(bare_repo, "ls-tree", "-r", "-l", commit_sha):
                if "\t" not in line:
                    continue
                meta, path = line.split("\t", 1)
                fields = meta.split()
                if len(fields) < 4 or fields[1] != "blob":
                    continue
                blob_sha = fields[2]
                size = None if fields[3] == "-" else int(fields[3])
                consider(refname, commit_sha, path, blob_sha, size, "ref-head")
        except (RuntimeError, ValueError):
            continue

    if include_deleted or all_commits:
        current_commit: str | None = None
        current_parents: list[str] = []
        for line in git_stream(
            bare_repo,
            "log",
            "--all",
            "--root",
            "--no-renames",
            "--raw",
            "--no-abbrev",
            "--format=%x1e%H%x1f%P",
        ):
            if line.startswith("\x1e"):
                parts = line[1:].split("\x1f", 1)
                current_commit = parts[0]
                current_parents = parts[1].split() if len(parts) > 1 and parts[1] else []
                continue
            if not current_commit or not line.startswith(":") or "\t" not in line:
                continue
            meta, path = line.split("\t", 1)
            fields = meta[1:].split()
            if len(fields) < 5:
                continue
            old_blob, new_blob, status_code = fields[2], fields[3], fields[4][:1]
            if status_code == "D" and include_deleted and current_parents:
                if re.fullmatch(r"[0-9a-f]{40,64}", old_blob) and set(old_blob) != {"0"}:
                    consider("history/deleted", current_parents[0], path, old_blob, None, "deleted")
            elif all_commits and status_code in {"A", "M"}:
                if re.fullmatch(r"[0-9a-f]{40,64}", new_blob) and set(new_blob) != {"0"}:
                    consider("history/commit", current_commit, path, new_blob, None, "commit")

    return candidates, stats


def ingest_repo(
    repo_or_bundle: Path,
    repo_name: str,
    conn: sqlite3.Connection,
    *,
    source_label: str | None = None,
    include_deleted: bool = True,
    all_commits: bool = False,
    replace_repo: bool = True,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    chunk_lines: int = DEFAULT_CHUNK_LINES,
    overlap_lines: int = DEFAULT_OVERLAP_LINES,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> dict:
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="content-index-") as tmp:
        bare_repo, resolved_source = _resolve_bare_repo(Path(repo_or_bundle), Path(tmp))
        source_value = source_label or resolved_source
        candidates, stats = _collect_candidates(
            bare_repo,
            include_deleted=include_deleted,
            all_commits=all_commits,
            max_file_bytes=max_file_bytes,
        )

        existing_blobs = {
            row[0] for row in conn.execute("SELECT blob_sha FROM content_blobs")
        }
        skipped_blobs = {
            row[0]: row[1]
            for row in conn.execute("SELECT blob_sha, reason FROM content_skipped_blobs")
        }

        to_fetch: dict[str, str] = {}
        deduped_hits = 0
        for item in candidates:
            bsha = item["blob_sha"]
            if bsha in existing_blobs:
                deduped_hits += 1
                continue
            if bsha in skipped_blobs:
                continue
            if bsha not in to_fetch:
                to_fetch[bsha] = item["language"]

        blob_bytes_map = read_blobs_batch(bare_repo, list(to_fetch.keys()))

        newly_indexed_blobs = 0
        newly_indexed_chunks = 0
        skipped_binary = 0
        skipped_secret_content = 0
        skipped_empty = 0
        skipped_oversized = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO content_repositories (repo, source, indexed_at) VALUES (?, ?, ?)",
                (repo_name, source_value, now_iso),
            )
            if replace_repo:
                conn.execute("DELETE FROM content_occurrences WHERE repo = ?", (repo_name,))

            for bsha, lang in to_fetch.items():
                raw = blob_bytes_map.get(bsha)
                if raw is None:
                    continue
                if len(raw) > max_file_bytes:
                    skipped_oversized += 1
                    skipped_blobs[bsha] = "size"
                    conn.execute(
                        "INSERT OR IGNORE INTO content_skipped_blobs (blob_sha, reason, bytes) VALUES (?, ?, ?)",
                        (bsha, "size", len(raw)),
                    )
                    continue
                if is_binary_bytes(raw):
                    skipped_binary += 1
                    skipped_blobs[bsha] = "binary"
                    conn.execute(
                        "INSERT OR IGNORE INTO content_skipped_blobs (blob_sha, reason, bytes) VALUES (?, ?, ?)",
                        (bsha, "binary", len(raw)),
                    )
                    continue
                text = raw.decode("utf-8")
                if contains_secret_content(text):
                    skipped_secret_content += 1
                    skipped_blobs[bsha] = "secret"
                    conn.execute(
                        "INSERT OR IGNORE INTO content_skipped_blobs (blob_sha, reason, bytes) VALUES (?, ?, ?)",
                        (bsha, "secret", len(raw)),
                    )
                    continue
                chunks = chunk_text(
                    text,
                    chunk_lines=chunk_lines,
                    overlap_lines=overlap_lines,
                    max_chunk_chars=max_chunk_chars,
                )
                if not chunks:
                    skipped_empty += 1
                    skipped_blobs[bsha] = "empty"
                    conn.execute(
                        "INSERT OR IGNORE INTO content_skipped_blobs (blob_sha, reason, bytes) VALUES (?, ?, ?)",
                        (bsha, "empty", len(raw)),
                    )
                    continue

                line_count = chunks[-1][1]
                conn.execute(
                    "INSERT OR IGNORE INTO content_blobs (blob_sha, bytes, line_count, language, chunk_count, indexed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (bsha, len(raw), line_count, lang, len(chunks), now_iso),
                )
                for chunk_idx, (start_line, end_line, chunk_body) in enumerate(chunks):
                    cur = conn.execute(
                        "INSERT OR IGNORE INTO content_chunks (blob_sha, chunk_index, start_line, end_line, content) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (bsha, chunk_idx, start_line, end_line, chunk_body),
                    )
                    chunk_id = cur.lastrowid
                    if cur.rowcount == 0 or not chunk_id:
                        chunk_id = conn.execute(
                            "SELECT id FROM content_chunks WHERE blob_sha=? AND chunk_index=?",
                            (bsha, chunk_idx),
                        ).fetchone()[0]
                    conn.execute(
                        "INSERT INTO content_fts (content, blob_sha, chunk_id, start_line, end_line, language) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (chunk_body, bsha, str(chunk_id), str(start_line), str(end_line), lang),
                    )
                    newly_indexed_chunks += 1
                existing_blobs.add(bsha)
                newly_indexed_blobs += 1

            occurrences_inserted = 0
            for item in candidates:
                bsha = item["blob_sha"]
                if bsha not in existing_blobs:
                    if skipped_blobs.get(bsha) == "size":
                        stats["skipped_size"] += 1
                    continue
                cur = conn.execute(
                    "INSERT OR IGNORE INTO content_occurrences "
                    "(repo, ref, commit_sha, path, extension, language, blob_sha, status) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        repo_name,
                        item["ref"],
                        item["commit_sha"],
                        item["path"],
                        item["extension"],
                        item["language"],
                        bsha,
                        item["status"],
                    ),
                )
                occurrences_inserted += cur.rowcount

    return {
        "repository": repo_name,
        "source": source_value,
        "candidates": len(candidates),
        "occurrences_inserted": occurrences_inserted,
        "new_blobs_indexed": newly_indexed_blobs,
        "new_chunks_indexed": newly_indexed_chunks,
        "deduped_blob_hits": deduped_hits,
        "skipped_binary": skipped_binary,
        "skipped_secret_path": stats["skipped_secret_path"],
        "skipped_secret_content": skipped_secret_content,
        "skipped_extension": stats["skipped_extension"],
        "skipped_size": stats["skipped_size"] + skipped_oversized,
        "skipped_empty": skipped_empty,
        "skipped_unsafe": stats["skipped_unsafe"],
        "elapsed_seconds": round(time.perf_counter() - t0, 4),
    }


def _extract_snippet(
    chunk_content: str,
    chunk_start_line: int,
    tokens: list[str],
    snippet_lines: int,
) -> tuple[int, int, str]:
    lines = chunk_content.split("\n")
    if snippet_lines <= 0 or len(lines) <= snippet_lines:
        return chunk_start_line, chunk_start_line + len(lines) - 1, chunk_content

    lowered_tokens = [t.lower() for t in tokens]
    best_idx = 0
    best_score = -1
    for i, line in enumerate(lines):
        low = line.lower()
        score = sum(1 for tok in lowered_tokens if tok in low)
        if score > best_score:
            best_score = score
            best_idx = i

    half = snippet_lines // 2
    start_idx = max(0, best_idx - half)
    end_idx = start_idx + snippet_lines
    if end_idx > len(lines):
        end_idx = len(lines)
        start_idx = max(0, end_idx - snippet_lines)
    excerpt = "\n".join(lines[start_idx:end_idx])
    return chunk_start_line + start_idx, chunk_start_line + end_idx - 1, excerpt


def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    repo: str | None = None,
    branch: str | None = None,
    ref: str | None = None,
    extension: str | None = None,
    language: str | None = None,
    status: str | None = None,
    limit: int = 10,
    snippet_lines: int = DEFAULT_SNIPPET_LINES,
    match_all: bool = True,
) -> list[dict]:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)[:8]
    if not tokens:
        return []
    joiner = " AND " if match_all else " OR "
    matcher = joiner.join('"' + token.replace('"', "") + '"*' for token in tokens)
    limit = max(1, min(int(limit), 100))

    sql = """
        SELECT
            o.repo,
            o.ref,
            o.commit_sha,
            o.path,
            o.extension,
            o.language,
            o.blob_sha,
            o.status,
            CAST(f.start_line AS INTEGER) AS chunk_start_line,
            CAST(f.end_line AS INTEGER) AS chunk_end_line,
            f.content,
            bm25(content_fts) AS score
        FROM content_fts f
        JOIN content_occurrences o ON o.blob_sha = f.blob_sha
        WHERE content_fts MATCH ?
    """
    params: list = [matcher]

    if repo:
        sql += " AND o.repo = ?"
        params.append(repo)

    effective_ref = ref or branch
    if effective_ref:
        if effective_ref.startswith("refs/") or effective_ref.startswith("history/"):
            sql += " AND o.ref = ?"
            params.append(effective_ref)
        else:
            sql += " AND (o.ref = ? OR o.ref = ?)"
            params.extend([effective_ref, f"refs/heads/{effective_ref}"])

    if extension:
        sql += " AND o.extension = ?"
        params.append(normalize_extension(extension))

    if language:
        sql += " AND o.language = ?"
        params.append(language.strip().lower())

    if status:
        sql += " AND o.status = ?"
        params.append(status.strip())

    sql += " ORDER BY score ASC, o.repo ASC, o.ref ASC, o.path ASC, chunk_start_line ASC LIMIT ?"
    params.append(limit)

    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return []

    results: list[dict] = []
    for row in rows:
        (
            r_repo,
            r_ref,
            r_sha,
            r_path,
            r_ext,
            r_lang,
            r_blob,
            r_status,
            c_start,
            c_end,
            chunk_content,
            score,
        ) = row
        s_line, e_line, excerpt = _extract_snippet(chunk_content, c_start, tokens, snippet_lines)
        results.append(
            {
                "repository": r_repo,
                "ref": r_ref,
                "commit_sha": r_sha,
                "path": r_path,
                "extension": r_ext,
                "language": r_lang,
                "blob_sha": r_blob,
                "status": r_status,
                "start_line": s_line,
                "end_line": e_line,
                "chunk_start_line": c_start,
                "chunk_end_line": c_end,
                "snippet": excerpt,
                "score": round(float(score), 6),
            }
        )
    return results


def recover_lines(
    repo_or_bundle: Path,
    commit_sha: str,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict:
    commit_sha = safe_ref(commit_sha)
    path = safe_path(path)
    with tempfile.TemporaryDirectory(prefix="content-recover-") as tmp:
        bare_repo, _ = _resolve_bare_repo(Path(repo_or_bundle), Path(tmp))
        raw = git(bare_repo, "show", f"{commit_sha}:{path}", binary=True)
        text = raw.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        if start_line is not None and end_line is not None:
            if start_line < 1 or end_line < start_line:
                raise ValueError("Invalid line range")
            selected = "\n".join(lines[start_line - 1 : end_line])
        else:
            start_line = 1 if lines else 0
            end_line = len(lines)
            selected = "\n".join(lines)
    return {
        "commit_sha": commit_sha,
        "path": path,
        "start_line": start_line,
        "end_line": end_line,
        "content": selected,
    }


def stats(conn: sqlite3.Connection, db_path: Path | None = None) -> dict:
    repos = [
        {
            "repository": row[0],
            "source": row[1],
            "indexed_at": row[2],
            "occurrences": conn.execute(
                "SELECT COUNT(*) FROM content_occurrences WHERE repo = ?", (row[0],)
            ).fetchone()[0],
        }
        for row in conn.execute("SELECT repo, source, indexed_at FROM content_repositories ORDER BY repo")
    ]
    unique_blobs, total_bytes = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(bytes), 0) FROM content_blobs"
    ).fetchone()
    total_chunks = conn.execute("SELECT COUNT(*) FROM content_chunks").fetchone()[0]
    total_occurrences = conn.execute("SELECT COUNT(*) FROM content_occurrences").fetchone()[0]
    skipped = {
        row[0]: row[1]
        for row in conn.execute("SELECT reason, COUNT(*) FROM content_skipped_blobs GROUP BY reason")
    }
    languages = {
        row[0]: row[1]
        for row in conn.execute("SELECT language, COUNT(*) FROM content_blobs GROUP BY language ORDER BY COUNT(*) DESC")
    }
    out = {
        "repositories": repos,
        "unique_blobs": unique_blobs,
        "total_chunks": total_chunks,
        "total_occurrences": total_occurrences,
        "indexed_source_bytes": total_bytes,
        "skipped_blobs": skipped,
        "languages": languages,
    }
    if db_path is not None and db_path.exists():
        out["db_bytes"] = db_path.stat().st_size
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="reports/content-index.sqlite")
    sub = ap.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Index text blobs from a bare repo or bundle")
    p_ingest.add_argument("--repo", required=True, help="Path to bare git dir, repo, or .bundle file")
    p_ingest.add_argument("--name", required=True, help="Logical repository name")
    p_ingest.add_argument("--source", default=None, help="Optional provenance source label")
    p_ingest.add_argument("--all-commits", action="store_true", help="Also index non-HEAD A/M commit blobs")
    p_ingest.add_argument("--no-deleted", action="store_true", help="Do not index deleted historical blobs")
    p_ingest.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    p_ingest.add_argument("--chunk-lines", type=int, default=DEFAULT_CHUNK_LINES)
    p_ingest.add_argument("--overlap-lines", type=int, default=DEFAULT_OVERLAP_LINES)

    p_search = sub.add_parser("search", help="Search indexed file chunks")
    p_search.add_argument("query")
    p_search.add_argument("--repo", default=None)
    p_search.add_argument("--branch", default=None)
    p_search.add_argument("--ref", default=None)
    p_search.add_argument("--ext", default=None, help="Filter by file extension (e.g. .ts)")
    p_search.add_argument("--lang", default=None, help="Filter by language (e.g. typescript)")
    p_search.add_argument("--status", default=None, help="Filter by status (ref-head, deleted, commit)")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--snippet-lines", type=int, default=DEFAULT_SNIPPET_LINES)
    p_search.add_argument("--or", dest="use_or", action="store_true", help="Match any token instead of all")

    p_recover = sub.add_parser("recover", help="Recover exact lines for SHA + path provenance verification")
    p_recover.add_argument("--repo", required=True)
    p_recover.add_argument("--sha", required=True)
    p_recover.add_argument("--path", required=True)
    p_recover.add_argument("--start-line", type=int, default=None)
    p_recover.add_argument("--end-line", type=int, default=None)

    sub.add_parser("stats", help="Show index statistics")

    args = ap.parse_args()
    if args.command == "recover":
        value = recover_lines(
            Path(args.repo),
            args.sha,
            args.path,
            start_line=args.start_line,
            end_line=args.end_line,
        )
    else:
        db_path = Path(args.db)
        conn = open_db(db_path)
        try:
            if args.command == "ingest":
                value = ingest_repo(
                    Path(args.repo),
                    args.name,
                    conn,
                    source_label=args.source,
                    include_deleted=not args.no_deleted,
                    all_commits=args.all_commits,
                    max_file_bytes=args.max_bytes,
                    chunk_lines=args.chunk_lines,
                    overlap_lines=args.overlap_lines,
                )
            elif args.command == "search":
                value = search(
                    conn,
                    args.query,
                    repo=args.repo,
                    branch=args.branch,
                    ref=args.ref,
                    extension=args.ext,
                    language=args.lang,
                    status=args.status,
                    limit=args.limit,
                    snippet_lines=args.snippet_lines,
                    match_all=not args.use_or,
                )
            else:
                value = stats(conn, db_path=db_path)
        finally:
            conn.close()
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
