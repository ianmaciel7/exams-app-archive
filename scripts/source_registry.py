#!/usr/bin/env python3
"""Declarative source registry, policy validator, and dry-run path evaluator (#84).

Consolidates `config/public-catalog-sources.json` and archive manifests into a
schema-validated declarative registry with:
  - Stable `source_id` and `context_key` identities
  - Supported adapters: `github_api`, `local_fs`, `git_bundle`
  - Scopes / ACLs: `public` vs `authenticated_archive`
  - Pinned branches/revisions, licenses, freshness policies, and allowed formats
  - Strict precedence: authorization & exclusion ALWAYS precede inclusion
    (blocking credentials, `.env`, `node_modules`, `secrets`, private keys, etc.)
  - `dry_run(source_id)` returning detailed per-file inclusion/exclusion reasons
    without reading sensitive file contents or sending data to external servers.

Zero external dependencies (Python 3.12 stdlib only).
Zero Emoji Policy: NO Unicode emojis [\\U00010000-\\U0010ffff].
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any
from urllib.parse import urlsplit

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DEFAULT_REGISTRY_PATH = ROOT_DIR / "config" / "source_registry.json"
LEGACY_PUBLIC_POLICY_PATH = ROOT_DIR / "config" / "public-catalog-sources.json"

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")
HEX_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")
SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")

SUPPORTED_ADAPTERS = frozenset({"github_api", "local_fs", "git_bundle"})
SUPPORTED_SCOPES = frozenset({"public", "authenticated_archive"})
SUPPORTED_ORIGIN_STATUSES = frozenset(
    {"online", "historical_unavailable", "private_authenticated", "archived"}
)
SUPPORTED_FRESHNESS_MODES = frozenset(
    {"pinned_snapshot", "immutable_archive", "incremental_content_hash", "content_addressed_manifest"}
)
SUPPORTED_SOURCE_TYPES = frozenset(
    {
        "git_repository",
        "git_bundle",
        "documentation_corpus",
        "research_catalog",
        "visual_media_library",
        "source_code",
        "ci_metadata",
    }
)

# Mandatory security exclusions: evaluated before any source-specific include rules.
MANDATORY_EXCLUDE_DIR_PARTS = frozenset(
    {
        ".git",
        "node_modules",
        ".cache",
        "__pycache__",
        "secrets",
        ".ssh",
        ".aws",
        ".gnupg",
        ".kube",
        ".docker",
        "private-keys",
    }
)
MANDATORY_EXCLUDE_EXTENSIONS = frozenset(
    {
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
)
MANDATORY_EXCLUDE_FILENAMES = frozenset(
    {
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
        "service-account-key.json",
        "firebase-adminsdk.json",
        "google-services.json",
        "secrets.json",
        "secrets.yaml",
        "secrets.yml",
        "secrets.toml",
        "master.key",
    }
)
MANDATORY_SECRET_NAME_RE = re.compile(
    r"(?:^|/)(?:\.env(?:\.[^/]+)?|secrets?|credentials?|private[-_]?keys?)(?:/|$)|"
    r"(?:password|api[_-]?key|secret[_-]?key|credential|auth[_-]?token|private[_-]?key)[-_.]",
    re.IGNORECASE,
)


class RegistryValidationError(ValueError):
    """Raised when the declarative source registry fails schema or security validation."""


@dataclass(frozen=True)
class EvaluationDecision:
    """Result of evaluating a file or URL candidate against registry policies."""

    target: str
    included: bool
    reason_code: str
    reason_detail: str
    precedence_stage: str  # "authorization" | "global_security_exclude" | "source_exclude" | "format_filter" | "source_include" | "size_limit"
    source_id: str
    scope: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "included": self.included,
            "reason_code": self.reason_code,
            "reason_detail": self.reason_detail,
            "precedence_stage": self.precedence_stage,
            "source_id": self.source_id,
            "scope": self.scope,
        }


def _norm_posix(path_str: str) -> str:
    clean = path_str.replace("\\", "/").strip()
    while clean.startswith("./"):
        clean = clean[2:]
    return clean


def _glob_match(path_str: str, pattern: str) -> bool:
    """Deterministic glob matching supporting `**` segments in pure stdlib."""
    norm_path = _norm_posix(path_str)
    norm_pat = _norm_posix(pattern)
    if not norm_pat:
        return False
    if norm_pat == "**/*" or norm_pat == "**":
        return True
    if fnmatch.fnmatch(norm_path, norm_pat):
        return True
    # Support `dir/**` matching `dir/a/b.txt` and `**/x/**` matching `a/x/b`
    if norm_pat.endswith("/**"):
        prefix = norm_pat[:-3].strip("/")
        if not prefix or norm_path == prefix or norm_path.startswith(prefix + "/"):
            return True
    if norm_pat.startswith("**/"):
        sub = norm_pat[3:]
        if fnmatch.fnmatch(norm_path, sub):
            return True
        if "/" in norm_path:
            parts = norm_path.split("/")
            for idx in range(len(parts)):
                tail = "/".join(parts[idx:])
                if fnmatch.fnmatch(tail, sub):
                    return True
    if "/**/" in norm_pat:
        left, right = norm_pat.split("/**/", 1)
        if fnmatch.fnmatch(norm_path, f"{left}/{right}"):
            return True
        if norm_path.startswith(left + "/") and fnmatch.fnmatch(norm_path[len(left) + 1 :], f"**/{right}"):
            return True
    return False


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_registry_schema(registry: dict[str, Any]) -> list[str]:
    """Validate declarative registry structure, ACLs, adapters, and egress invariants.

    Returns a list of validation errors (empty if valid).
    """
    errors: list[str] = []
    if not isinstance(registry, dict):
        return ["Registry root must be a JSON object"]

    if registry.get("schema_version") != 1:
        errors.append("schema_version must be integer 1")

    if not isinstance(registry.get("registry_version"), str) or not registry["registry_version"].strip():
        errors.append("registry_version must be a non-empty string")

    policies = registry.get("global_policies")
    if not isinstance(policies, dict):
        errors.append("global_policies must be an object")
    else:
        if policies.get("external_third_party_upload") is not False:
            errors.append("global_policies.external_third_party_upload must be strictly false")
        if policies.get("egress_policy") != "offline-local-only":
            errors.append("global_policies.egress_policy must be 'offline-local-only'")
        if policies.get("exclusion_precedence") is not True:
            errors.append("global_policies.exclusion_precedence must be true")
        if policies.get("authorization_precedence") is not True:
            errors.append("global_policies.authorization_precedence must be true")
        for limit_key in ("max_text_bytes", "max_image_bytes", "max_doc_bytes"):
            val = policies.get(limit_key)
            if not isinstance(val, int) or val <= 0:
                errors.append(f"global_policies.{limit_key} must be a positive integer")

    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty array")
        return errors

    seen_ids: set[str] = set()
    seen_context_keys: set[str] = set()

    for idx, src in enumerate(sources):
        if not isinstance(src, dict):
            errors.append(f"sources[{idx}] must be an object")
            continue
        sid = src.get("source_id", "")
        if not isinstance(sid, str) or not SOURCE_ID_RE.fullmatch(sid):
            errors.append(f"sources[{idx}].source_id invalid: {sid!r}")
        elif sid in seen_ids:
            errors.append(f"Duplicate source_id: {sid}")
        else:
            seen_ids.add(sid)

        ckey = src.get("context_key", "")
        if not isinstance(ckey, str) or "::" not in ckey:
            errors.append(f"{sid}: invalid context_key {ckey!r}")
        elif ckey in seen_context_keys:
            errors.append(f"Duplicate context_key: {ckey}")
        else:
            seen_context_keys.add(ckey)

        adapter = src.get("adapter")
        if adapter not in SUPPORTED_ADAPTERS:
            errors.append(f"{sid}: unsupported adapter {adapter!r}")

        scope = src.get("scope")
        if scope not in SUPPORTED_SCOPES:
            errors.append(f"{sid}: unsupported scope {scope!r}")

        auth_req = src.get("authorization_required")
        if not isinstance(auth_req, bool):
            errors.append(f"{sid}: authorization_required must be boolean")
        elif scope == "authenticated_archive" and not auth_req:
            errors.append(f"{sid}: authenticated_archive scope requires authorization_required=true")

        source_type = src.get("source_type")
        if source_type not in SUPPORTED_SOURCE_TYPES:
            errors.append(f"{sid}: unsupported source_type {source_type!r}")

        origin_status = src.get("origin_status")
        if origin_status not in SUPPORTED_ORIGIN_STATUSES:
            errors.append(f"{sid}: unsupported origin_status {origin_status!r}")

        if not isinstance(src.get("license"), str) or not src["license"].strip():
            errors.append(f"{sid}: license must be a non-empty string")

        freshness = src.get("freshness_policy")
        if not isinstance(freshness, dict) or freshness.get("mode") not in SUPPORTED_FRESHNESS_MODES:
            errors.append(f"{sid}: invalid freshness_policy")

        pinned_revs = src.get("pinned_revisions", {})
        if not isinstance(pinned_revs, dict):
            errors.append(f"{sid}: pinned_revisions must be an object")
        else:
            for ref_name, sha in pinned_revs.items():
                if not isinstance(sha, str) or not HEX_SHA_RE.fullmatch(sha):
                    errors.append(f"{sid}: invalid pinned SHA for {ref_name}: {sha!r}")

        if adapter == "local_fs" and not isinstance(src.get("root_path"), str):
            errors.append(f"{sid}: local_fs adapter requires root_path")
        if adapter in {"github_api", "git_bundle"} and not isinstance(src.get("repo"), str):
            errors.append(f"{sid}: {adapter} adapter requires repo")

        # Prevent private Notes repositories from ever being marked as public scope.
        repo_name = str(src.get("repo", "")).lower()
        if "notes" in repo_name and scope == "public":
            errors.append(f"{sid}: private Notes repository cannot use public scope")

        for list_field in (
            "pinned_refs",
            "formats",
            "include_paths",
            "exclude_paths",
            "include_extensions",
            "exclude_extensions",
            "include_urls",
            "exclude_urls",
        ):
            if list_field in src and not isinstance(src[list_field], list):
                errors.append(f"{sid}: {list_field} must be a list")

    return errors


def load_registry(
    path: Path | None = None,
    *,
    fallback_legacy_path: Path | None = None,
) -> dict[str, Any]:
    """Load and validate the declarative source registry (or synthesize from legacy config)."""
    target = path or DEFAULT_REGISTRY_PATH
    if target.is_file():
        data = json.loads(target.read_text(encoding="utf-8"))
        errors = validate_registry_schema(data)
        if errors:
            raise RegistryValidationError("; ".join(errors))
        return data

    legacy = fallback_legacy_path or LEGACY_PUBLIC_POLICY_PATH
    if legacy.is_file():
        legacy_data = json.loads(legacy.read_text(encoding="utf-8"))
        synthesized = synthesize_from_legacy_policy(legacy_data)
        errors = validate_registry_schema(synthesized)
        if errors:
            raise RegistryValidationError("; ".join(errors))
        return synthesized

    raise FileNotFoundError(f"Registry file not found: {target}")


def synthesize_from_legacy_policy(legacy_policy: dict[str, Any]) -> dict[str, Any]:
    """Build a valid declarative registry structure from legacy `public-catalog-sources.json`."""
    sources: list[dict[str, Any]] = []
    for repo in legacy_policy.get("repositories", []):
        slug = repo.split("/")[-1]
        sources.append(
            {
                "source_id": f"repo.{slug}",
                "context_key": f"public::engenharia::repo.{slug}",
                "title": f"{repo} (Public Repository)",
                "source_type": "git_repository",
                "adapter": "github_api",
                "scope": "public",
                "authorization_required": False,
                "origin_status": "online",
                "license": "proprietary-owner-public",
                "repo": repo,
                "pinned_refs": ["refs/heads/main"],
                "pinned_revisions": {},
                "preserve_history": True,
                "freshness_policy": {"mode": "pinned_snapshot", "ttl_hours": 168},
                "formats": [".ts", ".tsx", ".js", ".md", ".json"],
                "include_paths": ["**/*"],
                "exclude_paths": ["**/.env*", "**/node_modules/**", "**/secrets/**"],
                "include_extensions": [".ts", ".tsx", ".js", ".jsx", ".css", ".md", ".json", ".png", ".svg"],
                "exclude_extensions": [".pem", ".key", ".env"],
                "include_urls": [f"https://github.com/{repo}"],
                "exclude_urls": [],
            }
        )
    for repo in legacy_policy.get("historical_unavailable", []):
        slug = repo.split("/")[-1]
        sources.append(
            {
                "source_id": f"bundle.{slug}",
                "context_key": f"authenticated-archive::historico::bundle.{slug}",
                "title": f"{repo} (Historical Bundle)",
                "source_type": "git_bundle",
                "adapter": "git_bundle",
                "scope": "authenticated_archive",
                "authorization_required": True,
                "origin_status": "historical_unavailable",
                "license": "proprietary-owner-archive",
                "repo": repo,
                "pinned_refs": ["refs/heads/main"],
                "pinned_revisions": {},
                "preserve_history": True,
                "freshness_policy": {"mode": "immutable_archive", "ttl_hours": None},
                "formats": [".ts", ".tsx", ".js", ".md", ".json"],
                "include_paths": ["**/*"],
                "exclude_paths": ["**/.env*", "**/node_modules/**", "**/secrets/**"],
                "include_extensions": [".ts", ".tsx", ".js", ".jsx", ".css", ".md", ".json", ".png", ".svg"],
                "exclude_extensions": [".pem", ".key", ".env"],
                "include_urls": [],
                "exclude_urls": [],
            }
        )
    return {
        "schema_version": 1,
        "registry_version": "1.0.0-legacy",
        "global_policies": {
            "egress_policy": "offline-local-only",
            "external_third_party_upload": False,
            "exclusion_precedence": True,
            "authorization_precedence": True,
            "preserve_historical_revisions": True,
            "max_text_bytes": 262144,
            "max_image_bytes": 1572864,
            "max_doc_bytes": 8388608,
            "default_exclude_patterns": ["**/.git/**", "**/node_modules/**", "**/.env*", "**/secrets/**"],
            "default_exclude_urls": ["http://*", "ftp://*", "file://*"],
        },
        "sources": sources,
    }


def export_legacy_public_policy(registry: dict[str, Any]) -> dict[str, Any]:
    """Project registry back to `public-catalog-sources.json` format for backward compatibility."""
    repos = []
    unavailable = []
    for src in registry.get("sources", []):
        repo = src.get("repo")
        if not repo:
            continue
        if src.get("scope") == "public" and src.get("origin_status") == "online":
            repos.append(repo)
        elif src.get("origin_status") == "historical_unavailable":
            unavailable.append(repo)
    return {
        "repositories": repos,
        "historical_unavailable": unavailable,
        "historical_access": registry.get("compatibility", {}).get(
            "historical_access",
            "Restore authorized central archive bundles locally; do not publish historical private metadata.",
        ),
    }


def compute_registry_hash(registry: dict[str, Any]) -> str:
    """Deterministic SHA-256 fingerprint of registry policies and source definitions."""
    return hashlib.sha256(_canonical_json(registry).encode("utf-8")).hexdigest()


def get_source(registry: dict[str, Any], source_id: str) -> dict[str, Any]:
    for src in registry.get("sources", []):
        if src.get("source_id") == source_id:
            return src
    raise KeyError(f"Unknown source_id: {source_id}")


def evaluate_file_policy(
    source: dict[str, Any],
    rel_path: str,
    *,
    global_policies: dict[str, Any] | None = None,
    authorized: bool = False,
    byte_size: int | None = None,
) -> EvaluationDecision:
    """Evaluate a candidate file path strictly before reading its contents.

    Precedence order (strict):
      1. Authorization check (`authenticated_archive` requires explicit `authorized=True`).
      2. Global mandatory security exclusions (`.env`, `secrets`, `credentials`, `.pem`, `node_modules`, `.git`).
      3. Global default exclude globs.
      4. Source-level `exclude_paths` and `exclude_extensions`.
      5. Extension / format allowlist (`include_extensions` / `allowed_formats`).
      6. Size limit check (when `byte_size` provided).
      7. Source-level `include_paths`.
    """
    sid = source["source_id"]
    scope = source["scope"]
    policies = global_policies or {}
    norm_path = _norm_posix(rel_path)

    # 1. Authorization gate
    if source.get("authorization_required") and not authorized:
        return EvaluationDecision(
            target=norm_path,
            included=False,
            reason_code="authorization_required",
            reason_detail=f"Source '{sid}' has scope '{scope}' and requires explicit authorization.",
            precedence_stage="authorization",
            source_id=sid,
            scope=scope,
        )

    # Check control characters / path traversal
    posix = PurePosixPath(norm_path)
    if not norm_path or norm_path.startswith("/") or ".." in posix.parts or any(ord(ch) < 32 for ch in norm_path):
        return EvaluationDecision(
            target=norm_path,
            included=False,
            reason_code="unsafe_path",
            reason_detail="Path rejected due to traversal, absolute prefix, or control characters.",
            precedence_stage="global_security_exclude",
            source_id=sid,
            scope=scope,
        )

    # 2. Mandatory security exclusions (precedes any include rule)
    lower_parts = {p.lower() for p in posix.parts[:-1]}
    blocked_dirs = lower_parts & MANDATORY_EXCLUDE_DIR_PARTS
    if blocked_dirs:
        return EvaluationDecision(
            target=norm_path,
            included=False,
            reason_code="mandatory_dir_excluded",
            reason_detail=f"Blocked mandatory excluded directory part: {sorted(blocked_dirs)[0]}",
            precedence_stage="global_security_exclude",
            source_id=sid,
            scope=scope,
        )

    fname_lower = posix.name.lower()
    ext_lower = posix.suffix.lower()
    if fname_lower in MANDATORY_EXCLUDE_FILENAMES or fname_lower.startswith(".env"):
        return EvaluationDecision(
            target=norm_path,
            included=False,
            reason_code="mandatory_secret_filename",
            reason_detail=f"Blocked sensitive filename '{posix.name}' by global security policy.",
            precedence_stage="global_security_exclude",
            source_id=sid,
            scope=scope,
        )
    if ext_lower in MANDATORY_EXCLUDE_EXTENSIONS:
        return EvaluationDecision(
            target=norm_path,
            included=False,
            reason_code="mandatory_secret_extension",
            reason_detail=f"Blocked sensitive extension '{ext_lower}' by global security policy.",
            precedence_stage="global_security_exclude",
            source_id=sid,
            scope=scope,
        )
    if MANDATORY_SECRET_NAME_RE.search(norm_path):
        return EvaluationDecision(
            target=norm_path,
            included=False,
            reason_code="mandatory_secret_pattern",
            reason_detail="Path matched mandatory credential/secret naming rule.",
            precedence_stage="global_security_exclude",
            source_id=sid,
            scope=scope,
        )

    # 3. Global default exclude patterns
    for pat in policies.get("default_exclude_patterns", []):
        if _glob_match(norm_path, pat):
            return EvaluationDecision(
                target=norm_path,
                included=False,
                reason_code="global_exclude_pattern",
                reason_detail=f"Matched global_policies.default_exclude_patterns ({pat}).",
                precedence_stage="global_security_exclude",
                source_id=sid,
                scope=scope,
            )

    # 4. Source-level exclusions (precede source includes)
    for pat in source.get("exclude_paths", []):
        if _glob_match(norm_path, pat):
            return EvaluationDecision(
                target=norm_path,
                included=False,
                reason_code="source_exclude_path",
                reason_detail=f"Matched source exclude_paths rule ({pat}).",
                precedence_stage="source_exclude",
                source_id=sid,
                scope=scope,
            )

    excluded_exts = {e.lower() for e in source.get("exclude_extensions", [])}
    if ext_lower and ext_lower in excluded_exts:
        return EvaluationDecision(
            target=norm_path,
            included=False,
            reason_code="source_exclude_extension",
            reason_detail=f"Extension '{ext_lower}' is explicitly listed in source exclude_extensions.",
            precedence_stage="source_exclude",
            source_id=sid,
            scope=scope,
        )

    # 5. Extension / format filter
    allowed_exts = {e.lower() for e in source.get("include_extensions", [])}
    global_allowed = {e.lower() for e in policies.get("allowed_formats", [])}
    if allowed_exts and ext_lower not in allowed_exts:
        return EvaluationDecision(
            target=norm_path,
            included=False,
            reason_code="extension_not_allowed",
            reason_detail=f"Extension '{ext_lower or '<none>'}' not in source include_extensions.",
            precedence_stage="format_filter",
            source_id=sid,
            scope=scope,
        )
    if global_allowed and ext_lower and ext_lower not in global_allowed:
        return EvaluationDecision(
            target=norm_path,
            included=False,
            reason_code="global_format_not_allowed",
            reason_detail=f"Extension '{ext_lower}' not in global_policies.allowed_formats.",
            precedence_stage="format_filter",
            source_id=sid,
            scope=scope,
        )

    # 6. Size guard (before reading file body)
    if byte_size is not None:
        is_img = ext_lower in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".mp4"}
        max_bytes = (
            policies.get("max_image_bytes", 1572864)
            if is_img
            else policies.get("max_doc_bytes", 8388608)
            if ext_lower == ".pdf"
            else policies.get("max_text_bytes", 262144)
        )
        if byte_size > max_bytes:
            return EvaluationDecision(
                target=norm_path,
                included=False,
                reason_code="exceeds_max_bytes",
                reason_detail=f"File size {byte_size} bytes exceeds limit {max_bytes} bytes.",
                precedence_stage="size_limit",
                source_id=sid,
                scope=scope,
            )

    # 7. Source-level include_paths
    include_paths = source.get("include_paths", [])
    if include_paths:
        for pat in include_paths:
            if _glob_match(norm_path, pat):
                return EvaluationDecision(
                    target=norm_path,
                    included=True,
                    reason_code="included_by_rule",
                    reason_detail=f"Matched include_paths rule ({pat}) after passing authorization and exclusion checks.",
                    precedence_stage="source_include",
                    source_id=sid,
                    scope=scope,
                )
        return EvaluationDecision(
            target=norm_path,
            included=False,
            reason_code="not_in_include_paths",
            reason_detail="Did not match any include_paths rule.",
            precedence_stage="source_include",
            source_id=sid,
            scope=scope,
        )

    return EvaluationDecision(
        target=norm_path,
        included=True,
        reason_code="included_default",
        reason_detail="Passed authorization, exclusions, and format checks.",
        precedence_stage="source_include",
        source_id=sid,
        scope=scope,
    )


def evaluate_url_policy(
    source: dict[str, Any],
    url: str,
    *,
    global_policies: dict[str, Any] | None = None,
    authorized: bool = False,
) -> EvaluationDecision:
    """Evaluate an external reference URL against exclusion-precedent rules."""
    sid = source["source_id"]
    scope = source["scope"]
    policies = global_policies or {}
    if source.get("authorization_required") and not authorized:
        return EvaluationDecision(
            target=url,
            included=False,
            reason_code="authorization_required",
            reason_detail=f"Source '{sid}' requires authorization.",
            precedence_stage="authorization",
            source_id=sid,
            scope=scope,
        )

    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None:
        return EvaluationDecision(
            target=url,
            included=False,
            reason_code="insecure_or_invalid_url",
            reason_detail="Only HTTPS URLs with a valid hostname and no embedded credentials are allowed.",
            precedence_stage="global_security_exclude",
            source_id=sid,
            scope=scope,
        )

    for pat in list(policies.get("default_exclude_urls", [])) + list(source.get("exclude_urls", [])):
        if fnmatch.fnmatch(url, pat):
            return EvaluationDecision(
                target=url,
                included=False,
                reason_code="url_excluded",
                reason_detail=f"URL matched exclusion pattern ({pat}).",
                precedence_stage="source_exclude",
                source_id=sid,
                scope=scope,
            )

    include_urls = source.get("include_urls", [])
    if include_urls:
        for pat in include_urls:
            if fnmatch.fnmatch(url, pat):
                return EvaluationDecision(
                    target=url,
                    included=True,
                    reason_code="url_included",
                    reason_detail=f"URL matched include_urls rule ({pat}).",
                    precedence_stage="source_include",
                    source_id=sid,
                    scope=scope,
                )
        return EvaluationDecision(
            target=url,
            included=False,
            reason_code="url_not_in_include_list",
            reason_detail="URL did not match any include_urls pattern.",
            precedence_stage="source_include",
            source_id=sid,
            scope=scope,
        )

    return EvaluationDecision(
        target=url,
        included=True,
        reason_code="url_included_default",
        reason_detail="HTTPS URL passed exclusion filters.",
        precedence_stage="source_include",
        source_id=sid,
        scope=scope,
    )


def _discover_local_candidates(root_dir: Path, source: dict[str, Any]) -> list[tuple[str, int | None]]:
    rel_root = source.get("root_path", ".")
    base = (root_dir / rel_root).resolve()
    if not base.exists():
        return []
    items: list[tuple[str, int | None]] = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(base).as_posix()
        items.append((rel, p.stat().st_size))
    return items


def dry_run(
    source_id: str,
    *,
    registry: dict[str, Any] | None = None,
    registry_path: Path | None = None,
    workspace_root: Path | None = None,
    candidates: list[str | tuple[str, int | None]] | None = None,
    authorized: bool = False,
) -> dict[str, Any]:
    """Execute a dry-run policy evaluation for `source_id` without reading file contents or calling network.

    Returns detailed per-file inclusion/exclusion decisions, counts by reason_code,
    pinned revisions, freshness state, and policy hash.
    """
    reg = registry if registry is not None else load_registry(registry_path)
    errors = validate_registry_schema(reg)
    if errors:
        raise RegistryValidationError("; ".join(errors))

    source = get_source(reg, source_id)
    policies = reg.get("global_policies", {})
    root_dir = workspace_root or ROOT_DIR

    normalized_candidates: list[tuple[str, int | None]] = []
    if candidates is not None:
        for item in candidates:
            if isinstance(item, tuple):
                normalized_candidates.append((item[0], item[1]))
            else:
                normalized_candidates.append((item, None))
    elif source["adapter"] == "local_fs":
        normalized_candidates = _discover_local_candidates(root_dir, source)
    else:
        # For remote github_api or offline git_bundle without local checkout, inspect manifest/pinned refs if available
        manifest_ref = source.get("manifest_ref")
        if manifest_ref and (root_dir / manifest_ref).is_file():
            normalized_candidates.append((manifest_ref, (root_dir / manifest_ref).stat().st_size))

    decisions: list[dict[str, Any]] = []
    included_count = 0
    excluded_count = 0
    reason_counts: dict[str, int] = {}

    for rel_path, byte_size in normalized_candidates:
        decision = evaluate_file_policy(
            source,
            rel_path,
            global_policies=policies,
            authorized=authorized,
            byte_size=byte_size,
        )
        decisions.append(decision.to_dict())
        if decision.included:
            included_count += 1
        else:
            excluded_count += 1
        reason_counts[decision.reason_code] = reason_counts.get(decision.reason_code, 0) + 1

    freshness = refresh_status(source)
    return {
        "schema_version": 1,
        "registry_version": reg.get("registry_version"),
        "registry_hash": compute_registry_hash(reg),
        "source_id": source_id,
        "context_key": source["context_key"],
        "adapter": source["adapter"],
        "scope": source["scope"],
        "authorized": authorized,
        "origin_status": source["origin_status"],
        "pinned_revisions": source.get("pinned_revisions", {}),
        "freshness": freshness,
        "egress_policy": policies.get("egress_policy"),
        "summary": {
            "total_evaluated": len(decisions),
            "included": included_count,
            "excluded": excluded_count,
            "reason_counts": dict(sorted(reason_counts.items())),
        },
        "decisions": decisions,
    }


def refresh_status(source: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Compute declarative refresh/freshness status for a registered source."""
    policy = source.get("freshness_policy", {})
    mode = policy.get("mode", "pinned_snapshot")
    ttl = policy.get("ttl_hours")
    last_verified = policy.get("last_verified_at")
    ref_now = now or datetime.now(timezone.utc)

    stale = False
    age_hours: float | None = None
    if isinstance(last_verified, str) and last_verified:
        try:
            dt = datetime.fromisoformat(last_verified)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_hours = round((ref_now - dt).total_seconds() / 3600.0, 2)
            if isinstance(ttl, int) and ttl > 0 and age_hours > ttl:
                stale = True
        except ValueError:
            age_hours = None

    if mode == "immutable_archive":
        state = "immutable-pinned"
        stale = False
    elif source.get("origin_status") == "historical_unavailable":
        state = "origin-unavailable-bundle-only"
    elif stale:
        state = "refresh-due"
    else:
        state = "fresh"

    return {
        "mode": mode,
        "ttl_hours": ttl,
        "last_verified_at": last_verified,
        "age_hours": age_hours,
        "stale": stale,
        "state": state,
    }


