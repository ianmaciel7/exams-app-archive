---
name: save
description: Use when the user says "save", "/save", "salve o que aprendemos", or asks to persist reusable learning from the current conversation into the relevant plugins and repositories. Execute scoped, verified updates instead of merely summarizing; do not treat ordinary conversation as authorization.
---

# Save reusable knowledge

Use the completed work and feedback from the current conversation. Recover prior context only if the requested learning cannot be identified. Do not restart research unnecessarily or save unverified claims as facts.

## Workflow

1. **Extract:** identify durable decisions, corrections, patterns, procedures, acceptance criteria and sources. Separate verified facts, user-approved local conventions, proposed ideas, and unresolved gaps. Ignore transient chatter and redundant details.
2. **Route:** identify the owning plugin/skill, canonical repository, and affected active project. For UI/UX use Especialista em UI/UX's aprendizado-incremental, shared-ux-knowledge, and Exams Archive's sync-bridge when modifying its installed plugin or mirror. Default to the two existing UI/UX plugins and their relevant canonical knowledge, plus Exams App dev only when a project-specific instruction is affected. Never write unrelated repositories. Follow each destination's instructions and scope. If the user explicitly requests memory or Library persistence, follow sync-ux-knowledge and report its independent verification.
3. **Preflight:** inspect current release IDs, manifests, file paths, repository refs and permissions; compare current source, canonical records and existing PRs. Detect conflicts and drift. Do not use last-write-wins. Reuse stable concept IDs and avoid duplicate entries, repeated version bumps or needless commits.
4. **Persist:** create one compact, evidence-backed delta; update existing relevant documentation, skills, indexes and project instructions in place, including affected dependencies. Create a new reference only when the concept has no appropriate home. Preserve unrelated data and historical records. Publish plugin overlays with guarded release IDs and version bumps, and repository changes with expected revisions and reviewed PRs or authorized commits. Keep private data and restricted media out of public repositories.
5. **Verify:** read back each destination, comparing intended content, version, release, SHA, branch and PR/merge state. Validate schema and relevant tests when available. If already present, report a no-op. If access fails, complete the remaining authorized writes and provide exact pending steps. Never claim a local file or an open PR is an installed release or merged change.
6. **Report:** compact status per destination, links, version/commit/PR, changes, verified tests, drift and blockers. Do not schedule, launch background work, or invent success. A bare "save" authorizes this bounded workflow for the current reusable learning, not indiscriminate conversation archival, publication of personal data or application changes unrelated to that learning.

## Example

A sketch review establishes that composition-only sketches should replace nonessential labels with strokes, retaining semantic labels only when necessary. Save the rule as a local design convention (not a universal standard) in the relevant sketch guidance, shared UX contract and project instructions; use the canonical reference rather than duplicating its full content. Distinguish sketch, structural wireframe and mockup/prototype responsibilities. Verify each target independently.
