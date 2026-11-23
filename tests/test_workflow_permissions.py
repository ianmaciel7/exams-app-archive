#!/usr/bin/env python3
"""Governance tests ensuring least-privilege GitHub Actions workflow permissions."""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
INVENTORY_DOC = ROOT / "docs" / "WORKFLOW-PERMISSIONS.md"
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

# Explicit allowlist of workflows that require write permissions, mapped to
# the exact set of write scopes allowed and a concise justification.
# Any new workflow declaring ': write' (or any existing workflow adding new
# write scopes) will fail this test unless explicitly justified here and
# documented in docs/WORKFLOW-PERMISSIONS.md.
JUSTIFIED_WRITE_WORKFLOWS: dict[str, tuple[set[str], str]] = {
    "archive-audit-complement.yml": (
        {"contents"},
        "Commits manifests/release-2026-11-23-audit-complements.json and uploads private release bundles.",
    ),
    "archive-ci-evidence-sample.yml": (
        {"contents"},
        "Creates and publishes private release legacy-ci-evidence-sample-2026-11-23.",
    ),
    "archive-legacy-ci-artifacts.yml": (
        {"contents"},
        "Creates and uploads shard TARs and manifests to private release legacy-ci-artifacts-2026-11-23-bulk.",
    ),
    "archive-legacy-github-extras.yml": (
        {"contents"},
        "Creates and publishes private release legacy-github-extras-2026-11-23.",
    ),
    "archive-pages.yml": (
        {"pages", "id-token"},
        "Deploys static public shell to GitHub Pages via OIDC (contents remains read).",
    ),
    "archive-poc.yml": (
        {"contents"},
        "Publishes POC SQLite asset to private release poc-archive-index and commits reports/POC.md and reports/POC.json to main.",
    ),
    "archive-private-notes.yml": (
        {"contents"},
        "Creates private notes release and commits manifests/notes-app-private-full.json to main.",
    ),
    "archive-private-search.yml": (
        {"contents"},
        "Commits bounded query results to .archive-search/results on branch archive-search-queries.",
    ),
    "archive-release.yml": (
        {"contents"},
        "Creates private release archive-2026-11-23 and commits manifests to main.",
    ),
    "audit-public-git-externals.yml": (
        {"contents"},
        "Commits reports/PUBLIC-GIT-EXTERNALS.json and .md to main.",
    ),
    "exams-app-complete.yml": (
        {"contents"},
        "Creates private release exams-app-2026-11-23-complete and commits inventory/manifest/docs to main.",
    ),
    "export-public-platform-metadata.yml": (
        {"contents"},
        "Creates private release public-metadata-2026-11-23 and commits metadata reports/manifests to main.",
    ),
    "full-index-archive.yml": (
        {"contents"},
        "Creates private release index asset and commits reports/FULL-INDEX.* to main.",
    ),
    "index-all-git-refs.yml": (
        {"contents"},
        "Creates private release index asset and commits reports/FULL-INDEX.* to main.",
    ),
    "index-exams-app-complete.yml": (
        {"contents"},
        "Creates private release index-2026-11-23-exams-complete and commits reports/FULL-INDEX.* to main.",
    ),
    "preserve-all-git-refs.yml": (
        {"contents"},
        "Creates private release archive-2026-11-23-all-refs and commits manifests to main.",
    ),
    "preserve-exams-app-ci-logs.yml": (
        {"contents"},
        "Creates private release exams-app-2026-11-23-ci-logs and commits reports/EXAMS-APP-ACTIONS-LOGS.json.",
    ),
    "publish-legacy-artifact-release.yml": (
        {"contents"},
        "Edits private release legacy-ci-artifacts-2026-11-23-bulk to publish from draft.",
    ),
    "receive-notes-transfer.yml": (
        {"contents"},
        "Publishes private release notes-app-2026-11-23-private-full and deletes transfer branch.",
    ),
    "repair-legacy-evidence-manifests.yml": (
        {"contents"},
        "Uploads repaired manifest JSON files to private release legacy-ci-artifacts-2026-11-23-bulk.",
    ),
    "verify-embedded-bundles.yml": (
        {"contents"},
        "Commits reports/embedded-bundles-audit.json and .md to main.",
    ),
    "verify-exams-app-extras.yml": (
        {"contents"},
        "Commits reports/EXAMS-APP-VERIFY.json and .md to main.",
    ),
}

# Read-only workflows that must never acquire write permissions silently.
READ_ONLY_WORKFLOWS = {
    "archive-plugin-test.yml",
    "plugin-validation.yml",
    "tests.yml",
    "verify-legacy-archive.yml",
}


