# ClickUp — release-aware flow and motion evidence discovery (batch 6)

Reviewed 2026-11-27; baseline `c6ad8edd3784d3b88e246c8d8517d692cd1ade67`. 13 unique new sources, 9 documented flow contracts, 7 release observations, 11 feature catalog observations, 24 video-directory entries. No video or GIF frames inspected. No proprietary content copied.

## Release provenance

- Artifact remix (Nov 14, New): Independent copy of artifact; original stays intact.
- LaTeX (Nov 14, Out of Labs): Equation rendering in rich text and Doc exports.
- Timeline hours scale (Nov 14, Out of Labs): 15, 30 or 60-minute scheduling intervals.
- Deep Research (Nov 9, New feature): Research spans workspace, connections and web; report includes sources.
- Task settings menu (Nov 9, New feature): Context menu for object operations.
- Agent Workflows (Nov 8, Beta / feed says Out of Labs): Visual agent steps, branches and approvals; availability ambiguity must be revalidated.
- Artifact co-editing (Nov 8, New / Out of Labs): Shared editing and collaborator presence.

[Release feed](https://clickup.com/features/feed). The page states 32 updates since Oct 18, but only an excerpt was retrieved. Date labels are preserved as displayed; no full release archive asserted.

## Additional catalog observations

- clickup-live-artifacts: Artifact reads workspace on open; certain changes require approval. (Beta).
- clickup-artifact-templates: Save as reusable starting point. (Beta).
- clickup-artifact-walkthroughs: Vendor describes AI-narrated demo generation. (New).
- clickup-skill-demonstrations: Convert recorded or live browser procedures to reusable skills. (Unspecified).
- clickup-skill-miner: Suggest reusable workflows based on repeated activity. (Unspecified).
- clickup-browser-session: Visible browser automation steps and saved recording. (Unspecified).
- clickup-ai-governance: Per-user feature, model and credit controls. (New).
- clickup-ai-usage-dashboard: Workspace AI credit and run activity reporting. (Unspecified).
- clickup-brain-voice: Live voice in Ask AI sidebar via Labs. (Beta).
- clickup-cursor-agents: External coding agents assigned work with progress shown. (Beta).
- clickup-deep-search: Multi-step search across connected and workspace data. (Unspecified).

[Vendor feature catalog](https://clickup.com/features?gad=1). Plan and experiment labels are not universal entitlement or runtime guarantees.

## Documented flows and proposed QA

### Capture workflow

Sequence: entry from context → screen/window/tab and audio choice → browser permission → 3-second countdown → recording → pause/restart/discard or stop → saved with preview/link/task actions.

Proposed QA: Test denied permission, cancellation before start, interrupted recording, upload pending/error, duplicate save, recording privacy and visible indicators.

Source: [clickup-clip-recording](https://help.clickup.com/hc/en-us/articles/6311242882967-Clip-screen-recordings). No observed timing except explicitly documented countdown and approximate cursor-chat timeout.

### Media transcript navigation

Sequence: open recording → show transcript sidebar → choose timestamped snippet → seek playback → copy snippet or all.

Proposed QA: Test keyboard navigation, transcript processing/empty/failure, timing alignment, access and copy feedback.

Source: [clickup-clip-recording](https://help.clickup.com/hc/en-us/articles/6311242882967-Clip-screen-recordings). No observed timing except explicitly documented countdown and approximate cursor-chat timeout.

### Temporal annotations

Sequence: open preview → add comment → choose playback position and point → draft → send or assign → navigate via timeline marker.

Proposed QA: Test comments on seek, assigned item resolution, permission, empty comments and hidden resolved state.

Source: [clickup-clip-recording](https://help.clickup.com/hc/en-us/articles/6311242882967-Clip-screen-recordings). No observed timing except explicitly documented countdown and approximate cursor-chat timeout.

### Share and embed

Sequence: open saved recording → copy link → paste URL into rich text → embedded player.

Proposed QA: Vendor says link holders can access Clip; test disclosure, revocation, recipient permission and no unintended public exposure. Do not assume private by default.

Source: [clickup-clip-recording](https://help.clickup.com/hc/en-us/articles/6311242882967-Clip-screen-recordings). No observed timing except explicitly documented countdown and approximate cursor-chat timeout.

### Column boundary resize

Sequence: pointer at header edge → drag to desired width → release.

Proposed QA: Documented action, GIF inaccessible. Measure width, min/max, persistence, keyboard alternative and layout behavior only after runtime capture.

Source: [clickup-list-customize](https://help.clickup.com/hc/en-us/articles/7255389296919-Customize-List-view). No observed timing except explicitly documented countdown and approximate cursor-chat timeout.

### Canvas connection and snapping

Sequence: select arrow tool → drag from source toward target → guide appears → release to snap → adjust or disconnect endpoint.

Proposed QA: Test zoom, target hit region, cancellation, anchor persistence, undo, keyboard equivalent and reduced motion.

Source: [clickup-whiteboard-items](https://help.clickup.com/hc/en-us/articles/6326217118615-Add-items-to-a-Whiteboard). No observed timing except explicitly documented countdown and approximate cursor-chat timeout.

### Rotation affordance

Sequence: select object → hover near corner → rotation cursor → drag → release.

Proposed QA: Test touch, snapping, keyboard alternative, rotation bounds and cancel.

Source: [clickup-whiteboard-items](https://help.clickup.com/hc/en-us/articles/6326217118615-Add-items-to-a-Whiteboard). No observed timing except explicitly documented countdown and approximate cursor-chat timeout.

### Ephemeral cursor message

Sequence: invoke cursor chat → type → move cursor → message disappears after a few seconds or click.

Proposed QA: Exact duration not stated. Test screen reader visibility, focus, dismissal, reduced motion, user consent and history expectations.

Source: [clickup-whiteboard-items](https://help.clickup.com/hc/en-us/articles/6326217118615-Add-items-to-a-Whiteboard). No observed timing except explicitly documented countdown and approximate cursor-chat timeout.

### User-controlled feedback and performance

Sequence: open settings → toggle toast/confetti/keyboard/Markdown or performance → refresh if required.

Proposed QA: Test persistence, effects on essential error feedback, system reduced motion, and performance trade-offs; not a compliance claim.

Source: [clickup-my-settings](https://help.clickup.com/hc/en-us/articles/6311968998167-My-Settings). No observed timing except explicitly documented countdown and approximate cursor-chat timeout.

## Video directory

[Official video library](https://clickup.com/videos). Titles and displayed durations only; neither direct video URLs nor frames were recovered. Legacy versions coexist. Do not use listed runtime as animation timing.

- Chat View: 1:54.
- Board View: 3:03.
- Form View: 5:00.
- Box View: 4:12.
- Calendar View: 6:59.
- Timeline View: 3:58.
- Doc View: 5:05.
- Workload View: 8:24.
- Map View: 4 min.
- Gantt View: 5 min.
- Bulk Action Toolbar: 2:17.
- Sprints ClickApp: 8 min.
- Automations: 4:21.
- Milestones: 1:53.
- Chrome Extension: 3:17.
- Home/Inbox: 1:53.
- LineUp: 1:43.
- Mind Maps: 4 min.
- Assignees: 2 min.
- Image & Doc Proofing: 1 min.
- Formula Fields: 7 min.
- Dashboards: 7 min.
- Pulse: 1 min.
- Email ClickApp: 4 min.

## Motion retrieval blocker

[Column-resize GIF](https://help.clickup.com/hc/article_attachments/44225755104407): source link retried, web rejected image/gif; direct local HTTPS request failed DNS resolution. No bytes recovered. No frame timing, easing or dimensions asserted. The prior Whiteboard and desktop GIFs remain uninspected. Future authorized capture should record platform/version, viewport, input modality, initial/action/final states, frame timestamps, reduced-motion preference and license; keep source media link-only unless redistribution is allowed.

## Remaining gaps

- No full Help Center article denominator or exhaustive extraction
- No official GIF/video frame decoding, captured runtime or motion measurements
- Release feed visible excerpt only; Show more not traversed
- Video titles/durations are metadata, not verified visual evidence or current version
- No computed app CSS, accessibility tests or private session

[Structured batch](flows-motion-2026-11-27.json). No application or plugin changes.
