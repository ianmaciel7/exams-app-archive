#!/usr/bin/env python3
"""Unit tests for offsite backup checklist, checksums, bundle validation, and safety gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import offsite_backup_checklist as obc  # noqa: E402


class ManifestCompletenessTests(unittest.TestCase):
    """Test manifest completeness, coverage of 9 repositories, and hash schemas."""

    def setUp(self):
        self.manifests_dir = ROOT / "manifests"

    def test_all_9_repositories_defined_and_covered(self):
        report = obc.check_manifest_completeness(self.manifests_dir)
        self.assertEqual(report["total_repositories"], 9)
        self.assertEqual(report["covered_repositories_count"], 9)
        self.assertTrue(report["all_repositories_covered"])
        self.assertGreaterEqual(report["total_manifest_assets_indexed"], 30)

        for repo in obc.ALL_9_REPOSITORIES:
            self.assertIn(repo, report["repository_coverage"])
            self.assertTrue(report["repository_coverage"][repo]["covered_in_manifests"])

    def test_manifest_schema_and_sha256_format(self):
        report = obc.check_manifest_completeness(self.manifests_dir)
        sha_pattern = re.compile(r"^[0-9a-f]{64}$")
        self.assertGreater(len(report["sha256_index"]), 0)

        for asset, sha in report["sha256_index"].items():
            self.assertIsNotNone(sha_pattern.match(sha), f"Invalid SHA-256 for asset {asset}: {sha}")

    def test_normalize_repo_name(self):
        self.assertEqual(obc.normalize_repo_name("ianmaciel7/exams-app-old"), "exams-app-old")
        self.assertEqual(obc.normalize_repo_name("exams-app-antigo-2"), "exams-app-antigo-2")
        self.assertEqual(obc.normalize_repo_name("  ianmaciel7/notes-app  "), "notes-app")
        self.assertEqual(obc.normalize_repo_name(""), "")


class ChecksumTests(unittest.TestCase):
    """Test SHA-256 calculation, verification, and directory auditing."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="offsite-checksum-test-")
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_calculate_sha256_known_content(self):
        test_file = self.dir_path / "sample.txt"
        content = b"The quick brown fox jumps over the lazy dog"
        test_file.write_bytes(content)

        expected_hash = hashlib.sha256(content).hexdigest()
        actual_hash = obc.calculate_sha256(test_file)
        self.assertEqual(actual_hash, expected_hash)

    def test_calculate_sha256_empty_file(self):
        test_file = self.dir_path / "empty.bin"
        test_file.write_bytes(b"")

        empty_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        self.assertEqual(obc.calculate_sha256(test_file), empty_sha256)

    def test_verify_checksum_match_and_mismatch(self):
        test_file = self.dir_path / "verify.txt"
        test_file.write_bytes(b"deterministic content")
        correct_hash = hashlib.sha256(b"deterministic content").hexdigest()
        wrong_hash = "0" * 64

        self.assertTrue(obc.verify_checksum(test_file, correct_hash))
        self.assertTrue(obc.verify_checksum(test_file, correct_hash.upper()))
        self.assertFalse(obc.verify_checksum(test_file, wrong_hash))
        self.assertFalse(obc.verify_checksum(test_file, ""))

    def test_calculate_sha256_nonexistent_file(self):
        missing = self.dir_path / "nonexistent.bin"
        with self.assertRaises(FileNotFoundError):
            obc.calculate_sha256(missing)

    def test_verify_directory_checksums(self):
        file1 = self.dir_path / "asset1.bundle"
        file1.write_bytes(b"bundle content 1")
        hash1 = hashlib.sha256(b"bundle content 1").hexdigest()

        file2 = self.dir_path / "asset2.zip"
        file2.write_bytes(b"corrupted zip content")
        hash2_expected = hashlib.sha256(b"original zip content").hexdigest()

        sha_index = {
            "asset1.bundle": hash1,
            "asset2.zip": hash2_expected,
            "asset3.tar": "a" * 64,  # missing file
        }

        result = obc.verify_directory_checksums(self.dir_path, sha_index)
        self.assertTrue(result["directory_exists"])
        self.assertEqual(result["verified_count"], 1)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["missing_count"], 1)