def parse_workflow_permissions(text: str) -> tuple[bool, dict[str, str]]:
    """Parse top-level and job-level permissions declarations from a workflow YAML."""
    lines = text.splitlines()
    found_permissions_block = False
    perms: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        match = re.match(r"^(\s*)permissions:\s*(.*)$", line)
        if match:
            found_permissions_block = True
            base_indent = len(match.group(1))
            inline_val = match.group(2).strip()
            if inline_val:
                perms["__inline__"] = inline_val
                i += 1
                continue
            i += 1
            while i < len(lines):
                sub = lines[i]
                sub_stripped = sub.strip()
                if not sub_stripped or sub_stripped.startswith("#"):
                    i += 1
                    continue
                sub_indent = len(sub) - len(sub.lstrip(" "))
                if sub_indent <= base_indent:
                    break
                kv = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*([A-Za-z0-9_-]+)", sub_stripped)
                if kv:
                    perms[kv.group(1)] = kv.group(2)
                i += 1
            continue
        i += 1
    return found_permissions_block, perms


class WorkflowPermissionsTests(unittest.TestCase):
    def test_all_workflows_declare_explicit_permissions(self):
        workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml"))
        self.assertGreater(len(workflow_files), 0)
        for wf in workflow_files:
            found, perms = parse_workflow_permissions(wf.read_text(encoding="utf-8"))
            self.assertTrue(found, f"{wf.name} must declare an explicit permissions block")
            self.assertGreater(len(perms), 0, f"{wf.name} has an empty permissions block")

    def test_no_unjustified_write_permissions(self):
        workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml"))
        for wf in workflow_files:
            _, perms = parse_workflow_permissions(wf.read_text(encoding="utf-8"))
            inline = perms.get("__inline__", "")
            self.assertNotIn(
                inline,
                {"write-all"},
                f"{wf.name} must not use broad write-all permissions",
            )
            write_scopes = {k for k, v in perms.items() if v == "write"}
            if write_scopes:
                self.assertIn(
                    wf.name,
                    JUSTIFIED_WRITE_WORKFLOWS,
                    f"Workflow {wf.name} declares write permissions {sorted(write_scopes)} "
                    "without a listed justification in JUSTIFIED_WRITE_WORKFLOWS",
                )
                allowed_scopes, justification = JUSTIFIED_WRITE_WORKFLOWS[wf.name]
                self.assertTrue(justification.strip(), f"Empty justification for {wf.name}")
                self.assertEqual(
                    write_scopes,
                    allowed_scopes,
                    f"{wf.name} write scopes {sorted(write_scopes)} do not match justified scopes {sorted(allowed_scopes)}",
                )
            else:
                self.assertNotIn(
                    wf.name,
                    JUSTIFIED_WRITE_WORKFLOWS,
                    f"{wf.name} is listed in JUSTIFIED_WRITE_WORKFLOWS but declares no write scopes",
                )

    def test_read_only_workflows_have_only_read_permissions(self):
        for name in READ_ONLY_WORKFLOWS:
            wf = WORKFLOWS_DIR / name
            self.assertTrue(wf.is_file(), f"Missing expected read-only workflow: {name}")
            _, perms = parse_workflow_permissions(wf.read_text(encoding="utf-8"))
            self.assertEqual(perms.get("contents"), "read", f"{name} must set contents: read")
            write_scopes = {k for k, v in perms.items() if v == "write"}
            self.assertEqual(write_scopes, set(), f"{name} must not declare write scopes")

    def test_ci_tests_workflow_covers_all_required_paths(self):
        ci_wf = WORKFLOWS_DIR / "tests.yml"
        self.assertTrue(ci_wf.is_file(), "Missing .github/workflows/tests.yml")
        text = ci_wf.read_text(encoding="utf-8")
        self.assertIn("pull_request:", text)
        self.assertIn("push:", text)
        self.assertIn("pytest", text)
        self.assertIn("node --check site/app.js", text)
        for required_path in ("scripts/**", "plugins/**", "site/**", "tests/**"):
            self.assertIn(required_path, text)

    def test_inventory_doc_lists_all_workflows_and_no_emojis(self):
        self.assertTrue(INVENTORY_DOC.is_file(), "Missing docs/WORKFLOW-PERMISSIONS.md")
        doc = INVENTORY_DOC.read_text(encoding="utf-8")
        self.assertEqual(EMOJI_REGEX.findall(doc), [], "Found emoji in docs/WORKFLOW-PERMISSIONS.md")
        for wf in sorted(WORKFLOWS_DIR.glob("*.yml")):
            self.assertIn(wf.name, doc, f"{wf.name} missing from docs/WORKFLOW-PERMISSIONS.md")

    def test_zero_emoji_in_changed_ci_files(self):
        for path in (
            WORKFLOWS_DIR / "tests.yml",
            WORKFLOWS_DIR / "archive-plugin-test.yml",
            Path(__file__),
        ):
            content = path.read_text(encoding="utf-8")
            self.assertEqual(EMOJI_REGEX.findall(content), [], f"Found emoji in {path}")


if __name__ == "__main__":
    unittest.main()
