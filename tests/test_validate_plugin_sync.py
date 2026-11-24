#!/usr/bin/env python3
"""Unit tests for plugin sync verification and multi-client smoke test runner.

Tests verification of 19 canonical package files, detection of diverged or missing files,
and archive_query.py CLI routing validation.

Zero Emoji Policy strictly enforced.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validate_plugin_sync import (
    CANONICAL_FILES,
    CLI_ROUTING_COMMANDS,
    EXPECTED_PLUGIN_ID,
    EXPECTED_RELEASE_ID,
    EXPECTED_VERSION,
    compare_file_contents,
    compare_package_trees,
    load_file_map_from_dir,
    run_cli_smoke_runner,
    validate_all,
    verify_manifest_versions,
    verify_sync_state,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DIR = REPO_ROOT / "plugins" / "exams-archive-native"
SYNC_STATE_PATH = CANONICAL_DIR / ".sync-state.json"
CLI_PATH = CANONICAL_DIR / "scripts" / "archive_query.py"


class TestValidatePluginSync(unittest.TestCase):
    def test_canonical_files_count_and_presence(self):
        """Verify that exactly canonical files are specified and present on disk."""
        canonical_count = len(CANONICAL_FILES)
        self.assertEqual(len(set(CANONICAL_FILES)), canonical_count)

        for rel_path in CANONICAL_FILES:
            full_path = CANONICAL_DIR / rel_path
            self.assertTrue(full_path.is_file(), f"Missing canonical file: {rel_path}")

        file_map = load_file_map_from_dir(CANONICAL_DIR)
        self.assertEqual(len(file_map), canonical_count)
        self.assertEqual(set(file_map.keys()), set(CANONICAL_FILES))

    def test_verify_sync_state_valid(self):
        """Verify that .sync-state.json conforms to expected release specification."""
        result = verify_sync_state(SYNC_STATE_PATH)
        self.assertTrue(result["valid"])
        self.assertEqual(result["plugin_id"], EXPECTED_PLUGIN_ID)
        self.assertEqual(result["release_id"], EXPECTED_RELEASE_ID)
        self.assertEqual(result["version"], EXPECTED_VERSION)

    def test_verify_sync_state_invalid_schema(self):
        """Verify that .sync-state.json validation fails on corrupted fields."""
        with tempfile.TemporaryDirectory() as td:
            bad_path = Path(td) / ".sync-state.json"

            # Bad schema
            bad_path.write_text(json.dumps({"schema": 1}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                verify_sync_state(bad_path)
            self.assertIn("schema", str(ctx.exception))

            # Missing file
            missing_path = Path(td) / "nonexistent.json"
            with self.assertRaises(FileNotFoundError):
                verify_sync_state(missing_path)

            # Bad version
            valid_dict = json.loads(SYNC_STATE_PATH.read_text(encoding="utf-8"))
            valid_dict["desired_version"] = "0.5.0"
            bad_path.write_text(json.dumps(valid_dict), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                verify_sync_state(bad_path)
            self.assertIn("desired_version", str(ctx.exception))

    def test_verify_manifest_versions_all_platforms(self):
        """Verify that all platform manifests report v0.6.0 and correct name."""
        res = verify_manifest_versions(CANONICAL_DIR)
        self.assertTrue(res["valid"])
        manifests = res["manifests"]
        for platform in ("root", "codex", "claude", "antigravity"):
            self.assertIn(platform, manifests)
            self.assertEqual(manifests[platform]["version"], EXPECTED_VERSION)
            self.assertEqual(manifests[platform]["name"], "exams-archive-native")

    def test_compare_file_contents_equivalence(self):
        """Test byte-identical, JSON semantic, and diverged comparisons."""
        # 1. Byte identical
        b1 = b"exact byte match"
        self.assertEqual(compare_file_contents("test.txt", b1, b1), "byte_identical")

        # 2. JSON semantic equivalent (unicode escapes vs utf-8 characters)
        raw_json_a = b'{"name": "\xc3\xa3"}'  # UTF-8 "ã"
        raw_json_b = b'{"name": "\\u00e3"}'  # Escaped unicode
        self.assertEqual(
            compare_file_contents("test.json", raw_json_a, raw_json_b),
            "json_semantic_equivalent",
        )

        # 3. JSON diverged
        raw_json_c = b'{"name": "different"}'
        self.assertEqual(
            compare_file_contents("test.json", raw_json_a, raw_json_c),
            "diverged",
        )

        # 4. Non-JSON diverged
        b2 = b"different content"
        self.assertEqual(compare_file_contents("test.txt", b1, b2), "diverged")

    def test_compare_package_trees_identical(self):
        """Test comparing identical canonical and target trees."""
        canonical_map = load_file_map_from_dir(CANONICAL_DIR)
        target_map = dict(canonical_map)
        canonical_count = len(canonical_map)

        res = compare_package_trees(canonical_map, target_map)
        self.assertTrue(res["is_synced"])
        self.assertEqual(res["total_canonical"], canonical_count)
        self.assertEqual(res["verified_files"], canonical_count)
        self.assertEqual(res["byte_identical_files"], canonical_count)
        self.assertEqual(res["json_semantic_equivalent_files"], 0)
        self.assertEqual(res["diverged_files"], 0)
        self.assertEqual(res["missing_files"], 0)
        self.assertEqual(len(res["extra_files"]), 0)

    def test_compare_package_trees_detection_of_missing_and_diverged(self):
        """Test detection of missing files, diverged files, and extra files."""
        canonical_map = load_file_map_from_dir(CANONICAL_DIR)

        # Case 1: Missing file
        target_missing = dict(canonical_map)
        del target_missing["README.md"]
        res_missing = compare_package_trees(canonical_map, target_missing)
        self.assertFalse(res_missing["is_synced"])
        self.assertEqual(res_missing["missing_files"], 1)
        self.assertEqual(res_missing["file_details"]["README.md"], "missing")

        # Case 2: Diverged file
        target_diverged = dict(canonical_map)
        target_diverged["README.md"] = b"# Altered documentation"
        res_diverged = compare_package_trees(canonical_map, target_diverged)
        self.assertFalse(res_diverged["is_synced"])
        self.assertEqual(res_diverged["diverged_files"], 1)
        self.assertEqual(res_diverged["file_details"]["README.md"], "diverged")

        # Case 3: Extra file
        target_extra = dict(canonical_map)
        target_extra["unexpected_script.py"] = b"print('extra')"
        res_extra = compare_package_trees(canonical_map, target_extra)
        self.assertFalse(res_extra["is_synced"])
        self.assertEqual(len(res_extra["extra_files"]), 1)
        self.assertIn("unexpected_script.py", res_extra["extra_files"])

    def test_compare_package_trees_with_codex_unicode_escaping(self):
        """Verify that ChatGPT release profile is verified synced."""
        canonical_map = load_file_map_from_dir(CANONICAL_DIR)
        target_simulated = dict(canonical_map)
        canonical_count = len(canonical_map)

        # Simulate ChatGPT Personal Plugin Creator unicode escaping on .codex-plugin/plugin.json
        codex_data = json.loads(canonical_map[".codex-plugin/plugin.json"].decode("utf-8"))
        escaped_bytes = json.dumps(codex_data, ensure_ascii=True, indent=2).encode("utf-8")
        target_simulated[".codex-plugin/plugin.json"] = escaped_bytes

        res = compare_package_trees(canonical_map, target_simulated)
        self.assertTrue(res["is_synced"])
        self.assertEqual(res["verified_files"], canonical_count)
        self.assertEqual(res["byte_identical_files"], canonical_count - 1)
        self.assertEqual(res["json_semantic_equivalent_files"], 1)
        self.assertEqual(res["diverged_files"], 0)
        self.assertEqual(res["missing_files"], 0)
        self.assertEqual(
            res["file_details"][".codex-plugin/plugin.json"], "json_semantic_equivalent"
        )

    def test_cli_smoke_runner_validates_all_commands(self):
        """Execute automated smoke tests for archive_query.py CLI routing."""
        res = run_cli_smoke_runner(CLI_PATH)
        self.assertTrue(res["all_passed"], f"CLI smoke test failed: {res}")
        self.assertEqual(res["total_commands"], len(CLI_ROUTING_COMMANDS))
        self.assertEqual(res["passed_commands"], len(CLI_ROUTING_COMMANDS))

        commands = res["commands"]
        for cmd in CLI_ROUTING_COMMANDS:
            self.assertIn(cmd, commands)
            self.assertTrue(commands[cmd]["passed"], f"Command {cmd} failed: {commands[cmd]}")
            self.assertEqual(commands[cmd]["exit_code"], 0)
            self.assertTrue(commands[cmd]["json_parsed"])

    def test_cli_smoke_runner_handles_failures(self):
        """Test error handling when CLI script is missing or invalid."""
        with tempfile.TemporaryDirectory() as td:
            missing_cli = Path(td) / "missing_archive_query.py"
            with self.assertRaises(FileNotFoundError):
                run_cli_smoke_runner(missing_cli)

            # Faulty script that fails on ast command
            faulty_cli = Path(td) / "faulty_cli.py"
            faulty_cli.write_text(
                "import sys\n"
                "if 'ast' in sys.argv:\n"
                "    sys.exit(1)\n"
                "print('[]')\n",
                encoding="utf-8",
            )
            res = run_cli_smoke_runner(faulty_cli)
            self.assertFalse(res["all_passed"])
            self.assertFalse(res["commands"]["ast"]["passed"])

    def test_validate_all_end_to_end(self):
        """Test end-to-end composite validation on the repository plugin."""
        report = validate_all(canonical_dir=CANONICAL_DIR)
        self.assertTrue(report["all_valid"])
        self.assertTrue(report["stages"]["sync_state"]["passed"])
        self.assertTrue(report["stages"]["manifest_versions"]["passed"])
        self.assertTrue(report["stages"]["canonical_files"]["passed"])
        self.assertTrue(report["stages"]["cli_smoke"]["passed"])

    def test_zero_emoji_compliance(self):
        """Verify that no Unicode emoji characters exist in script, docs, or tests."""
        target_files = [
            REPO_ROOT / "scripts" / "validate_plugin_sync.py",
            REPO_ROOT / "docs" / "PLUGIN-SYNC-VERIFICATION.md",
            Path(__file__).resolve(),
        ]

        for file_path in target_files:
            text = file_path.read_text(encoding="utf-8")
            for line_idx, line in enumerate(text.splitlines(), start=1):
                for char in line:
                    code_point = ord(char)
                    self.assertFalse(
                        0x10000 <= code_point <= 0x10FFFF,
                        f"Emoji detected in {file_path.name} at line {line_idx}: {char!r} (U+{code_point:04X})",
                    )


if __name__ == "__main__":
    unittest.main()
