#!/usr/bin/env python3
"""Historical context linker for archived Git repositories and GitHub metadata.

Imports and indexes preserved platform metadata from inventory/ (issues, PRs,
reviews, inline review comments, conversation comments, issue events, PR file
diffs, releases, tags, workflow runs, branch file inventories, and audit gap
records) alongside optional bare Git repositories/bundles and image catalogs.

Objective links (repo + PR/issue + commit SHA + path + image/document) are
strictly separated from inferences: motivation/justification is reported ONLY
when explicitly cited in commits, PRs, issues, or review/conversation comments;
otherwise "sem justificativa citada" is returned explicitly.

Standard library only. No embeddings, no model inference, no shell interpolation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import image_catalog  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DB_PATH = ".cache/archive/context-linker.sqlite"
DEFAULT_INVENTORY_DIR = REPO_ROOT / "inventory"

NO_CITATION_TEXT = "sem justificativa citada"

IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"})
IMAGE_URL_RE = re.compile(
    r"!\[[^\]]*\]\(([^)\s]+)\)|https://github\.com/user-attachments/assets/[A-Za-z0-9_-]+|"
    r"[A-Za-z0-9_./-]+\.(?:png|jpg|jpeg|gif|svg|webp)\b",
    re.IGNORECASE,
)
PR_NUMBER_URL_RE = re.compile(r"/(?:pulls|issues)/(\d+)(?:$|[#?])")
BLOB_COMMIT_RE = re.compile(r"/blob/([0-9a-f]{40,64})/")
ISSUE_REF_RE = re.compile(
    r"(?:(?:closes|closed|fixes|fixed|resolves|resolved|refs?|related\s+to|see)\s+)?#(\d+)\b",
    re.IGNORECASE,
)
DECISION_LINE_RE = re.compile(
    r"(?i)(?:\b(?:why|reason|because|motivation|decision|context|rationale|"
    r"justificativa|motivo|porque|decisao|para\s+que|in\s+order\s+to|so\s+that|"
    r"prevent|avoid|fix|fixes|closes|resolves|replace|migrate|remove|add)\b|"
    r"^##\s*(?:context|summary|motivation|why|decision|rationale|objetivo|contexto))"
)
SECRET_REDACT_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-(?:proj-|live-|test-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{24,}\b"),
    re.compile(
        r"\b(?:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis)://[^:\s/]+:[^@\s]{6,}@"
    ),
)
SECRET_FILENAMES = {
    ".env",
    ".npmrc",
    ".pypirc",
    ".netrc",
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
SECRET_DIR_PARTS = {"secrets", ".ssh", ".aws", ".gnupg"}

DB_SCHEMA = """
PRAGMA journal_mode=DELETE;
CREATE TABLE IF NOT EXISTS ctx_sources (
    id INTEGER PRIMARY KEY,
    source_key TEXT UNIQUE NOT NULL,
    source_type TEXT NOT NULL,
    repo TEXT NOT NULL,
    location TEXT NOT NULL,
    imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ctx_items (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    kind TEXT NOT NULL,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    state TEXT NOT NULL,
    author TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    merged_at TEXT NOT NULL,
    head_ref TEXT NOT NULL,
    head_sha TEXT NOT NULL,
    base_ref TEXT NOT NULL,
    base_sha TEXT NOT NULL,
    merge_commit_sha TEXT NOT NULL,
    html_url TEXT NOT NULL,
    origin_file TEXT NOT NULL,
    UNIQUE(repo, kind, number)
);
CREATE TABLE IF NOT EXISTS ctx_comments (
    id INTEGER PRIMARY KEY,
    comment_uid TEXT UNIQUE NOT NULL,
    repo TEXT NOT NULL,
    item_kind TEXT NOT NULL,
    item_number INTEGER NOT NULL,
    comment_kind TEXT NOT NULL,
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    path TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    diff_hunk TEXT NOT NULL,
    review_state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    html_url TEXT NOT NULL,
    origin_file TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ctx_events (
    id INTEGER PRIMARY KEY,
    event_uid TEXT UNIQUE NOT NULL,
    repo TEXT NOT NULL,
    item_number INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    created_at TEXT NOT NULL,
    html_url TEXT NOT NULL,
    origin_file TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ctx_commits (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    date TEXT NOT NULL,
    ref TEXT NOT NULL,
    author TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    origin_source TEXT NOT NULL,
    UNIQUE(repo, commit_sha)
);
CREATE TABLE IF NOT EXISTS ctx_commit_files (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    ref TEXT NOT NULL,
    date TEXT NOT NULL,
    path TEXT NOT NULL,
    previous_path TEXT NOT NULL,
    status TEXT NOT NULL,
    blob_sha TEXT NOT NULL,
    additions INTEGER NOT NULL DEFAULT 0,
    deletions INTEGER NOT NULL DEFAULT 0,
    patch TEXT NOT NULL,
    blob_url TEXT NOT NULL,
    pr_number INTEGER,
    origin_file TEXT NOT NULL,
    UNIQUE(repo, commit_sha, path, status)
);
CREATE TABLE IF NOT EXISTS ctx_images (
    id INTEGER PRIMARY KEY,
    image_uid TEXT UNIQUE NOT NULL,
    repo TEXT NOT NULL,
    path TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    ref TEXT NOT NULL,
    blob_sha TEXT NOT NULL,
    pr_number INTEGER,
    issue_number INTEGER,
    media_type TEXT NOT NULL,
    origin_url TEXT NOT NULL,
    origin_file TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ctx_links (
    id INTEGER PRIMARY KEY,
    link_uid TEXT UNIQUE NOT NULL,
    repo TEXT NOT NULL,
    pr_number INTEGER,
    issue_number INTEGER,
    commit_sha TEXT NOT NULL,
    ref TEXT NOT NULL,
    path TEXT NOT NULL,
    image_path TEXT NOT NULL,
    link_type TEXT NOT NULL,
    origin_url TEXT NOT NULL,
    origin_file TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ctx_releases (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    name TEXT NOT NULL,
    body TEXT NOT NULL,
    target_commitish TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    created_at TEXT NOT NULL,
    published_at TEXT NOT NULL,
    html_url TEXT NOT NULL,
    origin_file TEXT NOT NULL,
    UNIQUE(repo, tag_name)
);
CREATE TABLE IF NOT EXISTS ctx_workflow_runs (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    run_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    head_branch TEXT NOT NULL,
    head_sha TEXT NOT NULL,
    event TEXT NOT NULL,
    status TEXT NOT NULL,
    conclusion TEXT NOT NULL,
    created_at TEXT NOT NULL,
    html_url TEXT NOT NULL,
    pr_numbers_json TEXT NOT NULL,
    origin_file TEXT NOT NULL,
    UNIQUE(repo, run_id)
);
CREATE TABLE IF NOT EXISTS ctx_gaps (
    id INTEGER PRIMARY KEY,
    gap_uid TEXT UNIQUE NOT NULL,
    repo TEXT NOT NULL,
    pr_number INTEGER,
    issue_number INTEGER,
    gap_type TEXT NOT NULL,
    description TEXT NOT NULL,
    origin_file TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ctx_branch_files (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    branch TEXT NOT NULL,
    ref TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    path TEXT NOT NULL,
    blob_sha TEXT NOT NULL,
    size INTEGER NOT NULL DEFAULT 0,
    origin_file TEXT NOT NULL,
    UNIQUE(repo, ref, commit_sha, path)
);
CREATE VIRTUAL TABLE IF NOT EXISTS ctx_text_fts USING fts5(
    content,
    repo UNINDEXED,
    record_kind UNINDEXED,
    record_id UNINDEXED,
    path UNINDEXED,
    commit_sha UNINDEXED,
    pr_number UNINDEXED,
    tokenize='unicode61'
);
CREATE INDEX IF NOT EXISTS idx_ctx_cf_path ON ctx_commit_files(path);
CREATE INDEX IF NOT EXISTS idx_ctx_cf_sha ON ctx_commit_files(commit_sha);
CREATE INDEX IF NOT EXISTS idx_ctx_cf_pr ON ctx_commit_files(pr_number);
CREATE INDEX IF NOT EXISTS idx_ctx_links_path ON ctx_links(path);
CREATE INDEX IF NOT EXISTS idx_ctx_links_sha ON ctx_links(commit_sha);
CREATE INDEX IF NOT EXISTS idx_ctx_comments_item ON ctx_comments(repo, item_number);
CREATE INDEX IF NOT EXISTS idx_ctx_comments_sha ON ctx_comments(commit_sha);
CREATE INDEX IF NOT EXISTS idx_ctx_images_path ON ctx_images(path);
"""


def safe_ref(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise ValueError("commit SHA must be full-length hexadecimal")
    return value


def safe_path(path: str) -> str:
    parts = Path(path).parts
    if (
        not path
        or path.startswith(("/", "-"))
        or "\\" in path
        or ".." in parts
        or "\x00" in path
        or ":" in path
    ):
        raise ValueError(f"unsafe path: {path!r}")
    return path


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


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for pat in SECRET_REDACT_PATTERNS:
        cleaned = pat.sub("[REDACTED_SECRET]", cleaned)
    return cleaned


def _stable_uid(*parts: Any) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8", "replace"))
        h.update(b"\x00")
    return h.hexdigest()[:32]


def _parse_iso_sort_key(date_str: str, sha: str = "") -> tuple[int, str, str]:
    if not date_str:
        return (1, "9999-99-99T99:99:99+00:00", sha)
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (0, dt.astimezone(timezone.utc).isoformat(), sha)
    except ValueError:
        return (0, date_str, sha)


def _extract_number_from_url(url: str) -> int | None:
    if not url:
        return None
    m = PR_NUMBER_URL_RE.search(url)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _extract_commit_from_blob_url(url: str) -> str:
    if not url:
        return ""
    m = BLOB_COMMIT_RE.search(url)
    return m.group(1) if m else ""


def _extract_image_refs(text: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for m in IMAGE_URL_RE.finditer(text):
        target = m.group(1) or m.group(0)
        target = target.strip().rstrip(".,;:")
        if not target:
            continue
        # Ignore badge URLs like shields.io
        if "img.shields.io" in target.lower():
            continue
        if target not in seen:
            seen.add(target)
            found.append(target)
    return found


def _extract_issue_refs(text: str) -> list[int]:
    if not text:
        return []
    nums: list[int] = []
    seen: set[int] = set()
    for m in ISSUE_REF_RE.finditer(text):
        try:
            num = int(m.group(1))
        except ValueError:
            continue
        if num > 0 and num not in seen:
            seen.add(num)
            nums.append(num)
    return nums


def _is_image_path(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def open_db(path: Path) -> sqlite3.Connection:
    validate_private_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(DB_SCHEMA)
    return conn


def validate_private_output_path(path: Path, repo_root: Path | None = None) -> Path:
    return image_catalog.validate_private_output_path(path, repo_root=repo_root or REPO_ROOT)


def _git_run(git_dir: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", f"--git-dir={git_dir}", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])} failed: {proc.stderr.strip()[:400]}")
    return proc.stdout


def _git_stream(git_dir: Path, *args: str):
    proc = subprocess.Popen(
        ["git", f"--git-dir={git_dir}", *args],
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
    if code != 0:
        raise RuntimeError(f"git {' '.join(args[:3])} returned {code}: {err[:400]}")


def _resolve_bare_repo(source: Path, tmp_dir: Path) -> tuple[Path, str]:
    source = Path(source)
    if source.is_file():
        bare = tmp_dir / "bundle.git"
        subprocess.run(
            ["git", "clone", "--mirror", "-q", str(source), str(bare)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return bare, str(source)
    if (source / "HEAD").is_file():
        return source, str(source)
    if (source / ".git").exists():
        bare = tmp_dir / "worktree.git"
        subprocess.run(
            ["git", "clone", "--mirror", "-q", str(source), str(bare)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return bare, str(source)
    raise ValueError(f"Expected a bare repository, working tree, or Git bundle: {source}")


def _fts_insert(
    conn: sqlite3.Connection,
    content: str,
    repo: str,
    record_kind: str,
    record_id: str,
    path: str = "",
    commit_sha: str = "",
    pr_number: int | None = None,
) -> None:
    cleaned = sanitize_text(content).strip()
    if not cleaned:
        return
    conn.execute(
        "INSERT INTO ctx_text_fts(content, repo, record_kind, record_id, path, commit_sha, pr_number) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cleaned, repo, record_kind, record_id, path, commit_sha, str(pr_number or "")),
    )


def _record_link(
    conn: sqlite3.Connection,
    *,
    repo: str,
    pr_number: int | None = None,
    issue_number: int | None = None,
    commit_sha: str = "",
    ref: str = "",
    path: str = "",
    image_path: str = "",
    link_type: str,
    origin_url: str = "",
    origin_file: str = "",
) -> int:
    uid = _stable_uid(
        repo,
        pr_number or "",
        issue_number or "",
        commit_sha,
        ref,
        path,
        image_path,
        link_type,
    )
    cur = conn.execute(
        "INSERT OR IGNORE INTO ctx_links "
        "(link_uid, repo, pr_number, issue_number, commit_sha, ref, path, image_path, link_type, origin_url, origin_file) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            uid,
            repo,
            pr_number,
            issue_number,
            commit_sha,
            ref,
            path,
            image_path,
            link_type,
            origin_url,
            origin_file,
        ),
    )
    return cur.rowcount


def _record_image(
    conn: sqlite3.Connection,
    *,
    repo: str,
    path: str,
    commit_sha: str = "",
    ref: str = "",
    blob_sha: str = "",
    pr_number: int | None = None,
    issue_number: int | None = None,
    media_type: str = "file",
    origin_url: str = "",
    origin_file: str = "",
) -> int:
    uid = _stable_uid(repo, path, commit_sha, blob_sha, pr_number or "", issue_number or "", origin_url)
    cur = conn.execute(
        "INSERT OR IGNORE INTO ctx_images "
        "(image_uid, repo, path, commit_sha, ref, blob_sha, pr_number, issue_number, media_type, origin_url, origin_file) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            uid,
            repo,
            path,
            commit_sha,
            ref,
            blob_sha,
            pr_number,
            issue_number,
            media_type,
            origin_url,
            origin_file,
        ),
    )
    return cur.rowcount


def _record_gap(
    conn: sqlite3.Connection,
    *,
    repo: str,
    gap_type: str,
    description: str,
    origin_file: str,
    pr_number: int | None = None,
    issue_number: int | None = None,
) -> int:
    uid = _stable_uid(repo, pr_number or "", issue_number or "", gap_type, description, origin_file)
    cur = conn.execute(
        "INSERT OR IGNORE INTO ctx_gaps "
        "(gap_uid, repo, pr_number, issue_number, gap_type, description, origin_file) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid, repo, pr_number, issue_number, gap_type, sanitize_text(description), origin_file),
    )
    return cur.rowcount


def _infer_repo_from_payload(payload: dict, file_path: Path) -> str:
    if isinstance(payload.get("source"), str) and payload["source"].strip():
        return payload["source"].strip()
    if isinstance(payload.get("source_repository"), str) and payload["source_repository"].strip():
        return payload["source_repository"].strip()
    if isinstance(payload.get("repository"), str) and payload["repository"].strip():
        return payload["repository"].strip()
    parts = file_path.parts
    if "inventory" in parts:
        idx = parts.index("inventory")
        if idx + 1 < len(parts):
            candidate = parts[idx + 1]
            if candidate and not candidate.endswith(".json"):
                return f"ianmaciel7/{candidate}" if "/" not in candidate else candidate
    return "unknown"


def _import_pulls_or_issues(
    conn: sqlite3.Connection,
    entries: list[dict],
    repo: str,
    origin_file: str,
    default_kind: str,
) -> dict[str, int]:
    counts = {"items": 0, "links": 0, "images": 0}
    for entry in entries:
        if not isinstance(entry, dict) or "number" not in entry:
            continue
        num = int(entry["number"])
        is_pr = default_kind == "pull_request" or bool(entry.get("pull_request")) or ("head" in entry)
        kind = "pull_request" if is_pr else "issue"
        title = sanitize_text(entry.get("title") or "")
        body = sanitize_text(entry.get("body") or "")
        state = str(entry.get("state") or "")
        user_obj = entry.get("user") if isinstance(entry.get("user"), dict) else {}
        author = str(user_obj.get("login") or "")
        created_at = str(entry.get("created_at") or "")
        updated_at = str(entry.get("updated_at") or "")
        merged_at = str(entry.get("merged_at") or "")
        head_obj = entry.get("head") if isinstance(entry.get("head"), dict) else {}
        base_obj = entry.get("base") if isinstance(entry.get("base"), dict) else {}
        head_ref = str(head_obj.get("ref") or "")
        head_sha = str(head_obj.get("sha") or "")
        base_ref = str(base_obj.get("ref") or "")
        base_sha = str(base_obj.get("sha") or "")
        merge_sha = str(entry.get("merge_commit_sha") or "")
        html_url = str(entry.get("html_url") or "")

        existing = conn.execute(
            "SELECT id, body, head_sha, merge_commit_sha FROM ctx_items WHERE repo=? AND kind=? AND number=?",
            (repo, kind, num),
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO ctx_items "
                "(repo, kind, number, title, body, state, author, created_at, updated_at, merged_at, "
                "head_ref, head_sha, base_ref, base_sha, merge_commit_sha, html_url, origin_file) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    repo,
                    kind,
                    num,
                    title,
                    body,
                    state,
                    author,
                    created_at,
                    updated_at,
                    merged_at,
                    head_ref,
                    head_sha,
                    base_ref,
                    base_sha,
                    merge_sha,
                    html_url,
                    origin_file,
                ),
            )
            _fts_insert(
                conn,
                f"{title}\n{body}",
                repo,
                kind,
                f"{repo}#{num}",
                commit_sha=merge_sha or head_sha,
                pr_number=num if is_pr else None,
            )
            counts["items"] += 1
        elif is_pr and head_sha and not existing["head_sha"]:
            conn.execute(
                "UPDATE ctx_items SET head_ref=?, head_sha=?, base_ref=?, base_sha=?, "
                "merge_commit_sha=?, merged_at=? WHERE id=?",
                (head_ref, head_sha, base_ref, base_sha, merge_sha, merged_at, existing["id"]),
            )

        pr_num = num if is_pr else None
        issue_num = None if is_pr else num
        primary_sha = merge_sha or head_sha
        primary_ref = head_ref or base_ref

        if primary_sha:
            counts["links"] += _record_link(
                conn,
                repo=repo,
                pr_number=pr_num,
                issue_number=issue_num,
                commit_sha=primary_sha,
                ref=primary_ref,
                link_type="pr_commit" if is_pr else "issue_commit",
                origin_url=html_url,
                origin_file=origin_file,
            )
        if head_sha and merge_sha and head_sha != merge_sha:
            counts["links"] += _record_link(
                conn,
                repo=repo,
                pr_number=pr_num,
                issue_number=issue_num,
                commit_sha=head_sha,
                ref=head_ref,
                link_type="pr_head_commit",
                origin_url=html_url,
                origin_file=origin_file,
            )

        # Extract cross-referenced issues from PR/issue body
        for ref_num in _extract_issue_refs(f"{title}\n{body}"):
            if ref_num != num:
                counts["links"] += _record_link(
                    conn,
                    repo=repo,
                    pr_number=pr_num,
                    issue_number=ref_num,
                    commit_sha=primary_sha,
                    ref=primary_ref,
                    link_type="text_cross_reference",
                    origin_url=html_url,
                    origin_file=origin_file,
                )

        # Extract image/screenshot references from PR/issue body
        for img_ref in _extract_image_refs(body):
            counts["images"] += _record_image(
                conn,
                repo=repo,
                path=img_ref,
                commit_sha=primary_sha,
                ref=primary_ref,
                pr_number=pr_num,
                issue_number=issue_num,
                media_type="attachment_or_reference",
                origin_url=html_url,
                origin_file=origin_file,
            )
            counts["links"] += _record_link(
                conn,
                repo=repo,
                pr_number=pr_num,
                issue_number=issue_num,
                commit_sha=primary_sha,
                ref=primary_ref,
                image_path=img_ref,
                link_type="body_image_reference",
                origin_url=html_url,
                origin_file=origin_file,
            )

        # Ensure PR commits exist in ctx_commits even without local Git bundle
        for sha_val, ref_val, date_val in (
            (merge_sha, base_ref or head_ref, merged_at or updated_at or created_at),
            (head_sha, head_ref, updated_at or created_at),
        ):
            if sha_val:
                conn.execute(
                    "INSERT OR IGNORE INTO ctx_commits "
                    "(repo, commit_sha, date, ref, author, subject, body, origin_source) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (repo, sha_val, date_val, ref_val, author, title, body, origin_file),
                )
    return counts


def _import_pr_file_diffs(
    conn: sqlite3.Connection,
    records: list[dict],
    repo: str,
    origin_file: str,
) -> dict[str, int]:
    counts = {"commit_files": 0, "links": 0, "images": 0, "gaps": 0}
    pr_meta_cache: dict[int, tuple[str, str, str]] = {}
    for row in conn.execute(
        "SELECT number, head_sha, merge_commit_sha, head_ref, base_ref, merged_at, updated_at, created_at "
        "FROM ctx_items WHERE repo=? AND kind='pull_request'",
        (repo,),
    ):
        sha = row["merge_commit_sha"] or row["head_sha"] or ""
        ref = row["head_ref"] or row["base_ref"] or ""
        date = row["merged_at"] or row["updated_at"] or row["created_at"] or ""
        pr_meta_cache[int(row["number"])] = (sha, ref, date)

    for rec in records:
        if not isinstance(rec, dict) or "number" not in rec:
            continue
        pr_num = int(rec["number"])
        if rec.get("possibly_truncated"):
            counts["gaps"] += _record_gap(
                conn,
                repo=repo,
                pr_number=pr_num,
                gap_type="truncated_pr_files",
                description=f"PR #{pr_num} file diff list was marked possibly_truncated during export.",
                origin_file=origin_file,
            )
        fallback_sha, pr_ref, pr_date = pr_meta_cache.get(pr_num, ("", "", ""))
        for fl in rec.get("files") or []:
            if not isinstance(fl, dict):
                continue
            fpath = str(fl.get("filename") or "")
            if not fpath or is_secret_path(fpath):
                continue
            try:
                safe_path(fpath)
            except ValueError:
                continue
            prev_path = str(fl.get("previous_filename") or "")
            status = str(fl.get("status") or "modified")
            blob_sha = str(fl.get("sha") or "")
            blob_url = str(fl.get("blob_url") or "")
            patch = sanitize_text(fl.get("patch") or "")
            additions = int(fl.get("additions") or 0)
            deletions = int(fl.get("deletions") or 0)
            commit_sha = _extract_commit_from_blob_url(blob_url) or fallback_sha
            if not commit_sha:
                continue

            conn.execute(
                "INSERT OR IGNORE INTO ctx_commits "
                "(repo, commit_sha, date, ref, author, subject, body, origin_source) "
                "VALUES (?, ?, ?, ?, '', '', '', ?)",
                (repo, commit_sha, pr_date, pr_ref, origin_file),
            )

            cur = conn.execute(
                "INSERT OR IGNORE INTO ctx_commit_files "
                "(repo, commit_sha, ref, date, path, previous_path, status, blob_sha, "
                "additions, deletions, patch, blob_url, pr_number, origin_file) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    repo,
                    commit_sha,
                    pr_ref,
                    pr_date,
                    fpath,
                    prev_path,
                    status,
                    blob_sha,
                    additions,
                    deletions,
                    patch,
                    blob_url,
                    pr_num,
                    origin_file,
                ),
            )
            if cur.rowcount:
                counts["commit_files"] += 1
                _fts_insert(
                    conn,
                    f"{fpath}\n{patch}",
                    repo,
                    "pr_diff",
                    f"{repo}#{pr_num}:{fpath}",
                    path=fpath,
                    commit_sha=commit_sha,
                    pr_number=pr_num,
                )

            counts["links"] += _record_link(
                conn,
                repo=repo,
                pr_number=pr_num,
                commit_sha=commit_sha,
                ref=pr_ref,
                path=fpath,
                image_path=fpath if _is_image_path(fpath) else "",
                link_type="pr_file_diff",
                origin_url=blob_url,
                origin_file=origin_file,
            )
            if _is_image_path(fpath):
                counts["images"] += _record_image(
                    conn,
                    repo=repo,
                    path=fpath,
                    commit_sha=commit_sha,
                    ref=pr_ref,
                    blob_sha=blob_sha,
                    pr_number=pr_num,
                    media_type=f"pr_diff_{status}",
                    origin_url=blob_url,
                    origin_file=origin_file,
                )
    return counts


def _import_reviews(
    conn: sqlite3.Connection,
    data: list[dict],
    repo: str,
    origin_file: str,
) -> dict[str, int]:
    counts = {"comments": 0, "links": 0}
    for rec in data:
        if not isinstance(rec, dict) or "number" not in rec:
            continue
        pr_num = int(rec["number"])
        for rev in rec.get("reviews") or []:
            if not isinstance(rev, dict):
                continue
            rev_id = rev.get("id") or _stable_uid(pr_num, rev.get("submitted_at"), rev.get("body"))
            uid = f"review:{repo}:{pr_num}:{rev_id}"
            user_obj = rev.get("user") if isinstance(rev.get("user"), dict) else {}
            author = str(user_obj.get("login") or "")
            body = sanitize_text(rev.get("body") or "")
            commit_sha = str(rev.get("commit_id") or "")
            state = str(rev.get("state") or "")
            created_at = str(rev.get("submitted_at") or "")
            html_url = str(rev.get("html_url") or "")
            cur = conn.execute(
                "INSERT OR IGNORE INTO ctx_comments "
                "(comment_uid, repo, item_kind, item_number, comment_kind, author, body, path, "
                "commit_sha, diff_hunk, review_state, created_at, html_url, origin_file) "
                "VALUES (?, ?, 'pull_request', ?, 'review', ?, ?, '', ?, '', ?, ?, ?, ?)",
                (uid, repo, pr_num, author, body, commit_sha, state, created_at, html_url, origin_file),
            )
            if cur.rowcount:
                counts["comments"] += 1
                _fts_insert(
                    conn,
                    body,
                    repo,
                    "review",
                    uid,
                    commit_sha=commit_sha,
                    pr_number=pr_num,
                )
            if commit_sha:
                counts["links"] += _record_link(
                    conn,
                    repo=repo,
                    pr_number=pr_num,
                    commit_sha=commit_sha,
                    link_type="pr_review",
                    origin_url=html_url,
                    origin_file=origin_file,
                )
    return counts


def _import_inline_comments(
    conn: sqlite3.Connection,
    data: list[dict],
    repo: str,
    origin_file: str,
) -> dict[str, int]:
    counts = {"comments": 0, "links": 0, "images": 0}
    for item in data:
        if not isinstance(item, dict):
            continue
        pr_num = _extract_number_from_url(str(item.get("pull_request_url") or item.get("html_url") or ""))
        if pr_num is None:
            continue
        cid = item.get("id") or _stable_uid(pr_num, item.get("path"), item.get("created_at"), item.get("body"))
        uid = f"inline:{repo}:{pr_num}:{cid}"
        user_obj = item.get("user") if isinstance(item.get("user"), dict) else {}
        author = str(user_obj.get("login") or "")
        body = sanitize_text(item.get("body") or "")
        fpath = str(item.get("path") or "")
        if fpath and is_secret_path(fpath):
            continue
        commit_sha = str(item.get("commit_id") or item.get("original_commit_id") or "")
        diff_hunk = sanitize_text(item.get("diff_hunk") or "")
        created_at = str(item.get("created_at") or "")
        html_url = str(item.get("html_url") or "")
        cur = conn.execute(
            "INSERT OR IGNORE INTO ctx_comments "
            "(comment_uid, repo, item_kind, item_number, comment_kind, author, body, path, "
            "commit_sha, diff_hunk, review_state, created_at, html_url, origin_file) "
            "VALUES (?, ?, 'pull_request', ?, 'inline_review_comment', ?, ?, ?, ?, ?, '', ?, ?, ?)",
            (uid, repo, pr_num, author, body, fpath, commit_sha, diff_hunk, created_at, html_url, origin_file),
        )
        if cur.rowcount:
            counts["comments"] += 1
            _fts_insert(
                conn,
                f"{fpath}\n{body}\n{diff_hunk}",
                repo,
                "inline_comment",
                uid,
                path=fpath,
                commit_sha=commit_sha,
                pr_number=pr_num,
            )
        counts["links"] += _record_link(
            conn,
            repo=repo,
            pr_number=pr_num,
            commit_sha=commit_sha,
            path=fpath,
            image_path=fpath if _is_image_path(fpath) else "",
            link_type="inline_review_comment",
            origin_url=html_url,
            origin_file=origin_file,
        )
        for img_ref in _extract_image_refs(body):
            counts["images"] += _record_image(
                conn,
                repo=repo,
                path=img_ref,
                commit_sha=commit_sha,
                pr_number=pr_num,
                media_type="comment_image_reference",
                origin_url=html_url,
                origin_file=origin_file,
            )
    return counts


def _import_conversation_comments(
    conn: sqlite3.Connection,
    data: list[dict],
    repo: str,
    origin_file: str,
) -> dict[str, int]:
    counts = {"comments": 0, "links": 0, "images": 0}
    for item in data:
        if not isinstance(item, dict):
            continue
        html_url = str(item.get("html_url") or "")
        issue_url = str(item.get("issue_url") or "")
        num = _extract_number_from_url(issue_url or html_url)
        if num is None:
            continue
        is_pr = "/pull/" in html_url
        item_kind = "pull_request" if is_pr else "issue"
        cid = item.get("id") or _stable_uid(num, item.get("created_at"), item.get("body"))
        uid = f"conv:{repo}:{num}:{cid}"
        user_obj = item.get("user") if isinstance(item.get("user"), dict) else {}
        author = str(user_obj.get("login") or "")
        body = sanitize_text(item.get("body") or "")
        created_at = str(item.get("created_at") or "")
        cur = conn.execute(
            "INSERT OR IGNORE INTO ctx_comments "
            "(comment_uid, repo, item_kind, item_number, comment_kind, author, body, path, "
            "commit_sha, diff_hunk, review_state, created_at, html_url, origin_file) "
            "VALUES (?, ?, ?, ?, 'conversation_comment', ?, ?, '', '', '', '', ?, ?, ?)",
            (uid, repo, item_kind, num, author, body, created_at, html_url, origin_file),
        )
        if cur.rowcount:
            counts["comments"] += 1
            _fts_insert(
                conn,
                body,
                repo,
                "conversation_comment",
                uid,
                pr_number=num if is_pr else None,
            )
        for img_ref in _extract_image_refs(body):
            counts["images"] += _record_image(
                conn,
                repo=repo,
                path=img_ref,
                pr_number=num if is_pr else None,
                issue_number=None if is_pr else num,
                media_type="comment_image_reference",
                origin_url=html_url,
                origin_file=origin_file,
            )
            counts["links"] += _record_link(
                conn,
                repo=repo,
                pr_number=num if is_pr else None,
                issue_number=None if is_pr else num,
                image_path=img_ref,
                link_type="comment_image_reference",
                origin_url=html_url,
                origin_file=origin_file,
            )
    return counts


def _import_issue_events(
    conn: sqlite3.Connection,
    data: list[dict],
    repo: str,
    origin_file: str,
) -> dict[str, int]:
    counts = {"events": 0, "links": 0}
    for item in data:
        if not isinstance(item, dict):
            continue
        issue_obj = item.get("issue") if isinstance(item.get("issue"), dict) else {}
        num = issue_obj.get("number")
        if num is None:
            continue
        num = int(num)
        ev_id = item.get("id") or _stable_uid(num, item.get("event"), item.get("created_at"))
        uid = f"event:{repo}:{num}:{ev_id}"
        ev_type = str(item.get("event") or "")
        actor_obj = item.get("actor") if isinstance(item.get("actor"), dict) else {}
        actor = str(actor_obj.get("login") or "")
        commit_sha = str(item.get("commit_id") or "")
        created_at = str(item.get("created_at") or "")
        html_url = str(issue_obj.get("html_url") or item.get("url") or "")
        cur = conn.execute(
            "INSERT OR IGNORE INTO ctx_events "
            "(event_uid, repo, item_number, event_type, actor, commit_sha, created_at, html_url, origin_file) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, repo, num, ev_type, actor, commit_sha, created_at, html_url, origin_file),
        )
        if cur.rowcount:
            counts["events"] += 1
        if commit_sha:
            is_pr = "/pull/" in html_url
            counts["links"] += _record_link(
                conn,
                repo=repo,
                pr_number=num if is_pr else None,
                issue_number=None if is_pr else num,
                commit_sha=commit_sha,
                link_type=f"issue_event_{ev_type or 'commit'}",
                origin_url=html_url,
                origin_file=origin_file,
            )
    return counts


def _import_releases(
    conn: sqlite3.Connection,
    entries: list[dict],
    repo: str,
    origin_file: str,
) -> int:
    count = 0
    for rel in entries:
        if not isinstance(rel, dict) or not rel.get("tag_name"):
            continue
        tag = str(rel["tag_name"])
        name = sanitize_text(rel.get("name") or tag)
        body = sanitize_text(rel.get("body") or "")
        target = str(rel.get("target_commitish") or "")
        created_at = str(rel.get("created_at") or "")
        published_at = str(rel.get("published_at") or "")
        html_url = str(rel.get("html_url") or "")
        cur = conn.execute(
            "INSERT OR IGNORE INTO ctx_releases "
            "(repo, tag_name, name, body, target_commitish, commit_sha, created_at, published_at, html_url, origin_file) "
            "VALUES (?, ?, ?, ?, ?, '', ?, ?, ?, ?)",
            (repo, tag, name, body, target, created_at, published_at, html_url, origin_file),
        )
        if cur.rowcount:
            count += 1
            _fts_insert(conn, f"{tag}\n{name}\n{body}", repo, "release", f"{repo}:{tag}")
    return count


def _import_tags(
    conn: sqlite3.Connection,
    entries: list[dict],
    repo: str,
) -> int:
    count = 0
    for tag in entries:
        if not isinstance(tag, dict):
            continue
        ref = str(tag.get("ref") or "")
        tag_name = ref.replace("refs/tags/", "", 1) if ref.startswith("refs/tags/") else ref
        obj = tag.get("object") if isinstance(tag.get("object"), dict) else {}
        sha = str(obj.get("sha") or "")
        if tag_name and sha:
            cur = conn.execute(
                "UPDATE ctx_releases SET commit_sha=? WHERE repo=? AND tag_name=? AND commit_sha=''",
                (sha, repo, tag_name),
            )
            count += cur.rowcount
    return count


def _import_workflow_runs(
    conn: sqlite3.Connection,
    records: list[dict],
    repo: str,
    origin_file: str,
) -> int:
    count = 0
    for rec in records:
        if not isinstance(rec, dict) or "id" not in rec:
            continue
        run_id = int(rec["id"])
        name = sanitize_text(rec.get("name") or "")
        branch = str(rec.get("head_branch") or "")
        sha = str(rec.get("head_sha") or "")
        event = str(rec.get("event") or "")
        status = str(rec.get("status") or "")
        conclusion = str(rec.get("conclusion") or "")
        created_at = str(rec.get("created_at") or "")
        html_url = str(rec.get("html_url") or "")
        prs = [
            int(p["number"])
            for p in (rec.get("pull_requests") or [])
            if isinstance(p, dict) and p.get("number") is not None
        ]
        cur = conn.execute(
            "INSERT OR IGNORE INTO ctx_workflow_runs "
            "(repo, run_id, name, head_branch, head_sha, event, status, conclusion, "
            "created_at, html_url, pr_numbers_json, origin_file) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (repo, run_id, name, branch, sha, event, status, conclusion, created_at, html_url, json.dumps(prs), origin_file),
        )
        if cur.rowcount:
            count += 1
        for pr_num in prs:
            _record_link(
                conn,
                repo=repo,
                pr_number=pr_num,
                commit_sha=sha,
                ref=branch,
                link_type="workflow_run",
                origin_url=html_url,
                origin_file=origin_file,
            )
    return count


def _import_branch_inventories(
    conn: sqlite3.Connection,
    payload: dict,
    repo: str,
    origin_file: str,
) -> dict[str, int]:
    counts = {"files": 0, "images": 0}
    for b in payload.get("branch_inventories") or []:
        if not isinstance(b, dict):
            continue
        branch = str(b.get("branch") or "")
        ref = str(b.get("ref") or branch)
        commit_sha = str(b.get("sha") or "")
        for fl in b.get("files") or []:
            if not isinstance(fl, dict):
                continue
            fpath = str(fl.get("path") or "")
            if not fpath or is_secret_path(fpath):
                continue
            try:
                safe_path(fpath)
            except ValueError:
                continue
            blob_sha = str(fl.get("sha") or "")
            size = int(fl.get("size") or 0)
            cur = conn.execute(
                "INSERT OR IGNORE INTO ctx_branch_files "
                "(repo, branch, ref, commit_sha, path, blob_sha, size, origin_file) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (repo, branch, ref, commit_sha, fpath, blob_sha, size, origin_file),
            )
            if cur.rowcount:
                counts["files"] += 1
            if _is_image_path(fpath):
                counts["images"] += _record_image(
                    conn,
                    repo=repo,
                    path=fpath,
                    commit_sha=commit_sha,
                    ref=ref,
                    blob_sha=blob_sha,
                    media_type="branch_inventory_image",
                    origin_file=origin_file,
                )
    return counts


def _import_supplement_or_gaps(
    conn: sqlite3.Connection,
    payload: dict,
    repo: str,
    origin_file: str,
) -> int:
    gaps = 0
    if "pull_request" in payload and ("original_export_error" in payload or "limitations" in payload):
        pr_num = int(payload["pull_request"])
        parts = []
        if payload.get("original_export_error"):
            parts.append(f"Export error: {payload['original_export_error']}")
        if payload.get("conclusion"):
            parts.append(f"Conclusion: {payload['conclusion']}")
        if payload.get("limitations"):
            parts.append(f"Limitations: {payload['limitations']}")
        gaps += _record_gap(
            conn,
            repo=repo,
            pr_number=pr_num,
            gap_type="platform_metadata_supplement",
            description=" | ".join(parts),
            origin_file=origin_file,
        )
        _fts_insert(
            conn,
            " | ".join(parts),
            repo,
            "gap_supplement",
            f"{repo}#{pr_num}:supplement",
            pr_number=pr_num,
        )
    return gaps


def _import_markdown_decisions(
    conn: sqlite3.Connection,
    md_path: Path,
    repo: str,
) -> int:
    text = sanitize_text(md_path.read_text(encoding="utf-8", errors="replace"))
    origin = str(md_path)
    gaps = 0
    for line in text.splitlines():
        low = line.lower()
        if any(tok in low for tok in ("expir", "indispon", "faltam", "lacuna", "pendente", "unavailable")):
            gaps += _record_gap(
                conn,
                repo=repo,
                gap_type="documented_gap",
                description=line.strip(),
                origin_file=origin,
            )
    _fts_insert(conn, text, repo, "decision_doc", origin, path=md_path.name)
    return gaps


def import_inventory(
    inventory_dir: Path,
    conn: sqlite3.Connection,
    *,
    repo_override: str | None = None,
) -> dict[str, int]:
    """Recursively import preserved metadata from an inventory directory."""
    inventory_dir = Path(inventory_dir)
    if not inventory_dir.is_dir():
        raise FileNotFoundError(f"Inventory directory not found: {inventory_dir}")

    summary = {
        "files_processed": 0,
        "items": 0,
        "commit_files": 0,
        "comments": 0,
        "events": 0,
        "images": 0,
        "links": 0,
        "releases": 0,
        "workflow_runs": 0,
        "branch_files": 0,
        "gaps": 0,
    }
    now_iso = datetime.now(timezone.utc).isoformat()

    json_files = sorted(inventory_dir.rglob("*.json"))
    md_files = sorted(inventory_dir.rglob("*.md"))

    # Pass 1: import pulls, issues, releases, tags, branch inventories, supplements
    deferred: list[tuple[Path, dict, str]] = []
    with conn:
        for jp in json_files:
            raw = jp.read_text(encoding="utf-8")
            try:
                payload = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(payload, dict):
                continue
            repo = repo_override or _infer_repo_from_payload(payload, jp)
            origin = str(jp)
            conn.execute(
                "INSERT OR REPLACE INTO ctx_sources (source_key, source_type, repo, location, imported_at) "
                "VALUES (?, 'inventory_json', ?, ?, ?)",
                (origin, repo, origin, now_iso),
            )
            summary["files_processed"] += 1

            name_low = jp.name.lower()
            endpoint = str(payload.get("endpoint") or "").lower()

            if "entries" in payload and isinstance(payload["entries"], list):
                if "pull" in name_low or "/pulls" in endpoint:
                    res = _import_pulls_or_issues(conn, payload["entries"], repo, origin, "pull_request")
                    for k in ("items", "links", "images"):
                        summary[k] += res[k]
                elif "issue" in name_low or "/issues" in endpoint:
                    res = _import_pulls_or_issues(conn, payload["entries"], repo, origin, "issue")
                    for k in ("items", "links", "images"):
                        summary[k] += res[k]
                elif "release" in name_low or "/releases" in endpoint:
                    summary["releases"] += _import_releases(conn, payload["entries"], repo, origin)
                elif "tag" in name_low or "/tags" in endpoint:
                    deferred.append((jp, payload, repo))
            elif "branch_inventories" in payload:
                res = _import_branch_inventories(conn, payload, repo, origin)
                summary["branch_files"] += res["files"]
                summary["images"] += res["images"]
            elif "pull_request" in payload and ("original_export_error" in payload or "limitations" in payload):
                summary["gaps"] += _import_supplement_or_gaps(conn, payload, repo, origin)
            else:
                deferred.append((jp, payload, repo))

        # Pass 2: tags, diffs, reviews, comments, events, workflow runs
        for jp, payload, repo in deferred:
            origin = str(jp)
            name_low = jp.name.lower()
            endpoint = str(payload.get("endpoint") or "").lower()
            if "entries" in payload and ("tag" in name_low or "/tags" in endpoint):
                _import_tags(conn, payload["entries"], repo)
            elif "records" in payload and isinstance(payload["records"], list):
                if "file-diffs" in name_low or "diff" in name_low:
                    res = _import_pr_file_diffs(conn, payload["records"], repo, origin)
                    for k in ("commit_files", "links", "images", "gaps"):
                        summary[k] += res[k]
                elif "workflow" in name_low or "actions" in jp.parts:
                    summary["workflow_runs"] += _import_workflow_runs(conn, payload["records"], repo, origin)
            elif "data" in payload and isinstance(payload["data"], list):
                if "review" in name_low and "inline" not in name_low:
                    res = _import_reviews(conn, payload["data"], repo, origin)
                    summary["comments"] += res["comments"]
                    summary["links"] += res["links"]
                elif "inline" in name_low or "/pulls/comments" in endpoint:
                    res = _import_inline_comments(conn, payload["data"], repo, origin)
                    summary["comments"] += res["comments"]
                    summary["links"] += res["links"]
                    summary["images"] += res["images"]
                elif "conversation" in name_low or "/issues/comments" in endpoint:
                    res = _import_conversation_comments(conn, payload["data"], repo, origin)
                    summary["comments"] += res["comments"]
                    summary["links"] += res["links"]
                    summary["images"] += res["images"]
                elif "event" in name_low or "/issues/events" in endpoint:
                    res = _import_issue_events(conn, payload["data"], repo, origin)
                    summary["events"] += res["events"]
                    summary["links"] += res["links"]

        for mp in md_files:
            repo = repo_override or _infer_repo_from_payload({}, mp)
            summary["gaps"] += _import_markdown_decisions(conn, mp, repo)

    return summary


def ingest_git_repo(
    repo_or_bundle: Path,
    repo_name: str,
    conn: sqlite3.Connection,
) -> dict[str, int]:
    """Ingest commits, per-file history, refs, and image paths from a Git repo or bundle."""
    summary = {"commits": 0, "commit_files": 0, "images": 0, "links": 0}
    now_iso = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix="ctx-git-") as tmp:
        bare, resolved_source = _resolve_bare_repo(Path(repo_or_bundle), Path(tmp))

        ref_for_sha: dict[str, str] = {}
        ref_list: list[tuple[str, str]] = []
        for line in _git_stream(bare, "for-each-ref", "--format=%(refname)%09%(objectname)"):
            if "\t" not in line:
                continue
            refname, obj_sha = line.split("\t", 1)
            ref_list.append((refname, obj_sha))
            try:
                csha = _git_run(bare, "rev-parse", f"{refname}^{{commit}}").strip()
            except RuntimeError:
                csha = obj_sha
            if csha not in ref_for_sha or refname.startswith("refs/heads/main"):
                ref_for_sha[csha] = refname

        # Map reachable commits to branch/ref names deterministically
        commit_ref_map: dict[str, str] = {}
        ordered_refs = sorted(
            ref_list,
            key=lambda x: (
                0 if x[0] == "refs/heads/main" else (1 if x[0].startswith("refs/heads/") else 2),
                x[0],
            ),
        )
        for refname, _ in ordered_refs:
            try:
                for csha in _git_stream(bare, "rev-list", refname):
                    if csha not in commit_ref_map:
                        commit_ref_map[csha] = refname
            except RuntimeError:
                continue

        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO ctx_sources (source_key, source_type, repo, location, imported_at) "
                "VALUES (?, 'git_repo', ?, ?, ?)",
                (f"git:{repo_name}:{resolved_source}", repo_name, resolved_source, now_iso),
            )
            current_sha = ""
            current_date = ""
            current_author = ""
            current_subject = ""
            current_body = ""
            current_ref = ""

            fmt = "%x1e%H%x1f%aI%x1f%an%x1f%s%x1f%b%x1e"
            # Read commit log with file name-status in one streaming pass
            log_args = ["log", "--all", "--root", "--no-renames", "--name-status", f"--format=%x1e%H%x1f%aI%x1f%an%x1f%s%x1f%b%x1d"]
            buf: list[str] = []
            in_header = False

            def flush_commit_header(header_text: str) -> None:
                nonlocal current_sha, current_date, current_author, current_subject, current_body, current_ref
                parts = header_text.split("\x1f", 4)
                if len(parts) != 5:
                    return
                current_sha, current_date, current_author, current_subject, current_body = parts
                current_subject = sanitize_text(current_subject.strip())
                current_body = sanitize_text(current_body.strip())
                current_ref = commit_ref_map.get(current_sha, ref_for_sha.get(current_sha, ""))
                cur = conn.execute(
                    "INSERT OR IGNORE INTO ctx_commits "
                    "(repo, commit_sha, date, ref, author, subject, body, origin_source) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        repo_name,
                        current_sha,
                        current_date,
                        current_ref,
                        current_author,
                        current_subject,
                        current_body,
                        resolved_source,
                    ),
                )
                if cur.rowcount:
                    summary["commits"] += 1
                    _fts_insert(
                        conn,
                        f"{current_subject}\n{current_body}",
                        repo_name,
                        "git_commit",
                        f"{repo_name}@{current_sha}",
                        commit_sha=current_sha,
                    )
                else:
                    conn.execute(
                        "UPDATE ctx_commits SET "
                        "date=CASE WHEN date='' THEN ? ELSE date END, "
                        "ref=CASE WHEN ref='' THEN ? ELSE ref END, "
                        "author=CASE WHEN author='' THEN ? ELSE author END, "
                        "subject=CASE WHEN subject='' THEN ? ELSE subject END, "
                        "body=CASE WHEN body='' THEN ? ELSE body END "
                        "WHERE repo=? AND commit_sha=?",
                        (
                            current_date,
                            current_ref,
                            current_author,
                            current_subject,
                            current_body,
                            repo_name,
                            current_sha,
                        ),
                    )
                for ref_pr in _extract_issue_refs(f"{current_subject}\n{current_body}"):
                    summary["links"] += _record_link(
                        conn,
                        repo=repo_name,
                        pr_number=ref_pr,
                        commit_sha=current_sha,
                        ref=current_ref,
                        link_type="commit_message_ref",
                        origin_file=resolved_source,
                    )

            for line in _git_stream(bare, *log_args):
                if "\x1e" in line:
                    _, rest = line.split("\x1e", 1)
                    if "\x1d" in rest:
                        header_part, _ = rest.split("\x1d", 1)
                        flush_commit_header(header_part)
                        in_header = False
                    else:
                        buf = [rest]
                        in_header = True
                    continue
                if in_header:
                    if "\x1d" in line:
                        end_part, _ = line.split("\x1d", 1)
                        buf.append(end_part)
                        flush_commit_header("\n".join(buf))
                        buf = []
                        in_header = False
                    else:
                        buf.append(line)
                    continue
                if not current_sha or "\t" not in line:
                    continue
                fields = line.split("\t")
                status_code = fields[0][:1]
                if status_code not in {"A", "M", "D", "T", "R", "C"}:
                    continue
                fpath = fields[-1]
                prev_path = fields[1] if len(fields) > 2 else ""
                if not fpath or is_secret_path(fpath):
                    continue
                try:
                    safe_path(fpath)
                except ValueError:
                    continue
                status_word = {
                    "A": "added",
                    "M": "modified",
                    "D": "removed",
                    "T": "type_changed",
                    "R": "renamed",
                    "C": "copied",
                }.get(status_code, status_code)
                cur = conn.execute(
                    "INSERT OR IGNORE INTO ctx_commit_files "
                    "(repo, commit_sha, ref, date, path, previous_path, status, blob_sha, "
                    "additions, deletions, patch, blob_url, pr_number, origin_file) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, '', 0, 0, '', '', NULL, ?)",
                    (repo_name, current_sha, current_ref, current_date, fpath, prev_path, status_word, resolved_source),
                )
                if cur.rowcount:
                    summary["commit_files"] += 1
                    _fts_insert(
                        conn,
                        fpath,
                        repo_name,
                        "git_file",
                        f"{repo_name}@{current_sha}:{fpath}",
                        path=fpath,
                        commit_sha=current_sha,
                    )
                if _is_image_path(fpath):
                    summary["images"] += _record_image(
                        conn,
                        repo=repo_name,
                        path=fpath,
                        commit_sha=current_sha,
                        ref=current_ref,
                        media_type=f"git_{status_word}",
                        origin_file=resolved_source,
                    )
                    summary["links"] += _record_link(
                        conn,
                        repo=repo_name,
                        commit_sha=current_sha,
                        ref=current_ref,
                        path=fpath,
                        image_path=fpath,
                        link_type="git_image_change",
                        origin_file=resolved_source,
                    )
            del fmt
    return summary


def _highlight_snippet(text: str, terms: list[str], max_chars: int = 240) -> str:
    """Extract a contextual snippet with matching terms highlighted with [[...]]."""
    clean = " ".join(sanitize_text(text).split())
    if not clean:
        return ""
    valid_terms = [t for t in terms if len(t) >= 2]
    pattern = None
    if valid_terms:
        ordered = sorted(set(valid_terms), key=len, reverse=True)
        pattern = re.compile("(" + "|".join(re.escape(t) for t in ordered) + ")", re.IGNORECASE)

    match = pattern.search(clean) if pattern else None
    if match:
        start = max(0, match.start() - max_chars // 3)
        end = min(len(clean), start + max_chars)
        if start > 0:
            ws = clean.rfind(" ", 0, start + 15)
            if ws != -1 and ws >= start - 20:
                start = ws + 1
        excerpt = clean[start:end]
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(clean):
            excerpt = excerpt + "..."
    else:
        excerpt = clean[:max_chars] + ("..." if len(clean) > max_chars else "")

    if pattern:
        excerpt = pattern.sub(lambda m: f"[[{m.group(0)}]]", excerpt)
    return excerpt


def _extract_cited_justifications(
    *,
    commit_subject: str,
    commit_body: str,
    pr_items: list[dict],
    comments: list[dict],
) -> tuple[bool, list[dict[str, str]]]:
    """Return ONLY explicitly cited justifications from commits, PRs, issues, or comments.

    Never invents or infers motivation when no explicit text evidence exists.
    """
    citations: list[dict[str, str]] = []
    seen_quotes: set[str] = set()

    def add_citation(source_type: str, source_ref: str, quote: str, author: str = "", url: str = "") -> None:
        normalized = " ".join(sanitize_text(quote).split())
        if not normalized or normalized in seen_quotes:
            return
        seen_quotes.add(normalized)
        citations.append(
            {
                "source_type": source_type,
                "source_ref": source_ref,
                "author": author,
                "quote": normalized[:400],
                "url": url,
            }
        )

    # 1. Explicit commit body (beyond bare subject) or explanatory subject
    if commit_body.strip():
        add_citation("commit_body", "commit", commit_body.strip())
    elif commit_subject.strip() and DECISION_LINE_RE.search(commit_subject):
        # Only treat commit subject as cited justification if it states a reason/decision
        # beyond a generic filename or merge line.
        lower_subj = commit_subject.strip().lower()
        if not lower_subj.startswith("merge pull request"):
            add_citation("commit_subject", "commit", commit_subject.strip())

    # 2. Linked PR / issue description body
    for item in pr_items:
        body = (item.get("body") or "").strip()
        if body:
            # Extract lines/paragraphs containing rationale or summary bullets, or full trimmed body
            selected_lines = [
                ln.strip()
                for ln in body.splitlines()
                if ln.strip() and not ln.strip().startswith("```")
            ]
            if selected_lines:
                quote = " ".join(selected_lines[:6])
                add_citation(
                    item.get("kind") or "pull_request",
                    f"#{item['number']}",
                    quote,
                    author=item.get("author") or "",
                    url=item.get("html_url") or "",
                )

    # 3. Review, inline review, or conversation comments
    for c in comments:
        cbody = (c.get("body") or "").strip()
        if not cbody:
            continue
        # Skip boilerplate rate-limit or generic automated banners with no technical rationale
        low = cbody.lower()
        if "you have reached your codex usage limits" in low:
            continue
        if "github code scanning has recently been set up" in low:
            continue
        add_citation(
            c.get("comment_kind") or "comment",
            f"#{c['item_number']}",
            cbody,
            author=c.get("author") or "",
            url=c.get("html_url") or "",
        )

    return (len(citations) > 0, citations)


def query_history(
    conn: sqlite3.Connection,
    path_or_keyword: str,
    *,
    repo: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Query historical file timeline with objective links and cited justifications.

    Groups results by (repository, path) with commits ordered chronologically from
    first to last, including date, ref/branch, full SHA, and highlighted snippet.
    Separates objective facts from inferences by reporting explicit citations or
    'sem justificativa citada'.
    """
    raw_query = (path_or_keyword or "").strip()
    if not raw_query:
        return {"query": raw_query, "files": [], "gaps": []}

    limit = max(1, min(int(limit), 100))
    terms = [t for t in re.findall(r"[A-Za-z0-9_.-]+", raw_query) if len(t) >= 2]
    if not terms:
        terms = [raw_query]
    highlight_terms = list(dict.fromkeys([raw_query, *terms, *re.findall(r"\w+", raw_query)]))

    matched_keys: set[tuple[str, str]] = set()
    # Track extra text snippets found via FTS or patches for each (repo, path)
    matched_snippets_by_commit: dict[tuple[str, str, str], list[str]] = {}

    # 1. Exact or partial path matches in ctx_commit_files
    exact_keys: set[tuple[str, str]] = set()
    path_keys: set[tuple[str, str]] = set()
    fts_keys: set[tuple[str, str]] = set()

    like_pat = "%" + raw_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    sql_exact = "SELECT DISTINCT repo, path FROM ctx_commit_files WHERE lower(path) = lower(?)"
    p_exact: list[Any] = [raw_query]
    if repo:
        sql_exact += " AND repo = ?"
        p_exact.append(repo)
    for row in conn.execute(sql_exact, p_exact):
        exact_keys.add((row["repo"], row["path"]))
        matched_keys.add((row["repo"], row["path"]))

    sql_path = "SELECT DISTINCT repo, path FROM ctx_commit_files WHERE lower(path) LIKE lower(?) ESCAPE '\\'"
    params_path: list[Any] = [like_pat]
    if repo:
        sql_path += " AND repo = ?"
        params_path.append(repo)
    for row in conn.execute(sql_path, params_path):
        path_keys.add((row["repo"], row["path"]))
        matched_keys.add((row["repo"], row["path"]))

    # 2. Multi-token path match if single full substring had few/no hits
    if len(terms) > 1:
        conds = " AND ".join("lower(path) LIKE lower(?) ESCAPE '\\'" for _ in terms)
        sql_tok_path = f"SELECT DISTINCT repo, path FROM ctx_commit_files WHERE ({conds})"
        p_tok: list[Any] = [
            "%" + t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            for t in terms
        ]
        if repo:
            sql_tok_path += " AND repo = ?"
            p_tok.append(repo)
        for row in conn.execute(sql_tok_path, p_tok):
            path_keys.add((row["repo"], row["path"]))
            matched_keys.add((row["repo"], row["path"]))

    # 3. Direct SHA prefix/full match
    if re.fullmatch(r"[0-9a-f]{7,64}", raw_query.lower()):
        sql_sha = "SELECT DISTINCT repo, path FROM ctx_commit_files WHERE lower(commit_sha) LIKE ?"
        p_sha: list[Any] = [raw_query.lower() + "%"]
        if repo:
            sql_sha += " AND repo = ?"
            p_sha.append(repo)
        for row in conn.execute(sql_sha, p_sha):
            path_keys.add((row["repo"], row["path"]))
            matched_keys.add((row["repo"], row["path"]))

    # 4. Patch / commit / PR / comment text matches
    fts_tokens = re.findall(r"\w+", raw_query, flags=re.UNICODE)[:6]
    if fts_tokens:
        matcher = " AND ".join(f'"{t}"*' for t in fts_tokens)
        sql_fts = (
            "SELECT repo, record_kind, record_id, path, commit_sha, pr_number, content "
            "FROM ctx_text_fts WHERE ctx_text_fts MATCH ?"
        )
        p_fts: list[Any] = [matcher]
        if repo:
            sql_fts += " AND repo = ?"
            p_fts.append(repo)
        sql_fts += " LIMIT 200"
        try:
            fts_rows = conn.execute(sql_fts, p_fts).fetchall()
        except sqlite3.OperationalError:
            fts_rows = []
        for frow in fts_rows:
            r_repo = frow["repo"]
            fpath = frow["path"]
            csha = frow["commit_sha"]
            pr_num_str = frow["pr_number"]
            if fpath:
                fts_keys.add((r_repo, fpath))
                matched_keys.add((r_repo, fpath))
                if csha:
                    matched_snippets_by_commit.setdefault((r_repo, fpath, csha), []).append(frow["content"])
            elif pr_num_str:
                for cf in conn.execute(
                    "SELECT DISTINCT path, commit_sha FROM ctx_commit_files WHERE repo=? AND pr_number=?",
                    (r_repo, int(pr_num_str)),
                ):
                    fts_keys.add((r_repo, cf["path"]))
                    matched_keys.add((r_repo, cf["path"]))
                    matched_snippets_by_commit.setdefault((r_repo, cf["path"], cf["commit_sha"]), []).append(
                        frow["content"]
                    )
            elif csha:
                for cf in conn.execute(
                    "SELECT DISTINCT path FROM ctx_commit_files WHERE repo=? AND commit_sha=?",
                    (r_repo, csha),
                ):
                    fts_keys.add((r_repo, cf["path"]))
                    matched_keys.add((r_repo, cf["path"]))
                    matched_snippets_by_commit.setdefault((r_repo, cf["path"], csha), []).append(
                        frow["content"]
                    )

    # Also match image paths in ctx_images when not in ctx_commit_files
    sql_img_only = "SELECT DISTINCT repo, path FROM ctx_images WHERE lower(path) LIKE lower(?) ESCAPE '\\'"
    p_img: list[Any] = [like_pat]
    if repo:
        sql_img_only += " AND repo = ?"
        p_img.append(repo)
    for row in conn.execute(sql_img_only, p_img):
        path_keys.add((row["repo"], row["path"]))
        matched_keys.add((row["repo"], row["path"]))

    # Order matched files deterministically: exact path > partial path > text/FTS match
    def _file_sort_key(k: tuple[str, str]) -> tuple[int, int, str, str]:
        if k in exact_keys:
            tier = 0
        elif k in path_keys:
            tier = 1
        else:
            tier = 2
        basename_hit = 0 if raw_query.lower() in Path(k[1]).name.lower() else 1
        return (tier, basename_hit, k[0], k[1])

    sorted_keys = sorted(matched_keys, key=_file_sort_key)[:limit]

    file_groups: list[dict[str, Any]] = []
    relevant_prs: set[tuple[str, int]] = set()

    for r_repo, fpath in sorted_keys:
        cf_rows = conn.execute(
            "SELECT cf.*, c.date AS c_date, c.ref AS c_ref, c.author AS c_author, "
            "c.subject AS c_subject, c.body AS c_body "
            "FROM ctx_commit_files cf "
            "LEFT JOIN ctx_commits c ON c.repo = cf.repo AND c.commit_sha = cf.commit_sha "
            "WHERE cf.repo = ? AND cf.path = ?",
            (r_repo, fpath),
        ).fetchall()

        # Deduplicate by commit_sha while keeping deterministic chronological timeline
        commits_by_sha: dict[str, dict[str, Any]] = {}
        for row in cf_rows:
            sha = row["commit_sha"]
            eff_date = row["date"] or row["c_date"] or ""
            eff_ref = row["ref"] or row["c_ref"] or ""
            pr_num = row["pr_number"]
            if pr_num is not None:
                relevant_prs.add((r_repo, int(pr_num)))

            # Gather linked PR/issue items via pr_number or ctx_links
            linked_item_nums: set[int] = set()
            if pr_num is not None:
                linked_item_nums.add(int(pr_num))
            for lrow in conn.execute(
                "SELECT pr_number, issue_number FROM ctx_links "
                "WHERE repo=? AND (commit_sha=? OR path=?)",
                (r_repo, sha, fpath),
            ):
                if lrow["pr_number"] is not None:
                    linked_item_nums.add(int(lrow["pr_number"]))
                if lrow["issue_number"] is not None:
                    linked_item_nums.add(int(lrow["issue_number"]))

            pr_items: list[dict[str, Any]] = []
            for inum in sorted(linked_item_nums):
                relevant_prs.add((r_repo, inum))
                for it in conn.execute(
                    "SELECT kind, number, title, body, state, author, html_url, created_at, merged_at "
                    "FROM ctx_items WHERE repo=? AND number=?",
                    (r_repo, inum),
                ):
                    pr_items.append(dict(it))

            # Gather comments linked to this commit, (this file path), or linked PR/issue
            # Note: inline review comments on OTHER files in the same PR should not pollute this file's citations.
            comment_rows: list[sqlite3.Row] = []
            if linked_item_nums:
                placeholders = ",".join("?" for _ in linked_item_nums)
                comment_rows = conn.execute(
                    f"SELECT * FROM ctx_comments WHERE repo=? AND ("
                    f"(path=? AND (commit_sha=? OR item_number IN ({placeholders}))) "
                    f"OR (path='' AND (commit_sha=? OR item_number IN ({placeholders})))"
                    f") ORDER BY created_at ASC, id ASC",
                    (r_repo, fpath, sha, *sorted(linked_item_nums), sha, *sorted(linked_item_nums)),
                ).fetchall()
            else:
                comment_rows = conn.execute(
                    "SELECT * FROM ctx_comments WHERE repo=? AND ("
                    "(path=? AND commit_sha=?) OR (path='' AND commit_sha=?) OR path=?"
                    ") ORDER BY created_at ASC, id ASC",
                    (r_repo, fpath, sha, sha, fpath),
                ).fetchall()

            comments = [dict(c) for c in comment_rows]

            # Gather associated screenshots/images (on this commit, path, or linked PRs)
            img_rows: list[sqlite3.Row]
            if linked_item_nums:
                placeholders = ",".join("?" for _ in linked_item_nums)
                img_rows = conn.execute(
                    f"SELECT DISTINCT path, commit_sha, ref, blob_sha, pr_number, issue_number, media_type, origin_url, origin_file "
                    f"FROM ctx_images WHERE repo=? AND (path=? OR commit_sha=? OR pr_number IN ({placeholders}) OR issue_number IN ({placeholders})) "
                    f"ORDER BY path ASC",
                    (r_repo, fpath, sha, *sorted(linked_item_nums), *sorted(linked_item_nums)),
                ).fetchall()
            else:
                img_rows = conn.execute(
                    "SELECT DISTINCT path, commit_sha, ref, blob_sha, pr_number, issue_number, media_type, origin_url, origin_file "
                    "FROM ctx_images WHERE repo=? AND (path=? OR commit_sha=?) ORDER BY path ASC",
                    (r_repo, fpath, sha),
                ).fetchall()

            images = [dict(im) for im in img_rows]

            commit_subject = row["c_subject"] or ""
            commit_body = row["c_body"] or ""
            has_citation, citations = _extract_cited_justifications(
                commit_subject=commit_subject,
                commit_body=commit_body,
                pr_items=pr_items,
                comments=comments,
            )

            # Build snippet highlighting the search term
            snippet_sources = []
            if row["patch"]:
                snippet_sources.append(row["patch"])
            if commit_subject or commit_body:
                snippet_sources.append(f"{commit_subject} {commit_body}".strip())
            snippet_sources.extend(matched_snippets_by_commit.get((r_repo, fpath, sha), []))
            for it in pr_items:
                snippet_sources.append(f"{it['title']} {it['body']}".strip())
            for c in comments:
                if c.get("body"):
                    snippet_sources.append(c["body"])
            snippet_sources.append(fpath)

            chosen_text = ""
            for cand in snippet_sources:
                if any(t.lower() in cand.lower() for t in highlight_terms):
                    chosen_text = cand
                    break
            if not chosen_text:
                chosen_text = next((s for s in snippet_sources if s), fpath)
            snippet_text = _highlight_snippet(chosen_text, highlight_terms)

            objective_links = []
            for it in pr_items:
                objective_links.append(
                    {
                        "repo": r_repo,
                        "kind": it["kind"],
                        "number": it["number"],
                        "commit_sha": sha,
                        "ref": eff_ref,
                        "path": fpath,
                        "origin_url": it["html_url"],
                    }
                )
            for im in images:
                objective_links.append(
                    {
                        "repo": r_repo,
                        "kind": "image",
                        "pr_number": im["pr_number"],
                        "issue_number": im["issue_number"],
                        "commit_sha": im["commit_sha"] or sha,
                        "ref": im["ref"] or eff_ref,
                        "path": fpath,
                        "image_path": im["path"],
                        "origin_url": im["origin_url"],
                    }
                )

            entry = {
                "commit_sha": sha,
                "date": eff_date,
                "ref": eff_ref,
                "status": row["status"],
                "author": row["c_author"] or "",
                "subject": commit_subject,
                "pr_number": pr_num,
                "blob_sha": row["blob_sha"],
                "blob_url": row["blob_url"],
                "additions": row["additions"],
                "deletions": row["deletions"],
                "snippet": snippet_text,
                "objective_links": objective_links,
                "associated_images": images,
                "justification_status": "cited" if has_citation else NO_CITATION_TEXT,
                "cited_justifications": citations,
                "has_cited_justification": has_citation,
                "origin_file": row["origin_file"],
            }
            if sha not in commits_by_sha:
                commits_by_sha[sha] = entry

        # Fallback if matched only in ctx_images with zero ctx_commit_files rows
        if not commits_by_sha:
            for im in conn.execute(
                "SELECT * FROM ctx_images WHERE repo=? AND path=? ORDER BY commit_sha ASC",
                (r_repo, fpath),
            ):
                sha = im["commit_sha"]
                commits_by_sha[sha or im["image_uid"]] = {
                    "commit_sha": sha,
                    "date": "",
                    "ref": im["ref"],
                    "status": im["media_type"],
                    "author": "",
                    "subject": "",
                    "pr_number": im["pr_number"],
                    "blob_sha": im["blob_sha"],
                    "blob_url": im["origin_url"],
                    "additions": 0,
                    "deletions": 0,
                    "snippet": _highlight_snippet(fpath, highlight_terms),
                    "objective_links": [
                        {
                            "repo": r_repo,
                            "kind": "image",
                            "pr_number": im["pr_number"],
                            "issue_number": im["issue_number"],
                            "commit_sha": sha,
                            "ref": im["ref"],
                            "path": fpath,
                            "image_path": im["path"],
                            "origin_url": im["origin_url"],
                        }
                    ],
                    "associated_images": [dict(im)],
                    "justification_status": NO_CITATION_TEXT,
                    "cited_justifications": [],
                    "has_cited_justification": False,
                    "origin_file": im["origin_file"],
                }

        timeline = sorted(
            commits_by_sha.values(),
            key=lambda c: _parse_iso_sort_key(c["date"], c["commit_sha"]),
        )
        n_commits = len(timeline)
        file_groups.append(
            {
                "repository": r_repo,
                "path": fpath,
                "commit_count": n_commits,
                "summary": f"este arquivo mudou em {n_commits} commits, do primeiro ao ultimo",
                "first_commit_sha": timeline[0]["commit_sha"] if timeline else "",
                "last_commit_sha": timeline[-1]["commit_sha"] if timeline else "",
                "commits": timeline,
            }
        )

    # Include recorded gaps relevant to the matched repositories/PRs
    gaps_out: list[dict[str, Any]] = []
    seen_gaps: set[str] = set()
    for r_repo, pr_num in sorted(relevant_prs):
        for g in conn.execute(
            "SELECT * FROM ctx_gaps WHERE repo=? AND (pr_number=? OR pr_number IS NULL)",
            (r_repo, pr_num),
        ):
            if g["gap_uid"] not in seen_gaps:
                seen_gaps.add(g["gap_uid"])
                gaps_out.append(dict(g))
    if not gaps_out and repo:
        for g in conn.execute("SELECT * FROM ctx_gaps WHERE repo=? LIMIT 20", (repo,)):
            if g["gap_uid"] not in seen_gaps:
                seen_gaps.add(g["gap_uid"])
                gaps_out.append(dict(g))

    return {
        "query": raw_query,
        "total_files": len(file_groups),
        "files": file_groups,
        "gaps": gaps_out,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=DEFAULT_DB_PATH)
    sub = ap.add_subparsers(dest="command", required=True)

    p_imp = sub.add_parser("import-inventory", help="Import preserved metadata from inventory/")
    p_imp.add_argument("--inventory-dir", default=str(DEFAULT_INVENTORY_DIR))
    p_imp.add_argument("--repo", default=None)

    p_git = sub.add_parser("ingest-git", help="Ingest commits/files/images from bare repo or bundle")
    p_git.add_argument("--source", required=True)
    p_git.add_argument("--repo", required=True)

    p_q = sub.add_parser("query", help="Query grouped chronological history for a path or keyword")
    p_q.add_argument("path_or_keyword")
    p_q.add_argument("--repo", default=None)
    p_q.add_argument("--limit", type=int, default=20)

    sub.add_parser("stats", help="Show context linker database statistics")

    args = ap.parse_args()
    conn = open_db(Path(args.db))
    try:
        if args.command == "import-inventory":
            out = import_inventory(Path(args.inventory_dir), conn, repo_override=args.repo)
        elif args.command == "ingest-git":
            out = ingest_git_repo(Path(args.source), args.repo, conn)
        elif args.command == "query":
            out = query_history(conn, args.path_or_keyword, repo=args.repo, limit=args.limit)
        else:
            out = {
                "sources": conn.execute("SELECT COUNT(*) FROM ctx_sources").fetchone()[0],
                "items": conn.execute("SELECT COUNT(*) FROM ctx_items").fetchone()[0],
                "commits": conn.execute("SELECT COUNT(*) FROM ctx_commits").fetchone()[0],
                "commit_files": conn.execute("SELECT COUNT(*) FROM ctx_commit_files").fetchone()[0],
                "comments": conn.execute("SELECT COUNT(*) FROM ctx_comments").fetchone()[0],
                "events": conn.execute("SELECT COUNT(*) FROM ctx_events").fetchone()[0],
                "images": conn.execute("SELECT COUNT(*) FROM ctx_images").fetchone()[0],
                "links": conn.execute("SELECT COUNT(*) FROM ctx_links").fetchone()[0],
                "releases": conn.execute("SELECT COUNT(*) FROM ctx_releases").fetchone()[0],
                "workflow_runs": conn.execute("SELECT COUNT(*) FROM ctx_workflow_runs").fetchone()[0],
                "gaps": conn.execute("SELECT COUNT(*) FROM ctx_gaps").fetchone()[0],
            }
    finally:
        conn.close()
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
