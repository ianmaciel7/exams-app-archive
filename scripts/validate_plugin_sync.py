#!/usr/bin/env python3
"""Automated plugin synchronization verification and multi-client smoke test runner.

Validates synchronization status between GitHub canonical package
(main:plugins/exams-archive-native/ v0.6.0) and ChatGPT Personal Plugin Creator release
(pluginrel_6b04c63bd96c8191bda2c535f2b62e1b).
Verifies byte-for-byte or semantic JSON equivalence across all 19 canonical package files
as recorded in .sync-state.json.
Runs automated smoke test suite for CLI routing (archive_query.py commands:
search, images, stats, ast, graph, context, secrets-check).

Zero Emoji Policy strictly enforced.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

CANONICAL_SOURCE = "ianmaciel7/exams-app-archive@main:plugins/exams-archive-native/"
EXPECTED_PLUGIN_ID = "plugins_6b04aaa9fd848191a24525011f76e2bb"
EXPECTED_VERSION = "0.6.0"
EXPECTED_RELEASE_ID = "pluginrel_6b04c63bd96c8191bda2c535f2b62e1b"
EXPECTED_SYNC_STATUS = "verified-synced"

CANONICAL_FILES: tuple[str, ...] = (
    "agents/openai.yaml",
    ".antigravity-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    "plugin.json",
    "README.md",
    "scripts/archive_query.py",
    "skills/archive-research/references/github-connected.md",
    "skills/archive-research/references/private-fts5.md",
    "skills/archive-research/SKILL.md",
    "skills/archive-search/SKILL.md",
    "skills/sync-bridge/SKILL.md",
    "skills/ui-fidelity/references/chat-preview-contract.md",
    "skills/ui-fidelity/references/source-map.md",
    "skills/ui-fidelity/references/visual-qa.md",
    "skills/ui-fidelity/references/visual-source-catalog.md",
    "skills/ui-fidelity/SKILL.md",
    "skills/ui-motion/references/motion-taxonomy.md",
    "skills/ui-motion/SKILL.md",
)

CLI_ROUTING_COMMANDS: tuple[str, ...] = (
    "search",
    "images",
    "stats",
    "ast",
    "graph",
    "context",
    "secrets-check",
)


def verify_sync_state(sync_state_path: Path) -> dict[str, Any]:
    """Validate .sync-state.json schema, versions, and release IDs."""
    if not sync_state_path.is_file():
        raise FileNotFoundError(f"Sync state file not found: {sync_state_path}")

    data = json.loads(sync_state_path.read_text(encoding="utf-8"))

    schema = data.get("schema")
    if schema != 2:
        raise ValueError(f"Unexpected schema version: {schema} (expected 2)")

    if data.get("source_of_truth") != CANONICAL_SOURCE:
        raise ValueError(
            f"source_of_truth mismatch: {data.get('source_of_truth')} != {CANONICAL_SOURCE}"
        )

    if data.get("plugin_id") != EXPECTED_PLUGIN_ID:
        raise ValueError(f"plugin_id mismatch: {data.get('plugin_id')} != {EXPECTED_PLUGIN_ID}")

    if data.get("desired_version") != EXPECTED_VERSION:
        raise ValueError(
            f"desired_version mismatch: {data.get('desired_version')} != {EXPECTED_VERSION}"
        )

    if data.get("last_published_version") != EXPECTED_VERSION:
        raise ValueError(
            f"last_published_version mismatch: {data.get('last_published_version')} != {EXPECTED_VERSION}"
        )

    if data.get("last_published_release_id") != EXPECTED_RELEASE_ID:
        raise ValueError(
            f"release_id mismatch: {data.get('last_published_release_id')} != {EXPECTED_RELEASE_ID}"
        )

    if data.get("status") != EXPECTED_SYNC_STATUS:
        raise ValueError(f"status mismatch: {data.get('status')} != {EXPECTED_SYNC_STATUS}")

    if data.get("verified_files") != 19:
        raise ValueError(f"verified_files count mismatch: {data.get('verified_files')} != 19")

    if data.get("byte_identical_files") != 18:
        raise ValueError(
            f"byte_identical_files count mismatch: {data.get('byte_identical_files')} != 18"
        )

    json_eq = data.get("json_semantic_equivalent_files", [])
    if json_eq != [".codex-plugin/plugin.json"]:
        raise ValueError(f"json_semantic_equivalent_files unexpected: {json_eq}")

    return {
        "valid": True,
        "plugin_id": EXPECTED_PLUGIN_ID,
        "release_id": EXPECTED_RELEASE_ID,
        "version": EXPECTED_VERSION,
        "verified_files": 19,
        "byte_identical_files": 18,
        "json_semantic_equivalent_files": json_eq,
    }


def verify_manifest_versions(canonical_dir: Path) -> dict[str, Any]:
    """Verify version 0.6.0 and package name across all platform manifests."""
    manifest_paths = {
        "root": canonical_dir / "plugin.json",
        "codex": canonical_dir / ".codex-plugin" / "plugin.json",
        "claude": canonical_dir / ".claude-plugin" / "plugin.json",
        "antigravity": canonical_dir / ".antigravity-plugin" / "plugin.json",
    }

    results: dict[str, dict[str, str]] = {}
    for platform, path in manifest_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Manifest missing for {platform}: {path}")
        content = json.loads(path.read_text(encoding="utf-8"))
        version = content.get("version")
        name = content.get("name")
        if version != EXPECTED_VERSION:
            raise ValueError(f"Manifest {platform} version {version} != {EXPECTED_VERSION}")
        if name != "exams-archive-native":
            raise ValueError(f"Manifest {platform} name {name} != 'exams-archive-native'")
        results[platform] = {"name": name, "version": version}

    return {"valid": True, "manifests": results}


def compare_file_contents(rel_path: str, canonical_bytes: bytes, target_bytes: bytes) -> str:
    """Compare canonical file content with target release content.

    Returns:
        'byte_identical': exact raw byte equality.
        'json_semantic_equivalent': JSON parses identically despite whitespace or unicode escaping.
        'diverged': content differences detected.
    """
    if canonical_bytes == target_bytes:
        return "byte_identical"

    if rel_path.endswith(".json"):
        try:
            c_json = json.loads(canonical_bytes.decode("utf-8"))
            t_json = json.loads(target_bytes.decode("utf-8"))
            if c_json == t_json:
                return "json_semantic_equivalent"
        except Exception:
            pass

    return "diverged"


def load_file_map_from_dir(directory: Path) -> dict[str, bytes]:
    """Load package files from directory into relative path -> bytes mapping."""
    if not directory.is_dir():
        raise NotADirectoryError(f"Directory not found: {directory}")

    file_map: dict[str, bytes] = {}
    for root, dirs, files in os.walk(directory):
        # Exclude internal metadata and cache dirs
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache")]
        for file in files:
            if file in (".sync-state.json", ".DS_Store"):
                continue
            full_path = Path(root) / file
            rel_path = full_path.relative_to(directory).as_posix()
            file_map[rel_path] = full_path.read_bytes()

    return file_map


def load_file_map_from_zip(zip_path: Path) -> dict[str, bytes]:
    """Load package files from zip archive into relative path -> bytes mapping."""
    if not zip_path.is_file():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    file_map: dict[str, bytes] = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        for entry in zf.infolist():
            if entry.is_dir():
                continue
            name = entry.filename.replace("\\", "/").lstrip("/")
            if name in (".sync-state.json", ".DS_Store") or name.startswith("__MACOSX/"):
                continue
            file_map[name] = zf.read(entry)

    return file_map


def compare_package_trees(
    canonical_map: dict[str, bytes],
    target_map: dict[str, bytes],
) -> dict[str, Any]:
    """Compare canonical 19 package files against target release file map."""
    details: dict[str, str] = {}
    byte_identical_count = 0
    json_semantic_count = 0
    diverged_count = 0
    missing_count = 0

    for path in CANONICAL_FILES:
        if path not in canonical_map:
            raise KeyError(f"Canonical map is missing required file: {path}")

        if path not in target_map:
            details[path] = "missing"
            missing_count += 1
            continue

        status = compare_file_contents(path, canonical_map[path], target_map[path])
        details[path] = status
        if status == "byte_identical":
            byte_identical_count += 1
        elif status == "json_semantic_equivalent":
            json_semantic_count += 1
        else:
            diverged_count += 1

    extra_files = [p for p in target_map if p not in CANONICAL_FILES and p != ".sync-state.json"]
    verified_files = byte_identical_count + json_semantic_count
    is_synced = (
        missing_count == 0
        and diverged_count == 0
        and verified_files == len(CANONICAL_FILES)
        and len(extra_files) == 0
    )

    return {
        "is_synced": is_synced,
        "total_canonical": len(CANONICAL_FILES),
        "verified_files": verified_files,
        "byte_identical_files": byte_identical_count,
        "json_semantic_equivalent_files": json_semantic_count,
        "diverged_files": diverged_count,
        "missing_files": missing_count,
        "extra_files": extra_files,
        "file_details": details,
    }


def setup_smoke_test_environment(temp_dir: Path) -> dict[str, Path]:
    """Initialize minimal test fixtures for CLI routing smoke tests."""
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    # 1. Full index SQLite
    archive_db = temp_dir / "full-index.sqlite"
    conn = sqlite3.connect(archive_db)
    conn.executescript("""
        CREATE TABLE repositories(id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE commits(repo_id INTEGER, sha TEXT, date TEXT, subject TEXT);
        CREATE TABLE changes(repo_id INTEGER, sha TEXT, status TEXT, path TEXT, previous_path TEXT);
        CREATE TABLE images(repo_id INTEGER, path TEXT, blob TEXT, commit_sha TEXT, kind TEXT, bytes INTEGER);
        CREATE VIRTUAL TABLE commit_fts USING fts5(subject, repo_id UNINDEXED, sha UNINDEXED);
        CREATE VIRTUAL TABLE change_fts USING fts5(path, repo_id UNINDEXED, sha UNINDEXED, status UNINDEXED);
        INSERT INTO repositories VALUES(1, 'exams-app-sample');
        INSERT INTO commits VALUES(1, '1111111111111111111111111111111111111111', '2026-01-01', 'Initial commit');
        INSERT INTO commit_fts VALUES('Initial commit', '1', '1111111111111111111111111111111111111111');
        INSERT INTO changes VALUES(1, '1111111111111111111111111111111111111111', 'A', 'src/sample.ts', '');
        INSERT INTO change_fts VALUES('src/sample.ts', '1', '1111111111111111111111111111111111111111', 'A');
        INSERT INTO images VALUES(1, 'assets/logo.png', 'blob123', '1111111111111111111111111111111111111111', 'active', 1024);
    """)
    conn.commit()
    conn.close()

    # 2. Graph SQLite using graph_linker
    graph_db = temp_dir / "graph-linker.sqlite"
    try:
        import graph_linker  # type: ignore
        conn_g = graph_linker.open_db(graph_db)
        conn_g.close()
    except Exception:
        pass

    # 3. Context SQLite using context_linker
    context_db = temp_dir / "context-linker.sqlite"
    try:
        import context_linker  # type: ignore
        conn_c = context_linker.open_db(context_db)
        conn_c.close()
    except Exception:
        pass

    # 4. Source file for AST testing
    sample_py = temp_dir / "sample_component.py"
    sample_py.write_text(
        "def render_sidebar():\n    \"\"\"Render sidebar component.\"\"\"\n    return True\n",
        encoding="utf-8",
    )

    # 5. Clean text file for secrets check
    clean_txt = temp_dir / "clean_documentation.txt"
    clean_txt.write_text(
        "Standard documentation file with no credentials or private keys.\n",
        encoding="utf-8",
    )

    return {
        "archive_db": archive_db,
        "graph_db": graph_db,
        "context_db": context_db,
        "sample_py": sample_py,
        "clean_txt": clean_txt,
    }


def run_cli_smoke_runner(cli_path: Path, python_bin: str = sys.executable) -> dict[str, Any]:
    """Run automated smoke tests for archive_query.py CLI commands."""
    if not cli_path.is_file():
        raise FileNotFoundError(f"CLI script not found: {cli_path}")

    commands_results: dict[str, dict[str, Any]] = {}
    all_passed = True

    with tempfile.TemporaryDirectory(prefix="plugin-smoke-") as td:
        fixtures = setup_smoke_test_environment(Path(td))

        test_invocations = {
            "search": [
                python_bin,
                str(cli_path),
                "--db",
                str(fixtures["archive_db"]),
                "search",
                "sample",
                "--limit",
                "5",
            ],
            "images": [
                python_bin,
                str(cli_path),
                "--db",
                str(fixtures["archive_db"]),
                "images",
                "--limit",
                "5",
            ],
            "stats": [
                python_bin,
                str(cli_path),
                "--db",
                str(fixtures["archive_db"]),
                "stats",
            ],
            "ast": [
                python_bin,
                str(cli_path),
                "ast",
                str(fixtures["sample_py"]),
                "--summary-only",
            ],
            "graph": [
                python_bin,
                str(cli_path),
                "graph",
                "--graph-db",
                str(fixtures["graph_db"]),
                "--stats",
            ],
            "context": [
                python_bin,
                str(cli_path),
                "context",
                "--context-db",
                str(fixtures["context_db"]),
                "--stats",
            ],
            "secrets-check": [
                python_bin,
                str(cli_path),
                "secrets-check",
                str(fixtures["clean_txt"]),
            ],
        }

        for cmd_name, cmd_args in test_invocations.items():
            proc = subprocess.run(cmd_args, text=True, capture_output=True)
            passed = proc.returncode == 0
            json_parsed = False
            parsed_data = None

            if passed:
                try:
                    parsed_data = json.loads(proc.stdout)
                    json_parsed = True
                except json.JSONDecodeError:
                    passed = False

            if not passed:
                all_passed = False

            commands_results[cmd_name] = {
                "command": cmd_name,
                "passed": passed,
                "exit_code": proc.returncode,
                "json_parsed": json_parsed,
                "stderr": proc.stderr.strip()[:200] if proc.stderr else None,
                "output_type": type(parsed_data).__name__ if json_parsed else None,
            }

    return {
        "all_passed": all_passed,
        "commands": commands_results,
        "total_commands": len(CLI_ROUTING_COMMANDS),
        "passed_commands": sum(1 for c in commands_results.values() if c["passed"]),
    }


def validate_all(
    canonical_dir: Path,
    target_dir: Path | None = None,
    target_zip: Path | None = None,
    cli_path: Path | None = None,
    skip_cli_smoke: bool = False,
    skip_sync_state: bool = False,
) -> dict[str, Any]:
    """Execute all verification stages and return composite report."""
    report: dict[str, Any] = {
        "canonical_dir": str(canonical_dir),
        "all_valid": True,
        "stages": {},
    }

    # 1. Sync state validation
    if not skip_sync_state:
        sync_state_file = canonical_dir / ".sync-state.json"
        try:
            sync_report = verify_sync_state(sync_state_file)
            report["stages"]["sync_state"] = {"passed": True, "details": sync_report}
        except Exception as exc:
            report["stages"]["sync_state"] = {"passed": False, "error": str(exc)}
            report["all_valid"] = False

    # 2. Manifest versions validation
    try:
        manifest_report = verify_manifest_versions(canonical_dir)
        report["stages"]["manifest_versions"] = {"passed": True, "details": manifest_report}
    except Exception as exc:
        report["stages"]["manifest_versions"] = {"passed": False, "error": str(exc)}
        report["all_valid"] = False

    # 3. Canonical files completeness & tree comparison
    try:
        canonical_map = load_file_map_from_dir(canonical_dir)
        # Check canonical directory contains all 19 files
        missing_in_canonical = [p for p in CANONICAL_FILES if p not in canonical_map]
        if missing_in_canonical:
            report["stages"]["canonical_files"] = {
                "passed": False,
                "error": f"Missing canonical files: {missing_in_canonical}",
            }
            report["all_valid"] = False
        else:
            report["stages"]["canonical_files"] = {
                "passed": True,
                "count": len(canonical_map),
                "canonical_expected": len(CANONICAL_FILES),
            }

        # Compare with target if specified
        if target_zip:
            target_map = load_file_map_from_zip(target_zip)
            tree_report = compare_package_trees(canonical_map, target_map)
            report["stages"]["target_comparison"] = {
                "passed": tree_report["is_synced"],
                "target_type": "zip",
                "details": tree_report,
            }
            if not tree_report["is_synced"]:
                report["all_valid"] = False
        elif target_dir:
            target_map = load_file_map_from_dir(target_dir)
            tree_report = compare_package_trees(canonical_map, target_map)
            report["stages"]["target_comparison"] = {
                "passed": tree_report["is_synced"],
                "target_type": "dir",
                "details": tree_report,
            }
            if not tree_report["is_synced"]:
                report["all_valid"] = False

    except Exception as exc:
        report["stages"]["canonical_files"] = {"passed": False, "error": str(exc)}
        report["all_valid"] = False

    # 4. CLI routing smoke tests
    if not skip_cli_smoke:
        effective_cli = cli_path or (canonical_dir / "scripts" / "archive_query.py")
        try:
            cli_report = run_cli_smoke_runner(effective_cli)
            report["stages"]["cli_smoke"] = {
                "passed": cli_report["all_passed"],
                "details": cli_report,
            }
            if not cli_report["all_passed"]:
                report["all_valid"] = False
        except Exception as exc:
            report["stages"]["cli_smoke"] = {"passed": False, "error": str(exc)}
            report["all_valid"] = False

    return report


def main() -> None:
    """CLI entrypoint."""
    repo_root = Path(__file__).resolve().parents[1]
    default_canonical = repo_root / "plugins" / "exams-archive-native"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--canonical-dir",
        type=Path,
        default=default_canonical,
        help="Path to canonical plugin directory (default: plugins/exams-archive-native)",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=None,
        help="Path to target directory to compare against canonical",
    )
    parser.add_argument(
        "--target-zip",
        type=Path,
        default=None,
        help="Path to target release zip archive to compare against canonical",
    )
    parser.add_argument(
        "--cli-path",
        type=Path,
        default=None,
        help="Path to archive_query.py CLI script",
    )
    parser.add_argument(
        "--skip-cli-smoke",
        action="store_true",
        help="Skip CLI smoke tests",
    )
    parser.add_argument(
        "--skip-sync-state",
        action="store_true",
        help="Skip .sync-state.json verification",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON report",
    )

    args = parser.parse_args()

    report = validate_all(
        canonical_dir=args.canonical_dir,
        target_dir=args.target_dir,
        target_zip=args.target_zip,
        cli_path=args.cli_path,
        skip_cli_smoke=args.skip_cli_smoke,
        skip_sync_state=args.skip_sync_state,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("=== Exams Archive Plugin Synchronization Verification ===")
        for stage_name, stage_data in report["stages"].items():
            status_text = "[OK]" if stage_data.get("passed") else "[FAIL]"
            print(f"{status_text} Stage: {stage_name}")
            if not stage_data.get("passed") and "error" in stage_data:
                print(f"       Error: {stage_data['error']}")
            elif "details" in stage_data:
                details = stage_data["details"]
                if stage_name == "sync_state":
                    print(
                        f"       Release ID: {details.get('release_id')}, "
                        f"Version: {details.get('version')}, "
                        f"Verified files: {details.get('verified_files')}"
                    )
                elif stage_name == "cli_smoke":
                    print(
                        f"       Commands passed: "
                        f"{details.get('passed_commands')}/{details.get('total_commands')}"
                    )
        print("---------------------------------------------------------")
        result_str = "SUCCESS" if report["all_valid"] else "FAILED"
        print(f"Overall Result: {result_str}")

    sys.exit(0 if report["all_valid"] else 1)


if __name__ == "__main__":
    main()
