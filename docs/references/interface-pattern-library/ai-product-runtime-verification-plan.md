# Five-product runtime verification plan — 2026-11-26

This is a **planned test protocol**, not executed tests or evidence. It translates product-specific gaps in issue #114 into 21 bounded checks across five products. All begin `not-run`. The protocol references the graph at `2cea0f25e211b99602df9cb83647b95569c75973`; do not infer current availability from the historical documentation. [Machine-readable cases](ai-product-runtime-verification-plan.json).

## Execution rules

- Use authorized accounts and disposable fictional fixtures only. Do not connect production data, send invitations to real contacts, incur costs, or mutate real shared objects. Record blocked or not-applicable when a plan, feature, platform or permission is missing.
- Capture before/after only with authorized rights, redact account details and sensitive content. Prefer public source links or permitted sanitized capture; no redistribution of proprietary assets without permission.
- Record date, platform, version (if visible), plan/role, viewport in CSS pixels, trigger, states, actual outcome and evidence. For motion, report only measured duration and actual observed/computed easing; unknown remains unknown. Static marketing stills are not runtime tests.
- Use keyboard, pointer and reduced-motion checks where applicable; screen reader tests require actual assistive technology. Do not mark an entire editor accessible on the basis of one case.
- Pass means the stated checks have been performed and supported by evidence; a missing feature or unavailable account is not automatically a defect. A failed test is a reproducible divergence or usability/accessibility finding with evidence, not a guess.

## Cases

### S01 — Child object vs reference
Product: chatgpt-space · Surface: `view:chatgpt-space:pages` · GAP-01, GAP-04, GAP-08 · Status: **not-run**

1. Create a disposable page; create a child and link to another disposable page
2. Rename and reopen the linked page and child
3. Move the child within the test space if authorized

Checks:
- Identify whether object identity and navigation persist; distinguish reference from reparenting
- Record inherited access separately from direct invitation

States to inspect: normal, empty, reopen, permission. Capture failures or unavailable controls only when observed.

### S02 — Task, checklist and generated controls
Product: chatgpt-space · Surface: `view:chatgpt-space:pages` · GAP-02, GAP-03, GAP-09, GAP-15 · Status: **not-run**

1. Open the creation menu on a blank test page
2. Add a checklist and, if enabled, a generated visualization using fictional data
3. Change an input, reload and inspect persisted state; do not execute a real agent task

Checks:
- Record menu labels, available controls and the observed state owner
- Separate scheduled tasks from checklist items and generated controls

States to inspect: empty, loading, success, reload, error. Capture failures or unavailable controls only when observed.

### S03 — Workspace shell and accessibility
Product: chatgpt-space · Surface: `view:chatgpt-space:space` · GAP-05, GAP-10, GAP-11, GAP-12, GAP-13, GAP-14 · Status: **not-run**

1. Measure desktop panel widths at three viewports; collapse and restore a panel where supported
2. Use keyboard-only navigation to a page and editor; check reduced motion
3. Open a permitted read-only fixture and compare visible actions

Checks:
- Record focus order, overflow, reflow, actual styles and reader role
- Record only measured transition duration/easing; mark unavailable properties unknown

States to inspect: focus, collapsed, readonly, responsive. Capture failures or unavailable controls only when observed.

### C01 — Canvas selection and editor regions
Product: claude · Surface: `view:claude:design-canvas` · GAP-02, GAP-03, GAP-10, GAP-11, GAP-13 · Status: **not-run**

1. Create a fictional design with nested groups
2. Navigate between canvas, properties and chat using documented keyboard controls
3. Select, enter and leave nested groups; compare inspector open and closed

Checks:
- Record focus target, retained selection and keyboard/pointer parity
- Capture actual toolbar and inspector labels and any keyboard limitations

States to inspect: normal, selected, focus, editing, disabled. Capture failures or unavailable controls only when observed.

### C02 — Artifact editing and persistence
Product: claude · Surface: `view:claude:artifacts-tab` · GAP-01, GAP-02, GAP-04, GAP-08, GAP-14, GAP-15 · Status: **not-run**