class BundleVerificationTests(unittest.TestCase):
    """Test git bundle verification logic with mock and actual git repositories."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="offsite-bundle-test-")
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_bundle_verification_valid_bundle(self):
        repo_dir = self.dir_path / "test_repo"
        subprocess.run(["git", "init", str(repo_dir)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@test.com"], check=True)
        (repo_dir / "file.txt").write_text("sample code")
        subprocess.run(["git", "-C", str(repo_dir), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "commit", "-m", "init"], check=True, capture_output=True)

        bundle_file = self.dir_path / "sample.bundle"
        subprocess.run(
            ["git", "-C", str(repo_dir), "bundle", "create", str(bundle_file), "HEAD"],
            check=True,
            capture_output=True,
        )

        is_valid, msg = obc.verify_git_bundle(bundle_file)
        self.assertTrue(is_valid, msg)
        self.assertIn("verified successfully", msg)

    def test_bundle_verification_corrupted_file(self):
        corrupted = self.dir_path / "corrupted.bundle"
        corrupted.write_bytes(b"this is not a valid git bundle header or content")

        is_valid, msg = obc.verify_git_bundle(corrupted)
        self.assertFalse(is_valid)
        self.assertIn("failed", msg)

    def test_bundle_verification_nonexistent_file(self):
        missing = self.dir_path / "missing.bundle"
        is_valid, msg = obc.verify_git_bundle(missing)
        self.assertFalse(is_valid)
        self.assertIn("does not exist", msg)


class SafetyGateBlockingTests(unittest.TestCase):
    """Test block-by-default safety gate rules and prerequisites."""

    def setUp(self):
        self.manifests_dir = ROOT / "manifests"
        self.manifest_data = obc.load_manifest_assets(self.manifests_dir)

    def test_block_by_default_without_external_record(self):
        gates = obc.evaluate_all_safety_gates(self.manifests_dir, external_backup_record=None)
        self.assertEqual(gates["total_repositories"], 9)
        self.assertEqual(gates["blocked_count"], 9)
        self.assertEqual(gates["eligible_count"], 0)
        self.assertTrue(gates["all_blocked_by_default"])

        for repo, gate in gates["results"].items():
            self.assertFalse(gate["ready_for_deletion"])
            self.assertEqual(gate["status"], "BLOCKED")
            self.assertGreater(len(gate["blockers"]), 0)

    def test_active_repos_permanently_blocked(self):
        # Even with complete external approval, active repos must remain permanently blocked
        mock_record = {
            "storage_location": "s3://independent-vault/backups",
            "confirmed_date": "2026-11-24T10:00:00Z",
            "checksums_verified": True,
            "independent_restore_tested": True,
            "explicit_owner_approval": True,
        }

        for active_repo in ("exams-app", "notes-app", "exams-app-archive"):
            gate = obc.evaluate_safety_gate(active_repo, mock_record, self.manifest_data)
            self.assertFalse(gate["ready_for_deletion"])
            self.assertEqual(gate["status"], "BLOCKED")
            self.assertEqual(gate["category"], "active_infrastructure")
            self.assertTrue(any("permanently blocked" in b.lower() for b in gate["blockers"]))

    def test_auxiliary_repos_blocked(self):
        mock_record = {
            "storage_location": "s3://independent-vault/backups",
            "confirmed_date": "2026-11-24T10:00:00Z",
            "checksums_verified": True,
            "independent_restore_tested": True,
            "explicit_owner_approval": True,
        }

        for aux_repo in ("ianmaciel7", "fcc-responsive-web-design"):
            gate = obc.evaluate_safety_gate(aux_repo, mock_record, self.manifest_data)
            self.assertFalse(gate["ready_for_deletion"])
            self.assertEqual(gate["status"], "BLOCKED")
            self.assertEqual(gate["category"], "auxiliary")

    def test_deprecated_candidate_blocked_when_record_missing_fields(self):
        candidate = "exams-app-old"

        # 1. Missing storage location
        rec1 = {
            "storage_location": "",
            "confirmed_date": "2026-11-24",
            "checksums_verified": True,
            "independent_restore_tested": True,
            "explicit_owner_approval": True,
        }
        self.assertFalse(obc.evaluate_safety_gate(candidate, rec1, self.manifest_data)["ready_for_deletion"])

        # 2. Storage location on GitHub (disallowed, must be independent)
        rec2 = {
            "storage_location": "https://github.com/backup/repo",
            "confirmed_date": "2026-11-24",
            "checksums_verified": True,
            "independent_restore_tested": True,
            "explicit_owner_approval": True,
        }
        self.assertFalse(obc.evaluate_safety_gate(candidate, rec2, self.manifest_data)["ready_for_deletion"])

        # 3. Checksums not verified
        rec3 = {
            "storage_location": "s3://my-backup-bucket/data",
            "confirmed_date": "2026-11-24",
            "checksums_verified": False,
            "independent_restore_tested": True,
            "explicit_owner_approval": True,
        }
        self.assertFalse(obc.evaluate_safety_gate(candidate, rec3, self.manifest_data)["ready_for_deletion"])

        # 4. Independent restore not tested
        rec4 = {
            "storage_location": "s3://my-backup-bucket/data",
            "confirmed_date": "2026-11-24",
            "checksums_verified": True,
            "independent_restore_tested": False,
            "explicit_owner_approval": True,
        }
        self.assertFalse(obc.evaluate_safety_gate(candidate, rec4, self.manifest_data)["ready_for_deletion"])

        # 5. Owner approval missing
        rec5 = {
            "storage_location": "s3://my-backup-bucket/data",
            "confirmed_date": "2026-11-24",
            "checksums_verified": True,
            "independent_restore_tested": True,
            "explicit_owner_approval": False,
        }
        self.assertFalse(obc.evaluate_safety_gate(candidate, rec5, self.manifest_data)["ready_for_deletion"])

        # 6. Asset hash mismatch in verified_assets
        rec6 = {
            "storage_location": "s3://my-backup-bucket/data",
            "confirmed_date": "2026-11-24",
            "checksums_verified": True,
            "independent_restore_tested": True,
            "explicit_owner_approval": True,
            "verified_assets": {
                "exams-app-old.bundle": "0" * 64,  # wrong hash
            },
        }
        self.assertFalse(obc.evaluate_safety_gate(candidate, rec6, self.manifest_data)["ready_for_deletion"])

    def test_deprecated_candidate_eligible_when_all_conditions_met(self):
        candidate = "exams-app-old"
        valid_rec = {
            "storage_location": "s3://encrypted-glacier-vault/20261124/",
            "confirmed_date": "2026-11-24T11:00:00Z",
            "checksums_verified": True,
            "independent_restore_tested": True,
            "explicit_owner_approval": True,
            "approved_by": "ianmaciel7",
        }
        gate = obc.evaluate_safety_gate(candidate, valid_rec, self.manifest_data)
        self.assertTrue(gate["ready_for_deletion"])
        self.assertEqual(gate["status"], "ELIGIBLE_PENDING_MANUAL_EXECUTION")
        self.assertEqual(len(gate["blockers"]), 0)

    def test_unknown_repo_blocked(self):
        gate = obc.evaluate_safety_gate("nonexistent-repo-12345", None, self.manifest_data)
        self.assertFalse(gate["ready_for_deletion"])
        self.assertEqual(gate["status"], "BLOCKED")
        self.assertEqual(gate["category"], "unknown")


class CliExecutionTests(unittest.TestCase):
    """Test CLI commands and flags: --manifests-dir, --verify-checksums, --check-safety-gate, --json."""

    def test_cli_check_safety_gate_text(self):
        cmd = [
            sys.executable,
            str(ROOT / "scripts/offsite_backup_checklist.py"),
            "--manifests-dir",
            str(ROOT / "manifests"),
            "--check-safety-gate",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("OFFSITE BACKUP VERIFICATION CHECKLIST", proc.stdout)
        self.assertIn("Block-by-Default In Effect: YES", proc.stdout)

    def test_cli_json_output(self):
        cmd = [
            sys.executable,
            str(ROOT / "scripts/offsite_backup_checklist.py"),
            "--manifests-dir",
            str(ROOT / "manifests"),
            "--check-safety-gate",
            "--json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0)
        parsed = json.loads(proc.stdout)
        self.assertTrue(parsed["safety_gates"]["all_blocked_by_default"])
        self.assertEqual(parsed["manifest_completeness"]["total_repositories"], 9)

    def test_cli_single_repo_blocked_exit_code(self):
        cmd = [
            sys.executable,
            str(ROOT / "scripts/offsite_backup_checklist.py"),
            "--manifests-dir",
            str(ROOT / "manifests"),
            "--repo",
            "exams-app-old",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("[BLOCKED]", proc.stdout)


class ZeroEmojiPolicyTests(unittest.TestCase):
    """Enforce Zero Emoji Policy across all created files."""

    def test_no_emojis_in_script_docs_and_tests(self):
        emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]")
        targets = [
            ROOT / "scripts/offsite_backup_checklist.py",
            ROOT / "docs/OFFSITE-BACKUP-CHECKLIST.md",
            ROOT / "tests/test_offsite_backup.py",
        ]

        for target in targets:
            content = target.read_text(encoding="utf-8")
            matches = emoji_pattern.findall(content)
            self.assertEqual(
                len(matches),
                0,
                f"Zero Emoji Policy violated in {target.name}: found {len(matches)} emojis ({matches[:5]})",
            )


if __name__ == "__main__":
    unittest.main()
