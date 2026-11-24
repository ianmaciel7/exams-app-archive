#!/usr/bin/env python3
"""Unit tests for pre-deletion compliance audit orchestrator.

Tests clean and deficient states, gate enforcement rules, report generation,
and Zero Emoji Policy compliance.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pre_deletion_audit as pda  # noqa: E402


class PreDeletionAuditTests(unittest.TestCase):
    """Test suite for pre_deletion_audit orchestrator across clean and deficient states."""

    def setUp(self) -> None:
        self.orchestrator = pda.PreDeletionAuditOrchestrator(root_dir=ROOT)

    def test_default_audit_execution(self) -> None:
        """Verify baseline audit on project workspace correctly catalogs all assets."""
        result = self.orchestrator.run_audit()

        self.assertIn("audit_timestamp_utc", result)
        self.assertEqual(result["total_repositories_audited"], 9)
        self.assertFalse(result["can_delete_repositories"])
        self.assertIn("FAIL", result["overall_verdict"])
        self.assertEqual(result["repositories_blocked_from_deletion"], 9)

        # Repositories check: 9/9 cataloged
        repo_cond = result["conditions"]["COND-01-REPOSITORIES-INVENTORIED"]
        self.assertEqual(repo_cond["result"], "PASS")

        # Branches check: 75/75 branches cataloged
        branch_cond = result["conditions"]["COND-02-BRANCHES-AUDITED"]
        self.assertEqual(branch_cond["result"], "PASS")

        # Tags check: at least 3 notes tags
        tag_cond = result["conditions"]["COND-03-TAGS-RECORDED"]
        self.assertEqual(tag_cond["result"], "PASS")

        # fsck check
        fsck_cond = result["conditions"]["COND-04-GIT-FSCK-INTEGRITY"]
        self.assertEqual(fsck_cond["result"], "PASS")

        # Bundles check
        bundle_cond = result["conditions"]["COND-05-RELEASE-BUNDLE-CHECKSUMS"]
        self.assertEqual(bundle_cond["result"], "PASS")

        # Notes Git coverage is verified independently of deletion readiness
        notes_cond = result["conditions"]["COND-07-NOTES-APP-PRIVATE-PRESERVED"]
        self.assertEqual(notes_cond["result"], "PASS")

        # Branch readiness gate: must FAIL for deletion
        gate_cond = result["conditions"]["COND-08-BRANCH-READINESS-GATE"]
        self.assertEqual(gate_cond["result"], "FAIL")

        # Offsite backup check: must FAIL for deletion
        offsite_cond = result["conditions"]["COND-09-OFFSITE-BACKUP-VERIFIED"]
        self.assertEqual(offsite_cond["result"], "FAIL")

        # Owner authorization check: must FAIL for deletion
        auth_cond = result["conditions"]["COND-11-OWNER-EXPLICIT-AUTHORIZATION"]
        self.assertEqual(auth_cond["result"], "FAIL")

    def test_notes_manifest_missing_or_invalid_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            orch = pda.PreDeletionAuditOrchestrator(root_dir=Path(tmp_dir))
            self.assertEqual(orch.check_notes_preservation()["status"], "FAIL")
            source = json.loads(self.orchestrator.notes_private_manifest.read_text(encoding="utf-8"))
            orch.notes_private_manifest.parent.mkdir(parents=True)
            source["verified"]["restore"] = False
            orch.notes_private_manifest.write_text(json.dumps(source), encoding="utf-8")
            self.assertEqual(orch.check_notes_preservation()["status"], "FAIL")
            source["verified"]["restore"] = True
            source["all_refs"].pop("refs/heads/main")
            orch.notes_private_manifest.write_text(json.dumps(source), encoding="utf-8")
            self.assertEqual(orch.check_notes_preservation()["status"], "FAIL")

    def test_repository_dispositions(self) -> None:
        """Verify per-repository disposition recommendations."""
        result = self.orchestrator.run_audit()
        dispositions = {d["repository"]: d for d in result["repository_dispositions"]}

        self.assertEqual(len(dispositions), 9)

        # Active repos must not be eligible for read-only archive or deletion
        for active in ("ianmaciel7/exams-app", "ianmaciel7/notes-app", "ianmaciel7/exams-app-archive"):
            self.assertFalse(dispositions[active]["read_only_archive_eligible"])
            self.assertEqual(dispositions[active]["deletion_status"], "BLOQUEADO PARA EXCLUSAO")

        # Legacy candidate repos are eligible for read-only archive, but blocked from deletion
        for legacy in pda.LEGACY_CANDIDATE_REPOSITORIES:
            self.assertTrue(dispositions[legacy]["read_only_archive_eligible"])
            self.assertEqual(dispositions[legacy]["deletion_status"], "BLOQUEADO PARA EXCLUSAO")
            self.assertIn("Apto para arquivar em modo somente leitura", dispositions[legacy]["recommendation"])

    def test_deficient_state_missing_inventory_file(self) -> None:
        """Ensure missing inventory causes repo check to fail and hard-fails the audit."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_orchestrator = pda.PreDeletionAuditOrchestrator(root_dir=Path(tmp_dir))
            repo_res = empty_orchestrator.check_repositories()
            self.assertEqual(repo_res["status"], "FAIL")
            self.assertEqual(len(repo_res["missing"]), len(pda.TARGET_REPOSITORIES))

            audit_result = empty_orchestrator.run_audit()
            self.assertEqual(audit_result["conditions"]["COND-01-REPOSITORIES-INVENTORIED"]["result"], "FAIL")
            self.assertFalse(audit_result["can_delete_repositories"])

    def test_deficient_state_missing_repository_in_inventory(self) -> None:
        """Ensure omission of a single target repository triggers hard failure."""
        incomplete_repos = {
            "status": "FAIL",
            "total_expected": 9,
            "total_found": 8,
            "found": pda.TARGET_REPOSITORIES[:-1],
            "missing": [pda.TARGET_REPOSITORIES[-1]],
        }
        orch = pda.PreDeletionAuditOrchestrator(
            root_dir=ROOT,
            overrides={"repositories": incomplete_repos},
        )
        result = orch.run_audit()
        self.assertEqual(result["conditions"]["COND-01-REPOSITORIES-INVENTORIED"]["result"], "FAIL")
        self.assertFalse(result["can_delete_repositories"])

    def test_deficient_state_missing_bundles(self) -> None:
        """Ensure corrupted or unverified bundle hard-fails the audit."""
        corrupted_bundles = {
            "status": "FAIL",
            "details": {
                "release_manifest_valid": False,
                "all_refs_manifest_valid": True,
                "embedded_bundles_verified": False,
            },
        }
        orch = pda.PreDeletionAuditOrchestrator(
            root_dir=ROOT,
            overrides={"bundles": corrupted_bundles},
        )
        result = orch.run_audit()
        self.assertEqual(result["conditions"]["COND-05-RELEASE-BUNDLE-CHECKSUMS"]["result"], "FAIL")
        self.assertFalse(result["can_delete_repositories"])

    def test_deficient_state_missing_offsite_backup(self) -> None:
        """Ensure absence of external offsite backup hard-fails the audit."""
        result = self.orchestrator.run_audit()
        offsite = result["conditions"]["COND-09-OFFSITE-BACKUP-VERIFIED"]
        self.assertEqual(offsite["result"], "FAIL")
        self.assertIn("#4", offsite["evidence"])
        self.assertFalse(result["can_delete_repositories"])

    def test_clean_state_fully_satisfied(self) -> None:
        """Ensure audit passes and allows candidate deletion when all conditions are satisfied."""
        satisfied_conditions = {
            "repositories": {"status": "PASS", "total_expected": 9, "total_found": 9, "found": pda.TARGET_REPOSITORIES, "missing": []},
            "branches": {"status": "PASS", "total_audited": 75, "total_expected": 75, "missing_sha_count": 0, "categories": {}, "branches": []},
            "tags": {"status": "PASS", "total_tags_cataloged": 5, "missing_notes_tags": []},
            "fsck": {"status": "PASS", "checks": []},
            "bundles": {"status": "PASS", "details": {"release_manifest_valid": True, "all_refs_manifest_valid": True, "embedded_bundles_verified": True}},
            "ci_metadata": {"status": "PASS", "ci_logs_verified": True, "platform_metadata_verified": True},
            "notes_preservation": {"status": "PASS", "fully_preserved": True, "blockers": "Preservacao concluida", "pending_branches": [], "pending_tags": []},
            "branch_gate": {"status": "PASS", "blocked_count": 0, "allowed_count": 75, "can_delete": True, "total_branches": 75},
            "offsite_backup": {"status": "PASS", "verified": True, "blockers": "Backup offsite verificado com sucesso"},
            "external_dependencies": {"status": "PASS", "cleared": True},
            "owner_authorization": {"status": "PASS", "authorized": True, "message": "Autorizacao expressa concedida"},
        }
        orch = pda.PreDeletionAuditOrchestrator(root_dir=ROOT, overrides=satisfied_conditions)
        result = orch.run_audit()

        self.assertEqual(result["passed_conditions_count"], 11)
        self.assertEqual(result["failed_conditions_count"], 0)
        self.assertIn("PASS", result["overall_verdict"])

        # Check that legacy repositories now show deletion authorized
        for disp in result["repository_dispositions"]:
            if disp["repository"] in pda.LEGACY_CANDIDATE_REPOSITORIES:
                self.assertEqual(disp["deletion_status"], "AUTORIZADO PARA EXCLUSAO")

    def test_report_saving_and_json_validity(self) -> None:
        """Verify Markdown and JSON reports are generated accurately in custom paths."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            md_path = Path(tmp_dir) / "REPORT.md"
            json_path = Path(tmp_dir) / "REPORT.json"

            audit_result = self.orchestrator.run_audit()
            ret_md, ret_json = self.orchestrator.save_reports(audit_result, md_path=md_path, json_path=json_path)

            self.assertTrue(ret_md.is_file())
            self.assertTrue(ret_json.is_file())

            md_content = ret_md.read_text(encoding="utf-8")
            self.assertIn("Relatorio de Auditoria Pre-Exclusao", md_content)
            self.assertIn("COND-01-REPOSITORIES-INVENTORIED", md_content)
            self.assertIn("COND-09-OFFSITE-BACKUP-VERIFIED", md_content)

            with open(ret_json, "r", encoding="utf-8") as f:
                loaded_json = json.load(f)
            self.assertEqual(loaded_json["total_repositories_audited"], 9)
            self.assertIn("COND-01-REPOSITORIES-INVENTORIED", loaded_json["conditions"])

    def test_zero_emoji_compliance(self) -> None:
        """Enforce Zero Emoji Policy across script, tests, and generated reports."""
        emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]")

        # Run orchestrator and generate reports
        audit_result = self.orchestrator.run_audit()
        md_text = self.orchestrator.generate_markdown_report(audit_result)
        json_text = json.dumps(audit_result, ensure_ascii=False)

        # Files to check
        script_file = ROOT / "scripts/pre_deletion_audit.py"
        test_file = ROOT / "tests/test_pre_deletion_audit.py"

        for name, text in [
            ("scripts/pre_deletion_audit.py", script_file.read_text(encoding="utf-8")),
            ("tests/test_pre_deletion_audit.py", test_file.read_text(encoding="utf-8")),
            ("generated Markdown report", md_text),
            ("generated JSON report", json_text),
        ]:
            matches = emoji_pattern.findall(text)
            self.assertEqual(
                len(matches),
                0,
                f"Zero Emoji Policy violated in {name}! Found emojis: {matches}",
            )

    def test_cli_strict_mode(self) -> None:
        """Verify CLI --strict flag exits with code 1 when deletion is blocked."""
        import subprocess

        cmd = [sys.executable, str(ROOT / "scripts/pre_deletion_audit.py"), "--strict", "--check-only"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL - REPOSITORY DELETION HARD-BLOCKED", proc.stdout)

    def test_cli_normal_mode(self) -> None:
        """Verify CLI default execution completes with code 0 and prints audit summary."""
        import subprocess

        cmd = [sys.executable, str(ROOT / "scripts/pre_deletion_audit.py"), "--check-only"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("[AUDIT] Overall Verdict:", proc.stdout)

    def test_pre_deletion_report_files_exist_and_conform(self) -> None:
        """Verify official reports/PRE-DELETION-AUDIT-REPORT.md and .json exist and are valid."""
        md_file = ROOT / "reports/PRE-DELETION-AUDIT-REPORT.md"
        json_file = ROOT / "reports/PRE-DELETION-AUDIT-REPORT.json"

        self.assertTrue(md_file.is_file(), "reports/PRE-DELETION-AUDIT-REPORT.md must exist")
        self.assertTrue(json_file.is_file(), "reports/PRE-DELETION-AUDIT-REPORT.json must exist")

        md_content = md_file.read_text(encoding="utf-8")
        self.assertIn("Relatorio de Auditoria Pre-Exclusao", md_content)
        self.assertIn("COND-01-REPOSITORIES-INVENTORIED", md_content)
        self.assertIn("COND-07-NOTES-APP-PRIVATE-PRESERVED", md_content)
        self.assertIn("COND-09-OFFSITE-BACKUP-VERIFIED", md_content)
        self.assertIn("BLOQUEADO PARA EXCLUSAO", md_content)

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["total_repositories_audited"], 9)
        self.assertFalse(data["can_delete_repositories"])
        self.assertEqual(data["repositories_blocked_from_deletion"], 9)
        self.assertEqual(data["repositories_eligible_read_only_archive"], 4)


if __name__ == "__main__":
    unittest.main()