1. Inventory available editor templates using the account's displayed plan and platform
2. Create a disposable spreadsheet or document with fictional content
3. Edit, reopen, inspect version history and export where enabled

Checks:
- Verify identity and persisted edits; distinguish exported copy from original
- Record visible version and export options; note unavailable templates

States to inspect: empty, loading, saved, readonly, error. Capture failures or unavailable controls only when observed.

### C03 — Dashboard lineage and shared data
Product: claude · Surface: `output:claude:data` · GAP-08, GAP-09, GAP-13, GAP-15 · Status: **not-run**

1. Use synthetic data in an authorized test dashboard, without connecting production accounts
2. Inspect chart query/refresh metadata, keyboard interactions and history if available
3. Compare approved test reader and editor access only with explicit account authorization

Checks:
- Record query access, freshness, snapshot/restore behavior and role boundary
- No claim of live connector behavior when only synthetic input is available

States to inspect: normal, empty, stale, readonly, permission. Capture failures or unavailable controls only when observed.

### G01 — Library facets and pins
Product: grok-bot · Surface: `view:grok-bot:library` · GAP-01, GAP-02, GAP-03, GAP-08, GAP-13 · Status: **not-run**

1. Use an existing disposable test Bot or create one only if authorized
2. Produce a fictional page; inspect available facets and pin controls
3. Reopen and check cross-device pin state where a second session is authorized

Checks:
- Record actual menu/facet labels, keyboard focus and pin persistence
- Do not treat unavailable cross-device access as a failure

States to inspect: empty, loading, hover, focus, pinned. Capture failures or unavailable controls only when observed.

### G02 — Page reader state and recovery
Product: grok-bot · Surface: `view:grok-bot:pages` · GAP-03, GAP-04, GAP-08, GAP-09, GAP-15 · Status: **not-run**

1. Generate a disposable page with a filter
2. Change a reader control, reload and compare page identity
3. Ask for a harmless edit in chat; observe update of the existing card

Checks:
- Separate transient reader controls from persistent agent edits
- Record loading, update indication and retry only if safely reproducible

States to inspect: normal, loading, updated, reload, error. Capture failures or unavailable controls only when observed.

### G03 — Agent handoff and shell
Product: grok-bot · Surface: `view:grok-bot:computer` · GAP-03, GAP-05, GAP-10, GAP-11, GAP-14 · Status: **not-run**

1. Observe a harmless test task in an isolated agent environment if available
2. Open preview and take control only with explicit authorization; return control
3. Record status, focus and collapse behavior; do not access private files

Checks:
- Distinguish indicator, preview and control ownership
- Capture actual transition only from a permitted recording; no inferred easing

States to inspect: idle, working, preview, takeover, returned. Capture failures or unavailable controls only when observed.

### M01 — Diagnostic learning states
Product: gemini · Surface: `view:gemini:study-notebooks` · GAP-01, GAP-03, GAP-04, GAP-05, GAP-09, GAP-14 · Status: **not-run**

1. Create test learning materials with fictional topic data
2. Take a diagnostic and a follow-up quiz if enabled
3. Record dashboard labels and filter controls before and after

Checks:
- Verify only visible state changes; do not infer mastery thresholds
- Capture initial, progress and completion states with citations where available

States to inspect: empty, loading, not-started, focus-area, strength. Capture failures or unavailable controls only when observed.

### M02 — Generated editor and recovery
Product: gemini · Surface: `view:gemini:canvas` · GAP-02, GAP-03, GAP-08, GAP-15 · Status: **not-run**

1. Create a harmless local-state counter or quiz in Canvas
2. Inspect preview/code and edit selected content; reopen
3. Observe a recoverable preview error in a disposable draft if safe

Checks:
- Document edit scope, state persistence, error and retry UI
- No production connector or externally published app required

States to inspect: normal, editing, loading, error, reopened. Capture failures or unavailable controls only when observed.

### M03 — Sharing boundary and responsive view
Product: gemini · Surface: `view:gemini:canvas` · GAP-05, GAP-08, GAP-10, GAP-12, GAP-13, GAP-14 · Status: **not-run**

