#!/usr/bin/env python3
"""Deterministic offline document extractor for historical archives.

Extracts structured hierarchy (h1/h2/h3+ sections), tables, diagram/image links,
page/position provenance, and SHA-256 integrity hashes from:
  - Markdown (.md, .mdx, .markdown)
  - Plain text / reStructuredText (.txt, .rst)
  - Structured JSON / JSONC specifications (.json, .jsonc)
  - Native PDFs (.pdf) using Python stdlib only (zlib stream decompression)

Design guarantees:
  - Standard library only; zero network calls, zero LLM/API calls, zero paid inference.
  - Explicit skip/error records for missing, secret-blocked, encrypted, or
    unreadable files, and explicit `image_only_needs_ocr` flags for scanned PDF pages.
  - Never claims image or diagram comprehension from metadata indexing alone
    (`understood: False` on every extracted visual reference).
  - Separates deterministic parsing from optional offline heavy PDF/OCR tools
    (Docling, OpenDataLoader PDF, Xberg, Tesseract), which are never required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import tracemalloc
import zlib
from pathlib import Path
from typing import Any

EXTRACTOR_VERSION = "1.0.0"
DEFAULT_MAX_DOC_BYTES = 8 * 1024 * 1024
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

MARKDOWN_EXTS = frozenset({".md", ".mdx", ".markdown"})
TEXT_EXTS = frozenset({".txt", ".rst"})
JSON_EXTS = frozenset({".json", ".jsonc"})
PDF_EXTS = frozenset({".pdf"})
SUPPORTED_DOC_EXTS = MARKDOWN_EXTS | TEXT_EXTS | JSON_EXTS | PDF_EXTS

IMAGE_LINK_EXTS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".drawio", ".excalidraw"})

SECRET_EXTENSIONS = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".kdbx",
    ".crt", ".cer", ".der", ".ppk", ".ovpn", ".age", ".gpg", ".asc",
    ".secret", ".secrets", ".env",
})
SECRET_FILENAMES = frozenset({
    ".env", ".npmrc", ".pypirc", ".netrc", ".dockercfg", ".htpasswd",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "credentials", "credentials.json", "service-account.json",
    "serviceaccountkey.json", "google-services.json",
    "secrets.json", "secrets.yaml", "secrets.yml", "secrets.toml", "master.key",
})
SECRET_DIR_PARTS = frozenset({"secrets", ".ssh", ".aws", ".gnupg"})
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
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)

_ATX_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
_MD_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
_HTML_IMG_RE = re.compile(
    r"<img\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)[\"'][^>]*>",
    re.IGNORECASE,
)
_HTML_ALT_RE = re.compile(r"\balt\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE)
_IMAGE_PATH_RE = re.compile(
    r"(?:https://github\.com/user-attachments/assets/[A-Za-z0-9_-]+|"
    r"[A-Za-z0-9_./-]+\.(?:png|jpg|jpeg|gif|webp|svg|drawio|excalidraw))\b",
    re.IGNORECASE,
)
_NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+){0,4})[.)]?\s+([A-ZÀ-Ü0-9][^\n]{1,100})$")

DB_SCHEMA = """
PRAGMA journal_mode=DELETE;
CREATE TABLE IF NOT EXISTS doc_sources (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    ref TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    path TEXT NOT NULL,
    document_type TEXT NOT NULL,
    doc_sha256 TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    status TEXT NOT NULL,
    skip_reason TEXT NOT NULL DEFAULT '',
    page_count INTEGER NOT NULL DEFAULT 0,
    section_count INTEGER NOT NULL DEFAULT 0,
    table_count INTEGER NOT NULL DEFAULT 0,
    diagram_link_count INTEGER NOT NULL DEFAULT 0,
    uninterpreted_pages_json TEXT NOT NULL DEFAULT '[]',
    extractor_version TEXT NOT NULL,
    UNIQUE(repo, ref, commit_sha, path, doc_sha256)
);
CREATE TABLE IF NOT EXISTS doc_elements (
    id INTEGER PRIMARY KEY,
    repo TEXT NOT NULL,
    ref TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    path TEXT NOT NULL,
    pdf_page INTEGER NOT NULL,
    element_id TEXT NOT NULL,
    element_type TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 0,
    section_path TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    bounding_box_json TEXT NOT NULL DEFAULT 'null',
    doc_sha256 TEXT NOT NULL,
    element_sha256 TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    UNIQUE(repo, ref, commit_sha, path, doc_sha256, element_id)
);
CREATE VIRTUAL TABLE IF NOT EXISTS doc_elements_fts USING fts5(
    title,
    section_path,
    content,
    repo UNINDEXED,
    ref UNINDEXED,
    commit_sha UNINDEXED,
    path UNINDEXED,
    pdf_page UNINDEXED,
    element_id UNINDEXED,
    element_type UNINDEXED,
    tokenize='unicode61'
);
"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return (len(text) + 3) // 4


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
        raise ValueError(f"unsafe path: {path!r}")
    return path


def safe_ref(value: str) -> str:
    if not value:
        return ""
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise ValueError("commit SHA must be full-length hexadecimal")
    return value


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


