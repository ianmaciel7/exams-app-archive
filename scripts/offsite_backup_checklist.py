#!/usr/bin/env python3
"""Automated verification checklist for offsite/independent backups outside GitHub.

This module validates manifest completeness across all 9 repositories, calculates
and verifies SHA-256 checksums, validates Git bundles, and implements a
block-by-default safety gate for repository deletion readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

ALL_9_REPOSITORIES = [
    "fcc-responsive-web-design",
    "ianmaciel7",
    "notes-app",
    "shadcn-template",
    "shadcn-firebase-template",
    "exams-app-old",
    "exams-app-antigo-2",
    "exams-app",
    "exams-app-archive",
]

# Active infrastructure or active projects: deletion is permanently prohibited
ACTIVE_OR_ARCHIVE_REPOS = {
    "exams-app",
    "notes-app",
    "exams-app-archive",
}

# Auxiliary profile/educational repositories: outside deletion scope
AUXILIARY_REPOS = {
    "fcc-responsive-web-design",
    "ianmaciel7",
}

# Legacy source repositories: candidates for potential future deletion
# only if all cumulative safety conditions are met
DEPRECATED_CANDIDATES = {
    "exams-app-old",
    "exams-app-antigo-2",
    "shadcn-template",
    "shadcn-firebase-template",
}


def normalize_repo_name(name: str) -> str:
    """Normalize repository name by stripping owner prefix and whitespace."""
    if not name:
        return ""
    cleaned = name.strip()
    if "/" in cleaned:
        cleaned = cleaned.split("/", 1)[1]
    return cleaned


def calculate_sha256(path: Path | str) -> str:
    """Calculate SHA-256 hex digest of a file in 1MB chunks."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    hasher = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def verify_checksum(path: Path | str, expected_sha256: str) -> bool:
    """Verify if a file's SHA-256 matches the expected digest (case-insensitive)."""
    if not expected_sha256:
        return False
    return calculate_sha256(path) == expected_sha256.lower().strip()


