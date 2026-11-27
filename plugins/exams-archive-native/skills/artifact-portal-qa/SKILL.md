---
name: artifact-portal-qa
description: Use when publishing, organizing, styling, auditing or verifying a native Open Artifact library, Playground, GitHub Pages board portal, artifact previews, native editor Shell or screenshot fallback; distinguishes static previews from persistent hosting and validates public deployment.
---

# Native artifact portals: design and delivery contract

Reviewed 2026-11-27. This is source-backed implementation guidance and a project case study, not a universal UX standard or a new runtime capability.

## Reuse before building a viewer

- Confirm the exact upstream identity (JimLiu/open-artifact, formerly baoyu-design), installed skill package version, actual runtime version, release/tag/commit and available host before deciding. The private plugin package is not a hosted editor; a package patch does not upgrade its vendored runtime.
- Upstream v0.17.0 introduced a static Playground using the real Shell and editors with a browser-memory provider. Its README explicitly documents GitHub Pages, project base paths, build output and deep links. Distinguish this from the full Open Artifact Host (Node or Cloudflare, persistent collaboration, auth, APIs/remote MCP), and from a PNG portal. No backend is needed for temporary interactive viewing; shared storage, real agent requests and comments persisted across sessions are NOT provided by the static Playground.
- Prefer adapting the upstream seed loader/editor and design tokens to the committed artifact directories over reconstructing an editor. Pin the source revision; build in an isolated temporary checkout; copy the same committed board snapshot as the screenshot manifest. Preserve original JSON, IDs, order, native geometry and historical source. Exclude local/private comments, history, credentials and unpublished assets from public Pages; publish only approved public content. Disable simulated agent requests; make temporary edits/no persistence explicit. Do not present a fake agent, fake success or fake comments.
- Keep the existing read-only screenshots and original native runtime as a fallback until the optional parallel build passes. Gate publication of the preview and its navigation link on all boards passing; rollback independently. Do not migrate source boards merely to improve portal presentation.

## Library and Shell UX

- Reuse the actual native artifact library pattern: compact heading, semantic light/dark tokens, responsive grid, genuine 16:9 board thumbnails, concise title and metadata, one clear link per card, keyboard focus, no decorative emoji or marketing chrome. Prefer a representative authentic image without distortion; do not invent thumbnails. Keep the screenshot portal accessible separately.
- A library is a navigation surface, not a new product stage. Group project-wide boards separately from release artifacts; group product/structure and interface design; number release stages from the canonical ordered release-state record, not alphabetical order, screenshot content or element counts. Show current stage and its status from that record; distinguish in-progress, complete for progression and approved. Don't invent approval or imply a blank/unstarted board exists. Provide direct current-stage access. Grid/List are alternative views of identical objects in identical semantic order; persist the view preference locally if supported, make both keyboard accessible and test responsive reflow.
- Maintain shell continuity: inspect original TopBar and shared UI tokens before restyling. Remove unrelated demo-only banners, language toggles and dismiss controls; avoid a separate bright strip competing with the native header. Integrate the return-to-library action and concise temporary-edits indicator in the existing Shell header using native button/icon styles, accessible names, and neutral typography. Do not suppress persistence warnings or remove native editor functionality. The user specifically rejected a visually inconsistent blue demo strip and an unstyled list home; these are project feedback, not universal rules.
- Preserve the user's existing stage-specific sketch/wireframe responsibilities, notes, anchored comments and source links. Public preview limitations are not a reason to rewrite the boards. Genuine native screenshots should be shown directly in chat where supported, not represented by invented mockups or bare links; distinguish an actual capture from a schematic preview.

## Verification and publication

1. Check the active branch at start/end, pinned upstream, exact manifest commit, actual board content and counts. A sparse/empty board may be intentional; compare board metadata and files before blaming deployment. Distinguish build, upload, deploy and public URL serving.
2. CI must verify the exact optional Playground step, not just overall green status (continue-on-error can conceal a failed optional build). Canceled/superseded runs are not deployment proof. Test at the repository subpath: each board's exact persisted IDs in store and rendered layer, page identity, console/errors, link targets and back navigation; distinguish element coverage from visual/interaction fidelity.
3. Test real home thumbnails in both tested themes, stage order and current shortcut, Grid/List preference and keyboard activation, no horizontal overflow at desktop/mobile. For the header, verify one bar, no legacy demo controls, correct return link, warning visible, narrow-width clipping, focus and actual navigation. Test visual parity, comments, uploads, theme, zoom and interactions independently; do not infer them from element counts or a screenshot.
4. Verify the PUBLIC page after deploy: actual loaded commit/title/DOM and representative board routes, not only CI. If browser displays an older SHA, distinguish cache/CDN propagation from source errors; try a versioned query URL and confirm its content, do not assert cache as the cause without evidence. Report pending publication or visual QA honestly. Never say a URL was opened if it was not.
5. For project-specific evidence, link immutable source/CI revisions. Successful CI 46006601771 (165f554) verified ten board element sets and deploy; 46008354579 (f093629) verified ten cards/thumbnails at 1440x900 dark and 390x844 light, ten board sets and deploy. The user subsequently saw the older SHA in the browser, then acknowledged the versioned link. Canonical-order/Grid-List commit 2e3e0e8 and native-header commit d8606ff were pushed; their publication/visual approval was not established in that exchange. Recheck current branch/CI/public site before claiming any newer status. No collaborative persistence or full accessibility certification established.

## Original sources

- https://github.com/JimLiu/open-artifact/blob/v0.17.0/website/README.md#deploy
- https://github.com/JimLiu/open-artifact/tree/v0.17.0/website/playground
- https://github.com/JimLiu/open-artifact/blob/v0.17.0/website/playground/src/seeds/manifest.ts
- https://github.com/JimLiu/open-artifact/blob/v0.17.0/docs/hosting.md
- https://github.com/JimLiu/open-artifact/blob/v0.17.0/packages/shell/src/home/components/ArtifactList.tsx
- https://github.com/JimLiu/open-artifact/blob/v0.17.0/packages/ui/src/styles.css
- https://github.com/JimLiu/open-artifact/blob/v0.17.0/packages/shell/src/shell/components/TopBar.tsx
- https://github.com/ianmaciel7/exams-app/actions/runs/46006601771
- https://github.com/ianmaciel7/exams-app/actions/runs/46008354579
- https://github.com/ianmaciel7/exams-app/commit/2e3e0e8d30df4cf014d9a31c20ee60de8f1fa754
- https://github.com/ianmaciel7/exams-app/commit/d8606ffa64f48ea58354b0148e74999f3d646e8f

## Routing
Use alongside ui-fidelity, component-explorer, whiteboard-tools-comments and sync-bridge. Archive immutable source, SHA, evidence and validation boundaries; use Especialista em UI/UX for general design guidance. Never confuse public Pages with the private artifact host or an in-chat preview.