def contains_secret_content(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def detect_document_type(path: str, raw: bytes | None = None) -> str:
    ext = Path(path).suffix.lower()
    if ext in MARKDOWN_EXTS:
        return "markdown"
    if ext in TEXT_EXTS:
        return "text"
    if ext in JSON_EXTS:
        return "json_spec"
    if ext in PDF_EXTS or (raw is not None and raw[:1024].lstrip().startswith(b"%PDF-")):
        return "pdf"
    return "unknown"


def _provenance_uri(
    *,
    repo: str,
    ref: str,
    commit_sha: str,
    path: str,
    page: int,
    element_id: str,
) -> str:
    ref_part = ref or "-"
    sha_part = commit_sha or "-"
    return f"{repo}/{ref_part}/{sha_part}/{path}#page={page}&element={element_id}"


def _make_provenance_record(
    *,
    repo: str,
    ref: str,
    commit_sha: str,
    path: str,
    page: int,
    element_id: str,
    bounding_box: list[float] | None,
    doc_sha256: str,
) -> dict[str, Any]:
    return {
        "repo": repo,
        "ref": ref,
        "commit_sha": commit_sha,
        "path": path,
        "pdf_page": page,
        "element_id": element_id,
        "bounding_box": bounding_box,
        "extractor_version": EXTRACTOR_VERSION,
        "doc_sha256": doc_sha256,
        "citation_key": _provenance_uri(
            repo=repo,
            ref=ref,
            commit_sha=commit_sha,
            path=path,
            page=page,
            element_id=element_id,
        ),
    }


def _skipped_result(
    *,
    repo: str,
    ref: str,
    commit_sha: str,
    path: str,
    document_type: str,
    raw_bytes: bytes | None,
    skip_reason: str,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    doc_hash = sha256_bytes(raw_bytes) if raw_bytes is not None else ""
    byte_len = len(raw_bytes) if raw_bytes is not None else 0
    return {
        "extractor_version": EXTRACTOR_VERSION,
        "status": "skipped",
        "skip_reason": skip_reason,
        "provenance": {
            "repo": repo,
            "ref": ref,
            "commit_sha": commit_sha,
            "path": path,
            "document_type": document_type,
            "sha256": doc_hash,
            "bytes": byte_len,
            "extractor_version": EXTRACTOR_VERSION,
        },
        "metadata": {
            "title": "",
            "page_count": 0,
            "section_count": 0,
            "table_count": 0,
            "diagram_link_count": 0,
            "heading_levels": [],
        },
        "sections": [],
        "tables": [],
        "diagram_links": [],
        "pages": [],
        "chunks": [],
        "uninterpreted_pages": [],
        "warnings": [],
        "errors": errors or [skip_reason],
    }


def _split_md_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for ch in stripped:
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    cells.append("".join(current).strip())
    return cells


def _is_md_table_separator(line: str, expected_cols: int | None = None) -> bool:
    stripped = line.strip()
    if "|" not in stripped:
        return False
    cells = _split_md_table_row(stripped)
    if not cells:
        return False
    if expected_cols is not None and len(cells) != expected_cols:
        return False
    for cell in cells:
        if not re.fullmatch(r":?-{3,}:?", cell.strip()):
            return False
    return True


def _extract_links_from_text_lines(
    lines: list[str],
    *,
    line_offset: int = 1,
    page: int = 1,
    section_id: str | None = None,
    section_path: str = "",
) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()
    in_fence = False
    fence_char = ""
    fence_len = 0
    fence_lang = ""
    fence_start_line = 0

    for idx, line in enumerate(lines):
        lineno = line_offset + idx
        m_fence = _FENCE_RE.match(line)
        if m_fence:
            marker = m_fence.group(1)
            info = m_fence.group(2).strip().lower()
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
                fence_lang = info.split()[0] if info else ""
                fence_start_line = lineno
                if fence_lang in {"mermaid", "plantuml", "graphviz", "dot", "d2"}:
                    key = (lineno, "diagram_block", fence_lang)
                    if key not in seen:
                        seen.add(key)
                        links.append({
                            "kind": f"{fence_lang}_block" if fence_lang == "mermaid" else "diagram_block",
                            "target": f"inline:{fence_lang}:line-{lineno}",
                            "alt_text": fence_lang,
                            "page": page,
                            "line": lineno,
                            "section_id": section_id,
                            "section_path": section_path,
                            "understood": False,
                        })
                continue
            elif marker[0] == fence_char and len(marker) >= fence_len and not info:
                in_fence = False
                fence_lang = ""
                continue

        if in_fence:
            continue

        for m in _MD_IMAGE_RE.finditer(line):
            alt_text, target = m.group(1).strip(), m.group(2).strip()
            key = (lineno, "markdown_image", target)
            if key not in seen:
                seen.add(key)
                links.append({
                    "kind": "markdown_image",
                    "target": target,
                    "alt_text": alt_text,
                    "page": page,
                    "line": lineno,
                    "section_id": section_id,
                    "section_path": section_path,
                    "understood": False,
                })

        for m in _MD_LINK_RE.finditer(line):
            label, target = m.group(1).strip(), m.group(2).strip()
            target_no_frag = target.split("#", 1)[0].split("?", 1)[0].lower()
            if Path(target_no_frag).suffix in IMAGE_LINK_EXTS or "diagram" in target_no_frag or "screenshot" in target_no_frag:
                key = (lineno, "markdown_link", target)
                if key not in seen:
                    seen.add(key)
                    links.append({
                        "kind": "markdown_link",
                        "target": target,
                        "alt_text": label,
                        "page": page,
                        "line": lineno,
                        "section_id": section_id,
                        "section_path": section_path,
                        "understood": False,
                    })

        for m in _HTML_IMG_RE.finditer(line):
            target = m.group(1).strip()
            alt_m = _HTML_ALT_RE.search(m.group(0))
            alt_text = alt_m.group(1).strip() if alt_m else ""
            key = (lineno, "html_img", target)
            if key not in seen:
                seen.add(key)
                links.append({
                    "kind": "html_img",
                    "target": target,
                    "alt_text": alt_text,
                    "page": page,
                    "line": lineno,
                    "section_id": section_id,
                    "section_path": section_path,
                    "understood": False,
                })

        for m in _IMAGE_PATH_RE.finditer(line):
            target = m.group(0).strip()
            if any(l["line"] == lineno and l["target"] == target for l in links):
                continue
            key = (lineno, "diagram_mention", target)
            if key not in seen:
                seen.add(key)
                links.append({
                    "kind": "diagram_mention",
                    "target": target,
                    "alt_text": "",
                    "page": page,
                    "line": lineno,
                    "section_id": section_id,
                    "section_path": section_path,
                    "understood": False,
                })

    return links


def _extract_tables_from_lines(
    lines: list[str],
    *,
    line_offset: int = 1,
    page: int = 1,
    section_id: str | None = None,
    section_path: str = "",
) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        m_fence = _FENCE_RE.match(line)
        if m_fence:
            marker = m_fence.group(1)
            info = m_fence.group(2).strip()
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
                i += 1
                continue
            elif marker[0] == fence_char and len(marker) >= fence_len and not info:
                in_fence = False
                i += 1
                continue

        if in_fence:
            i += 1
            continue

        if i + 1 < n and "|" in line and "|" in lines[i + 1]:
            headers = _split_md_table_row(line)
            if len(headers) >= 2 and _is_md_table_separator(lines[i + 1], expected_cols=len(headers)):
                start_idx = i
                i += 2
                rows: list[list[str]] = []
                while i < n:
                    row_line = lines[i]
                    if not row_line.strip() or "|" not in row_line:
                        break
                    if _FENCE_RE.match(row_line):
                        break
                    cells = _split_md_table_row(row_line)
                    if len(cells) < len(headers):
                        cells.extend([""] * (len(headers) - len(cells)))
                    elif len(cells) > len(headers):
                        cells = cells[: len(headers)]
                    rows.append(cells)
                    i += 1
                tables.append({
                    "section_id": section_id,
                    "section_path": section_path,
                    "page": page,
                    "start_line": line_offset + start_idx,
                    "end_line": line_offset + i - 1,
                    "bounding_box": None,
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                    "col_count": len(headers),
                })
                continue
        i += 1

    return tables


def _extract_markdown(
    text: str,
    *,
    repo: str,
    ref: str,
    commit_sha: str,
    path: str,
    doc_sha256: str,
) -> dict[str, Any]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    line_starts: list[int] = []
    char_cursor = 0
    for ln in lines:
        line_starts.append(char_cursor)
        char_cursor += len(ln) + 1

    # Detect optional YAML frontmatter
    content_start_idx = 0
    frontmatter_title = ""
    if len(lines) >= 3 and lines[0].strip() == "---":
        for j in range(1, min(len(lines), 80)):
            if lines[j].strip() == "---":
                for fm_line in lines[1:j]:
                    if fm_line.lower().startswith("title:"):
                        frontmatter_title = fm_line.split(":", 1)[1].strip().strip("\"'")
                content_start_idx = j + 1
                break

    # Pass 1: find headings respecting fenced code blocks
    headings: list[dict[str, Any]] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    current_page = 1

    i = content_start_idx
    while i < len(lines):
        line = lines[i]
        if "\f" in line:
            current_page += line.count("\f")
        m_fence = _FENCE_RE.match(line)
        if m_fence:
            marker = m_fence.group(1)
            info = m_fence.group(2).strip()
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len and not info:
                in_fence = False
            i += 1
            continue

        if not in_fence:
            m_atx = _ATX_HEADING_RE.match(line)
            if m_atx:
                headings.append({
                    "line_idx": i,
                    "level": len(m_atx.group(1)),
                    "title": m_atx.group(2).strip(),
                    "page": current_page,
                })
                i += 1
                continue
            if i + 1 < len(lines) and line.strip() and not line.lstrip().startswith(("|", ">", "-", "*", "+")):
                next_ln = lines[i + 1].strip()
                if re.fullmatch(r"={3,}", next_ln):
                    headings.append({"line_idx": i, "level": 1, "title": line.strip(), "page": current_page})
                    i += 2
                    continue
                if re.fullmatch(r"-{3,}", next_ln) and "|" not in line:
                    headings.append({"line_idx": i, "level": 2, "title": line.strip(), "page": current_page})
                    i += 2
                    continue
        i += 1

    sections: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    diagram_links: list[dict[str, Any]] = []

    if not headings:
        # Single root section
        sec_id = "sec-0001"
        body_lines = lines[content_start_idx:]
        body_text = "\n".join(body_lines).strip()
        title = frontmatter_title or Path(path).stem
        start_ln = content_start_idx + 1 if lines else 1
        end_ln = len(lines) if lines else 1
        sections.append({
            "element_id": sec_id,
            "parent_id": None,
            "level": 1,
            "title": title,
            "section_path": title,
            "page": 1,
            "position": {
                "start_line": start_ln,
                "end_line": end_ln,
                "start_char": line_starts[content_start_idx] if content_start_idx < len(line_starts) else 0,
                "end_char": char_cursor,
            },
            "bounding_box": None,
            "content": body_text,
            "content_sha256": sha256_text(body_text),
            "provenance": _make_provenance_record(
                repo=repo, ref=ref, commit_sha=commit_sha, path=path,
                page=1, element_id=sec_id, bounding_box=None, doc_sha256=doc_sha256,
            ),
        })
        tables.extend(_extract_tables_from_lines(body_lines, line_offset=start_ln, page=1, section_id=sec_id, section_path=title))
        diagram_links.extend(_extract_links_from_text_lines(body_lines, line_offset=start_ln, page=1, section_id=sec_id, section_path=title))
    else:
        # Optional preamble before first heading
        first_idx = headings[0]["line_idx"]
        if first_idx > content_start_idx:
            preamble_lines = lines[content_start_idx:first_idx]
            preamble_text = "\n".join(preamble_lines).strip()
            if preamble_text:
                sec_id = f"sec-{len(sections) + 1:04d}"
                title = frontmatter_title or "Preamble"
                start_ln = content_start_idx + 1
                end_ln = first_idx
                sections.append({
                    "element_id": sec_id,
                    "parent_id": None,
                    "level": 0,
                    "title": title,
                    "section_path": title,
                    "page": 1,
                    "position": {
                        "start_line": start_ln,
                        "end_line": end_ln,
                        "start_char": line_starts[content_start_idx],
                        "end_char": line_starts[first_idx],
                    },
                    "bounding_box": None,
                    "content": preamble_text,
                    "content_sha256": sha256_text(preamble_text),
                    "provenance": _make_provenance_record(
                        repo=repo, ref=ref, commit_sha=commit_sha, path=path,
                        page=1, element_id=sec_id, bounding_box=None, doc_sha256=doc_sha256,
                    ),
                })
                tables.extend(_extract_tables_from_lines(preamble_lines, line_offset=start_ln, page=1, section_id=sec_id, section_path=title))
                diagram_links.extend(_extract_links_from_text_lines(preamble_lines, line_offset=start_ln, page=1, section_id=sec_id, section_path=title))

        stack: list[tuple[int, str, str]] = []  # (level, element_id, title)
        for h_idx, h in enumerate(headings):
            level = h["level"]
            title = h["title"]
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent_id = stack[-1][1] if stack else None
            sec_id = f"sec-{len(sections) + 1:04d}"
            stack.append((level, sec_id, title))
            section_path = " > ".join(item[2] for item in stack)

            start_idx = h["line_idx"]
            next_idx = headings[h_idx + 1]["line_idx"] if h_idx + 1 < len(headings) else len(lines)
            sec_lines = lines[start_idx:next_idx]
            sec_text = "\n".join(sec_lines).strip()
            start_ln = start_idx + 1
            end_ln = max(start_ln, next_idx)
            start_char = line_starts[start_idx]
            end_char = line_starts[next_idx] if next_idx < len(line_starts) else char_cursor
            page = h["page"]

            sections.append({
                "element_id": sec_id,
                "parent_id": parent_id,
                "level": level,
                "title": title,
                "section_path": section_path,
                "page": page,
                "position": {
                    "start_line": start_ln,
                    "end_line": end_ln,
                    "start_char": start_char,
                    "end_char": end_char,
                },
                "bounding_box": None,
                "content": sec_text,
                "content_sha256": sha256_text(sec_text),
                "provenance": _make_provenance_record(
                    repo=repo, ref=ref, commit_sha=commit_sha, path=path,
                    page=page, element_id=sec_id, bounding_box=None, doc_sha256=doc_sha256,
                ),
            })
            tables.extend(_extract_tables_from_lines(sec_lines, line_offset=start_ln, page=page, section_id=sec_id, section_path=section_path))
            diagram_links.extend(_extract_links_from_text_lines(sec_lines, line_offset=start_ln, page=page, section_id=sec_id, section_path=section_path))

    doc_title = frontmatter_title or next((s["title"] for s in sections if s["level"] == 1), Path(path).stem)
    return _finalize_document_payload(
        document_type="markdown",
        title=doc_title,
        repo=repo,
        ref=ref,
        commit_sha=commit_sha,
        path=path,
        doc_sha256=doc_sha256,
        total_bytes=len(text.encode("utf-8")),
        page_count=current_page,
        sections=sections,
        tables=tables,
        diagram_links=diagram_links,
        pages=[
            {
                "page": p_idx,
                "text_length": len(text) if current_page == 1 else len(text) // current_page,
                "extraction_mode": "structured_text",
                "image_xobjects": 0,
                "bounding_boxes": [],
                "warnings": [],
            }
            for p_idx in range(1, current_page + 1)
        ],
        uninterpreted_pages=[],
        warnings=[],
    )


def _extract_plain_text(
    text: str,
    *,
    repo: str,
    ref: str,
    commit_sha: str,
    path: str,
    doc_sha256: str,
) -> dict[str, Any]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_pages = normalized.split("\f")
    sections: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    diagram_links: list[dict[str, Any]] = []
    pages_meta: list[dict[str, Any]] = []
    global_line_offset = 1

    for page_num, page_text in enumerate(raw_pages, start=1):
        lines = page_text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        pages_meta.append({
            "page": page_num,
            "text_length": len(page_text.strip()),
            "extraction_mode": "structured_text" if page_text.strip() else "uninterpreted",
            "image_xobjects": 0,
            "bounding_boxes": [],
            "warnings": [],
        })
        if not lines or not page_text.strip():
            global_line_offset += max(1, len(lines))
            continue

        headings: list[tuple[int, int, str]] = []  # (local_idx, level, title)
        idx = 0
        while idx < len(lines):
            ln = lines[idx].strip()
            if idx + 1 < len(lines) and ln:
                nxt = lines[idx + 1].strip()
                if len(nxt) >= 3 and len(set(nxt)) == 1 and nxt[0] in {"=", "-", "~"}:
                    lvl = 1 if nxt[0] == "=" else (2 if nxt[0] == "-" else 3)
                    headings.append((idx, lvl, ln))
                    idx += 2
                    continue
            m_num = _NUMBERED_HEADING_RE.match(ln)
            if m_num:
                lvl = min(4, m_num.group(1).count(".") + 1)
                headings.append((idx, lvl, ln))
                idx += 1
                continue
            m_atx = _ATX_HEADING_RE.match(lines[idx])
            if m_atx:
                headings.append((idx, len(m_atx.group(1)), m_atx.group(2).strip()))
            idx += 1

        if not headings:
            sec_id = f"sec-{len(sections) + 1:04d}"
            title = f"Page {page_num}" if len(raw_pages) > 1 else Path(path).stem
            sec_text = "\n".join(lines).strip()
            sections.append({
                "element_id": sec_id,
                "parent_id": None,
                "level": 1,
                "title": title,
                "section_path": title,
                "page": page_num,
                "position": {"start_line": global_line_offset, "end_line": global_line_offset + len(lines) - 1},
                "bounding_box": None,
                "content": sec_text,
                "content_sha256": sha256_text(sec_text),
                "provenance": _make_provenance_record(
                    repo=repo, ref=ref, commit_sha=commit_sha, path=path,
                    page=page_num, element_id=sec_id, bounding_box=None, doc_sha256=doc_sha256,
                ),
            })
            tables.extend(_extract_tables_from_lines(lines, line_offset=global_line_offset, page=page_num, section_id=sec_id, section_path=title))
            diagram_links.extend(_extract_links_from_text_lines(lines, line_offset=global_line_offset, page=page_num, section_id=sec_id, section_path=title))
        else:
            stack: list[tuple[int, str, str]] = []
            for h_pos, (loc_idx, lvl, title) in enumerate(headings):
                while stack and stack[-1][0] >= lvl:
                    stack.pop()
                parent_id = stack[-1][1] if stack else None
                sec_id = f"sec-{len(sections) + 1:04d}"
                stack.append((lvl, sec_id, title))
                section_path = " > ".join(item[2] for item in stack)
                next_loc = headings[h_pos + 1][0] if h_pos + 1 < len(headings) else len(lines)
                sec_lines = lines[loc_idx:next_loc]
                sec_text = "\n".join(sec_lines).strip()
                start_ln = global_line_offset + loc_idx
                end_ln = global_line_offset + max(loc_idx, next_loc - 1)
                sections.append({
                    "element_id": sec_id,
                    "parent_id": parent_id,
                    "level": lvl,
                    "title": title,
                    "section_path": section_path,
                    "page": page_num,
                    "position": {"start_line": start_ln, "end_line": end_ln},
                    "bounding_box": None,
                    "content": sec_text,
                    "content_sha256": sha256_text(sec_text),
                    "provenance": _make_provenance_record(
                        repo=repo, ref=ref, commit_sha=commit_sha, path=path,
                        page=page_num, element_id=sec_id, bounding_box=None, doc_sha256=doc_sha256,
                    ),
                })
                tables.extend(_extract_tables_from_lines(sec_lines, line_offset=start_ln, page=page_num, section_id=sec_id, section_path=section_path))
                diagram_links.extend(_extract_links_from_text_lines(sec_lines, line_offset=start_ln, page=page_num, section_id=sec_id, section_path=section_path))

        global_line_offset += len(lines)

    uninterpreted = [p["page"] for p in pages_meta if p["extraction_mode"] == "uninterpreted"]
    doc_title = next((s["title"] for s in sections if s["level"] == 1), Path(path).stem)
    return _finalize_document_payload(
        document_type="text",
        title=doc_title,
        repo=repo,
        ref=ref,
        commit_sha=commit_sha,
        path=path,
        doc_sha256=doc_sha256,
        total_bytes=len(text.encode("utf-8")),
        page_count=len(raw_pages),
        sections=sections,
        tables=tables,
        diagram_links=diagram_links,
        pages=pages_meta,
        uninterpreted_pages=uninterpreted,
        warnings=[],
    )


def _strip_jsonc_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    in_str = False
    escaped = False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            i += 2
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                if text[i] == "\n":
                    out.append("\n")
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _extract_json_spec(
    text: str,
    *,
    repo: str,
    ref: str,
    commit_sha: str,
    path: str,
    doc_sha256: str,
) -> dict[str, Any]:
    cleaned = _strip_jsonc_comments(text) if Path(path).suffix.lower() == ".jsonc" else text
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return _skipped_result(
            repo=repo,
            ref=ref,
            commit_sha=commit_sha,
            path=path,
            document_type="json_spec",
            raw_bytes=text.encode("utf-8"),
            skip_reason="invalid_json",
            errors=[f"JSONDecodeError: {exc.msg} at line {exc.lineno}"],
        )

    lines = text.splitlines()
    key_line_cache: dict[str, int] = {}
    for idx, ln in enumerate(lines, start=1):
        m = re.match(r'^\s*"([^"]+)"\s*:', ln)
        if m and m.group(1) not in key_line_cache:
            key_line_cache[m.group(1)] = idx

    sections: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    diagram_links: list[dict[str, Any]] = []

    def _scan_links(val: Any, sec_id: str | None, sec_path: str, line_hint: int) -> None:
        if isinstance(val, str):
            for m in _IMAGE_PATH_RE.finditer(val):
                diagram_links.append({
                    "kind": "json_image_ref",
                    "target": m.group(0),
                    "alt_text": sec_path,
                    "page": 1,
                    "line": line_hint,
                    "section_id": sec_id,
                    "section_path": sec_path,
                    "understood": False,
                })
        elif isinstance(val, dict):
            for k, v in val.items():
                _scan_links(v, sec_id, f"{sec_path}.{k}" if sec_path else str(k), key_line_cache.get(str(k), line_hint))
        elif isinstance(val, list):
            for item in val[:200]:
                _scan_links(item, sec_id, sec_path, line_hint)

    def _maybe_extract_table(items: list[Any], sec_id: str, sec_path: str, line_hint: int) -> None:
        if not items or not all(isinstance(it, dict) for it in items):
            return
        headers: list[str] = []
        for it in items[:200]:
            for k in it.keys():
                if k not in headers:
                    headers.append(str(k))
        if len(headers) < 2:
            return
        rows: list[list[str]] = []
        for it in items[:200]:
            row: list[str] = []
            for h in headers:
                v = it.get(h, "")
                if isinstance(v, (dict, list)):
                    row.append(json.dumps(v, ensure_ascii=False, separators=(",", ":"))[:160])
                else:
                    row.append(str(v))
            rows.append(row)
        tables.append({
            "section_id": sec_id,
            "section_path": sec_path,
            "page": 1,
            "start_line": line_hint,
            "end_line": line_hint,
            "bounding_box": None,
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "col_count": len(headers),
        })

    def _walk(node: Any, *, level: int, parent_id: str | None, path_parts: list[str], key_name: str, line_hint: int) -> None:
        sec_id = f"sec-{len(sections) + 1:04d}"
        sec_path = " > ".join(path_parts)
        summary_obj = node
        if isinstance(node, dict) and level < 3:
            # Keep concise JSON summary for parent container
            summary_obj = {
                k: (f"<object:{len(v)}>" if isinstance(v, dict) else (f"<array:{len(v)}>" if isinstance(v, list) else v))
                for k, v in list(node.items())[:40]
            }
        content_str = json.dumps(summary_obj, ensure_ascii=False, indent=2)
        if len(content_str) > 8000:
            content_str = content_str[:8000] + "\n..."
        sections.append({
            "element_id": sec_id,
            "parent_id": parent_id,
            "level": level,
            "title": key_name,
            "section_path": sec_path,
            "page": 1,
            "position": {"start_line": line_hint, "end_line": line_hint},
            "bounding_box": None,
            "content": content_str,
            "content_sha256": sha256_text(content_str),
            "provenance": _make_provenance_record(
                repo=repo, ref=ref, commit_sha=commit_sha, path=path,
                page=1, element_id=sec_id, bounding_box=None, doc_sha256=doc_sha256,
            ),
        })

        if isinstance(node, list):
            _maybe_extract_table(node, sec_id, sec_path, line_hint)
            _scan_links(node, sec_id, sec_path, line_hint)
        elif isinstance(node, dict) and level < 3:
            for k, v in node.items():
                child_line = key_line_cache.get(str(k), line_hint)
                if isinstance(v, (dict, list)):
                    _walk(v, level=level + 1, parent_id=sec_id, path_parts=path_parts + [str(k)], key_name=str(k), line_hint=child_line)
                else:
                    _scan_links(v, sec_id, f"{sec_path} > {k}", child_line)
        else:
            _scan_links(node, sec_id, sec_path, line_hint)

    doc_title = Path(path).stem
    if isinstance(data, dict):
        doc_title = str(data.get("title") or data.get("name") or doc_title)
        for k, v in data.items():
            _walk(v, level=1, parent_id=None, path_parts=[str(k)], key_name=str(k), line_hint=key_line_cache.get(str(k), 1))
    else:
        _walk(data, level=1, parent_id=None, path_parts=[doc_title], key_name=doc_title, line_hint=1)

    return _finalize_document_payload(
        document_type="json_spec",
        title=doc_title,
        repo=repo,
        ref=ref,
        commit_sha=commit_sha,
        path=path,
        doc_sha256=doc_sha256,
        total_bytes=len(text.encode("utf-8")),
        page_count=1,
        sections=sections,
        tables=tables,
        diagram_links=diagram_links,
        pages=[{
            "page": 1,
            "text_length": len(text),
            "extraction_mode": "structured_text",
            "image_xobjects": 0,
            "bounding_boxes": [],
            "warnings": [],
        }],
        uninterpreted_pages=[],
        warnings=[],
    )


# ---------------------------------------------------------------------------
# Pure-stdlib deterministic PDF parser (native text, fonts, coords, XObjects)
# ---------------------------------------------------------------------------

_PDF_OBJ_RE = re.compile(rb"(\d+)\s+(\d+)\s+obj\b(.*?)\bendobj", re.DOTALL)
_PDF_REF_RE = re.compile(rb"(\d+)\s+(\d+)\s+R\b")
_PDF_MEDIABOX_RE = re.compile(
    rb"/MediaBox\s*\[\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*\]"
)


def _decode_pdf_literal_string(raw: bytes) -> str:
    out = bytearray()
    i = 0
    n = len(raw)
    escapes = {
        ord("n"): 10,
        ord("r"): 13,
        ord("t"): 9,
        ord("b"): 8,
        ord("f"): 12,
        ord("("): ord("("),
        ord(")"): ord(")"),
        ord("\\"): ord("\\"),
    }
    while i < n:
        b = raw[i]
        if b == ord("\\") and i + 1 < n:
            nxt = raw[i + 1]
            if nxt in escapes:
                out.append(escapes[nxt])
                i += 2
                continue
            if 48 <= nxt <= 55:
                oct_digits = bytes([nxt])
                j = i + 2
                while j < min(n, i + 4) and 48 <= raw[j] <= 55:
                    oct_digits += bytes([raw[j]])
                    j += 1
                out.append(int(oct_digits, 8) & 0xFF)
                i = j
                continue
            if nxt in (10, 13):
                i += 2
                if nxt == 13 and i < n and raw[i] == 10:
                    i += 1
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(b)
        i += 1
    if out.startswith(b"\xfe\xff"):
        return out[2:].decode("utf-16-be", "replace")
    return out.decode("utf-8", "replace")


def _decode_pdf_hex_string(raw: bytes) -> str:
    cleaned = re.sub(rb"\s+", b"", raw)
    if len(cleaned) % 2 == 1:
        cleaned += b"0"
    try:
        decoded = bytes.fromhex(cleaned.decode("ascii"))
    except ValueError:
        return ""
    if decoded.startswith(b"\xfe\xff"):
        return decoded[2:].decode("utf-16-be", "replace")
    return decoded.decode("utf-8", "replace")


def _split_pdf_dict_and_stream(body: bytes) -> tuple[bytes, bytes | None]:
    m_stream = re.search(rb"\bstream\r?\n", body)
    if not m_stream:
        return body, None
    dict_part = body[: m_stream.start()]
    stream_start = m_stream.end()
    end_idx = body.rfind(b"endstream")
    if end_idx == -1 or end_idx < stream_start:
        return dict_part, None
    stream_bytes = body[stream_start:end_idx]
    if stream_bytes.endswith(b"\r\n"):
        stream_bytes = stream_bytes[:-2]
    elif stream_bytes.endswith((b"\n", b"\r")):
        stream_bytes = stream_bytes[:-1]
    return dict_part, stream_bytes


def _decompress_pdf_stream(dict_part: bytes, stream_bytes: bytes) -> tuple[bytes | None, str | None]:
    filters = re.findall(rb"/([A-Za-z0-9]+)\b", dict_part)
    has_filter = b"/Filter" in dict_part
    if not has_filter:
        return stream_bytes, None
    if b"/FlateDecode" in dict_part:
        try:
            return zlib.decompress(stream_bytes), None
        except zlib.error as exc:
            return None, f"flate_decompress_error:{exc}"
    unsupported = [f.decode("ascii", "replace") for f in filters if f not in {b"Filter", b"Length", b"FlateDecode"}]
    return None, f"unsupported_pdf_filter:{','.join(unsupported) or 'unknown'}"


def _parse_pdf_content_stream(stream_bytes: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse BT..ET text operators and Do XObject invocations from a PDF content stream."""
    text_items: list[dict[str, Any]] = []
    do_ops: list[dict[str, Any]] = []

    tokens: list[tuple[str, Any]] = []
    i = 0
    n = len(stream_bytes)
    while i < n:
        b = stream_bytes[i]
        if b in (9, 10, 12, 13, 32):
            i += 1
            continue
        if b == ord("%"):
            while i < n and stream_bytes[i] not in (10, 13):
                i += 1
            continue
        if b == ord("("):
            depth = 1
            i += 1
            start = i
            while i < n and depth > 0:
                if stream_bytes[i] == ord("\\"):
                    i += 2
                    continue
                if stream_bytes[i] == ord("("):
                    depth += 1
                elif stream_bytes[i] == ord(")"):
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            tokens.append(("str", _decode_pdf_literal_string(stream_bytes[start:i])))
            i += 1
            continue
        if b == ord("<"):
            if i + 1 < n and stream_bytes[i + 1] == ord("<"):
                i += 2
                tokens.append(("op", "<<"))
                continue
            i += 1
            start = i
            while i < n and stream_bytes[i] != ord(">"):
                i += 1
            tokens.append(("str", _decode_pdf_hex_string(stream_bytes[start:i])))
            i += 1
            continue
        if b == ord(">") and i + 1 < n and stream_bytes[i + 1] == ord(">"):
            i += 2
            tokens.append(("op", ">>"))
            continue
        if b in (ord("["), ord("]")):
            tokens.append(("op", chr(b)))
            i += 1
            continue
        if b == ord("/"):
            i += 1
            start = i
            while i < n and stream_bytes[i] not in b" \t\r\n()<>[]{}/%":
                i += 1
            tokens.append(("name", "/" + stream_bytes[start:i].decode("latin-1", "replace")))
            continue
        start = i
        while i < n and stream_bytes[i] not in b" \t\r\n()<>[]{}/%":
            i += 1
        word = stream_bytes[start:i].decode("latin-1", "replace")
        try:
            if "." in word:
                tokens.append(("num", float(word)))
            else:
                tokens.append(("num", float(int(word))))
        except ValueError:
            tokens.append(("op", word))

    # Interpret token stream
    operands: list[tuple[str, Any]] = []
    in_array = False
    array_items: list[tuple[str, Any]] = []
    font_name = "/F1"
    font_size = 11.0
    tx, ty = 72.0, 720.0
    leading = 14.0
    ctm = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]

    for kind, val in tokens:
        if kind == "op" and val == "[":
            in_array = True
            array_items = []
            continue
        if kind == "op" and val == "]":
            in_array = False
            operands.append(("array", array_items))
            continue
        if in_array:
            array_items.append((kind, val))
            continue
        if kind in ("num", "str", "name"):
            operands.append((kind, val))
            continue

        op = val
        if op == "BT":
            tx, ty = 0.0, 0.0
        elif op == "Tf" and len(operands) >= 2:
            if operands[-2][0] == "name":
                font_name = str(operands[-2][1])
            if operands[-1][0] == "num":
                font_size = abs(float(operands[-1][1])) or 11.0
        elif op == "TL" and operands and operands[-1][0] == "num":
            leading = abs(float(operands[-1][1])) or 14.0
        elif op == "Tm" and len(operands) >= 6:
            nums = [float(x[1]) for x in operands[-6:] if x[0] == "num"]
            if len(nums) == 6:
                tx, ty = nums[4], nums[5]
                if nums[3] > 0:
                    font_size = max(font_size, abs(nums[3]))
        elif op in ("Td", "TD") and len(operands) >= 2:
            if operands[-2][0] == "num" and operands[-1][0] == "num":
                dx, dy = float(operands[-2][1]), float(operands[-1][1])
                tx += dx
                ty += dy
                if op == "TD" and dy != 0:
                    leading = abs(dy)
        elif op == "T*":
            ty -= leading
        elif op == "cm" and len(operands) >= 6:
            nums = [float(x[1]) for x in operands[-6:] if x[0] == "num"]
            if len(nums) == 6:
                ctm = nums
        elif op == "Do" and operands and operands[-1][0] == "name":
            x0, y0 = ctm[4], ctm[5]
            w, h = abs(ctm[0]), abs(ctm[3])
            bbox = [round(x0, 2), round(y0, 2), round(x0 + w, 2), round(y0 + h, 2)]
            do_ops.append({"name": str(operands[-1][1]), "bounding_box": bbox})
        elif op in ("Tj", "'", '"') and operands:
            if op == "'" :
                ty -= leading
            elif op == '"' and len(operands) >= 3:
                ty -= leading
            s_val = str(operands[-1][1]) if operands[-1][0] == "str" else ""
            if s_val.strip():
                est_w = max(font_size * 0.5, len(s_val) * font_size * 0.48)
                text_items.append({
                    "text": s_val,
                    "x": round(tx, 2),
                    "y": round(ty, 2),
                    "font": font_name,
                    "font_size": round(font_size, 2),
                    "bbox": [round(tx, 2), round(ty, 2), round(tx + est_w, 2), round(ty + font_size, 2)],
                })
                tx += est_w
        elif op == "TJ" and operands and operands[-1][0] == "array":
            parts: list[str] = []
            for ak, av in operands[-1][1]:
                if ak == "str":
                    parts.append(str(av))
                elif ak == "num" and float(av) < -180:
                    parts.append(" ")
            joined = "".join(parts)
            if joined.strip():
                est_w = max(font_size * 0.5, len(joined) * font_size * 0.48)
                text_items.append({
                    "text": joined,
                    "x": round(tx, 2),
                    "y": round(ty, 2),
                    "font": font_name,
                    "font_size": round(font_size, 2),
                    "bbox": [round(tx, 2), round(ty, 2), round(tx + est_w, 2), round(ty + font_size, 2)],
                })
                tx += est_w

        operands.clear()

    return text_items, do_ops


def _extract_pdf(
    raw: bytes,
    *,
    repo: str,
    ref: str,
    commit_sha: str,
    path: str,
    doc_sha256: str,
) -> dict[str, Any]:
    header_slice = raw[:1024]
    if b"%PDF-" not in header_slice:
        return _skipped_result(
            repo=repo, ref=ref, commit_sha=commit_sha, path=path,
            document_type="pdf", raw_bytes=raw, skip_reason="invalid_pdf_header",
        )
    if re.search(rb"/Encrypt\b", raw):
        return _skipped_result(
            repo=repo, ref=ref, commit_sha=commit_sha, path=path,
            document_type="pdf", raw_bytes=raw, skip_reason="encrypted_pdf",
        )

    objects: dict[int, bytes] = {}
    for m in _PDF_OBJ_RE.finditer(raw):
        obj_num = int(m.group(1))
        objects[obj_num] = m.group(3)

    # Extract basic /Info title
    pdf_title = ""
    for obj_body in objects.values():
        m_title = re.search(rb"/Title\s*\(([^)]{1,200})\)", obj_body)
        if m_title:
            pdf_title = _decode_pdf_literal_string(m_title.group(1)).strip()
            break

    # Collect /Type /Page objects (avoid /Type /Pages)
    page_objs: list[tuple[int, bytes]] = []
    for obj_num in sorted(objects):
        body = objects[obj_num]
        dict_part, _ = _split_pdf_dict_and_stream(body)
        if re.search(rb"/Type\s*/Page(?![a-zA-Z])", dict_part):
            page_objs.append((obj_num, body))

    if not page_objs:
        # Fallback: treat stream objects containing BT..ET as single-page
        stream_objs = [
            (num, body) for num, body in sorted(objects.items())
            if _split_pdf_dict_and_stream(body)[1] is not None
        ]
        if not stream_objs:
            return _skipped_result(
                repo=repo, ref=ref, commit_sha=commit_sha, path=path,
                document_type="pdf", raw_bytes=raw, skip_reason="no_pdf_pages_or_streams",
            )
        page_objs = [(0, b"")]

    sections: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    diagram_links: list[dict[str, Any]] = []
    pages_meta: list[dict[str, Any]] = []
    uninterpreted_pages: list[int] = []
    warnings: list[str] = []

    image_xobj_nums: set[int] = set()
    for obj_num, body in objects.items():
        d_part, _ = _split_pdf_dict_and_stream(body)
        if re.search(rb"/Subtype\s*/Image\b", d_part):
            image_xobj_nums.add(obj_num)

    stack: list[tuple[int, str, str]] = []
    global_line = 1

    for page_idx, (_p_obj_num, p_body) in enumerate(page_objs, start=1):
        p_dict, _ = _split_pdf_dict_and_stream(p_body) if p_body else (b"", None)
        mediabox = [0.0, 0.0, 612.0, 792.0]
        m_mb = _PDF_MEDIABOX_RE.search(p_dict)
        if m_mb:
            mediabox = [float(m_mb.group(k)) for k in range(1, 5)]

        # Resolve /Contents references
        content_nums: list[int] = []
        if p_body:
            m_arr = re.search(rb"/Contents\s*\[([^\]]+)\]", p_dict)
            if m_arr:
                content_nums = [int(r[0]) for r in _PDF_REF_RE.findall(m_arr.group(1))]
            else:
                m_single = re.search(rb"/Contents\s+(\d+)\s+\d+\s+R\b", p_dict)
                if m_single:
                    content_nums = [int(m_single.group(1))]
        else:
            content_nums = [
                num for num, body in sorted(objects.items())
                if _split_pdf_dict_and_stream(body)[1] is not None and num not in image_xobj_nums
            ]

        # Count referenced image XObjects on page
        page_img_refs = [
            int(r[0]) for r in _PDF_REF_RE.findall(p_dict) if int(r[0]) in image_xobj_nums
        ]

        page_text_items: list[dict[str, Any]] = []
        page_do_ops: list[dict[str, Any]] = []
        page_warnings: list[str] = []

        for cnum in content_nums:
            cbody = objects.get(cnum)
            if cbody is None:
                page_warnings.append(f"missing_content_object:{cnum}")
                continue
            cdict, cstream = _split_pdf_dict_and_stream(cbody)
            if cstream is None:
                continue
            decompressed, err = _decompress_pdf_stream(cdict, cstream)
            if err:
                page_warnings.append(err)
                continue
            if decompressed:
                t_items, d_ops = _parse_pdf_content_stream(decompressed)
                page_text_items.extend(t_items)
                page_do_ops.extend(d_ops)

        # Group text items into visual lines by y coordinate
        line_groups: list[list[dict[str, Any]]] = []
        for item in sorted(page_text_items, key=lambda it: (-it["y"], it["x"])):
            if not line_groups or abs(line_groups[-1][0]["y"] - item["y"]) > 3.0:
                line_groups.append([item])
            else:
                line_groups[-1].append(item)

        visual_lines: list[dict[str, Any]] = []
        multi_col_hits = 0
        for grp in line_groups:
            grp_sorted = sorted(grp, key=lambda it: it["x"])
            # Detect multi-column gap (> 120 pt horizontal gap between items on same y)
            col_cells: list[str] = []
            buf: list[str] = []
            prev_end = None
            for it in grp_sorted:
                gap = (it["x"] - prev_end) if prev_end is not None else 0.0
                if prev_end is not None and gap > 45.0:
                    col_cells.append(" ".join(buf).strip())
                    buf = [it["text"].strip()]
                    if gap > 120.0:
                        multi_col_hits += 1
                else:
                    buf.append(it["text"].strip())
                prev_end = it["bbox"][2]
            if buf:
                col_cells.append(" ".join(buf).strip())

            line_text = " ".join(c for c in col_cells if c).strip()
            if not line_text:
                continue
            x0 = min(it["bbox"][0] for it in grp_sorted)
            y0 = min(it["bbox"][1] for it in grp_sorted)
            x1 = max(it["bbox"][2] for it in grp_sorted)
            y1 = max(it["bbox"][3] for it in grp_sorted)
            max_font = max(it["font_size"] for it in grp_sorted)
            visual_lines.append({
                "text": line_text,
                "cells": col_cells,
                "font_size": max_font,
                "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
            })

        if multi_col_hits >= 2:
            page_warnings.append("multi_column_layout_detected")

        raw_page_text = "\n".join(vl["text"] for vl in visual_lines)
        img_count = max(len(page_img_refs), len(page_do_ops))

        if len(raw_page_text.strip()) < 10 and (img_count > 0 or not visual_lines):
            mode = "image_only_needs_ocr" if img_count > 0 else "uninterpreted"
            uninterpreted_pages.append(page_idx)
            if img_count > 0:
                page_warnings.append("scanned_or_image_only_page_requires_ocr")
        else:
            mode = "native_text"

        # Record XObject diagram/image references with understood=False
        for d_idx, d_op in enumerate(page_do_ops):
            diagram_links.append({
                "kind": "pdf_image_xobject",
                "target": f"page-{page_idx}:{d_op['name']}",
                "alt_text": "",
                "page": page_idx,
                "line": global_line,
                "bounding_box": d_op["bounding_box"],
                "section_id": sections[-1]["element_id"] if sections else None,
                "section_path": sections[-1]["section_path"] if sections else "",
                "understood": False,
            })
        if not page_do_ops and page_img_refs:
            for ref_num in page_img_refs:
                diagram_links.append({
                    "kind": "pdf_image_xobject",
                    "target": f"page-{page_idx}:obj-{ref_num}",
                    "alt_text": "",
                    "page": page_idx,
                    "line": global_line,
                    "bounding_box": mediabox,
                    "section_id": sections[-1]["element_id"] if sections else None,
                    "section_path": sections[-1]["section_path"] if sections else "",
                    "understood": False,
                })

        pages_meta.append({
            "page": page_idx,
            "media_box": mediabox,
            "text_length": len(raw_page_text),
            "extraction_mode": mode,
            "image_xobjects": img_count,
            "bounding_boxes": [vl["bbox"] for vl in visual_lines[:50]],
            "warnings": page_warnings,
        })
        warnings.extend(f"page {page_idx}: {w}" for w in page_warnings)

        if not visual_lines:
            continue

        # Detect headings by font size or numbering on this page
        font_sizes = [vl["font_size"] for vl in visual_lines]
        body_font = sorted(font_sizes)[len(font_sizes) // 2] if font_sizes else 11.0
        headings_on_page: list[tuple[int, int, str]] = []
        for idx_vl, vl in enumerate(visual_lines):
            txt = vl["text"]
            fs = vl["font_size"]
            m_num = _NUMBERED_HEADING_RE.match(txt)
            if fs >= body_font + 5.5 or fs >= 17.5:
                headings_on_page.append((idx_vl, 1, txt))
            elif fs >= body_font + 2.5 or fs >= 13.5:
                headings_on_page.append((idx_vl, 2, txt))
            elif m_num and len(vl["cells"]) == 1:
                headings_on_page.append((idx_vl, min(3, m_num.group(1).count(".") + 1), txt))

        if not headings_on_page:
            sec_id = f"sec-{len(sections) + 1:04d}"
            title = f"Page {page_idx}"
            sec_path = f"{stack[-1][2]} > {title}" if stack else title
            parent_id = stack[-1][1] if stack else None
            bbox = [
                min(vl["bbox"][0] for vl in visual_lines),
                min(vl["bbox"][1] for vl in visual_lines),
                max(vl["bbox"][2] for vl in visual_lines),
                max(vl["bbox"][3] for vl in visual_lines),
            ]
            sections.append({
                "element_id": sec_id,
                "parent_id": parent_id,
                "level": 2 if parent_id else 1,
                "title": title,
                "section_path": sec_path,
                "page": page_idx,
                "position": {"start_line": global_line, "end_line": global_line + len(visual_lines) - 1},
                "bounding_box": bbox,
                "content": raw_page_text,
                "content_sha256": sha256_text(raw_page_text),
                "provenance": _make_provenance_record(
                    repo=repo, ref=ref, commit_sha=commit_sha, path=path,
                    page=page_idx, element_id=sec_id, bounding_box=bbox, doc_sha256=doc_sha256,
                ),
            })
        else:
            for h_pos, (loc_idx, lvl, title) in enumerate(headings_on_page):
                while stack and stack[-1][0] >= lvl:
                    stack.pop()
                parent_id = stack[-1][1] if stack else None
                sec_id = f"sec-{len(sections) + 1:04d}"
                stack.append((lvl, sec_id, title))
                sec_path = " > ".join(item[2] for item in stack)
                next_loc = headings_on_page[h_pos + 1][0] if h_pos + 1 < len(headings_on_page) else len(visual_lines)
                slice_vls = visual_lines[loc_idx:next_loc]
                sec_text = "\n".join(vl["text"] for vl in slice_vls)
                bbox = [
                    min(vl["bbox"][0] for vl in slice_vls),
                    min(vl["bbox"][1] for vl in slice_vls),
                    max(vl["bbox"][2] for vl in slice_vls),
                    max(vl["bbox"][3] for vl in slice_vls),
                ]
                sections.append({
                    "element_id": sec_id,
                    "parent_id": parent_id,
                    "level": lvl,
                    "title": title,
                    "section_path": sec_path,
                    "page": page_idx,
                    "position": {"start_line": global_line + loc_idx, "end_line": global_line + max(loc_idx, next_loc - 1)},
                    "bounding_box": bbox,
                    "content": sec_text,
                    "content_sha256": sha256_text(sec_text),
                    "provenance": _make_provenance_record(
                        repo=repo, ref=ref, commit_sha=commit_sha, path=path,
                        page=page_idx, element_id=sec_id, bounding_box=bbox, doc_sha256=doc_sha256,
                    ),
                })

        # Extract aligned multi-column tables from visual_lines on this page
        t_idx = 0
        while t_idx < len(visual_lines):
            if len(visual_lines[t_idx]["cells"]) >= 2:
                col_count = len(visual_lines[t_idx]["cells"])
                t_start = t_idx
                t_rows: list[list[str]] = [visual_lines[t_idx]["cells"]]
                t_idx += 1
                while t_idx < len(visual_lines) and len(visual_lines[t_idx]["cells"]) == col_count:
                    t_rows.append(visual_lines[t_idx]["cells"])
                    t_idx += 1
                if len(t_rows) >= 2:
                    t_slice = visual_lines[t_start:t_idx]
                    t_bbox = [
                        min(vl["bbox"][0] for vl in t_slice),
                        min(vl["bbox"][1] for vl in t_slice),
                        max(vl["bbox"][2] for vl in t_slice),
                        max(vl["bbox"][3] for vl in t_slice),
                    ]
                    tables.append({
                        "section_id": sections[-1]["element_id"] if sections else None,
                        "section_path": sections[-1]["section_path"] if sections else "",
                        "page": page_idx,
                        "start_line": global_line + t_start,
                        "end_line": global_line + t_idx - 1,
                        "bounding_box": t_bbox,
                        "headers": t_rows[0],
                        "rows": t_rows[1:],
                        "row_count": len(t_rows) - 1,
                        "col_count": col_count,
                    })
                continue
            t_idx += 1

        # Also catch any textual markdown/image links in native PDF text
        txt_lines = [vl["text"] for vl in visual_lines]
        tables.extend(_extract_tables_from_lines(
            txt_lines, line_offset=global_line, page=page_idx,
            section_id=sections[-1]["element_id"] if sections else None,
            section_path=sections[-1]["section_path"] if sections else "",
        ))
        diagram_links.extend(_extract_links_from_text_lines(
            txt_lines, line_offset=global_line, page=page_idx,
            section_id=sections[-1]["element_id"] if sections else None,
            section_path=sections[-1]["section_path"] if sections else "",
        ))
        global_line += len(visual_lines)

    doc_title = pdf_title or next((s["title"] for s in sections if s["level"] == 1), Path(path).stem)
    return _finalize_document_payload(
        document_type="pdf",
        title=doc_title,
        repo=repo,
        ref=ref,
        commit_sha=commit_sha,
        path=path,
        doc_sha256=doc_sha256,
        total_bytes=len(raw),
        page_count=len(page_objs),
        sections=sections,
        tables=tables,
        diagram_links=diagram_links,
        pages=pages_meta,
        uninterpreted_pages=uninterpreted_pages,
        warnings=warnings,
    )


def _finalize_document_payload(
    *,
    document_type: str,
    title: str,
    repo: str,
    ref: str,
    commit_sha: str,
    path: str,
    doc_sha256: str,
    total_bytes: int,
    page_count: int,
    sections: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    diagram_links: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    uninterpreted_pages: list[int],
    warnings: list[str],
) -> dict[str, Any]:
    # Assign deterministic element_id + provenance to tables and diagram_links
    final_tables: list[dict[str, Any]] = []
    for idx, tbl in enumerate(tables, start=1):
        eid = f"tbl-{idx:04d}"
        tbl_copy = dict(tbl)
        tbl_copy["element_id"] = eid
        tbl_copy["sha256"] = sha256_text(json.dumps({"headers": tbl["headers"], "rows": tbl["rows"]}, ensure_ascii=False))
        tbl_copy["provenance"] = _make_provenance_record(
            repo=repo, ref=ref, commit_sha=commit_sha, path=path,
            page=tbl["page"], element_id=eid, bounding_box=tbl.get("bounding_box"), doc_sha256=doc_sha256,
        )
        final_tables.append(tbl_copy)

    final_links: list[dict[str, Any]] = []
    for idx, lnk in enumerate(diagram_links, start=1):
        eid = f"fig-{idx:04d}"
        lnk_copy = dict(lnk)
        lnk_copy["element_id"] = eid
        lnk_copy["understood"] = False
        lnk_copy["provenance"] = _make_provenance_record(
            repo=repo, ref=ref, commit_sha=commit_sha, path=path,
            page=lnk["page"], element_id=eid, bounding_box=lnk.get("bounding_box"), doc_sha256=doc_sha256,
        )
        final_links.append(lnk_copy)

    chunks: list[dict[str, Any]] = []
    for idx, sec in enumerate(sections, start=1):
        chunk_text_val = sec["content"]
        chunks.append({
            "chunk_id": f"chk-{idx:04d}",
            "repo": repo,
            "ref": ref,
            "commit_sha": commit_sha,
            "path": path,
            "page": sec["page"],
            "section": sec["title"],
            "section_path": sec["section_path"],
            "element_id": sec["element_id"],
            "bounding_box": sec.get("bounding_box"),
            "extractor_version": EXTRACTOR_VERSION,
            "doc_sha256": doc_sha256,
            "chunk_sha256": sha256_text(chunk_text_val),
            "start_line": sec["position"].get("start_line", 1),
            "end_line": sec["position"].get("end_line", 1),
            "text": chunk_text_val,
            "estimated_tokens": estimate_tokens(chunk_text_val),
        })

    if uninterpreted_pages and len(uninterpreted_pages) == page_count:
        status = "partial"
    elif uninterpreted_pages:
        status = "partial"
    else:
        status = "ok"

    return {
        "extractor_version": EXTRACTOR_VERSION,
        "status": status,
        "skip_reason": None,
        "provenance": {
            "repo": repo,
            "ref": ref,
            "commit_sha": commit_sha,
            "path": path,
            "document_type": document_type,
            "sha256": doc_sha256,
            "bytes": total_bytes,
            "extractor_version": EXTRACTOR_VERSION,
        },
        "metadata": {
            "title": title,
            "page_count": page_count,
            "section_count": len(sections),
            "table_count": len(final_tables),
            "diagram_link_count": len(final_links),
            "heading_levels": sorted({s["level"] for s in sections}),
        },
        "sections": sections,
        "tables": final_tables,
        "diagram_links": final_links,
        "pages": pages,
        "chunks": chunks,
        "uninterpreted_pages": uninterpreted_pages,
        "warnings": warnings,
        "errors": [],
    }


def extract_document_bytes(
    raw: bytes,
    *,
    path: str,
    repo: str = "local",
    ref: str = "",
    commit_sha: str = "",
    max_bytes: int = DEFAULT_MAX_DOC_BYTES,
) -> dict[str, Any]:
    """Deterministically extract structured hierarchy, tables, and visual links from raw bytes."""
    safe = safe_path(path)
    if commit_sha:
        commit_sha = safe_ref(commit_sha)

    doc_type = detect_document_type(safe, raw)
    if is_secret_path(safe):
        return _skipped_result(
            repo=repo, ref=ref, commit_sha=commit_sha, path=safe,
            document_type=doc_type, raw_bytes=raw, skip_reason="secret_path_blocked",
        )
    if len(raw) > max_bytes:
        return _skipped_result(
            repo=repo, ref=ref, commit_sha=commit_sha, path=safe,
            document_type=doc_type, raw_bytes=raw, skip_reason="oversized_document",
        )
    if not raw.strip():
        return _skipped_result(
            repo=repo, ref=ref, commit_sha=commit_sha, path=safe,
            document_type=doc_type, raw_bytes=raw, skip_reason="empty_document",
        )

    doc_sha256 = sha256_bytes(raw)

    if doc_type == "pdf":
        return _extract_pdf(
            raw, repo=repo, ref=ref, commit_sha=commit_sha, path=safe, doc_sha256=doc_sha256
        )

    if b"\x00" in raw:
        return _skipped_result(
            repo=repo, ref=ref, commit_sha=commit_sha, path=safe,
            document_type=doc_type, raw_bytes=raw, skip_reason="binary_non_document",
        )

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return _skipped_result(
            repo=repo, ref=ref, commit_sha=commit_sha, path=safe,
            document_type=doc_type, raw_bytes=raw, skip_reason="unreadable_encoding",
        )

    if contains_secret_content(text):
        return _skipped_result(
            repo=repo, ref=ref, commit_sha=commit_sha, path=safe,
            document_type=doc_type, raw_bytes=raw, skip_reason="secret_content_blocked",
        )

    if doc_type == "markdown":
        return _extract_markdown(text, repo=repo, ref=ref, commit_sha=commit_sha, path=safe, doc_sha256=doc_sha256)
    if doc_type == "json_spec":
        return _extract_json_spec(text, repo=repo, ref=ref, commit_sha=commit_sha, path=safe, doc_sha256=doc_sha256)
    if doc_type == "text":
        return _extract_plain_text(text, repo=repo, ref=ref, commit_sha=commit_sha, path=safe, doc_sha256=doc_sha256)

    return _skipped_result(
        repo=repo, ref=ref, commit_sha=commit_sha, path=safe,
        document_type="unknown", raw_bytes=raw, skip_reason="unsupported_extension",
    )


def extract_document_file(
    file_path: Path,
    *,
    display_path: str | None = None,
    repo: str = "local",
    ref: str = "",
    commit_sha: str = "",
    max_bytes: int = DEFAULT_MAX_DOC_BYTES,
) -> dict[str, Any]:
    rel = display_path or file_path.as_posix().lstrip("/") or file_path.name
    if not file_path.is_file():
        return _skipped_result(
            repo=repo, ref=ref, commit_sha=commit_sha, path=rel,
            document_type=detect_document_type(rel), raw_bytes=None, skip_reason="missing_file",
        )
    raw = file_path.read_bytes()
    return extract_document_bytes(
        raw, path=rel, repo=repo, ref=ref, commit_sha=commit_sha, max_bytes=max_bytes
    )


def _git_bytes(git_dir: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", f"--git-dir={git_dir}", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()[:400]
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {err}")
    return proc.stdout


def extract_from_git(
    repo_source: Path,
    *,
    commit_sha: str,
    path: str,
    repo_name: str = "archive",
    ref: str = "",
    max_bytes: int = DEFAULT_MAX_DOC_BYTES,
) -> dict[str, Any]:
    """Recover a document blob directly from a bare Git repo or bundle without checkout."""
    sha = safe_ref(commit_sha)
    safe = safe_path(path)
    if repo_source.is_file():
        with tempfile.TemporaryDirectory(prefix="doc-extract-bundle-") as tmp:
            mirror = Path(tmp) / "repo.git"
            proc = subprocess.run(
                ["git", "clone", "--mirror", "-q", str(repo_source), str(mirror)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"Cannot clone bundle {repo_source}: {proc.stderr.decode('utf-8', 'replace')}")
            raw = _git_bytes(mirror, "show", f"{sha}:{safe}")
    else:
        raw = _git_bytes(repo_source, "show", f"{sha}:{safe}")
    return extract_document_bytes(
        raw, path=safe, repo=repo_name, ref=ref, commit_sha=sha, max_bytes=max_bytes
    )


def open_doc_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(DB_SCHEMA)
    return conn


def index_extracted_document(conn: sqlite3.Connection, doc: dict[str, Any]) -> None:
    prov = doc["provenance"]
    meta = doc["metadata"]
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO doc_sources (
                repo, ref, commit_sha, path, document_type, doc_sha256, bytes,
                status, skip_reason, page_count, section_count, table_count,
                diagram_link_count, uninterpreted_pages_json, extractor_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prov["repo"], prov["ref"], prov["commit_sha"], prov["path"],
                prov["document_type"], prov["sha256"], prov["bytes"],
                doc["status"], doc["skip_reason"] or "",
                meta["page_count"], meta["section_count"], meta["table_count"],
                meta["diagram_link_count"],
                json.dumps(doc.get("uninterpreted_pages", [])),
                doc["extractor_version"],
            ),
        )
        for sec in doc.get("sections", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO doc_elements (
                    repo, ref, commit_sha, path, pdf_page, element_id, element_type,
                    level, section_path, title, content, bounding_box_json,
                    doc_sha256, element_sha256, extractor_version
                ) VALUES (?, ?, ?, ?, ?, ?, 'section', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prov["repo"], prov["ref"], prov["commit_sha"], prov["path"],
                    sec["page"], sec["element_id"], sec["level"], sec["section_path"],
                    sec["title"], sec["content"], json.dumps(sec.get("bounding_box")),
                    prov["sha256"], sec["content_sha256"], doc["extractor_version"],
                ),
            )
            conn.execute(
                """
                INSERT INTO doc_elements_fts (
                    title, section_path, content, repo, ref, commit_sha, path,
                    pdf_page, element_id, element_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'section')
                """,
                (
                    sec["title"], sec["section_path"], sec["content"],
                    prov["repo"], prov["ref"], prov["commit_sha"], prov["path"],
                    sec["page"], sec["element_id"],
                ),
            )
        for tbl in doc.get("tables", []):
            tbl_text = " | ".join(tbl["headers"]) + "\n" + "\n".join(" | ".join(r) for r in tbl["rows"])
            conn.execute(
                """
                INSERT OR REPLACE INTO doc_elements (
                    repo, ref, commit_sha, path, pdf_page, element_id, element_type,
                    level, section_path, title, content, bounding_box_json,
                    doc_sha256, element_sha256, extractor_version
                ) VALUES (?, ?, ?, ?, ?, ?, 'table', 0, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prov["repo"], prov["ref"], prov["commit_sha"], prov["path"],
                    tbl["page"], tbl["element_id"], tbl.get("section_path", ""),
                    f"Table ({tbl['row_count']}x{tbl['col_count']})", tbl_text,
                    json.dumps(tbl.get("bounding_box")),
                    prov["sha256"], tbl["sha256"], doc["extractor_version"],
                ),
            )
            conn.execute(
                """
                INSERT INTO doc_elements_fts (
                    title, section_path, content, repo, ref, commit_sha, path,
                    pdf_page, element_id, element_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'table')
                """,
                (
                    " | ".join(tbl["headers"]), tbl.get("section_path", ""), tbl_text,
                    prov["repo"], prov["ref"], prov["commit_sha"], prov["path"],
                    tbl["page"], tbl["element_id"],
                ),
            )


def search_documents(conn: sqlite3.Connection, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)[:8]
    if not tokens:
        return []
    matcher = " AND ".join(f'"{t}"' for t in tokens)
    rows = conn.execute(
        """
        SELECT f.repo, f.ref, f.commit_sha, f.path, f.pdf_page, f.element_id,
               f.element_type, f.section_path, f.title,
               snippet(doc_elements_fts, 2, '[', ']', '...', 18) AS snippet_text,
               bm25(doc_elements_fts) AS rank,
               e.bounding_box_json, e.doc_sha256, e.extractor_version
        FROM doc_elements_fts f
        LEFT JOIN doc_elements e
          ON e.repo = f.repo AND e.ref = f.ref AND e.commit_sha = f.commit_sha
         AND e.path = f.path AND e.element_id = f.element_id
        WHERE doc_elements_fts MATCH ?
        ORDER BY rank ASC
        LIMIT ?
        """,
        (matcher, max(1, min(limit, 50))),
    ).fetchall()
    return [
        {
            "repo": r[0],
            "ref": r[1],
            "commit_sha": r[2],
            "path": r[3],
            "pdf_page": int(r[4]),
            "element_id": r[5],
            "element_type": r[6],
            "section_path": r[7],
            "title": r[8],
            "snippet": r[9],
            "rank": round(float(r[10]), 6),
            "bounding_box": json.loads(r[11]) if r[11] else None,
            "doc_sha256": r[12] or "",
            "extractor_version": r[13] or EXTRACTOR_VERSION,
        }
        for r in rows
    ]


def scan_directory(
    root_dir: Path,
    *,
    repo_name: str = "local",
    ref: str = "HEAD",
    commit_sha: str = "",
    db_path: Path | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    tracemalloc.start()
    conn = open_doc_db(db_path) if db_path is not None else None
    docs_summary: list[dict[str, Any]] = []
    totals = {
        "files_scanned": 0,
        "extracted_ok": 0,
        "partial": 0,
        "skipped": 0,
        "sections": 0,
        "tables": 0,
        "diagram_links": 0,
        "uninterpreted_pages": 0,
        "raw_bytes": 0,
    }
    try:
        for file_path in sorted(root_dir.rglob("*")):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(root_dir).as_posix()
            if file_path.suffix.lower() not in SUPPORTED_DOC_EXTS and not is_secret_path(rel):
                continue
            totals["files_scanned"] += 1
            res = extract_document_file(
                file_path, display_path=rel, repo=repo_name, ref=ref, commit_sha=commit_sha
            )
            totals["raw_bytes"] += res["provenance"]["bytes"]
            if res["status"] == "ok":
                totals["extracted_ok"] += 1
            elif res["status"] == "partial":
                totals["partial"] += 1
            else:
                totals["skipped"] += 1
            totals["sections"] += res["metadata"]["section_count"]
            totals["tables"] += res["metadata"]["table_count"]
            totals["diagram_links"] += res["metadata"]["diagram_link_count"]
            totals["uninterpreted_pages"] += len(res["uninterpreted_pages"])
            if conn is not None:
                index_extracted_document(conn, res)
            docs_summary.append({
                "path": rel,
                "document_type": res["provenance"]["document_type"],
                "status": res["status"],
                "skip_reason": res["skip_reason"],
                "bytes": res["provenance"]["bytes"],
                "sha256": res["provenance"]["sha256"],
                "sections": res["metadata"]["section_count"],
                "tables": res["metadata"]["table_count"],
                "diagram_links": res["metadata"]["diagram_link_count"],
                "uninterpreted_pages": res["uninterpreted_pages"],
            })
    finally:
        if conn is not None:
            conn.close()
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "extractor_version": EXTRACTOR_VERSION,
        "root": str(root_dir),
        "totals": totals,
        "latency_ms": round(elapsed_ms, 3),
        "peak_ram_kib": round(peak_bytes / 1024.0, 2),
        "documents": docs_summary,
    }


def detect_external_document_tools() -> dict[str, dict[str, Any]]:
    """Detect whether external heavy extractors (Docling, PageIndex, Xberg, OpenDataLoader, OCR) exist."""
    tools: dict[str, dict[str, Any]] = {}
    for cmd in ("docling", "xberg", "opendataloader", "pdftotext", "pdfinfo", "mutool", "tesseract", "java"):
        resolved = shutil.which(cmd)
        tools[cmd] = {"installed": resolved is not None, "path": resolved}
    for mod in ("docling", "pageindex", "opendataloader_pdf", "pypdf", "fitz", "pdfplumber"):
        try:
            __import__(mod)
            tools[mod] = {"installed": True}
        except ImportError:
            tools[mod] = {"installed": False}
    return tools


def build_synthetic_pdf_bytes(
    pages: list[dict[str, Any]],
    *,
    title: str = "Synthetic Historical Spec",
    encrypt: bool = False,
) -> bytes:
    """Build a valid multi-page PDF byte stream in pure Python stdlib for testing/benchmarking."""
    objects: list[bytes] = []
    # 1: Catalog, 2: Pages, 3: Info, 4: Font /F1
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    page_obj_nums: list[int] = []
    info_dict = f"<< /Title ({title}) >>".encode("latin-1")
    objects.append(b"")  # placeholder for 2: Pages
    objects.append(info_dict)
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    next_num = 5
    for page_spec in pages:
        content_num = next_num
        next_num += 1
        stream_data = page_spec["stream"].encode("latin-1")
        compressed = zlib.compress(stream_data)
        objects.append(
            f"<< /Length {len(compressed)} /Filter /FlateDecode >>\nstream\n".encode("latin-1")
            + compressed
            + b"\nendstream"
        )
        img_ref_str = ""
        if page_spec.get("has_image_xobject"):
            img_num = next_num
            next_num += 1
            fake_img = b"\x00\x01\x02\x03"
            objects.append(
                f"<< /Type /XObject /Subtype /Image /Width 100 /Height 80 /ColorSpace /DeviceGray /BitsPerComponent 8 /Length {len(fake_img)} >>\nstream\n".encode("latin-1")
                + fake_img
                + b"\nendstream"
            )
            img_ref_str = f" /XObject << /Im1 {img_num} 0 R >>"

        page_num = next_num
        next_num += 1
        page_obj_nums.append(page_num)
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 4 0 R >>{img_ref_str} >> "
            f"/Contents {content_num} 0 R >>"
        ).encode("latin-1")
        objects.append(page_dict)

    kids = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_nums)} >>".encode("latin-1")

    if encrypt:
        objects.append(b"<< /Filter /Standard /V 2 /R 3 /Length 128 >>")

    buf = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = [0]
    for idx, obj_body in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf.extend(f"{idx} 0 obj\n".encode("latin-1"))
        buf.extend(obj_body)
        buf.extend(b"\nendobj\n")

    xref_pos = len(buf)
    buf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for off in offsets[1:]:
        buf.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    encrypt_ref = f" /Encrypt {len(objects)} 0 R" if encrypt else ""
    buf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 3 0 R{encrypt_ref} >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )
    return bytes(buf)


