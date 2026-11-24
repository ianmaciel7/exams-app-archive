#!/usr/bin/env python3
"""Independent local secret-scanning and sanitization gate for repositories and derived artifacts.

Validates:
  - directories and plain text/code/config files (including dot-files and sensitive paths)
  - JSON exports, previews, and logs (recursive string inspection)
  - SQLite databases (all user tables and text/blob columns)
  - Git bare repositories or local .bundle files (refs, history, blob inspection)

Security invariants:
  - Never stores, prints, or logs raw secret values in reports or exceptions.
  - Emits only deterministic HMAC-less SHA-256 prefix fingerprints + masked redactions.
  - Supports strict blocking (gate exit code != 0) and synthetic false-positive allowlists
    while flagging dangerous bypass/evasion cases.
  - Standard library only; optionally delegates to local `gitleaks` when explicitly requested.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import content_index  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

SENSITIVE_EXTENSIONS = frozenset(content_index.SECRET_EXTENSIONS) | {
    ".pfx",
    ".p12",
    ".pem",
    ".key",
    ".kdbx",
    ".jks",
    ".keystore",
    ".ppk",
    ".ovpn",
    ".env",
}

SENSITIVE_FILENAMES = frozenset(content_index.SECRET_FILENAMES) | {
    "serviceaccountkey.json",
    "service-account-key.json",
    "firebase-adminsdk.json",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
    ".env",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".htpasswd",
}

SENSITIVE_DIR_PARTS = frozenset(content_index.SECRET_DIR_PARTS) | {".kube", ".docker", "private-keys"}

# Placeholder / synthetic false-positive tokens that should not trigger false alarms
# when explicitly appearing inside benign documentation or mock placeholders, EXCEPT
# when matching high-confidence structured provider prefixes (e.g. private keys, ghp_, sk_live_).
FALSE_POSITIVE_PLACEHOLDERS = (
    "example",
    "placeholder",
    "changeme",
    "dummy",
    "your_api_key_here",
    "replace_me",
    "xxxx",
    "<your-",
    "${",
)

# High-confidence secret rules (rule_id, severity, compiled regex, description)
SECRET_RULES: tuple[tuple[str, str, re.Pattern[str], str], ...] = (
    (
        "private-key-header",
        "critical",
        re.compile(
            r"-----BEGIN\s+(?:RSA\s+|OPENSSH\s+|EC\s+|DSA\s+|PGP\s+|ENCRYPTED\s+)?PRIVATE\s+KEY-----"
        ),
        "Private key PEM/OpenSSH header",
    ),
    (
        "github-token",
        "critical",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
        "GitHub classic or OAuth token",
    ),
    (
        "github-fine-grained-pat",
        "critical",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
        "GitHub fine-grained personal access token",
    ),
    (
        "stripe-secret-key",
        "critical",
        re.compile(r"\b(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{16,}\b"),
        "Stripe secret or restricted API key",
    ),
    (
        "aws-access-key-id",
        "high",
        re.compile(r"\b(?:AKIA|ASIA|AROA|AIDA)[0-9A-Z]{16}\b"),
        "AWS IAM/STS access key ID",
    ),
    (
        "aws-secret-access-key",
        "high",
        re.compile(
            r"(?i)\baws_secret_access_key\s*[:=]\s*[\"']?([A-Za-z0-9/+=]{32,})[\"']?"
        ),
        "AWS secret access key assignment",
    ),
    (
        "google-api-key",
        "high",
        re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
        "Google Cloud / Firebase API key",
    ),
    (
        "google-oauth-token",
        "high",
        re.compile(r"\bya29\.[0-9A-Za-z_-]{20,}\b"),
        "Google OAuth2 access token",
    ),
    (
        "openai-api-key",
        "high",
        re.compile(r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}\b"),
        "OpenAI / provider sk- API key",
    ),
    (
        "slack-token",
        "high",
        re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),
        "Slack API token",
    ),
    (
        "connection-url-credentials",
        "high",
        re.compile(
            r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|rediss|amqp|amqps|mssql|https?)://"
            r"[^:\s/@\"'<>]+:[^@\s\"'<>]{4,}@[^\s/\"'<>]+"
        ),
        "URL containing embedded username and password",
    ),
    (
        "bearer-token",
        "medium",
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{24,}\b"),
        "HTTP Authorization Bearer token",
    ),
    (
        "jwt-token",
        "medium",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "JSON Web Token (JWT)",
    ),
    (
        "generic-secret-assignment",
        "medium",
        re.compile(
            r"(?i)\b(?:api_key|apikey|secret_key|private_key|access_token|auth_token|"
            r"client_secret|db_password|database_password|webhook_secret|signing_secret)"
            r"\s*[:=]\s*[\"']?([A-Za-z0-9/+=._:-]{16,})[\"']?"
        ),
        "Generic hardcoded secret assignment",
    ),
)

# Heuristic patterns indicating escaped/obfuscated secret construction or sensitive JSON structures
BYPASS_PATTERNS: tuple[tuple[str, str, re.Pattern[str], str], ...] = (
    (
        "service-account-json-payload",
        "critical",
        re.compile(r'"type"\s*:\s*"service_account"'),
        "GCP/Firebase service account JSON structure",
    ),
    (
        "inline-private-key-json-field",
        "critical",
        re.compile(r'"private_key"\s*:\s*"[^"]{12,}"'),
        "JSON private_key field",
    ),
)

SQLITE_MAGIC = b"SQLite format 3\x00"


@dataclass(frozen=True)
class GateFinding:
    """Audit finding that never holds raw secret material."""

    rule_id: str
    severity: str
    artifact_type: str
    location: str
    line: int | None
    fingerprint: str
    redacted_preview: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "artifact_type": self.artifact_type,
            "location": self.location,
            "line": self.line,
            "fingerprint": self.fingerprint,
            "redacted_preview": self.redacted_preview,
            "reason": self.reason,
        }


@dataclass
class GateAllowlist:
    """Justified allowlist for audited synthetic false positives (fingerprints or path globs)."""

    fingerprints: set[str] = field(default_factory=set)
    path_prefixes: tuple[str, ...] = ()
    rule_ids: set[str] = field(default_factory=set)

    def allows(self, finding: GateFinding) -> bool:
        if finding.fingerprint in self.fingerprints:
            return True
        if finding.rule_id in self.rule_ids:
            return True
        norm_loc = finding.location.replace("\\", "/")
        return any(norm_loc.startswith(prefix) for prefix in self.path_prefixes)


def fingerprint_secret(raw_value: str) -> str:
    """Return a non-reversible SHA-256 prefix fingerprint for audit trails."""
    digest = hashlib.sha256(raw_value.encode("utf-8", errors="replace")).hexdigest()
    return f"sha256:{digest[:16]}"


def mask_secret(raw_value: str) -> str:
    """Return a deterministic redacted mask that never leaks the full secret."""
    if not raw_value:
        return "[REDACTED]"
    # For connection URLs, keep scheme and redact userinfo completely
    if "://" in raw_value and "@" in raw_value:
        scheme, rest = raw_value.split("://", 1)
        _, host_part = rest.split("@", 1)
        return f"{scheme}://[REDACTED]@{host_part}"
    # Keep at most 4 prefix chars only when length >= 16 and not a key header
    if raw_value.startswith("-----BEGIN"):
        return "-----BEGIN [REDACTED PRIVATE KEY]-----"
    if len(raw_value) >= 16:
        return f"{raw_value[:4]}...[REDACTED:{len(raw_value)}]"
    return f"[REDACTED:{len(raw_value)}]"


def sanitize_text(text: str) -> tuple[str, int]:
    """Redact all detected secret values in text without altering non-secret structure.

    Returns (sanitized_text, redaction_count).
    """
    if not text:
        return text, 0

    spans: list[tuple[int, int, str]] = []
    for rule_id, _, pattern, _ in SECRET_RULES:
        for match in pattern.finditer(text):
            if rule_id in {"aws-secret-access-key", "generic-secret-assignment"} and match.lastindex:
                val = match.group(1)
                if _is_placeholder_value(val):
                    continue
                start, end = match.span(1)
                spans.append((start, end, mask_secret(val)))
            else:
                val = match.group(0)
                if rule_id == "connection-url-credentials" and _is_placeholder_url(val):
                    continue
                spans.append((match.start(), match.end(), mask_secret(val)))

    if not spans:
        return text, 0

    # Merge overlapping spans deterministically (leftmost, longest first)
    spans.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    merged: list[tuple[int, int, str]] = []
    for start, end, repl in spans:
        if merged and start < merged[-1][1]:
            continue
        merged.append((start, end, repl))

    parts: list[str] = []
    cursor = 0
    for start, end, repl in merged:
        parts.append(text[cursor:start])
        parts.append(repl)
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts), len(merged)


def sanitize_json_value(value: object) -> tuple[object, int]:
    """Recursively redact secrets in decoded JSON values."""
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        total = 0
        out = []
        for item in value:
            cleaned, count = sanitize_json_value(item)
            total += count
            out.append(cleaned)
        return out, total
    if isinstance(value, dict):
        total = 0
        out_dict = {}
        for k, v in value.items():
            cleaned_k, c1 = sanitize_text(str(k)) if isinstance(k, str) else (k, 0)
            cleaned_v, c2 = sanitize_json_value(v)
            total += c1 + c2
            out_dict[cleaned_k] = cleaned_v
        return out_dict, total
    return value, 0


def _is_placeholder_value(val: str) -> bool:
    low = val.strip().lower()
    if any(low.startswith(p) or p in low for p in FALSE_POSITIVE_PLACEHOLDERS):
        return True
    # Repeated identical characters (e.g. "0000000000000000", "aaaaaaaaaaaaaaaa")
    if len(set(low)) <= 2:
        return True
    return False


def _is_placeholder_url(url: str) -> bool:
    try:
        creds = url.split("://", 1)[1].split("@", 1)[0]
        _, password = creds.split(":", 1)
    except ValueError:
        return False
    return _is_placeholder_value(password)


def is_sensitive_path(path_str: str) -> tuple[bool, str | None]:
    """Check whether a relative or filesystem path matches sensitive filenames/extensions/dirs."""
    norm = path_str.replace("\\", "/")
    p = Path(norm)
    parts_lower = [part.lower() for part in p.parts]
    name_lower = p.name.lower()

    if name_lower == ".env" or name_lower.startswith(".env."):
        # Allow .env.example / .env.sample / .env.template unless content itself has secrets
        if name_lower in {".env.example", ".env.sample", ".env.template"}:
            return False, None
        return True, f"sensitive env file: {p.name}"
    if name_lower in SENSITIVE_FILENAMES or name_lower.startswith("firebase-adminsdk"):
        return True, f"sensitive filename: {p.name}"
    if p.suffix.lower() in SENSITIVE_EXTENSIONS:
        return True, f"sensitive extension: {p.suffix.lower()}"
    if any(part in SENSITIVE_DIR_PARTS for part in parts_lower[:-1]):
        return True, "sensitive directory segment"
    return False, None


def _redact_line_context(line_text: str, raw_secret: str) -> str:
    """Mask raw_secret inside a single line and bound length for safe audit output."""
    masked, _ = sanitize_text(line_text)
    if raw_secret in masked:
        masked = masked.replace(raw_secret, mask_secret(raw_secret))
    masked = masked.strip()
    if len(masked) > 140:
        masked = masked[:137] + "..."
    return masked


def scan_text(
    text: str,
    *,
    location: str,
    artifact_type: str = "text",
    allowlist: GateAllowlist | None = None,
) -> list[GateFinding]:
    """Scan a string for secret patterns and return sanitized findings."""
    findings: list[GateFinding] = []
    if not text:
        return findings

    lines = text.splitlines()
    for line_no, line in enumerate(lines, start=1):
        for rule_id, severity, pattern, reason in SECRET_RULES:
            for match in pattern.finditer(line):
                if rule_id in {"aws-secret-access-key", "generic-secret-assignment"} and match.lastindex:
                    secret_val = match.group(1)
                    if _is_placeholder_value(secret_val):
                        continue
                else:
                    secret_val = match.group(0)
                    if rule_id == "connection-url-credentials" and _is_placeholder_url(secret_val):
                        continue

                finding = GateFinding(
                    rule_id=rule_id,
                    severity=severity,
                    artifact_type=artifact_type,
                    location=location,
                    line=line_no,
                    fingerprint=fingerprint_secret(secret_val),
                    redacted_preview=_redact_line_context(line, secret_val),
                    reason=reason,
                )
                if allowlist and allowlist.allows(finding):
                    continue
                findings.append(finding)

        for rule_id, severity, pattern, reason in BYPASS_PATTERNS:
            for match in pattern.finditer(line):
                val = match.group(0)
                if _is_placeholder_value(val):
                    continue
                finding = GateFinding(
                    rule_id=rule_id,
                    severity=severity,
                    artifact_type=artifact_type,
                    location=location,
                    line=line_no,
                    fingerprint=fingerprint_secret(val),
                    redacted_preview=_redact_line_context(line, val),
                    reason=reason,
                )
                if allowlist and allowlist.allows(finding):
                    continue
                findings.append(finding)

    # Also detect multi-line private key blocks spanning beyond a single line
    # if a newline-escaped PEM string appears in JSON/Python strings.
    if "\\n" in text and "PRIVATE KEY" in text:
        unescaped = text.replace("\\n", "\n")
        if unescaped != text:
            for line_no, line in enumerate(unescaped.splitlines(), start=1):
                for rule_id, severity, pattern, reason in SECRET_RULES[:1]:
                    for match in pattern.finditer(line):
                        val = match.group(0)
                        fp = fingerprint_secret(val)
                        if any(f.fingerprint == fp and f.location == location for f in findings):
                            continue
                        finding = GateFinding(
                            rule_id=rule_id,
                            severity=severity,
                            artifact_type=artifact_type,
                            location=location,
                            line=line_no,
                            fingerprint=fp,
                            redacted_preview=_redact_line_context(line, val),
                            reason=reason,
                        )
                        if allowlist and allowlist.allows(finding):
                            continue
                        findings.append(finding)

    return findings


def scan_json_file(
    path: Path,
    *,
    display_path: str | None = None,
    allowlist: GateAllowlist | None = None,
) -> list[GateFinding]:
    """Scan a JSON artifact recursively without ever logging raw secret values."""
    loc = display_path or str(path)
    raw = path.read_text(encoding="utf-8", errors="replace")
    findings: list[GateFinding] = []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return scan_text(raw, location=loc, artifact_type="json-raw", allowlist=allowlist)

    def walk(node: object, json_path: str) -> None:
        if isinstance(node, str):
            findings.extend(
                scan_text(
                    node,
                    location=f"{loc}#{json_path}",
                    artifact_type="json",
                    allowlist=allowlist,
                )
            )
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                walk(item, f"{json_path}[{idx}]")
        elif isinstance(node, dict):
            for k, v in node.items():
                key_str = str(k)
                if key_str.lower() in {"private_key", "client_secret", "secret_key", "access_token", "auth_token"}:
                    if isinstance(v, str) and len(v) >= 12 and not _is_placeholder_value(v):
                        fp = fingerprint_secret(v)
                        finding = GateFinding(
                            rule_id="json-sensitive-key",
                            severity="high",
                            artifact_type="json",
                            location=f"{loc}#{json_path}.{key_str}",
                            line=None,
                            fingerprint=fp,
                            redacted_preview=f'"{key_str}": "{mask_secret(v)}"',
                            reason=f"Sensitive JSON key '{key_str}' holds non-placeholder secret",
                        )
                        if not (allowlist and allowlist.allows(finding)):
                            findings.append(finding)
                walk(v, f"{json_path}.{key_str}" if json_path else key_str)

    walk(parsed, "$")
    # Deduplicate same location+fingerprint if caught by both walk and regex
    deduped: list[GateFinding] = []
    seen: set[tuple[str, str, str]] = set()
    for f in findings:
        key = (f.rule_id, f.location, f.fingerprint)
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    return deduped


def scan_sqlite_file(
    db_path: Path,
    *,
    display_path: str | None = None,
    allowlist: GateAllowlist | None = None,
    max_rows_per_table: int = 50_000,
) -> list[GateFinding]:
    """Scan all tables and text/blob values in a SQLite database artifact."""
    loc = display_path or str(db_path)
    findings: list[GateFinding] = []
    uri = f"file:{db_path.resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for table in tables:
            # Skip FTS5 shadow tables that mirror virtual tables or are binary indexes
            if any(table.endswith(suffix) for suffix in ("_data", "_idx", "_docsize", "_config")):
                continue
            safe_tbl = '"' + table.replace('"', '""') + '"'
            cur = conn.execute(f"SELECT * FROM {safe_tbl} LIMIT ?", (max_rows_per_table,))
            col_names = [desc[0] for desc in (cur.description or [])]
            for row_idx, row in enumerate(cur, start=1):
                for col_idx, val in enumerate(row):
                    if val is None:
                        continue
                    if isinstance(val, bytes):
                        try:
                            text_val = val.decode("utf-8")
                        except UnicodeDecodeError:
                            continue
                    elif isinstance(val, str):
                        text_val = val
                    else:
                        continue
                    col_name = col_names[col_idx] if col_idx < len(col_names) else f"col{col_idx}"
                    # Check if a stored path column itself points to a sensitive path
                    if col_name in {"path", "file_path", "previous_path"}:
                        sens, sens_reason = is_sensitive_path(text_val)
                        if sens and sens_reason:
                            fp = fingerprint_secret(text_val)
                            finding = GateFinding(
                                rule_id="sqlite-sensitive-path",
                                severity="high",
                                artifact_type="sqlite",
                                location=f"{loc}::{table}.{col_name}[row={row_idx}]",
                                line=None,
                                fingerprint=fp,
                                redacted_preview=f"path={Path(text_val).name}",
                                reason=f"Indexed path matches sensitive file ({sens_reason})",
                            )
                            if not (allowlist and allowlist.allows(finding)):
                                findings.append(finding)
                    findings.extend(
                        scan_text(
                            text_val,
                            location=f"{loc}::{table}.{col_name}[row={row_idx}]",
                            artifact_type="sqlite",
                            allowlist=allowlist,
                        )
                    )
    finally:
        conn.close()
    return findings


def scan_file(
    file_path: Path,
    *,
    root: Path | None = None,
    allowlist: GateAllowlist | None = None,
    max_file_bytes: int = 8 * 1024 * 1024,
) -> list[GateFinding]:
    """Scan an individual file (plain text, JSON, SQLite, logs, previews)."""
    rel = str(file_path.relative_to(root)) if root and file_path.is_relative_to(root) else str(file_path)
    findings: list[GateFinding] = []

    sens, sens_reason = is_sensitive_path(rel)
    if sens and sens_reason:
        fp = fingerprint_secret(rel)
        finding = GateFinding(
            rule_id="sensitive-file-path",
            severity="critical",
            artifact_type="file",
            location=rel,
            line=None,
            fingerprint=fp,
            redacted_preview=f"blocked_path={Path(rel).name}",
            reason=sens_reason,
        )
        if not (allowlist and allowlist.allows(finding)):
            findings.append(finding)

    try:
        size = file_path.stat().st_size
    except OSError:
        return findings

    if size == 0 or size > max_file_bytes:
        return findings

    with file_path.open("rb") as fh:
        head = fh.read(16)

    if head == SQLITE_MAGIC or file_path.suffix.lower() in {".sqlite", ".sqlite3", ".db"}:
        if head == SQLITE_MAGIC:
            findings.extend(scan_sqlite_file(file_path, display_path=rel, allowlist=allowlist))
        return findings

    raw_bytes = file_path.read_bytes()
    if content_index.is_binary_bytes(raw_bytes):
        return findings

    if file_path.suffix.lower() == ".json":
        findings.extend(scan_json_file(file_path, display_path=rel, allowlist=allowlist))
        return findings

    text = raw_bytes.decode("utf-8", errors="replace")
    art_type = "log" if file_path.suffix.lower() in {".log", ".out"} else "file"
    findings.extend(scan_text(text, location=rel, artifact_type=art_type, allowlist=allowlist))
    return findings


def scan_directory(
    directory: Path,
    *,
    allowlist: GateAllowlist | None = None,
    exclude_dirs: Iterable[str] = (".git", "__pycache__", ".pytest_cache", "node_modules"),
) -> dict:
    """Scan all files in a directory tree and return a structured gate report."""
    excluded = set(exclude_dirs)
    findings: list[GateFinding] = []
    files_scanned = 0

    for root_dir, dirnames, filenames in os.walk(directory):
        dirnames[:] = sorted(d for d in dirnames if d not in excluded)
        for name in sorted(filenames):
            target = Path(root_dir) / name
            if target.is_symlink():
                continue
            files_scanned += 1
            findings.extend(scan_file(target, root=directory, allowlist=allowlist))

    return build_gate_report(
        target=str(directory),
        target_type="directory",
        items_scanned=files_scanned,
        findings=findings,
    )


def scan_git_repo_or_bundle(
    source: Path,
    *,
    allowlist: GateAllowlist | None = None,
    max_blob_bytes: int = 1024 * 1024,
) -> dict:
    """Scan all reachable/historical blobs and tree paths in a Git bare repo or bundle."""
    findings: list[GateFinding] = []
    blobs_scanned = 0

    with tempfile.TemporaryDirectory(prefix="secrets-gate-git-") as tmp:
        bare_repo, _ = content_index._resolve_bare_repo(source, Path(tmp))

        # Check all paths across refs and full commit history
        seen_blob_paths: dict[str, set[str]] = {}
        for line in content_index.git_stream(
            bare_repo,
            "log",
            "--all",
            "--raw",
            "--no-renames",
            "--no-abbrev",
            "--format=%x1e%H",
        ):
            if line.startswith("\x1e") or not line.startswith(":") or "\t" not in line:
                continue
            meta, path = line.split("\t", 1)
            fields = meta[1:].split()
            if len(fields) < 5:
                continue
            new_blob = fields[3]
            if re.fullmatch(r"[0-9a-f]{40,64}", new_blob) and set(new_blob) != {"0"}:
                seen_blob_paths.setdefault(new_blob, set()).add(path)

            sens, sens_reason = is_sensitive_path(path)
            if sens and sens_reason:
                finding = GateFinding(
                    rule_id="git-sensitive-path",
                    severity="critical",
                    artifact_type="git-path",
                    location=path,
                    line=None,
                    fingerprint=fingerprint_secret(path),
                    redacted_preview=f"blocked_path={Path(path).name}",
                    reason=sens_reason,
                )
                if not (allowlist and allowlist.allows(finding)):
                    findings.append(finding)

        blob_shas = sorted(seen_blob_paths.keys())
        for start in range(0, len(blob_shas), 500):
            batch = blob_shas[start : start + 500]
            raw_map = content_index.read_blobs_batch(bare_repo, batch)
            for bsha, raw_bytes in raw_map.items():
                if len(raw_bytes) > max_blob_bytes or content_index.is_binary_bytes(raw_bytes):
                    continue
                blobs_scanned += 1
                text = raw_bytes.decode("utf-8", errors="replace")
                rep_path = sorted(seen_blob_paths[bsha])[0]
                findings.extend(
                    scan_text(
                        text,
                        location=f"{rep_path}@{bsha[:12]}",
                        artifact_type="git-blob",
                        allowlist=allowlist,
                    )
                )

    return build_gate_report(
        target=str(source),
        target_type="git",
        items_scanned=blobs_scanned,
        findings=findings,
    )


def run_optional_gitleaks(target: Path, *, mode: str = "dir") -> dict:
    """Run local gitleaks with --redact if installed, never transmitting data externally."""
    binary = shutil.which("gitleaks")
    if not binary:
        return {
            "available": False,
            "executed": False,
            "reason": "gitleaks binary not installed in PATH",
            "findings": [],
        }

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        report_path = Path(tf.name)
    try:
        subcmd = "git" if mode == "git" else "dir"
        cmd = [
            binary,
            subcmd,
            str(target),
            "--redact",
            "--no-banner",
            "--report-format",
            "json",
            "--report-path",
            str(report_path),
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
        parsed = []
        if report_path.exists() and report_path.stat().st_size > 0:
            raw = json.loads(report_path.read_text(encoding="utf-8", errors="replace"))
            for item in raw if isinstance(raw, list) else []:
                parsed.append(
                    {
                        "rule_id": str(item.get("RuleID", "gitleaks")),
                        "file": str(item.get("File", "")),
                        "start_line": item.get("StartLine"),
                        "fingerprint": fingerprint_secret(str(item.get("Match", ""))),
                    }
                )
        return {
            "available": True,
            "executed": True,
            "exit_code": proc.returncode,
            "finding_count": len(parsed),
            "findings": parsed,
        }
    finally:
        if report_path.exists():
            report_path.unlink()


def build_gate_report(
    *,
    target: str,
    target_type: str,
    items_scanned: int,
    findings: list[GateFinding],
) -> dict:
    """Assemble a safe, zero-secret-leakage audit report."""
    # Deduplicate identical findings
    unique: list[GateFinding] = []
    seen: set[tuple[str, str, int | None, str]] = set()
    for f in findings:
        key = (f.rule_id, f.location, f.line, f.fingerprint)
        if key not in seen:
            seen.add(key)
            unique.append(f)

    severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0}
    for f in unique:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

    blocked = len(unique) > 0
    return {
        "ok": not blocked,
        "blocked": blocked,
        "gate_decision": "BLOCK" if blocked else "PASS",
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "target": target,
        "target_type": target_type,
        "items_scanned": items_scanned,
        "finding_count": len(unique),
        "severity_counts": severity_counts,
        "findings": [f.to_dict() for f in unique],
    }


def scan_target(
    target: Path,
    *,
    allowlist: GateAllowlist | None = None,
    use_gitleaks: bool = False,
) -> dict:
    """Auto-detect target type (file, SQLite, JSON, directory, Git repo/bundle) and scan."""
    if not target.exists():
        raise FileNotFoundError(f"Target does not exist: {target}")

    if target.is_file():
        if target.suffix == ".bundle":
            report = scan_git_repo_or_bundle(target, allowlist=allowlist)
        else:
            findings = scan_file(target, allowlist=allowlist)
            report = build_gate_report(
                target=str(target),
                target_type="file",
                items_scanned=1,
                findings=findings,
            )
    elif (target / "HEAD").is_file() or (target / ".git" / "HEAD").is_file():
        # Scan working tree (if any) + git history
        if (target / ".git").is_dir():
            dir_report = scan_directory(target, allowlist=allowlist)
            git_report = scan_git_repo_or_bundle(target / ".git", allowlist=allowlist)
            combined_findings = [
                GateFinding(**f) for f in (dir_report["findings"] + git_report["findings"])
            ]
            report = build_gate_report(
                target=str(target),
                target_type="git-workspace",
                items_scanned=dir_report["items_scanned"] + git_report["items_scanned"],
                findings=combined_findings,
            )
        else:
            report = scan_git_repo_or_bundle(target, allowlist=allowlist)
    else:
        report = scan_directory(target, allowlist=allowlist)

    if use_gitleaks:
        mode = "git" if report["target_type"].startswith("git") else "dir"
        report["gitleaks"] = run_optional_gitleaks(target, mode=mode)
    return report


def _load_allowlist(path: Path | None) -> GateAllowlist:
    if path is None:
        return GateAllowlist()
    data = json.loads(path.read_text(encoding="utf-8"))
    return GateAllowlist(
        fingerprints=set(data.get("fingerprints", [])),
        path_prefixes=tuple(data.get("path_prefixes", [])),
        rule_ids=set(data.get("rule_ids", [])),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Independent local secrets gate for repositories and derived artifacts."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="Scan a file, directory, SQLite DB, JSON, or Git repo/bundle.")
    scan_p.add_argument("target", type=Path, help="Path to scan.")
    scan_p.add_argument("--allowlist", type=Path, default=None, help="JSON allowlist file.")
    scan_p.add_argument(
        "--use-gitleaks",
        action="store_true",
        help="Optionally invoke local gitleaks binary with --redact if available.",
    )
    scan_p.add_argument("--output", type=Path, default=None, help="Optional JSON report path.")

    san_p = sub.add_parser("sanitize", help="Sanitize/redact secrets in a text or JSON file.")
    san_p.add_argument("input", type=Path, help="Input file path.")
    san_p.add_argument("--output", type=Path, default=None, help="Output file path (stdout if omitted).")

    args = parser.parse_args(argv)

    if args.command == "scan":
        allowlist = _load_allowlist(args.allowlist)
        report = scan_target(args.target, allowlist=allowlist, use_gitleaks=args.use_gitleaks)
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        else:
            sys.stdout.write(payload)
        return 2 if report["blocked"] else 0

    if args.command == "sanitize":
        raw = args.input.read_text(encoding="utf-8", errors="replace")
        if args.input.suffix.lower() == ".json":
            try:
                parsed = json.loads(raw)
                cleaned_obj, count = sanitize_json_value(parsed)
                cleaned_text = json.dumps(cleaned_obj, ensure_ascii=False, indent=2) + "\n"
            except json.JSONDecodeError:
                cleaned_text, count = sanitize_text(raw)
        else:
            cleaned_text, count = sanitize_text(raw)

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(cleaned_text, encoding="utf-8")
            sys.stdout.write(json.dumps({"ok": True, "redactions": count}) + "\n")
        else:
            sys.stdout.write(cleaned_text)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
