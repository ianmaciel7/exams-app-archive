---
name: sync-ux-knowledge
description: "Execute when the user asks 'mande tudo memoria,plugin,github', 'mande tudo memoria,plugin,gihtub', 'salve tudo na memória, plugin e GitHub', 'sincronize conhecimento UI/UX' or equivalent explicit request. Consolidate a single evidence-backed UX knowledge delta, update the private Especialista em UI/UX plugin, the Exams Archive GitHub repository, ChatGPT memory where supported, and the existing private Library reference file; verify each destination independently."
---

# Sync UX Knowledge — one research batch, four destinations

## Intent and routing

The explicit command “mande tudo memoria,plugin,github” (including typos, accents, and equivalent Portuguese/English phrases) requests actual synchronization of the current UI/UX knowledge, not another explanation, a new research task, or a change to application code. Use the current conversation and completed research result; recover prior research only if necessary. Do not assume a pending Deep Research task has completed. If no report is available, preserve only supported findings and identify the missing report. This is not an autonomous scheduled process.

- **Plugin** always means the user's existing private **Especialista em UI/UX** (`especialista-ui-ux`), not Exams Archive. Resolve its exact installed/owned ID via authorized Plugin Creator or Plugin Management; confirm name, ownership, privacy, current release ID. Read its incremental learning skill and canonical reference index. Do not create a new plugin or silently substitute another.
- **GitHub** always means `ianmaciel7/exams-app-archive@main`, not active Exams App/Notes App repositories. Public archive: only general, nonprivate, licensed-to-share knowledge may be published. Read current head and source register before editing.
- **Memória** means ChatGPT personal memory **and** the existing Markdown file in the user's private ChatGPT Library, `/Referencias/UI-UX/referencias-ui-ux-2026.md`. Verify exact file by listing the folder; if missing, search exact title before creating anything. Do not create a duplicate or another public copy of personal data. The path is a configuration default, not proof of access.
- **Exams Archive plugin** hosts this orchestration skill only. Change its source/release only if the user explicitly requests changing the workflow, then use `sync-bridge`. Ordinary research batches update the UX specialist, not this host.

## Fast execution

1. **Resolve and preflight once.** Read completed source material and existing relevant sections, not the entire archive. Discover only needed tools. Confirm Github permissions/visibility/head, UX plugin release and actual relevant paths, Library file identity/current content, and supported memory capability. Independent read-only requests may be batched where tool rules permit.
2. **Build one canonical delta.** Record original term, aliases, category, context, problem, solution, rationale, trade-offs, limitations, accessibility, acceptance tests, source URLs, provenance, access/evidence status and review date. Separate pattern, principle, guideline, standard, implementation technique, hypothesis and formal decision. For video/screenshots record original rights, source and status; never copy restricted media. Do not invent examples, rankings, measurements or research completion. Match existing entries by semantic ID and normalized URL; preserve historical links and provenance. Distinguish new entries from cross-indexed existing concepts. No changes if already identical.
3. **Publish archive delta** in one guarded commit (or PR if required). Use canonical files under `docs/references/interface-pattern-library/` and `docs/references/ui-ux-research-sources/` when they fit; update Markdown/JSON, source register, relevant index and synchronization record. Use current tree plus only intended files and expected head. Preserve existing archives, reports and unrelated changes. Treat concurrent conflicts as conflicts, not last-write-wins. Do not publish private research, secrets, full conversations, internal plugin IDs, signed URLs or licensed media.
4. **Publish UX specialist delta** using its learning protocol, one overlay archive per batch, same identity and guarded release ID. Preserve unrelated files, manifests, existing source metadata and versions; bump patch only for material changes. Use actual host-uploaded archive with valid path; do not guess a ZIP path or claim local creation is publication. Read back changed reference files, manifest version and routing skill after success.
5. **Update the private Library Markdown** by preserving its original contents and merging the same knowledge delta and all relevant direct source URLs. Include canonical archive links, review date, source/evidence boundaries and current counts. Edit only the verified native file using a supported file mutation; if a container copy is needed, materialize, preserve existing text, and upload explicitly to the exact verified path with safe replacement semantics. For shared files use version guard as supported. Re-list/re-read the exact destination; avoid duplicate files or losing historical links. A new companion file is not a verified update of the canonical file.
6. **ChatGPT memory:** request only a concise durable preference/knowledge summary and pointers to the canonical Library, archive and UX plugin through supported memory functionality. Never store full URLs/catalog as the sole memory mechanism. If memory has no writable/verifiable capability, is disabled, or updates asynchronously, state that persistence is unconfirmed; do not claim success, manipulate settings, or simulate memory via a file. Memory is independent of Library.
7. **Read back and reconcile.** Compare pattern IDs and content, normalized source URL sets, source metadata/provenance, version, release, branch and commit. Compare the Library's actual preserved links and added sections. Record partial states separately; finalize archive sync record after plugin readback. Never label entire batch synced when one destination failed. No background work or extra confirmation unless needed for a real permission or conflict.

## Output contract

Report one compact table: archive commit/main, UX specialist version/release, Library file and actual readback, ChatGPT memory status (confirmed only if explicitly verified; otherwise pending/unconfirmed). Include direct links, counts of added vs retained patterns and sources, any drift, and blockers. Distinguish confirmed publication from staged artifacts/PRs. If one operation fails, complete other authorized destinations, preserve existing versions, provide exact next step; do not repeat already verified writes. Do not request the user repeat known destinations.

## Acceptance scenarios

- A completed research batch with new patterns: one delta, one archive content commit, one UX plugin publication, Library merge, honest memory status; readback matching entries and URLs.
- Same batch again: idempotent no-op, no redundant version bump, no duplicate URLs or Library files.
- Incomplete report: no fabricated report, save verified available facts only and state limitation.
- Public archive + private content: separate or redact, never leak private source or credentials.
- Plugin conflict/release drift, archive concurrent changes, Library missing or memory unavailable: preserve unaffected destinations, verify partial completion, report exact blocker.
- User says "plugin": target Especialista em UI/UX, not the orchestrator; explicit request to modify Exams Archive skill instead invokes sync-bridge.

This workflow is an instruction skill, not a new tool, automatic synchronizer or guarantee of faster external services. It reduces redundant discovery, research and commits.