def run_benchmark(*, docs_dir: Path | None = None) -> dict[str, Any]:
    """Run reproducible offline extraction benchmark on synthetic fixtures and optional repo docs."""
    md_fixture = (
        "# Arquitetura do Modulo de Simulados\n\n"
        "## 1. Visao Geral\n"
        "Fluxo principal documentado em ![Diagrama de Fluxo](docs/assets/exam-flow.png).\n\n"
        "| Componente | Responsabilidade | Referencia |\n"
        "|---|---|---|\n"
        "| ExamRunner | Executa sessao cronometrada | `src/domain/exam.ts` |\n"
        "| GraphCanvas | Renderiza nos e conexoes | `src/components/graph/graph-canvas.tsx` |\n\n"
        "### 1.1 Fluxo Mermaid\n"
        "```mermaid\nflowchart LR\n  A[Start] --> B[Exam]\n```\n"
    ).encode("utf-8")

    json_fixture = json.dumps({
        "name": "exams-archive-spec",
        "version": "1.0",
        "screens": [
            {"id": "home", "route": "/", "screenshot": "assets/home.png"},
            {"id": "graph", "route": "/graph", "screenshot": "assets/graph.png"},
        ],
        "limits": {"max_tokens": 4000, "offline": True},
    }, indent=2).encode("utf-8")

    txt_fixture = (
        "Relatorio de Decisao\n"
        "====================\n\n"
        "1. Contexto Inicial\n"
        "Ver captura old-10-home.png para layout legado.\n\n"
        "1.1 Critérios\n"
        "Manter operacao offline sem LLM pago.\n"
    ).encode("utf-8")

    pdf_native_plus_scan = build_synthetic_pdf_bytes([
        {
            "stream": (
                "BT /F1 18 Tf 72 720 Td (1. Historical Architecture) Tj "
                "/F1 11 Tf 0 -24 Td (Decision record for exam graph navigation.) Tj "
                "0 -24 Td (Metric) Tj 180 0 Td (Value) Tj "
                "-180 -16 Td (Latency) Tj 180 0 Td (12 ms) Tj "
                "-180 -16 Td (Offline) Tj 180 0 Td (True) Tj ET"
            ),
            "has_image_xobject": False,
        },
        {
            "stream": "q 400 0 0 300 100 200 cm /Im1 Do Q",
            "has_image_xobject": True,
        },
    ])

    pdf_encrypted = build_synthetic_pdf_bytes(
        [{"stream": "BT /F1 12 Tf 72 720 Td (Secret) Tj ET"}],
        encrypt=True,
    )

    fixtures: list[tuple[str, bytes]] = [
        ("docs/architecture.md", md_fixture),
        ("specs/screens.json", json_fixture),
        ("notes/decision.txt", txt_fixture),
        ("archive/legacy-spec.pdf", pdf_native_plus_scan),
        ("archive/locked.pdf", pdf_encrypted),
    ]

    tracemalloc.start()
    t0 = time.perf_counter()
    results = [
        extract_document_bytes(raw, path=rel, repo="benchmark-synthetic", ref="main", commit_sha="a" * 40)
        for rel, raw in fixtures
    ]
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    per_fixture = [
        {
            "path": r["provenance"]["path"],
            "document_type": r["provenance"]["document_type"],
            "status": r["status"],
            "skip_reason": r["skip_reason"],
            "bytes": r["provenance"]["bytes"],
            "sections": r["metadata"]["section_count"],
            "tables": r["metadata"]["table_count"],
            "diagram_links": r["metadata"]["diagram_link_count"],
            "uninterpreted_pages": r["uninterpreted_pages"],
            "raw_tokens": estimate_tokens(raw.decode("utf-8", "ignore")),
            "structured_outline_tokens": estimate_tokens(
                json.dumps([{"id": s["element_id"], "path": s["section_path"], "page": s["page"]} for s in r["sections"]])
            ),
        }
        for (_, raw), r in zip(fixtures, results)
    ]

    payload: dict[str, Any] = {
        "extractor_version": EXTRACTOR_VERSION,
        "external_tools": detect_external_document_tools(),
        "synthetic_benchmark": {
            "fixtures": len(fixtures),
            "latency_ms": round(elapsed_ms, 3),
            "peak_ram_kib": round(peak_bytes / 1024.0, 2),
            "results": per_fixture,
        },
    }

    if docs_dir is not None and docs_dir.is_dir():
        payload["repo_docs_scan"] = scan_directory(docs_dir, repo_name="exams-app-archive", ref="main")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_ext = sub.add_parser("extract", help="Extract structured sections/tables/links from a document")
    p_ext.add_argument("path", help="Filesystem path or repo-relative path when --repo is given")
    p_ext.add_argument("--repo", type=Path, default=None, help="Optional bare Git repo or .bundle")
    p_ext.add_argument("--sha", default="", help="Commit SHA when using --repo")
    p_ext.add_argument("--ref", default="", help="Ref name for provenance")
    p_ext.add_argument("--repo-name", default="local", help="Repository name for provenance")

    p_scan = sub.add_parser("scan", help="Scan a directory of documents and optionally index to SQLite FTS5")
    p_scan.add_argument("dir", type=Path, help="Directory to scan")
    p_scan.add_argument("--db", type=Path, default=None, help="Optional SQLite output DB path")
    p_scan.add_argument("--repo-name", default="local")
    p_scan.add_argument("--ref", default="HEAD")

    p_search = sub.add_parser("search", help="Search extracted sections and tables in SQLite FTS5")
    p_search.add_argument("--db", type=Path, required=True)
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10)

    p_bench = sub.add_parser("benchmark", help="Run reproducible offline extraction benchmark")
    p_bench.add_argument("--docs-dir", type=Path, default=None, help="Optional local docs directory to benchmark")
    p_bench.add_argument("--output", type=Path, default=None, help="Optional JSON output path")

    args = parser.parse_args()
    if args.command == "extract":
        if args.repo is not None:
            if not args.sha:
                raise SystemExit("--sha is required when --repo is specified")
            res = extract_from_git(args.repo, commit_sha=args.sha, path=args.path, repo_name=args.repo_name, ref=args.ref)
        else:
            res = extract_document_file(Path(args.path), repo=args.repo_name, ref=args.ref, commit_sha=args.sha)
    elif args.command == "scan":
        res = scan_directory(args.dir, repo_name=args.repo_name, ref=args.ref, db_path=args.db)
    elif args.command == "search":
        conn = open_doc_db(args.db)
        try:
            res = search_documents(conn, args.query, limit=args.limit)
        finally:
            conn.close()
    else:
        res = run_benchmark(docs_dir=args.docs_dir)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