1. Use a synthetic app in a permitted private test environment
2. Inspect sharing options without publishing unless authorized
3. Compare view widths and keyboard controls; test a copy using a permitted second account if available

Checks:
- Distinguish private and shared storage and editable copy identity
- Record actual permission wording and viewport, not inferred account eligibility

States to inspect: normal, readonly, permission, responsive, focus. Capture failures or unavailable controls only when observed.

### N01 — Source-grounded review loop
Product: gemini-notebook · Surface: `view:gemini-notebook:full-screen-study-view` · GAP-03, GAP-04, GAP-05, GAP-08, GAP-13 · Status: **not-run**

1. Use a fictional source document and generate a quiz or cards
2. Answer correctly and incorrectly, inspect explanation and source link
3. Exit, reopen and retry missed items when offered

Checks:
- Record actual review states, source navigation and progress restoration
- Separate learner state from source and generated artifact

States to inspect: loading, correct, incorrect, explanation, resume. Capture failures or unavailable controls only when observed.

### N02 — Staged artifact revision
Product: gemini-notebook · Surface: `view:gemini-notebook:studio` · GAP-02, GAP-03, GAP-04, GAP-08, GAP-11, GAP-15 · Status: **not-run**

1. Generate a small disposable deck where plan allows
2. Mark a slide for deletion, restore it, and inspect preview before applying
3. Apply revision only if authorized; compare original and revised artifact

Checks:
- Capture pending deletion and restoration with focus state
- Record original/new identity, quota warning and failure controls where visible

States to inspect: normal, pending-delete, restored, generating, ready. Capture failures or unavailable controls only when observed.

### N03 — Three-pane shell and source tables
Product: gemini-notebook · Surface: `view:gemini-notebook:sources` · GAP-05, GAP-09, GAP-10, GAP-12, GAP-13 · Status: **not-run**

1. Open a disposable notebook with fictional sources; inspect panel collapse and resizing
2. Generate a source-grounded data table where available; inspect citation navigation
3. Inspect export menu; export to test destination only if explicitly authorized

Checks:
- Record dimensions, focus, responsive behavior and export as a separate object
- Capture source and row references without private data

States to inspect: empty, loading, normal, focus, responsive, export. Capture failures or unavailable controls only when observed.

## Supplemental contract checks — 2026-11-26

### S04 — Effective access and revocation
Product: chatgpt-space · Surface: `view:chatgpt-space:pages` · Reference: `contract:space-inherited-access-revocation` · GAP-04, GAP-08, GAP-13 · Status: **not-run**

1. Use only explicitly authorized disposable roles and test pages
2. Inspect direct and inherited grants separately; if authorized, remove the direct grant on the fictional fixture
3. Verify actual access with the test reader and inspect the inherited grant; restore fixture permissions when authorized

Checks:
- Distinguish effective access from a single invitation; verify linked objects independently
- Record actual access changes, role wording and propagation timing when measurable; do not expose real account identities

States to inspect: direct-grant, inherited-grant, both-grants, direct-removed, revoked, permission-denied. Record only observed behavior.

### C04 — Progressive Escape and focus return
Product: claude · Surface: `view:claude:side-by-side-chat-and-artifact` · Reference: `contract:claude-artifact-panel-focus-return` · GAP-02, GAP-03, GAP-11, GAP-13 · Status: **not-run**

1. Open a fictional artifact using keyboard only
2. Navigate from header into an available nested control; press Escape once and observe which interaction closes
3. Continue Escape when applicable; record focus destination after panel closure

Checks:
- Observe the focused element before and after each step; compare documented legacy and current editor behavior only if accessible
- Check that no unexpected destructive action occurs; measure focus and motion separately

States to inspect: trigger-focus, panel-open, nested-control-open, nested-control-closed, panel-closed, focus-restored. Record only observed behavior.

### C05 — Anchored comment mode and role boundaries
Product: claude · Surface: `view:claude:design-canvas` · Reference: `contract:claude-comment-mode-focus` · GAP-02, GAP-03, GAP-08, GAP-13 · Status: **not-run**