def inspect_coverage(
    *,
    registry: dict[str, Any] | None = None,
    registry_path: Path | None = None,
    workspace_root: Path | None = None,
    authorized_scopes: set[str] | None = None,
) -> dict[str, Any]:
    """Produce a coverage and refresh inspection report across all registered sources."""
    reg = registry if registry is not None else load_registry(registry_path)
    errors = validate_registry_schema(reg)
    if errors:
        raise RegistryValidationError("; ".join(errors))

    auth_scopes = authorized_scopes or {"public"}
    root_dir = workspace_root or ROOT_DIR
    rows: list[dict[str, Any]] = []
    by_adapter: dict[str, int] = {}
    by_scope: dict[str, int] = {}

    for src in reg["sources"]:
        sid = src["source_id"]
        adapter = src["adapter"]
        scope = src["scope"]
        by_adapter[adapter] = by_adapter.get(adapter, 0) + 1
        by_scope[scope] = by_scope.get(scope, 0) + 1
        is_auth = scope in auth_scopes or not src.get("authorization_required", False)
        run = dry_run(sid, registry=reg, workspace_root=root_dir, authorized=is_auth)
        rows.append(
            {
                "source_id": sid,
                "context_key": src["context_key"],
                "adapter": adapter,
                "scope": scope,
                "origin_status": src["origin_status"],
                "license": src["license"],
                "pinned_refs_count": len(src.get("pinned_refs", [])),
                "pinned_revisions_count": len(src.get("pinned_revisions", {})),
                "freshness": run["freshness"],
                "evaluated_files": run["summary"]["total_evaluated"],
                "included_files": run["summary"]["included"],
                "excluded_files": run["summary"]["excluded"],
            }
        )

    return {
        "schema_version": 1,
        "registry_version": reg.get("registry_version"),
        "registry_hash": compute_registry_hash(reg),
        "egress_policy": reg["global_policies"]["egress_policy"],
        "total_sources": len(rows),
        "by_adapter": dict(sorted(by_adapter.items())),
        "by_scope": dict(sorted(by_scope.items())),
        "sources": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="Validate registry schema and security invariants")
    cov = sub.add_parser("coverage", help="Inspect coverage and refresh status across sources")
    cov.add_argument("--include-authenticated", action="store_true")

    dr = sub.add_parser("dry-run", help="Run policy inclusion/exclusion dry-run for a source")
    dr.add_argument("source_id")
    dr.add_argument("--authorized", action="store_true")
    dr.add_argument("--candidate", action="append", default=[])

    args = parser.parse_args(argv)
    try:
        reg = load_registry(args.registry)
    except (RegistryValidationError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    if args.command == "validate":
        print(
            json.dumps(
                {
                    "ok": True,
                    "registry_version": reg["registry_version"],
                    "registry_hash": compute_registry_hash(reg),
                    "sources": len(reg["sources"]),
                    "egress_policy": reg["global_policies"]["egress_policy"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "coverage":
        scopes = {"public", "authenticated_archive"} if args.include_authenticated else {"public"}
        report = inspect_coverage(registry=reg, authorized_scopes=scopes)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.command == "dry-run":
        cands = list(args.candidate) if args.candidate else None
        report = dry_run(args.source_id, registry=reg, candidates=cands, authorized=args.authorized)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
