#!/usr/bin/env python3
"""Offline deterministic search -> fetch -> preview -> recover flow with original evidence.

Reuses scripts/content_index.py (search, recover_lines) and scripts/image_catalog.py
without starting an MCP server or writing private data into site/.
Standard library only (optional Pillow delegation handled by image_catalog).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import content_index  # noqa: E402
import image_catalog  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parent

DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50
DEFAULT_SNIPPET_LINES = 7
DEFAULT_PREVIEW_LINES = 40
MAX_PREVIEW_LINES = 120
DEFAULT_MAX_CHARS = 8000
DEFAULT_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_PAYLOAD_BYTES = 256 * 1024
DEFAULT_THUMB_SIZE = 160
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 2
MAX_RETRIES_LIMIT = 5
DEFAULT_RETRY_DELAY_SECONDS = 0.05

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_OR_256_RE = re.compile(r"^[0-9a-f]{40,64}$")
SAFE_TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
SAFE_ASSET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")
SAFE_REF_NAME_RE = re.compile(r"^(?!-)(?!.*\.\.)(?!.*//)[A-Za-z0-9._/@{}-]{1,200}$")

MIME_BY_EXT: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".md": "text/markdown",
    ".mdx": "text/markdown",
    ".txt": "text/plain",
    ".rst": "text/plain",
    ".json": "application/json",
    ".jsonc": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".toml": "application/toml",
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".scss": "text/css",
    ".sass": "text/css",
    ".less": "text/css",
    ".xml": "application/xml",
    ".sql": "application/sql",
    ".sh": "text/x-shellscript",
    ".bash": "text/x-shellscript",
    ".ps1": "text/plain",
    ".py": "text/x-python",
    ".pyi": "text/x-python",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".cjs": "text/javascript",
    ".jsx": "text/javascript",
    ".ts": "text/typescript",
    ".mts": "text/typescript",
    ".cts": "text/typescript",
    ".tsx": "text/typescript",
    ".go": "text/x-go",
    ".rs": "text/rust",
    ".java": "text/x-java-source",
    ".c": "text/x-c",
    ".h": "text/x-c",
    ".cpp": "text/x-c++",
    ".hpp": "text/x-c++",
    ".rb": "text/x-ruby",
    ".php": "text/x-php",
    ".svelte": "text/plain",
    ".vue": "text/plain",
    ".graphql": "application/graphql",
    ".gql": "application/graphql",
}

MIME_BY_DETECTED_FORMAT: dict[str, str] = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
}


class ArchiveFlowError(RuntimeError):
    """Structured explicit error for archive flow operations."""

    code = "archive_flow_error"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        retryable: bool | None = None,
        attempts: int = 1,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        if retryable is not None:
            self.retryable = retryable
        self.message = message
        self.attempts = attempts
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "attempts": self.attempts,
                "details": self.details,
            },
        }


class NotFoundError(ArchiveFlowError):
    code = "not_found"
    retryable = False


class ReleaseMissingError(ArchiveFlowError):
    code = "release_missing"
    retryable = False


class PermissionDeniedError(ArchiveFlowError):
    code = "permission_denied"
    retryable = False


class ArchiveTimeoutError(ArchiveFlowError):
    code = "timeout"
    retryable = True


class TransientTransportError(ArchiveFlowError):
    code = "transient_error"
    retryable = True


class ChecksumMismatchError(ArchiveFlowError):
    code = "checksum_mismatch"
    retryable = False


class SizeLimitExceededError(ArchiveFlowError):
    code = "size_limit_exceeded"
    retryable = False


class PayloadLimitExceededError(ArchiveFlowError):
    code = "payload_limit_exceeded"
    retryable = False


class UnsafeInputError(ArchiveFlowError):
    code = "unsafe_input"
    retryable = False


def validate_private_path(path: Path, repo_root: Path | None = None) -> Path:
    """Reject any path targeting site/ or public GitHub Pages output."""
    try:
        return image_catalog.validate_private_output_path(path, repo_root=repo_root or REPO_ROOT)
    except ValueError as exc:
        raise PermissionDeniedError(str(exc), details={"path": str(path)}) from exc


def validate_sha256(value: str, label: str = "sha256") -> str:
    cleaned = value.strip().lower()
    if not SHA256_RE.fullmatch(cleaned):
        raise UnsafeInputError(f"Invalid {label}: expected 64 lowercase hex characters")
    return cleaned


def validate_commit_sha(value: str) -> str:
    try:
        return content_index.safe_ref(value.strip().lower())
    except ValueError as exc:
        raise UnsafeInputError(str(exc), details={"sha": value}) from exc


def validate_path(path: str) -> str:
    try:
        return content_index.safe_path(path)
    except ValueError as exc:
        raise UnsafeInputError(str(exc), details={"path": path}) from exc


def validate_ref_name(ref: str) -> str:
    cleaned = ref.strip()
    if not cleaned or not SAFE_REF_NAME_RE.fullmatch(cleaned) or "\\" in cleaned or "\x00" in cleaned:
        raise UnsafeInputError(f"Unsafe git ref: {ref!r}", details={"ref": ref})
    return cleaned


def guess_mime(path: str, raw: bytes | None = None, detected_format: str | None = None) -> str:
    ext = Path(path).suffix.lower()
    if detected_format and detected_format in MIME_BY_DETECTED_FORMAT:
        return MIME_BY_DETECTED_FORMAT[detected_format]
    if raw is not None and ext in image_catalog.IMAGE_EXTENSIONS:
        fmt = image_catalog.detect_format(raw, ext)
        if fmt in MIME_BY_DETECTED_FORMAT:
            return MIME_BY_DETECTED_FORMAT[fmt]
    if ext in MIME_BY_EXT:
        return MIME_BY_EXT[ext]
    if raw is not None:
        if not content_index.is_binary_bytes(raw):
            return "text/plain"
        return "application/octet-stream"
    return "application/octet-stream"


def estimate_tokens(payload: object, content_text: str | None = None) -> dict:
    """Estimate deterministic token transfer counts using stdlib only."""
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    total_chars = len(serialized)
    total_bytes = len(serialized.encode("utf-8"))
    estimated_tokens = (total_chars + 3) // 4 if total_chars else 0
    content_chars = len(content_text) if content_text is not None else 0
    content_tokens = (content_chars + 3) // 4 if content_chars else 0
    return {
        "estimated_tokens": estimated_tokens,
        "content_tokens": content_tokens,
        "payload_chars": total_chars,
        "payload_bytes": total_bytes,
        "method": "approx_chars_div_4",
    }


def _attach_tokens(body: dict, content_text: str | None = None) -> dict:
    tokens = estimate_tokens(body, content_text=content_text)
    out = dict(body)
    out["tokens"] = tokens
    return out


def run_with_retry(
    fn: Callable[[], object],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> tuple[object, int]:
    if max_retries < 0 or max_retries > MAX_RETRIES_LIMIT:
        raise UnsafeInputError(f"max_retries must be between 0 and {MAX_RETRIES_LIMIT}")
    if retry_delay < 0:
        raise UnsafeInputError("retry_delay must be >= 0")

    last_exc: ArchiveFlowError | None = None
    for attempt in range(1, max_retries + 2):
        try:
            return fn(), attempt
        except ArchiveFlowError as exc:
            exc.attempts = attempt
            last_exc = exc
            if not exc.retryable or attempt > max_retries:
                raise
            if retry_delay > 0:
                time.sleep(retry_delay * attempt)
    assert last_exc is not None
    raise last_exc


def _run_subprocess(
    cmd: list[str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    binary: bool = True,
) -> bytes | str:
    if timeout <= 0:
        raise UnsafeInputError("timeout must be > 0")
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ArchiveTimeoutError(
            f"Command timed out after {timeout}s: {' '.join(cmd[:3])}",
            details={"command": cmd[:3], "timeout": timeout},
        ) from exc
    except FileNotFoundError as exc:
        raise NotFoundError(f"Missing executable: {cmd[0]}") from exc
    except OSError as exc:
        raise ArchiveFlowError(f"OS error running {cmd[0]}: {exc}", code="os_error") from exc

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()[:600]
        lowered = err.lower()
        if "not found" in lowered or "does not exist" in lowered or "exists on disk, but not in" in lowered or "bad object" in lowered or "invalid object name" in lowered or "unknown revision" in lowered or "not a valid object name" in lowered:
            raise NotFoundError(err or f"Object not found running {' '.join(cmd[:3])}")
        if "permission denied" in lowered or "authentication" in lowered or "401" in lowered or "403" in lowered or "not logged into" in lowered:
            raise PermissionDeniedError(err or f"Permission denied running {' '.join(cmd[:3])}")
        if "timed out" in lowered or "timeout" in lowered:
            raise ArchiveTimeoutError(err or f"Timed out running {' '.join(cmd[:3])}")
        raise ArchiveFlowError(err or f"Command failed ({proc.returncode}): {' '.join(cmd[:3])}", code="command_failed")
    return proc.stdout if binary else proc.stdout.decode("utf-8", "replace")


def _open_bare_repo_with_retry(
    source: Path,
    temp_root: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> tuple[Path, str, int]:
    if not source.exists():
        raise NotFoundError(f"Source repository or bundle not found: {source}", details={"source": str(source)})

    if source.is_dir():
        if (source / "HEAD").is_file():
            return source, "bare", 1
        if (source / ".git" / "HEAD").is_file():
            return source / ".git", "workdir", 1
        raise NotFoundError(f"Directory is not a valid git repository: {source}", details={"source": str(source)})

    if source.is_file():
        bare = temp_root / "mirror.git"

        def clone_bundle() -> Path:
            if bare.exists():
                for root_dir, dirs, files in os.walk(bare, topdown=False):
                    for name in files:
                        Path(root_dir, name).unlink(missing_ok=True)
                    for name in dirs:
                        Path(root_dir, name).rmdir()
                bare.rmdir()
            _run_subprocess(["git", "init", "--bare", "-q", str(bare)], timeout=timeout, binary=True)
            try:
                _run_subprocess(["git", f"--git-dir={bare}", "bundle", "verify", "-q", str(source)], timeout=timeout, binary=True)
                _run_subprocess(["git", f"--git-dir={bare}", "fetch", "-q", str(source), "refs/*:refs/*"], timeout=timeout, binary=True)
            except NotFoundError as exc:
                raise ArchiveFlowError(f"Invalid or corrupt git bundle: {exc.message}", code="invalid_bundle") from exc
            return bare

        resolved_bare, attempts = run_with_retry(
            clone_bundle,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        return resolved_bare, "bundle", attempts

    raise UnsafeInputError(f"Unsupported source path: {source}")


def resolve_release_asset(
    *,
    release_tag: str,
    asset: str,
    release_dir: Path | None = None,
    dest_dir: Path | None = None,
    manifest_path: Path | None = None,
    expected_sha256: str | None = None,
    max_bytes: int | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
    fetcher: Callable[[str, str, Path, float], Path] | None = None,
) -> dict:
    """Resolve and verify a release asset offline (from release_dir/fetcher) with retry and checksum checks."""
    if not SAFE_TAG_RE.fullmatch(release_tag):
        raise UnsafeInputError(f"Invalid release tag: {release_tag!r}")
    if not SAFE_ASSET_RE.fullmatch(asset):
        raise UnsafeInputError(f"Invalid asset name: {asset!r}")
    if expected_sha256 is not None:
        expected_sha256 = validate_sha256(expected_sha256, "expected_sha256")
    if max_bytes is not None and max_bytes < 1:
        raise UnsafeInputError("max_bytes must be >= 1")

    if manifest_path is not None:
        if not manifest_path.is_file():
            raise NotFoundError(f"Manifest file not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_tag = manifest.get("tag")
        if manifest_tag and manifest_tag != release_tag:
            raise ReleaseMissingError(
                f"Release tag {release_tag!r} absent in manifest (found {manifest_tag!r})",
                details={"release_tag": release_tag, "manifest_tag": manifest_tag},
            )
        assets = manifest.get("assets", [])
        entry = next(
            (a for a in assets if a.get("asset") == asset or a.get("name") == asset),
            None,
        )
        if entry is None:
            raise ReleaseMissingError(
                f"Asset {asset!r} absent in release {release_tag!r}",
                details={"release_tag": release_tag, "asset": asset},
            )
        if expected_sha256 is None and isinstance(entry.get("sha256"), str):
            expected_sha256 = validate_sha256(entry["sha256"], "manifest sha256")

    if dest_dir is not None:
        validate_private_path(dest_dir)

    def acquire() -> Path:
        if fetcher is not None:
            target_dir = dest_dir if dest_dir is not None else (release_dir or Path(tempfile.gettempdir()))
            return fetcher(release_tag, asset, target_dir, timeout)

        if release_dir is not None:
            tag_dir = release_dir / release_tag
            if not release_dir.exists() or not tag_dir.is_dir():
                raise ReleaseMissingError(
                    f"Release absent locally: {release_tag}",
                    details={"release_tag": release_tag, "release_dir": str(release_dir)},
                )
            candidate = tag_dir / asset
            if not candidate.is_file():
                raise ReleaseMissingError(
                    f"Release asset absent: {release_tag}/{asset}",
                    details={"release_tag": release_tag, "asset": asset},
                )
            return candidate

        raise ReleaseMissingError(
            f"Offline mode requires --source or --release-dir for release {release_tag}",
            details={"release_tag": release_tag, "asset": asset},
        )

    asset_path, attempts = run_with_retry(
        acquire,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
    assert isinstance(asset_path, Path)
    if not asset_path.is_file():
        raise ReleaseMissingError(
            f"Release asset missing after acquisition: {release_tag}/{asset}",
            attempts=attempts,
            details={"release_tag": release_tag, "asset": asset},
        )

    actual_bytes = asset_path.stat().st_size
    if max_bytes is not None and actual_bytes > max_bytes:
        raise SizeLimitExceededError(
            f"Asset size {actual_bytes} exceeds max_bytes {max_bytes}",
            attempts=attempts,
            details={"bytes": actual_bytes, "max_bytes": max_bytes},
        )

    digest = hashlib.sha256()
    with asset_path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()

    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ChecksumMismatchError(
            f"Checksum mismatch for {asset}: expected {expected_sha256}, got {actual_sha256}",
            attempts=attempts,
            details={
                "asset": asset,
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
            },
        )

    return {
        "release_tag": release_tag,
        "asset": asset,
        "path": asset_path,
        "bytes": actual_bytes,
        "sha256": actual_sha256,
        "attempts": attempts,
    }


def _resolve_commit_and_ref(
    bare_repo: Path,
    *,
    sha: str | None,
    ref: str | None,
    timeout: float,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> tuple[str, str]:
    if sha is None and ref is None:
        raise UnsafeInputError("Either --sha or --ref must be provided")

    def resolve() -> tuple[str, str]:
        if sha is not None:
            full_sha = validate_commit_sha(sha)
            obj_type = _run_subprocess(
                ["git", f"--git-dir={bare_repo}", "cat-file", "-t", full_sha],
                timeout=timeout,
                binary=False,
            )
            assert isinstance(obj_type, str)
            if obj_type.strip() != "commit":
                raise NotFoundError(f"SHA {full_sha} is not a commit object")
        else:
            assert ref is not None
            safe_r = validate_ref_name(ref)
            resolved = _run_subprocess(
                ["git", f"--git-dir={bare_repo}", "rev-parse", f"{safe_r}^{{commit}}"],
                timeout=timeout,
                binary=False,
            )
            assert isinstance(resolved, str)
            full_sha = validate_commit_sha(resolved.strip())

        if ref is not None:
            resolved_ref = validate_ref_name(ref)
        else:
            raw_refs = _run_subprocess(
                ["git", f"--git-dir={bare_repo}", "for-each-ref", "--format=%(refname)", "--contains", full_sha],
                timeout=timeout,
                binary=False,
            )
            assert isinstance(raw_refs, str)
            candidates = [line.strip() for line in raw_refs.splitlines() if line.strip()]
            candidates.sort(key=image_catalog._ref_sort_key)
            resolved_ref = candidates[0] if candidates else "history/detached"
        return full_sha, resolved_ref

    result, attempts = run_with_retry(
        resolve,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
    assert isinstance(result, tuple)
    return result[0], result[1], attempts


def _read_git_object(
    bare_repo: Path,
    *,
    full_sha: str,
    path: str,
    expected_sha256: str | None = None,
    expected_blob_sha: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> tuple[str, bytes, str, int]:
    if max_bytes < 1:
        raise UnsafeInputError("max_bytes must be >= 1")
    if expected_sha256 is not None:
        expected_sha256 = validate_sha256(expected_sha256, "expected_sha256")
    if expected_blob_sha is not None:
        expected_blob_sha = validate_commit_sha(expected_blob_sha)

    def fetch_blob() -> tuple[str, bytes, str]:
        blob_sha_raw = _run_subprocess(
            ["git", f"--git-dir={bare_repo}", "rev-parse", f"{full_sha}:{path}"],
            timeout=timeout,
            binary=False,
        )
        assert isinstance(blob_sha_raw, str)
        blob_sha = blob_sha_raw.strip().lower()
        if not SHA1_OR_256_RE.fullmatch(blob_sha):
            raise NotFoundError(f"Object {full_sha}:{path} is not a blob")

        obj_type = _run_subprocess(
            ["git", f"--git-dir={bare_repo}", "cat-file", "-t", blob_sha],
            timeout=timeout,
            binary=False,
        )
        assert isinstance(obj_type, str)
        if obj_type.strip() != "blob":
            raise NotFoundError(f"Path {path} at {full_sha} is not a file blob")

        if expected_blob_sha is not None and blob_sha != expected_blob_sha:
            raise ChecksumMismatchError(
                f"Git blob SHA mismatch for {path}: expected {expected_blob_sha}, got {blob_sha}",
                details={"expected_blob_sha": expected_blob_sha, "actual_blob_sha": blob_sha},
            )

        size_raw = _run_subprocess(
            ["git", f"--git-dir={bare_repo}", "cat-file", "-s", blob_sha],
            timeout=timeout,
            binary=False,
        )
        assert isinstance(size_raw, str)
        blob_size = int(size_raw.strip())
        if blob_size > max_bytes:
            raise SizeLimitExceededError(
                f"Blob size {blob_size} bytes exceeds max_bytes {max_bytes}",
                details={"path": path, "bytes": blob_size, "max_bytes": max_bytes},
            )

        raw = _run_subprocess(
            ["git", f"--git-dir={bare_repo}", "cat-file", "blob", blob_sha],
            timeout=timeout,
            binary=True,
        )
        assert isinstance(raw, bytes)
        if len(raw) > max_bytes:
            raise SizeLimitExceededError(
                f"Blob size {len(raw)} bytes exceeds max_bytes {max_bytes}",
                details={"path": path, "bytes": len(raw), "max_bytes": max_bytes},
            )
        actual_sha256 = hashlib.sha256(raw).hexdigest()
        if expected_sha256 is not None and actual_sha256 != expected_sha256:
            raise ChecksumMismatchError(
                f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual_sha256}",
                details={
                    "path": path,
                    "expected_sha256": expected_sha256,
                    "actual_sha256": actual_sha256,
                },
            )
        return blob_sha, raw, actual_sha256

    (blob_sha, raw, actual_sha256), attempts = run_with_retry(
        fetch_blob,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
    return blob_sha, raw, actual_sha256, attempts


def _is_deleted_at_ref(bare_repo: Path, ref: str, path: str, timeout: float) -> bool:
    if not ref or ref.startswith("history/"):
        return True
    try:
        _run_subprocess(
            ["git", f"--git-dir={bare_repo}", "cat-file", "-e", f"{ref}:{path}"],
            timeout=timeout,
            binary=True,
        )
        return False
    except ArchiveFlowError:
        return True


def _is_image_path_or_bytes(path: str, raw: bytes) -> bool:
    ext = Path(path).suffix.lower()
    if ext in image_catalog.IMAGE_EXTENSIONS:
        return True
    return image_catalog.detect_format(raw, ext) != "unknown"


def _slice_text_lines(
    raw_bytes: bytes,
    *,
    full_sha: str,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict:
    """Slice exact lines from already-verified blob bytes using content_index line semantics."""
    if start_line is not None and start_line < 1:
        raise UnsafeInputError("start_line must be >= 1")
    if end_line is not None and end_line < 1:
        raise UnsafeInputError("end_line must be >= 1")
    if start_line is not None and end_line is not None and end_line < start_line:
        raise UnsafeInputError("end_line must be >= start_line")

    text = raw_bytes.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    if start_line is not None and end_line is not None:
        eff_start = start_line
        eff_end = end_line
    elif start_line is not None:
        eff_start = start_line
        eff_end = len(lines)
    elif end_line is not None:
        eff_start = 1 if lines else 0
        eff_end = end_line
    else:
        eff_start = 1 if lines else 0
        eff_end = len(lines)

    if eff_start == 0:
        selected = ""
    else:
        selected = "\n".join(lines[eff_start - 1 : eff_end])
    return {
        "commit_sha": full_sha,
        "path": path,
        "start_line": eff_start,
        "end_line": eff_end,
        "lines_total": len(lines),
        "content": selected,
    }


def _compute_text_sha256_map(
    source: Path,
    blob_shas: list[str],
    timeout: float,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict[str, str]:
    unique = [s for s in dict.fromkeys(blob_shas) if s]
    if not unique:
        return {}
    with tempfile.TemporaryDirectory(prefix="flow-sha256-") as tmp:
        bare_repo, _, _ = _open_bare_repo_with_retry(
            source,
            Path(tmp),
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        blobs = image_catalog._read_blobs_batch(bare_repo, unique)
        return {
            bsha: hashlib.sha256(data).hexdigest()
            for bsha, data in blobs.items()
            if data is not None
        }


def flow_search(
    query: str,
    *,
    db_path: Path | None = None,
    source: Path | None = None,
    repo: str | None = None,
    ref: str | None = None,
    extension: str | None = None,
    language: str | None = None,
    status: str | None = None,
    kind: str = "all",
    limit: int = DEFAULT_SEARCH_LIMIT,
    snippet_lines: int = DEFAULT_SNIPPET_LINES,
    match_all: bool = True,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict:
    """Search content index and/or image catalog with bounded deterministic results."""
    if not isinstance(query, str) or not query.strip():
        raise UnsafeInputError("Search query must not be empty")
    if len(query) > 200 or query.lstrip().startswith("-") or any(ord(ch) < 32 for ch in query):
        raise UnsafeInputError("Unsafe search query")
    if kind not in {"all", "code", "text", "image"}:
        raise UnsafeInputError(f"Invalid kind: {kind!r}")
    if limit < 1 or limit > MAX_SEARCH_LIMIT:
        raise UnsafeInputError(f"limit must be between 1 and {MAX_SEARCH_LIMIT}")
    if snippet_lines < 1 or snippet_lines > 40:
        raise UnsafeInputError("snippet_lines must be between 1 and 40")

    results: list[dict] = []
    source_repo_label = repo or (source.stem if source is not None else None)
    text_fetch_limit = min(MAX_SEARCH_LIMIT * 3, max(limit * 3, limit))

    if kind in {"all", "code", "text"}:
        code_hits: list[dict] = []
        if db_path is not None and db_path.exists():
            conn = content_index.open_db(db_path)
            try:
                code_hits = content_index.search(
                    conn,
                    query,
                    repo=repo,
                    ref=ref,
                    extension=extension,
                    language=language,
                    status=status,
                    limit=text_fetch_limit,
                    snippet_lines=snippet_lines,
                    match_all=match_all,
                )
            finally:
                conn.close()
        elif source is not None:
            if not source.exists():
                raise NotFoundError(f"Source repository or bundle not found: {source}")
            with tempfile.TemporaryDirectory(prefix="flow-index-") as tmp:
                temp_db = Path(tmp) / "content.sqlite"
                conn = content_index.open_db(temp_db)
                try:
                    repo_name = source_repo_label or "archive-source"
                    content_index.ingest_repo(source, repo_name, conn)
                    code_hits = content_index.search(
                        conn,
                        query,
                        repo=repo,
                        ref=ref,
                        extension=extension,
                        language=language,
                        status=status,
                        limit=text_fetch_limit,
                        snippet_lines=snippet_lines,
                        match_all=match_all,
                    )
                finally:
                    conn.close()
        elif db_path is not None:
            raise NotFoundError(f"Index database not found: {db_path}")
        else:
            raise UnsafeInputError("Provide --db or --source for code/text search")

        sha256_map: dict[str, str] = {}
        if source is not None and source.exists() and code_hits:
            sha256_map = _compute_text_sha256_map(
                source,
                [h["blob_sha"] for h in code_hits],
                timeout=timeout,
                max_retries=max_retries,
                retry_delay=retry_delay,
            )

        seen_text_keys: set[tuple[str, str, str, str, int, int]] = set()
        for hit in code_hits:
            item_kind = "markdown" if hit["language"] in {"markdown", "mdx"} else "code"
            if kind == "code" and item_kind == "markdown":
                continue
            dedupe_key = (
                hit["repository"],
                hit["ref"],
                hit["commit_sha"],
                hit["path"],
                int(hit["start_line"]),
                int(hit["end_line"]),
            )
            if dedupe_key in seen_text_keys:
                continue
            seen_text_keys.add(dedupe_key)
            results.append(
                {
                    "source_repo": hit["repository"],
                    "ref": hit["ref"],
                    "full_sha": hit["commit_sha"],
                    "path": hit["path"],
                    "mime": guess_mime(hit["path"]),
                    "sha256": sha256_map.get(hit["blob_sha"]),
                    "blob_sha": hit["blob_sha"],
                    "kind": item_kind,
                    "language": hit["language"],
                    "status": hit["status"],
                    "start_line": hit["start_line"],
                    "end_line": hit["end_line"],
                    "preview": hit["snippet"],
                    "score": hit["score"],
                }
            )

    if kind in {"all", "image"} and source is not None:
        if not source.exists():
            raise NotFoundError(f"Source repository or bundle not found: {source}")
        catalog = image_catalog.catalog_git_source(
            source,
            origin=source_repo_label or "archive-source",
            query=query,
            deleted_only=(status == "deleted"),
            limit=limit,
            force_no_pillow=True,
        )
        norm_ext = content_index.normalize_extension(extension) if extension else None
        for item in catalog.get("items", []):
            if item.get("missing"):
                continue
            if norm_ext and item["extension"] != norm_ext:
                continue
            item_ref = item["ref"] or ("history/deleted" if item["deleted"] else "history/detached")
            if ref:
                if ref.startswith("refs/") or ref.startswith("history/"):
                    if item_ref != ref and ref not in item.get("refs", []):
                        continue
                elif f"refs/heads/{ref}" not in item.get("refs", []) and item_ref != ref:
                    continue
            if status == "ref-head" and item["deleted"]:
                continue
            if not item.get("commit"):
                continue
            results.append(
                {
                    "source_repo": item["origin"],
                    "ref": item_ref,
                    "full_sha": item["commit"],
                    "path": item["path"],
                    "mime": guess_mime(item["path"], detected_format=item.get("format")),
                    "sha256": item["sha256"],
                    "blob_sha": item["blob_sha"],
                    "kind": "image",
                    "language": "image",
                    "status": item["status"],
                    "deleted": item["deleted"],
                    "bytes": item["bytes"],
                    "width": item["width"],
                    "height": item["height"],
                    "inert": item["inert"],
                    "script_detected": item["script_detected"],
                    "preview": (
                        f"image/{item['format']} {item['width']}x{item['height']} "
                        f"({item['bytes']} bytes, {item['status']})"
                    ),
                    "score": 0.0,
                }
            )

    results.sort(
        key=lambda r: (
            0 if r["kind"] != "image" else 1,
            float(r.get("score", 0.0)),
            r["source_repo"],
            r["ref"],
            r["path"],
            r["full_sha"],
        )
    )
    bounded = results[:limit]
    content_preview = "\n".join(str(r.get("preview", "")) for r in bounded)
    body = {
        "ok": True,
        "operation": "search",
        "query": query,
        "kind": kind,
        "limit": limit,
        "returned": len(bounded),
        "results": bounded,
    }
    return _attach_tokens(body, content_text=content_preview)


def flow_fetch(
    *,
    source: Path,
    path: str,
    sha: str | None = None,
    ref: str | None = None,
    source_repo: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    expected_sha256: str | None = None,
    expected_blob_sha: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict:
    """Fetch verified original code/markdown/image bytes from historical Git commit."""
    if max_payload_bytes < 64:
        raise UnsafeInputError("max_payload_bytes must be >= 64")
    safe_rel_path = validate_path(path)
    if content_index.is_secret_path(safe_rel_path):
        raise PermissionDeniedError(
            f"Refusing to fetch secret path: {safe_rel_path}",
            details={"path": safe_rel_path},
        )
    repo_label = source_repo or source.stem or source.name

    with tempfile.TemporaryDirectory(prefix="flow-fetch-") as tmp:
        bare_repo, _source_type, clone_attempts = _open_bare_repo_with_retry(
            source,
            Path(tmp),
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        full_sha, resolved_ref, resolve_attempts = _resolve_commit_and_ref(
            bare_repo,
            sha=sha,
            ref=ref,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        blob_sha, raw_bytes, actual_sha256, read_attempts = _read_git_object(
            bare_repo,
            full_sha=full_sha,
            path=safe_rel_path,
            expected_sha256=expected_sha256,
            expected_blob_sha=expected_blob_sha,
            max_bytes=max_bytes,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        deleted_at_head = _is_deleted_at_ref(bare_repo, resolved_ref, safe_rel_path, timeout=timeout)
        attempts = max(clone_attempts, resolve_attempts, read_attempts)

        if _is_image_path_or_bytes(safe_rel_path, raw_bytes):
            ext = Path(safe_rel_path).suffix.lower()
            fmt = image_catalog.detect_format(raw_bytes, ext)
            mime = guess_mime(safe_rel_path, raw_bytes, detected_format=fmt)
            b64 = base64.b64encode(raw_bytes).decode("ascii")
            if len(b64.encode("ascii")) > max_payload_bytes:
                raise PayloadLimitExceededError(
                    f"Base64 image payload ({len(b64)} bytes) exceeds max_payload_bytes ({max_payload_bytes})",
                    attempts=attempts,
                    details={"payload_bytes": len(b64), "max_payload_bytes": max_payload_bytes},
                )
            if fmt == "svg" or ext == ".svg":
                svg_meta = image_catalog.inspect_svg_inert(raw_bytes)
                width, height = svg_meta["width"], svg_meta["height"]
                inert = True
                script_detected = svg_meta["script_detected"]
            else:
                width, height = image_catalog.parse_image_dimensions(raw_bytes, ext)
                inert = False
                script_detected = False
            preview_summary = f"image/{fmt} {width}x{height} ({len(raw_bytes)} bytes)"
            body = {
                "ok": True,
                "operation": "fetch",
                "source_repo": repo_label,
                "ref": resolved_ref,
                "full_sha": full_sha,
                "path": safe_rel_path,
                "mime": mime,
                "sha256": actual_sha256,
                "blob_sha": blob_sha,
                "bytes": len(raw_bytes),
                "deleted_at_ref_head": deleted_at_head,
                "kind": "image",
                "encoding": "base64",
                "content_base64": b64,
                "preview": preview_summary,
                "width": width,
                "height": height,
                "inert": inert,
                "script_detected": script_detected,
                "attempts": attempts,
            }
            return _attach_tokens(body, content_text=b64)

        if content_index.is_binary_bytes(raw_bytes):
            b64 = base64.b64encode(raw_bytes).decode("ascii")
            if len(b64.encode("ascii")) > max_payload_bytes:
                raise PayloadLimitExceededError(
                    f"Base64 binary payload ({len(b64)} bytes) exceeds max_payload_bytes ({max_payload_bytes})",
                    attempts=attempts,
                    details={"payload_bytes": len(b64), "max_payload_bytes": max_payload_bytes},
                )
            body = {
                "ok": True,
                "operation": "fetch",
                "source_repo": repo_label,
                "ref": resolved_ref,
                "full_sha": full_sha,
                "path": safe_rel_path,
                "mime": "application/octet-stream",
                "sha256": actual_sha256,
                "blob_sha": blob_sha,
                "bytes": len(raw_bytes),
                "deleted_at_ref_head": deleted_at_head,
                "kind": "binary",
                "encoding": "base64",
                "content_base64": b64,
                "preview": f"binary ({len(raw_bytes)} bytes)",
                "attempts": attempts,
            }
            return _attach_tokens(body, content_text=b64)

        full_text = raw_bytes.decode("utf-8", "replace")
        if content_index.contains_secret_content(full_text):
            raise PermissionDeniedError(
                f"Refusing to return blob containing secret pattern: {safe_rel_path}",
                attempts=attempts,
                details={"path": safe_rel_path},
            )

        if start_line is not None and end_line is not None:
            if start_line < 1 or end_line < start_line:
                raise UnsafeInputError("Invalid line range: expected 1 <= start_line <= end_line")
            recovered = content_index.recover_lines(
                bare_repo,
                full_sha,
                safe_rel_path,
                start_line=start_line,
                end_line=end_line,
            )
            selected_text = recovered["content"]
            eff_start = recovered["start_line"]
            eff_end = recovered["end_line"]
            lines_total = len(
                [
                    line
                    for line in full_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                ]
            )
            if full_text.endswith(("\n", "\r")) and lines_total > 0:
                lines_total -= 1
        else:
            sliced = _slice_text_lines(
                raw_bytes,
                full_sha=full_sha,
                path=safe_rel_path,
                start_line=start_line,
                end_line=end_line,
            )
            selected_text = sliced["content"]
            eff_start = sliced["start_line"]
            eff_end = sliced["end_line"]
            lines_total = sliced["lines_total"]

        if len(selected_text.encode("utf-8")) > max_payload_bytes:
            raise PayloadLimitExceededError(
                f"Text payload ({len(selected_text.encode('utf-8'))} bytes) exceeds max_payload_bytes ({max_payload_bytes})",
                attempts=attempts,
                details={
                    "payload_bytes": len(selected_text.encode("utf-8")),
                    "max_payload_bytes": max_payload_bytes,
                },
            )
        lang_info = content_index.detect_language(safe_rel_path)
        item_kind = "markdown" if (lang_info and lang_info[1] in {"markdown", "mdx"}) else "code"
        preview_lines = selected_text.splitlines()[:DEFAULT_SNIPPET_LINES]
        body = {
            "ok": True,
            "operation": "fetch",
            "source_repo": repo_label,
            "ref": resolved_ref,
            "full_sha": full_sha,
            "path": safe_rel_path,
            "mime": guess_mime(safe_rel_path, raw_bytes),
            "sha256": actual_sha256,
            "blob_sha": blob_sha,
            "bytes": len(raw_bytes),
            "deleted_at_ref_head": deleted_at_head,
            "kind": item_kind,
            "encoding": "utf-8",
            "start_line": eff_start,
            "end_line": min(eff_end, lines_total) if lines_total else 0,
            "lines_total": lines_total,
            "truncated": (
                eff_start > 1 or (lines_total > 0 and eff_end < lines_total)
            ),
            "content": selected_text,
            "preview": "\n".join(preview_lines),
            "attempts": attempts,
        }
        return _attach_tokens(body, content_text=selected_text)


def flow_preview(
    *,
    source: Path,
    path: str,
    sha: str | None = None,
    ref: str | None = None,
    source_repo: str | None = None,
    start_line: int = 1,
    max_lines: int = DEFAULT_PREVIEW_LINES,
    max_chars: int = DEFAULT_MAX_CHARS,
    thumb_size: int = DEFAULT_THUMB_SIZE,
    thumb_dir: Path | None = None,
    force_no_pillow: bool = False,
    expected_sha256: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict:
    """Return bounded deterministic preview (line-bounded text or base64 image preview)."""
    if start_line < 1:
        raise UnsafeInputError("start_line must be >= 1")
    if max_lines < 1 or max_lines > MAX_PREVIEW_LINES:
        raise UnsafeInputError(f"max_lines must be between 1 and {MAX_PREVIEW_LINES}")
    if max_chars < 64:
        raise UnsafeInputError("max_chars must be >= 64")
    if max_payload_bytes < 64:
        raise UnsafeInputError("max_payload_bytes must be >= 64")
    if thumb_dir is not None:
        validate_private_path(thumb_dir)

    safe_rel_path = validate_path(path)
    if content_index.is_secret_path(safe_rel_path):
        raise PermissionDeniedError(
            f"Refusing to preview secret path: {safe_rel_path}",
            details={"path": safe_rel_path},
        )
    repo_label = source_repo or source.stem or source.name

    with tempfile.TemporaryDirectory(prefix="flow-preview-") as tmp:
        tmp_path = Path(tmp)
        bare_repo, _source_type, clone_attempts = _open_bare_repo_with_retry(
            source,
            tmp_path,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        full_sha, resolved_ref, resolve_attempts = _resolve_commit_and_ref(
            bare_repo,
            sha=sha,
            ref=ref,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        blob_sha, raw_bytes, actual_sha256, read_attempts = _read_git_object(
            bare_repo,
            full_sha=full_sha,
            path=safe_rel_path,
            expected_sha256=expected_sha256,
            max_bytes=max_bytes,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        deleted_at_head = _is_deleted_at_ref(bare_repo, resolved_ref, safe_rel_path, timeout=timeout)
        attempts = max(clone_attempts, resolve_attempts, read_attempts)

        if _is_image_path_or_bytes(safe_rel_path, raw_bytes):
            ext = Path(safe_rel_path).suffix.lower()
            fmt = image_catalog.detect_format(raw_bytes, ext)
            mime = guess_mime(safe_rel_path, raw_bytes, detected_format=fmt)
            if fmt == "svg" or ext == ".svg":
                svg_meta = image_catalog.inspect_svg_inert(raw_bytes)
                width, height = svg_meta["width"], svg_meta["height"]
                inert = True
                script_detected = svg_meta["script_detected"]
                preview_bytes = raw_bytes
                preview_mode = "inert_svg"
                preview_mime = "image/svg+xml"
                preview_w, preview_h = width, height
            else:
                width, height = image_catalog.parse_image_dimensions(raw_bytes, ext)
                inert = False
                script_detected = False
                active_thumb_dir = thumb_dir if thumb_dir is not None else (tmp_path / "thumbs")
                thumb_info = image_catalog.generate_thumbnail(
                    raw_bytes,
                    ext,
                    actual_sha256,
                    active_thumb_dir,
                    max_size=(thumb_size, thumb_size),
                    force_no_pillow=force_no_pillow,
                )
                if thumb_info.get("generated") and thumb_info.get("path"):
                    thumb_bytes = Path(thumb_info["path"]).read_bytes()
                    orig_b64_len = ((len(raw_bytes) + 2) // 3) * 4
                    if len(thumb_bytes) <= len(raw_bytes) or orig_b64_len > max_payload_bytes:
                        preview_bytes = thumb_bytes
                        preview_mode = "thumbnail"
                        preview_mime = "image/png"
                        preview_w = thumb_info["width"]
                        preview_h = thumb_info["height"]
                    else:
                        preview_bytes = raw_bytes
                        preview_mode = "original"
                        preview_mime = mime
                        preview_w, preview_h = width, height
                else:
                    preview_bytes = raw_bytes
                    preview_mode = "original"
                    preview_mime = mime
                    preview_w, preview_h = width, height

            b64 = base64.b64encode(preview_bytes).decode("ascii")
            if len(b64.encode("ascii")) > max_payload_bytes:
                raise PayloadLimitExceededError(
                    f"Image preview base64 payload ({len(b64)} bytes) exceeds max_payload_bytes ({max_payload_bytes})",
                    attempts=attempts,
                    details={"payload_bytes": len(b64), "max_payload_bytes": max_payload_bytes},
                )
            preview_sha256 = hashlib.sha256(preview_bytes).hexdigest()
            preview_summary = (
                f"image/{fmt} {width}x{height} -> {preview_mode} {preview_w}x{preview_h} "
                f"({len(preview_bytes)} bytes base64-encoded)"
            )
            body = {
                "ok": True,
                "operation": "preview",
                "source_repo": repo_label,
                "ref": resolved_ref,
                "full_sha": full_sha,
                "path": safe_rel_path,
                "mime": mime,
                "sha256": actual_sha256,
                "blob_sha": blob_sha,
                "bytes": len(raw_bytes),
                "deleted_at_ref_head": deleted_at_head,
                "kind": "image",
                "encoding": "base64",
                "content_base64": b64,
                "preview": preview_summary,
                "preview_mode": preview_mode,
                "preview_mime": preview_mime,
                "preview_sha256": preview_sha256,
                "preview_bytes": len(preview_bytes),
                "width": width,
                "height": height,
                "preview_width": preview_w,
                "preview_height": preview_h,
                "inert": inert,
                "script_detected": script_detected,
                "attempts": attempts,
            }
            return _attach_tokens(body, content_text=b64)

        if content_index.is_binary_bytes(raw_bytes):
            b64 = base64.b64encode(raw_bytes).decode("ascii")
            if len(b64.encode("ascii")) > max_payload_bytes:
                raise PayloadLimitExceededError(
                    f"Binary preview payload ({len(b64)} bytes) exceeds max_payload_bytes ({max_payload_bytes})",
                    attempts=attempts,
                    details={"payload_bytes": len(b64), "max_payload_bytes": max_payload_bytes},
                )
            body = {
                "ok": True,
                "operation": "preview",
                "source_repo": repo_label,
                "ref": resolved_ref,
                "full_sha": full_sha,
                "path": safe_rel_path,
                "mime": "application/octet-stream",
                "sha256": actual_sha256,
                "blob_sha": blob_sha,
                "bytes": len(raw_bytes),
                "deleted_at_ref_head": deleted_at_head,
                "kind": "binary",
                "encoding": "base64",
                "content_base64": b64,
                "preview": f"binary ({len(raw_bytes)} bytes)",
                "attempts": attempts,
            }
            return _attach_tokens(body, content_text=b64)

        full_text = raw_bytes.decode("utf-8", "replace")
        if content_index.contains_secret_content(full_text):
            raise PermissionDeniedError(
                f"Refusing to preview blob containing secret pattern: {safe_rel_path}",
                attempts=attempts,
                details={"path": safe_rel_path},
            )
        all_lines = full_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if all_lines and all_lines[-1] == "":
            all_lines.pop()

        end_line = start_line + max_lines - 1
        recovered = content_index.recover_lines(
            bare_repo,
            full_sha,
            safe_rel_path,
            start_line=start_line,
            end_line=end_line,
        )
        preview_text = recovered["content"]
        truncated = recovered["end_line"] < len(all_lines) or recovered["start_line"] > 1
        effective_limit = min(max_chars, max_payload_bytes)
        if len(preview_text) > effective_limit:
            preview_text = preview_text[:effective_limit]
            truncated = True
        while len(preview_text.encode("utf-8")) > max_payload_bytes and preview_text:
            preview_text = preview_text[:-1]
            truncated = True

        lang_info = content_index.detect_language(safe_rel_path)
        item_kind = "markdown" if (lang_info and lang_info[1] in {"markdown", "mdx"}) else "code"
        body = {
            "ok": True,
            "operation": "preview",
            "source_repo": repo_label,
            "ref": resolved_ref,
            "full_sha": full_sha,
            "path": safe_rel_path,
            "mime": guess_mime(safe_rel_path, raw_bytes),
            "sha256": actual_sha256,
            "blob_sha": blob_sha,
            "bytes": len(raw_bytes),
            "deleted_at_ref_head": deleted_at_head,
            "kind": item_kind,
            "encoding": "utf-8",
            "start_line": recovered["start_line"],
            "end_line": min(recovered["end_line"], len(all_lines)) if all_lines else 0,
            "lines_total": len(all_lines),
            "truncated": truncated,
            "preview": preview_text,
            "attempts": attempts,
        }
        return _attach_tokens(body, content_text=preview_text)


def flow_recover(
    *,
    source: Path,
    path: str,
    sha: str | None = None,
    ref: str | None = None,
    source_repo: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    output: Path | None = None,
    overwrite: bool = False,
    expected_sha256: str | None = None,
    expected_blob_sha: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict:
    """Recover exact original historical evidence with hash/size verification and optional private file output."""
    if output is not None:
        validate_private_path(output)
        if output.exists() and not overwrite:
            raise ArchiveFlowError(
                f"Destination already exists: {output}",
                code="destination_exists",
                details={"output": str(output)},
            )

    fetched = flow_fetch(
        source=source,
        path=path,
        sha=sha,
        ref=ref,
        source_repo=source_repo,
        start_line=start_line,
        end_line=end_line,
        expected_sha256=expected_sha256,
        expected_blob_sha=expected_blob_sha,
        max_bytes=max_bytes,
        max_payload_bytes=max_payload_bytes,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )

    if output is not None:
        validate_private_path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        if fetched["encoding"] == "base64":
            out_bytes = base64.b64decode(fetched["content_base64"])
        elif start_line is None and end_line is None:
            with tempfile.TemporaryDirectory(prefix="flow-recover-raw-") as tmp:
                bare_repo, _, _ = _open_bare_repo_with_retry(
                    source,
                    Path(tmp),
                    timeout=timeout,
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                )
                _, out_bytes, _, _ = _read_git_object(
                    bare_repo,
                    full_sha=fetched["full_sha"],
                    path=fetched["path"],
                    expected_sha256=fetched["sha256"],
                    expected_blob_sha=fetched["blob_sha"],
                    max_bytes=max_bytes,
                    timeout=timeout,
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                )
        else:
            out_bytes = fetched["content"].encode("utf-8")
        if overwrite:
            tmp = output.with_suffix(output.suffix + ".tmp")
            try:
                tmp.write_bytes(out_bytes)
                tmp.replace(output)
            finally:
                tmp.unlink(missing_ok=True)
        else:
            with output.open("xb") as handle:
                handle.write(out_bytes)

    body = {k: v for k, v in fetched.items() if k != "tokens"}
    body["operation"] = "recover"
    body["recovered"] = True
    if output is not None:
        body["output"] = str(output)
        body["output_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    content_str = (
        body.get("content_base64")
        if body.get("encoding") == "base64"
        else body.get("content")
    )
    return _attach_tokens(body, content_text=content_str)


def _resolve_cli_source(args: argparse.Namespace) -> Path:
    if getattr(args, "source", None) is not None:
        return args.source
    if getattr(args, "release_tag", None) and getattr(args, "asset", None):
        info = resolve_release_asset(
            release_tag=args.release_tag,
            asset=args.asset,
            release_dir=getattr(args, "release_dir", None),
            manifest_path=getattr(args, "manifest", None),
            expected_sha256=getattr(args, "expected_bundle_sha256", None),
            max_bytes=getattr(args, "max_bundle_bytes", None),
            timeout=args.timeout,
            max_retries=args.max_retries,
        )
        return info["path"]
    raise UnsafeInputError("Provide --source or (--release-tag and --asset)")


def _add_common_source_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--source", type=Path, default=None, help="Path to bare repo, git workdir, or .bundle")
    p.add_argument("--source-repo", default=None, help="Logical source repository name")
    p.add_argument("--release-tag", default=None, help="Optional release tag for bundle resolution")
    p.add_argument("--asset", default=None, help="Optional release asset filename")
    p.add_argument("--release-dir", type=Path, default=None, help="Local directory of release/<tag>/<asset>")
    p.add_argument("--manifest", type=Path, default=None, help="Optional manifest JSON for asset SHA-256")
    p.add_argument("--expected-bundle-sha256", default=None, help="Expected SHA-256 for release bundle")
    p.add_argument("--max-bundle-bytes", type=int, default=None, help="Optional max size for release bundle")
    p.add_argument("--sha", default=None, help="Full commit SHA")
    p.add_argument("--ref", default=None, help="Git ref name (e.g. refs/heads/main)")
    p.add_argument("--path", required=True, help="Historical relative path")
    p.add_argument("--expected-sha256", default=None, help="Expected SHA-256 of target file bytes")
    p.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    p.add_argument("--max-payload-bytes", type=int, default=DEFAULT_MAX_PAYLOAD_BYTES)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    p.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search historical code, markdown, and images")
    p_search.add_argument("query")
    p_search.add_argument("--db", type=Path, default=None, help="Path to content_index SQLite DB")
    p_search.add_argument("--source", type=Path, default=None, help="Optional bare repo, workdir, or bundle")
    p_search.add_argument("--repo", default=None, help="Filter by source_repo name")
    p_search.add_argument("--ref", default=None, help="Filter by git ref or branch")
    p_search.add_argument("--ext", default=None, help="Filter by extension (e.g. .ts)")
    p_search.add_argument("--lang", default=None, help="Filter by language (e.g. typescript)")
    p_search.add_argument("--status", default=None, help="Filter by status (ref-head, deleted, commit)")
    p_search.add_argument("--kind", choices=("all", "code", "text", "image"), default="all")
    p_search.add_argument("--limit", type=int, default=DEFAULT_SEARCH_LIMIT)
    p_search.add_argument("--snippet-lines", type=int, default=DEFAULT_SNIPPET_LINES)
    p_search.add_argument("--or", dest="use_or", action="store_true")
    p_search.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    p_search.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)

    p_fetch = sub.add_parser("fetch", help="Fetch verified original blob/lines from Git history")
    _add_common_source_args(p_fetch)
    p_fetch.add_argument("--start-line", type=int, default=None)
    p_fetch.add_argument("--end-line", type=int, default=None)
    p_fetch.add_argument("--expected-blob-sha", default=None)

    p_preview = sub.add_parser("preview", help="Preview bounded lines or base64 image thumbnail")
    _add_common_source_args(p_preview)
    p_preview.add_argument("--start-line", type=int, default=1)
    p_preview.add_argument("--max-lines", type=int, default=DEFAULT_PREVIEW_LINES)
    p_preview.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    p_preview.add_argument("--thumb-size", type=int, default=DEFAULT_THUMB_SIZE)
    p_preview.add_argument("--thumb-dir", type=Path, default=None)
    p_preview.add_argument("--no-pillow", action="store_true")

    p_recover = sub.add_parser("recover", help="Recover verified original evidence (and optional private file)")
    _add_common_source_args(p_recover)
    p_recover.add_argument("--start-line", type=int, default=None)
    p_recover.add_argument("--end-line", type=int, default=None)
    p_recover.add_argument("--expected-blob-sha", default=None)
    p_recover.add_argument("--output", type=Path, default=None, help="Private output path (never inside site/)")
    p_recover.add_argument("--overwrite", action="store_true")

    return ap


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "search":
        result = flow_search(
            args.query,
            db_path=args.db,
            source=args.source,
            repo=args.repo,
            ref=args.ref,
            extension=args.ext,
            language=args.lang,
            status=args.status,
            kind=args.kind,
            limit=args.limit,
            snippet_lines=args.snippet_lines,
            match_all=not args.use_or,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )
    elif args.command == "fetch":
        source_path = _resolve_cli_source(args)
        result = flow_fetch(
            source=source_path,
            path=args.path,
            sha=args.sha,
            ref=args.ref,
            source_repo=args.source_repo,
            start_line=args.start_line,
            end_line=args.end_line,
            expected_sha256=args.expected_sha256,
            expected_blob_sha=args.expected_blob_sha,
            max_bytes=args.max_bytes,
            max_payload_bytes=args.max_payload_bytes,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )
    elif args.command == "preview":
        source_path = _resolve_cli_source(args)
        result = flow_preview(
            source=source_path,
            path=args.path,
            sha=args.sha,
            ref=args.ref,
            source_repo=args.source_repo,
            start_line=args.start_line,
            max_lines=args.max_lines,
            max_chars=args.max_chars,
            thumb_size=args.thumb_size,
            thumb_dir=args.thumb_dir,
            force_no_pillow=args.no_pillow,
            expected_sha256=args.expected_sha256,
            max_bytes=args.max_bytes,
            max_payload_bytes=args.max_payload_bytes,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )
    else:
        source_path = _resolve_cli_source(args)
        result = flow_recover(
            source=source_path,
            path=args.path,
            sha=args.sha,
            ref=args.ref,
            source_repo=args.source_repo,
            start_line=args.start_line,
            end_line=args.end_line,
            output=args.output,
            overwrite=args.overwrite,
            expected_sha256=args.expected_sha256,
            expected_blob_sha=args.expected_blob_sha,
            max_bytes=args.max_bytes,
            max_payload_bytes=args.max_payload_bytes,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ArchiveFlowError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        err = ArchiveFlowError(str(exc), code="invalid_input")
        print(json.dumps(err.to_dict(), ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