1. Enter comment mode on a disposable design or slide using keyboard
2. Select a fictional target; type a draft and cancel; reopen an existing test comment if available
3. Submit only within an explicitly authorized test fixture; inspect read-only action availability without sending external invitations

Checks:
- Record focus return to control or marker and draft behavior; inspect announced state using actual assistive technology if available
- Distinguish comment mode, input, submitted reply and role restrictions; never infer failure behavior

States to inspect: comment-mode, target-selected, draft, cancelled, submitted, readonly, focus-restored. Record only observed behavior.

### G04 — Non-destructive recovery and escalation affordances
Product: grok-bot · Surface: `view:grok-bot:computer` · Reference: `contract:grok-bot-computer-recovery-escalation` · GAP-03, GAP-04, GAP-08, GAP-11, GAP-15 · Status: **not-run**

1. Inspect recovery documentation alongside an authorized disposable session; record any naturally occurring disconnect
2. If permitted and safe, retry or reconnect the disposable session without changing production connections
3. Inspect offered recovery choices without executing recover/reset; mark destructive branches not-run

Checks:
- Record observed retry outcome and any warnings about running work and data retention
- Separate documented recover/reset behavior from executed retry; do not induce a fault or reset an account-wide computer

States to inspect: connected, disconnected-if-observed, reconnecting, retry, recovered-if-observed, escalation-offered. Record only observed behavior.

### M04 — Learning plan adaptation after material update
Product: gemini · Surface: `view:gemini:study-notebooks` · Reference: `flow:gemini-study-adaptive-materials` · GAP-03, GAP-04, GAP-08, GAP-09, GAP-14 · Status: **not-run**

1. Use fictional learning material in an authorized notebook and record the initial topic plan
2. Complete an available progress quiz and add a second fictional source
3. Inspect the resulting plan and topic statuses; compare observed changes without assuming an adaptation algorithm

Checks:
- Distinguish newly generated lesson content from learner progress and source changes
- Record no-change and unavailable cases without treating them as defects; do not claim educational efficacy

States to inspect: initial-plan, quiz-complete, source-added, plan-updated-if-observed, unchanged. Record only observed behavior.

### N04 — Flashcard resumption and missed-only review
Product: gemini-notebook · Surface: `view:gemini-notebook:full-screen-study-view` · Reference: `contract:notebook-flashcard-progress-and-review` · GAP-03, GAP-04, GAP-08, GAP-13, GAP-15 · Status: **not-run**

1. Generate or open an authorized disposable flashcard set using fictional sources
2. Mark cards known and missed, exit partway and reopen
3. Complete the session; inspect same/all/missed review options if offered and record behavior with no missed cards only when safely reproducible

Checks:
- Record persisted learner position and visible review scope; separate learner state from artifact editing rights
- Verify exact labels, empty-subset behavior and keyboard controls if present; do not infer scheduling or mastery thresholds

States to inspect: studying, known, missed, exited, resumed, results, missed-only, empty-subset-if-observed. Record only observed behavior.

## Independent retrieval annotation protocol

Use a reviewer who did not author the original benchmark or tune ranking. Freeze a new question set and corpus snapshot before examining ranked results. Include Portuguese/English, all five products, different evidence types, ambiguous queries, and unrelated negatives. Reviewer defines the information need and acceptable equivalent records, then grades pooled candidates in randomized order without model rank or score. Use explicit relevance grades (0 irrelevant, 1 partially relevant, 2 directly answers), plus source/provenance validity, duplicate groups and confidence. Resolve disagreements with a second reviewer where possible; preserve unknowns and report judgment coverage. Only after freezing judgments run and score the unchanged retriever. Report recall against judged targets, precision/nDCG with explicit unjudged handling, MRR, abstention, budget and per-product breakdown. Evaluate answer claims against primary sources separately; never conflate catalog matching with factual correctness.

No independent reviewers have completed this protocol. The existing 22-query suite remains development regression, not held-out certification.

## Closure criteria

Issue #114 remains open until remaining required evidence is collected or explicitly scoped out with user approval. This plan is not exhaustive inventory or a substitute for live product access.
