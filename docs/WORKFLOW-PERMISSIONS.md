# Workflow Permissions Inventory

This document catalogs every GitHub Actions workflow in `.github/workflows/`, its trigger model, declared `permissions:`, classification, and justification for any write permissions.

## Classification Summary

| Workflow | Classification | Triggers | Permissions | Write Justification |
|---|---|---|---|---|
| `tests.yml` | Active CI | `pull_request`, `push` (`main` paths), `workflow_dispatch` | `contents: read` | None (read-only) |
| `archive-plugin-test.yml` | Active CI | `pull_request`, `push` (`main` paths) | `contents: read` | None (read-only; uses `GH_TOKEN` to read private release index) |
| `plugin-validation.yml` | Active CI | `pull_request`, `push` (`main` paths), `workflow_dispatch` | `contents: read` | None (read-only; uploads workflow artifact only) |
| `archive-pages.yml` | Active deployment | `workflow_dispatch`, `push` (`main`: `site/**`) | `contents: read`, `pages: write`, `id-token: write` | Deploys static public shell to GitHub Pages via OIDC |
| `archive-private-search.yml` | Active query bridge | `push` (`archive-search-queries`) | `contents: write` | Commits bounded query results to `.archive-search/results` on branch `archive-search-queries` |
| `receive-notes-transfer.yml` | Preservation / transfer | `push` (`notes-private-import`) | `contents: write` | Publishes private release `notes-app-2026-11-23-private-full` and deletes transfer branch `notes-private-import` |
| `archive-private-notes.yml` | Preservation / backup | `workflow_dispatch`, `push` (`main`: self) | `contents: write`, `actions: read` | Creates/updates private release and commits `manifests/notes-app-private-full.json` to `main` |
| `archive-audit-complement.yml` | Preservation / backup | `push` (`main`: self) | `contents: write` | Commits `manifests/release-2026-11-23-audit-complements.json` and creates private release bundles |
| `archive-ci-evidence-sample.yml` | Preservation / backup | `workflow_dispatch`, `push` (`main`: self) | `contents: write`, `actions: read` | Creates and publishes private release `legacy-ci-evidence-sample-2026-11-23` |
| `archive-legacy-ci-artifacts.yml` | Preservation / backup | `workflow_dispatch`, `push` (`main`: self) | `contents: write`, `actions: read` | Creates and uploads shard TARs/manifests to private release `legacy-ci-artifacts-2026-11-23-bulk` |
| `archive-legacy-github-extras.yml` | Preservation / backup | `workflow_dispatch`, `push` (`main`: self) | `contents: write`, `discussions: read`, `repository-projects: read` | Creates and publishes private release `legacy-github-extras-2026-11-23` |
| `archive-poc.yml` | Historical / POC | `workflow_dispatch`, `push` (`main`: `scripts/**`, `tests/**`, self) | `contents: write` | Commits `reports/POC.md`, `reports/POC.json`, `reports/archive-index.sqlite` to `main` |
| `archive-release.yml` | Preservation / backup | `workflow_dispatch`, `push` (`main`: `scripts/create_release_archives.py`, self) | `contents: write` | Creates private release `archive-2026-11-23` and commits `manifests/release-2026-11-23.json` and `manifests/README.md` |
| `audit-public-git-externals.yml` | Preservation / audit | `push` (`main`: self) | `contents: write` | Commits `reports/PUBLIC-GIT-EXTERNALS.json` and `reports/PUBLIC-GIT-EXTERNALS.md` to `main` |
| `exams-app-complete.yml` | Preservation / backup | `push` (`main`: self) | `contents: write` | Creates private release `exams-app-2026-11-23-complete` and commits inventory/manifest/docs to `main` |
| `export-public-platform-metadata.yml` | Preservation / backup | `push` (`main`: self) | `contents: write`, `actions: read` | Creates private release `public-metadata-2026-11-23` and commits metadata reports/manifests to `main` |
| `full-index-archive.yml` | Preservation / indexing | `push` (`main`: self) | `contents: write` | Creates private release index asset and commits `reports/FULL-INDEX.*` to `main` |
| `index-all-git-refs.yml` | Preservation / indexing | `push` (`main`: self) | `contents: write` | Creates private release index asset and commits `reports/FULL-INDEX.*` to `main` |
| `index-exams-app-complete.yml` | Preservation / indexing | `push` (`main`: self) | `contents: write` | Creates private release `index-2026-11-23-exams-complete` and commits `reports/FULL-INDEX.*` to `main` |
| `preserve-all-git-refs.yml` | Preservation / backup | `push` (`main`: self) | `contents: write` | Creates private release `archive-2026-11-23-all-refs` and commits `manifests/release-2026-11-23-all-refs.json` and `manifests/ALL-REFS.md` |
| `preserve-exams-app-ci-logs.yml` | Preservation / backup | `push` (`main`: self) | `contents: write`, `actions: read` | Creates private release `exams-app-2026-11-23-ci-logs` and commits `reports/EXAMS-APP-ACTIONS-LOGS.json` |
| `publish-legacy-artifact-release.yml` | Preservation / backup | `push` (`main`: self), `workflow_dispatch` | `contents: write` | Edits private release `legacy-ci-artifacts-2026-11-23-bulk` (`--draft=false`) |
| `repair-legacy-evidence-manifests.yml` | Preservation / repair | `workflow_dispatch`, `push` (`main`: self) | `contents: write` | Uploads repaired manifest JSONs to private release `legacy-ci-artifacts-2026-11-23-bulk` |
| `verify-embedded-bundles.yml` | Preservation / audit | `push` (`main`: self) | `contents: write` | Commits `reports/embedded-bundles-audit.json` and `reports/embedded-bundles-audit.md` to `main` |
| `verify-exams-app-extras.yml` | Preservation / audit | `push` (`main`: self) | `contents: write`, `actions: read` | Commits `reports/EXAMS-APP-VERIFY.json` and `reports/EXAMS-APP-VERIFY.md` to `main` |
| `verify-legacy-archive.yml` | Preservation / audit | `workflow_dispatch`, `push` (`main`: self) | `contents: read` | None (read-only; uploads workflow artifact `legacy-delete-readiness`) |

## Governance Guardrail

`tests/test_workflow_permissions.py` enforces least-privilege governance on `.github/workflows/*.yml`:

1. Every workflow must declare an explicit `permissions:` block.
2. Any workflow declaring a `: write` permission must be explicitly justified in the allowlist in `tests/test_workflow_permissions.py` and match the exact set of allowed write scopes documented in this inventory.
3. Adding a new workflow with write permissions—or expanding write permissions on an existing workflow—fails `pytest` unless an explicit justification is added and documented here.
4. Notice that all existing backup, preservation, indexing, `archive-private-search.yml`, and `archive-private-notes.yml` workflows legitimately push commits to `main`/`archive-search-queries`, publish/edit private GitHub Releases, or clean up transfer branches, so their `contents: write` permissions were audited and preserved rather than stripped.