def verify_git_bundle(bundle_path: Path | str) -> Tuple[bool, str]:
    """Verify a Git bundle file using 'git bundle verify' and 'git bundle list-heads'.

    Returns (is_valid, message).
    """
    path = Path(bundle_path)
    if not path.is_file():
        return False, f"Bundle file does not exist: {path}"

    try:
        proc = subprocess.run(
            ["git", "bundle", "verify", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            return False, f"git bundle verify failed: {err}"

        heads_proc = subprocess.run(
            ["git", "bundle", "list-heads", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if heads_proc.returncode != 0:
            err = heads_proc.stderr.strip() or heads_proc.stdout.strip()
            return False, f"git bundle list-heads failed: {err}"

        heads = [line for line in heads_proc.stdout.splitlines() if line.strip()]
        if not heads:
            return False, "Bundle contains no references or heads."

        return True, f"Bundle verified successfully ({len(heads)} references)."
    except Exception as exc:
        return False, f"Error executing git bundle command: {exc}"


def load_manifest_assets(manifests_dir: Path | str) -> Dict[str, Any]:
    """Load and index all release manifests from the given manifests directory.

    Returns a dictionary containing:
    - manifest_files: list of parsed JSON manifest filenames
    - repositories: dict mapping normalized repo name to asset list and metadata
    - all_assets: flat list of all indexed assets with SHA-256 and byte sizes
    - sha256_index: mapping of asset filename to expected SHA-256
    """
    dir_path = Path(manifests_dir)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Manifests directory not found: {dir_path}")

    repo_assets: Dict[str, List[Dict[str, Any]]] = {
        repo: [] for repo in ALL_9_REPOSITORIES
    }
    manifest_files: List[str] = []
    all_assets: List[Dict[str, Any]] = []
    sha256_index: Dict[str, str] = {}

    for manifest_path in sorted(dir_path.glob("*.json")):
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            continue

        manifest_files.append(manifest_path.name)
        tag = data.get("tag", "")

        # Process 'assets' array (e.g. release-2026-11-23.json, release-2026-11-23-all-refs.json,
        # exams-app-complete-2026-11-23.json, notes-app-private-full.json)
        if "assets" in data and isinstance(data["assets"], list):
            for item in data["assets"]:
                asset_name = item.get("asset") or item.get("name")
                raw_repo = item.get("repository") or data.get("source") or ""
                repo_norm = normalize_repo_name(raw_repo)
                sha = item.get("sha256", "").lower().strip()
                size = item.get("size_bytes") if item.get("size_bytes") is not None else item.get("bytes")

                record = {
                    "asset": asset_name,
                    "repository": repo_norm or "unknown",
                    "manifest": manifest_path.name,
                    "tag": tag,
                    "sha256": sha,
                    "size_bytes": size,
                    "verified_in_manifest": item.get("verified", False),
                }
                all_assets.append(record)
                if asset_name and sha:
                    sha256_index[asset_name] = sha
                if repo_norm in repo_assets:
                    repo_assets[repo_norm].append(record)

        # Process 'sources' array (e.g. public-platform-metadata-2026-11-23.json)
        if "sources" in data and isinstance(data["sources"], list):
            for item in data["sources"]:
                asset_name = item.get("asset")
                raw_repo = item.get("repository", "")
                repo_norm = normalize_repo_name(raw_repo)
                sha = item.get("sha256", "").lower().strip()
                size = item.get("size_bytes") if item.get("size_bytes") is not None else item.get("bytes")

                record = {
                    "asset": asset_name,
                    "repository": repo_norm or "unknown",
                    "manifest": manifest_path.name,
                    "tag": tag,
                    "sha256": sha,
                    "size_bytes": size,
                    "verified_in_manifest": True,
                }
                all_assets.append(record)
                if asset_name and sha:
                    sha256_index[asset_name] = sha
                if repo_norm in repo_assets:
                    repo_assets[repo_norm].append(record)

    return {
        "manifest_files": manifest_files,
        "repositories": repo_assets,
        "all_assets": all_assets,
        "sha256_index": sha256_index,
    }


def check_manifest_completeness(manifests_dir: Path | str) -> Dict[str, Any]:
    """Check completeness of release manifests across all 9 repositories.

    Returns completeness audit summary including per-repo asset count and status.
    """
    manifest_data = load_manifest_assets(manifests_dir)
    repo_assets = manifest_data["repositories"]

    repo_status: Dict[str, Any] = {}
    total_assets = 0
    covered_repos = 0

    for repo in ALL_9_REPOSITORIES:
        assets = repo_assets.get(repo, [])
        total_assets += len(assets)

        if repo == "exams-app-archive":
            # The archive itself is the primary target repository containing manifests & scripts
            covered = True
            note = "Primary archive container repository (hosts manifests, inventory, tooling, reports)."
        else:
            covered = len(assets) > 0
            note = f"{len(assets)} backup assets indexed across manifests." if covered else "No assets found in manifests."

        if covered:
            covered_repos += 1

        repo_status[repo] = {
            "repository": repo,
            "covered_in_manifests": covered,
            "asset_count": len(assets),
            "assets": [a["asset"] for a in assets],
            "note": note,
        }

    all_covered = covered_repos == len(ALL_9_REPOSITORIES)

    return {
        "all_repositories_covered": all_covered,
        "total_repositories": len(ALL_9_REPOSITORIES),
        "covered_repositories_count": covered_repos,
        "total_manifest_assets_indexed": total_assets,
        "manifest_files_audited": manifest_data["manifest_files"],
        "repository_coverage": repo_status,
        "sha256_index": manifest_data["sha256_index"],
        "all_assets": manifest_data["all_assets"],
    }


def verify_directory_checksums(
    backup_dir: Path | str,
    sha256_index: Dict[str, str],
) -> Dict[str, Any]:
    """Verify files present in backup_dir against expected manifest SHA-256 hashes."""
    dir_path = Path(backup_dir)
    if not dir_path.is_dir():
        return {
            "backup_dir": str(dir_path),
            "directory_exists": False,
            "verified_count": 0,
            "failed_count": 0,
            "missing_count": len(sha256_index),
            "items": [],
        }

    items = []
    verified_count = 0
    failed_count = 0
    missing_count = 0

    for asset_name, expected_sha in sorted(sha256_index.items()):
        # Search directly or recursively for the asset
        candidates = list(dir_path.glob(f"**/{asset_name}"))
        if not candidates:
            missing_count += 1
            items.append({
                "asset": asset_name,
                "status": "MISSING",
                "expected_sha256": expected_sha,
                "calculated_sha256": None,
                "file_path": None,
            })
            continue

        target_file = candidates[0]
        actual_sha = calculate_sha256(target_file)
        if actual_sha == expected_sha.lower().strip():
            verified_count += 1
            status = "VERIFIED"
        else:
            failed_count += 1
            status = "HASH_MISMATCH"

        items.append({
            "asset": asset_name,
            "status": status,
            "expected_sha256": expected_sha,
            "calculated_sha256": actual_sha,
            "file_path": str(target_file),
        })

    return {
        "backup_dir": str(dir_path),
        "directory_exists": True,
        "verified_count": verified_count,
        "failed_count": failed_count,
        "missing_count": missing_count,
        "items": items,
    }


def evaluate_safety_gate(
    repo: str,
    external_backup_record: Optional[Dict[str, Any]] = None,
    manifest_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate deletion readiness safety gate for a given repository.

    Safety Gate Rule: Block by default.
    ready_for_deletion returns False unless:
    1. Repository is a deprecated candidate (never active infrastructure).
    2. Manifest completeness is confirmed for the repository.
    3. An independent external storage copy outside GitHub is explicitly confirmed.
    4. SHA-256 checksums are verified against expected manifest hashes.
    5. Independent restore testing is proven without GitHub access.
    6. Explicit owner deletion approval is recorded.
    """
    norm_repo = normalize_repo_name(repo)
    blockers: List[str] = []

    if norm_repo not in ALL_9_REPOSITORIES:
        return {
            "repository": norm_repo,
            "ready_for_deletion": False,
            "category": "unknown",
            "status": "BLOCKED",
            "blockers": [f"Repository '{norm_repo}' is not among the 9 inventoried repositories."],
            "criteria": {
                "is_deprecated_candidate": False,
                "manifest_coverage": False,
                "external_storage_confirmed": False,
                "checksums_verified": False,
                "independent_restore_tested": False,
                "explicit_owner_approval": False,
            },
        }

    # Condition 1: Active infrastructure and current projects can NEVER be deleted
    if norm_repo in ACTIVE_OR_ARCHIVE_REPOS:
        category = "active_infrastructure"
        blockers.append(
            f"Repository '{norm_repo}' is active infrastructure or an active project. "
            "Deletion is permanently blocked."
        )
        return {
            "repository": norm_repo,
            "ready_for_deletion": False,
            "category": category,
            "status": "BLOCKED",
            "blockers": blockers,
            "criteria": {
                "is_deprecated_candidate": False,
                "manifest_coverage": True,
                "external_storage_confirmed": False,
                "checksums_verified": False,
                "independent_restore_tested": False,
                "explicit_owner_approval": False,
            },
        }

    # Condition 2: Auxiliary profile/learning repositories are outside deletion scope
    if norm_repo in AUXILIARY_REPOS:
        category = "auxiliary"
        blockers.append(
            f"Repository '{norm_repo}' is an auxiliary public reference/profile repository "
            "and outside the deletion scope."
        )
        return {
            "repository": norm_repo,
            "ready_for_deletion": False,
            "category": category,
            "status": "BLOCKED",
            "blockers": blockers,
            "criteria": {
                "is_deprecated_candidate": False,
                "manifest_coverage": True,
                "external_storage_confirmed": False,
                "checksums_verified": False,
                "independent_restore_tested": False,
                "explicit_owner_approval": False,
            },
        }

    category = "deprecated_candidate"
    is_candidate = True

    # Condition 3: Manifest coverage
    manifest_covered = False
    if manifest_data:
        repo_assets = manifest_data.get("repositories", {}).get(norm_repo, [])
        manifest_covered = len(repo_assets) > 0
    else:
        manifest_covered = True

    if not manifest_covered:
        blockers.append(f"No backup assets found in manifests for repository '{norm_repo}'.")

    # Condition 4: Block-by-default on external backup record
    if not external_backup_record:
        blockers.append(
            "Block-by-default: External independent storage copy is NOT confirmed. "
            "A verified copy outside GitHub is mandatory prior to deletion."
        )
        return {
            "repository": norm_repo,
            "ready_for_deletion": False,
            "category": category,
            "status": "BLOCKED",
            "blockers": blockers,
            "criteria": {
                "is_deprecated_candidate": is_candidate,
                "manifest_coverage": manifest_covered,
                "external_storage_confirmed": False,
                "checksums_verified": False,
                "independent_restore_tested": False,
                "explicit_owner_approval": False,
            },
        }

    # Evaluate external storage confirmation details
    storage_loc = str(external_backup_record.get("storage_location", "")).strip()
    confirmed_date = str(external_backup_record.get("confirmed_date", "")).strip()
    checksums_verified = bool(external_backup_record.get("checksums_verified", False))
    independent_restore = bool(external_backup_record.get("independent_restore_tested", False))
    owner_approval = bool(external_backup_record.get("explicit_owner_approval", False))

    external_storage_ok = bool(storage_loc and "github.com" not in storage_loc.lower())
    if not storage_loc:
        blockers.append("External storage location is missing from external record.")
    elif "github.com" in storage_loc.lower():
        blockers.append("External storage location cannot be on GitHub; offsite copy must be independent.")

    if not confirmed_date:
        blockers.append("External backup confirmation date is missing.")

    if not checksums_verified:
        blockers.append("External backup SHA-256 checksums are not verified.")

    if not independent_restore:
        blockers.append(
            "Independent restore test is not proven. Code, media, and CI evidence "
            "must be restored independently without accessing original GitHub repositories."
        )

    if not owner_approval:
        blockers.append("Explicit repository deletion approval from repository owner is missing.")

    # Check specific verified assets if provided in external record
    verified_assets = external_backup_record.get("verified_assets")
    if isinstance(verified_assets, dict) and manifest_data:
        expected_index = manifest_data.get("sha256_index", {})
        for asset, recorded_hash in verified_assets.items():
            if asset in expected_index:
                if str(recorded_hash).lower().strip() != expected_index[asset]:
                    blockers.append(
                        f"Asset '{asset}' hash mismatch in external record: "
                        f"{recorded_hash} != {expected_index[asset]}"
                    )

    can_delete = (
        is_candidate
        and manifest_covered
        and external_storage_ok
        and checksums_verified
        and independent_restore
        and owner_approval
        and len(blockers) == 0
    )

    status = "ELIGIBLE_PENDING_MANUAL_EXECUTION" if can_delete else "BLOCKED"

    return {
        "repository": norm_repo,
        "ready_for_deletion": can_delete,
        "category": category,
        "status": status,
        "blockers": blockers,
        "criteria": {
            "is_deprecated_candidate": is_candidate,
            "manifest_coverage": manifest_covered,
            "external_storage_confirmed": external_storage_ok,
            "checksums_verified": checksums_verified,
            "independent_restore_tested": independent_restore,
            "explicit_owner_approval": owner_approval,
        },
    }


def evaluate_all_safety_gates(
    manifests_dir: Path | str,
    external_backup_record: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate safety gates across all 9 repositories."""
    manifest_data = load_manifest_assets(manifests_dir)
    results = {}
    blocked_count = 0
    eligible_count = 0

    for repo in ALL_9_REPOSITORIES:
        gate_res = evaluate_safety_gate(repo, external_backup_record, manifest_data)
        results[repo] = gate_res
        if gate_res["ready_for_deletion"]:
            eligible_count += 1
        else:
            blocked_count += 1

    return {
        "total_repositories": len(ALL_9_REPOSITORIES),
        "blocked_count": blocked_count,
        "eligible_count": eligible_count,
        "all_blocked_by_default": eligible_count == 0,
        "results": results,
    }


def run_full_checklist(
    manifests_dir: Path | str,
    backup_dir: Optional[Path | str] = None,
    external_record_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Execute complete offsite backup checklist auditing manifests, checksums, and safety gate."""
    completeness = check_manifest_completeness(manifests_dir)

    external_record = None
    if external_record_path:
        rec_path = Path(external_record_path)
        if rec_path.is_file():
            with rec_path.open("r", encoding="utf-8") as f:
                external_record = json.load(f)

    # Checksum verification if backup directory is specified
    checksum_results = None
    if backup_dir:
        checksum_results = verify_directory_checksums(backup_dir, completeness["sha256_index"])

    gates = evaluate_all_safety_gates(manifests_dir, external_record)

    return {
        "manifest_completeness": completeness,
        "checksum_verification": checksum_results,
        "safety_gates": gates,
    }


def format_text_report(checklist_result: Dict[str, Any]) -> str:
    """Format checklist result into human-readable plain text (Zero Emoji Policy compliant)."""
    completeness = checklist_result["manifest_completeness"]
    gates = checklist_result["safety_gates"]
    checksums = checklist_result.get("checksum_verification")

    lines = [
        "================================================================================",
        "OFFSITE BACKUP VERIFICATION CHECKLIST AND DELETION SAFETY GATE REPORT",
        "================================================================================",
        "",
        "1. MANIFEST COMPLETENESS ACROSS 9 REPOSITORIES:",
        f"   - Total Repositories Audited: {completeness['total_repositories']}",
        f"   - Covered in Manifests: {completeness['covered_repositories_count']}/{completeness['total_repositories']}",
        f"   - Total Manifest Assets Indexed: {completeness['total_manifest_assets_indexed']}",
        f"   - Manifest Files Audited: {', '.join(completeness['manifest_files_audited'])}",
        "",
        "   Repository Coverage Table:",
        "   " + "-" * 76,
        f"   {'Repository':<26} | {'Assets':<8} | {'Covered':<8} | {'Note'}",
        "   " + "-" * 76,
    ]

    for repo, item in completeness["repository_coverage"].items():
        cov_str = "YES" if item["covered_in_manifests"] else "NO"
        lines.append(f"   {repo:<26} | {item['asset_count']:<8} | {cov_str:<8} | {item['note']}")

    lines.extend([
        "   " + "-" * 76,
        "",
        "2. SAFETY GATE EVALUATION (BLOCK-BY-DEFAULT):",
        f"   - Total Repositories: {gates['total_repositories']}",
        f"   - Repositories Blocked from Deletion: {gates['blocked_count']}",
        f"   - Repositories Eligible for Deletion: {gates['eligible_count']}",
        f"   - Block-by-Default In Effect: {'YES' if gates['all_blocked_by_default'] else 'NO'}",
        "",
        "   Safety Gate Status per Repository:",
        "   " + "-" * 76,
        f"   {'Repository':<26} | {'Status':<10} | {'Category':<22} | {'Can Delete'}",
        "   " + "-" * 76,
    ])

    for repo, gate in gates["results"].items():
        can_del_str = "TRUE" if gate["ready_for_deletion"] else "FALSE"
        lines.append(f"   {repo:<26} | {gate['status']:<10} | {gate['category']:<22} | {can_del_str}")
        if gate["blockers"]:
            for b in gate["blockers"]:
                lines.append(f"     [BLOCKER] {b}")

    lines.append("   " + "-" * 76)

    if checksums:
        lines.extend([
            "",
            "3. SHA-256 CHECKSUM VERIFICATION:",
            f"   - Target Backup Directory: {checksums['backup_dir']}",
            f"   - Directory Found: {'YES' if checksums['directory_exists'] else 'NO'}",
            f"   - Verified Assets: {checksums['verified_count']}",
            f"   - Hash Mismatches: {checksums['failed_count']}",
            f"   - Missing Assets: {checksums['missing_count']}",
        ])

    lines.extend([
        "",
        "================================================================================",
        "END OF REPORT - ZERO EMOJI POLICY ENFORCED",
        "================================================================================",
    ])

    return "\n".join(lines)


def main() -> None:
    """CLI entrypoint for offsite backup checklist and deletion safety gate."""
    parser = argparse.ArgumentParser(
        description="Verify offsite backups, SHA-256 checksums, and evaluate deletion safety gate."
    )
    parser.add_argument(
        "--manifests-dir",
        type=str,
        default="manifests",
        help="Path to manifests directory (default: manifests).",
    )
    parser.add_argument(
        "--verify-checksums",
        nargs="?",
        const="",
        default=None,
        help="Verify SHA-256 checksums of backup files in the specified directory or current directory.",
    )
    parser.add_argument(
        "--backup-dir",
        type=str,
        default=None,
        help="Directory containing downloaded backup assets to verify.",
    )
    parser.add_argument(
        "--check-safety-gate",
        action="store_true",
        help="Run deletion readiness safety gate evaluation.",
    )
    parser.add_argument(
        "--external-record",
        type=str,
        default=None,
        help="Path to JSON file with external storage confirmation record.",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Evaluate safety gate for a specific repository.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format.",
    )

    args = parser.parse_args()

    # Determine backup dir if --verify-checksums was provided with an argument
    backup_target = args.backup_dir
    if args.verify_checksums is not None and args.verify_checksums != "":
        backup_target = args.verify_checksums

    checklist_result = run_full_checklist(
        manifests_dir=args.manifests_dir,
        backup_dir=backup_target,
        external_record_path=args.external_record,
    )

    # If specific repo requested
    if args.repo:
        norm_r = normalize_repo_name(args.repo)
        single_gate = checklist_result["safety_gates"]["results"].get(norm_r)
        if not single_gate:
            single_gate = evaluate_safety_gate(norm_r)
        if args.json:
            print(json.dumps(single_gate, indent=2, ensure_ascii=False))
        else:
            can_del = single_gate["ready_for_deletion"]
            status = "ALLOWED" if can_del else "BLOCKED"
            print(f"[{status}] Repository: {norm_r}")
            print(f"  Category: {single_gate['category']}")
            print(f"  Ready for deletion: {can_del}")
            for b in single_gate["blockers"]:
                print(f"  Blocker: {b}")
        sys.exit(0 if single_gate["ready_for_deletion"] else 1)

    if args.json:
        print(json.dumps(checklist_result, indent=2, ensure_ascii=False))
    else:
        report_text = format_text_report(checklist_result)
        print(report_text)

    # Return exit code: if safety gate was explicitly checked and any candidate failed or blocked
    if args.check_safety_gate and not args.json:
        gates = checklist_result["safety_gates"]
        print(f"\nSafety Gate Summary: {gates['blocked_count']} blocked, {gates['eligible_count']} eligible.")


if __name__ == "__main__":
    main()
