# Semantic Ingestion & Source Coverage Audit (#82)

- Generated at: `2026-11-25T22:31:17.586837+00:00`
- Registry version: `1.0.0` (`9224f9c30c762475`)
- Egress policy: `offline-local-only`

## 1. Universe Coverage Summary

- Registered sources: **12**
- Local eligible files audited: **419** (excluded by policy: **1034**)
- Extracted knowledge units (AST + Docs + Metadata + Visual records): **2443**
- Distinct MIME types observed: **11**

### Lifecycle State Distribution

| Lifecycle State | Count |
|---|---:|
| `located` | 0 |
| `retrieved` | 0 |
| `extracted` | 30 |
| `indexed` | 111 |
| `queryable` | 48 |
| `verified` | 230 |
| `partial` | 1 |
| `unavailable` | 5 |

### Modality Coverage

| Modality | Files | Knowledge Units |
|---|---:|---:|
| `ast_code` | 105 | 1406 |
| `document` | 125 | 817 |
| `metadata` | 115 | 85 |
| `media_visual` | 74 | 74 |

## 2. Visual Media Audit (Verified vs Inferred)

- Total visual catalog records: **61**
- Verified local blobs (`archived-blob-verified` / declared): **35**
- Link-only external references: **26**
- Sampled frames reviewed (`sampled-frames-reviewed`): **9**
- Uninspected visual records (not inferred from filenames): **52**
- Duplicate blob groups (deduplicated by `blob_sha`): **0**

## 3. Traceability Graph (Requirement -> Decision -> Implementation -> Test -> Visual -> Version)

- Total graph nodes: **245**
- Total graph edges: **367**
- Orphan nodes detected: **3**

| Node Type | Count |
|---|---:|
| `decision_or_doc` | 55 |
| `implementation` | 56 |
| `requirement` | 37 |
| `test` | 35 |
| `version` | 1 |
| `visual_evidence` | 61 |

## 4. Source Inventory & Bundle Recovery

| Source ID | Adapter | Scope | Origin Status | Files Included | Files Excluded | Units |
|---|---|---|---|---:|---:|---:|
| `repo.exams-app` | `github_api` | `public` | `online` | 0 | 0 | 0 |
| `bundle.exams-app-old` | `git_bundle` | `authenticated_archive` | `historical_unavailable` | 0 | 1 | 0 |
| `bundle.exams-app-antigo-2` | `git_bundle` | `authenticated_archive` | `historical_unavailable` | 0 | 1 | 0 |
| `bundle.shadcn-template` | `git_bundle` | `authenticated_archive` | `historical_unavailable` | 0 | 1 | 0 |
| `bundle.shadcn-firebase-template` | `git_bundle` | `authenticated_archive` | `historical_unavailable` | 0 | 1 | 0 |
| `bundle.notes-app` | `git_bundle` | `authenticated_archive` | `private_authenticated` | 0 | 1 | 0 |
| `local.archive-docs-and-reports` | `local_fs` | `public` | `online` | 130 | 465 | 560 |
| `local.research-catalogs` | `local_fs` | `public` | `online` | 46 | 110 | 203 |
| `local.visual-evidence-library` | `local_fs` | `public` | `online` | 56 | 8 | 72 |
| `local.grok-bot-media` | `local_fs` | `public` | `online` | 14 | 3 | 30 |
| `local.visual-library-legacy` | `local_fs` | `public` | `online` | 14 | 7 | 14 |
| `local.code-and-tests` | `local_fs` | `public` | `online` | 159 | 436 | 1503 |

## 5. Backlog of Coverage Gaps

- **[repo.exams-app] `bundle_blobs_not_mounted_locally`**: Manifest 'manifests/exams-app-complete-2026-11-23.json' is verified locally; full Git objects live in release bundle.
- **[bundle.exams-app-old] `authorization_or_bundle_restore_required`**: Source 'bundle.exams-app-old' (historical_unavailable) requires authenticated bundle restoration locally; not indexed publicly.
- **[bundle.exams-app-antigo-2] `authorization_or_bundle_restore_required`**: Source 'bundle.exams-app-antigo-2' (historical_unavailable) requires authenticated bundle restoration locally; not indexed publicly.
- **[bundle.shadcn-template] `authorization_or_bundle_restore_required`**: Source 'bundle.shadcn-template' (historical_unavailable) requires authenticated bundle restoration locally; not indexed publicly.
- **[bundle.shadcn-firebase-template] `authorization_or_bundle_restore_required`**: Source 'bundle.shadcn-firebase-template' (historical_unavailable) requires authenticated bundle restoration locally; not indexed publicly.
- **[bundle.notes-app] `authorization_or_bundle_restore_required`**: Source 'bundle.notes-app' (private_authenticated) requires authenticated bundle restoration locally; not indexed publicly.
- **[local.visual-evidence-library] `visual_semantic_inspection_incomplete`**: 52 visual media records lack human/sampled-frame semantic inspection; never infer UI behavior from filename alone.
