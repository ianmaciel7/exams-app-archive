# Behavioral UX Quality — Interaction Design Patterns and Guidelines (2026)

Review: 2026-11-25. General and product-independent. Consolidated from completed deep research, preserving all thematic families and direct source URLs. 58 indexed entries, overlapping previous catalogs intentionally by cross-reference; not 58 new distinct patterns across the repository. Examples are acceptance scenarios, not claims of tested products. Priority fundamental means generally important when applicable; contextual means adopt according to task, risk and evidence.

## Scope and evidence limitations

- This is a curated consolidation of the completed deep research, not an independently validated market ranking or an assertion that every recommendation was empirically tested.
- 2026 is the review date, not the invention or publication date of all patterns. Preserve historical guidance and validate applicability.
- Optimistic UI: no universal 97% success threshold or two-second failure rule; use risk, reversibility, measured latency and actual reconciliation. Never fake confirmed success.
- Progress: no universal spinner cutoff or precise ETA; show actual measured progress or meaningful indeterminate state. Completion dialogs only where consequence warrants interruption.
- Offline, realtime collaboration, multiple tabs, command palette and cross-device handoff are contextual, not mandatory for all sites. Offline does not imply storing sensitive information locally.
- Session continuity preserves authorized task state, not transfer of authentication tokens; distinguish authentication, UI state, persisted domain data and job durability.
- WCAG success criteria are normative within the selected conformance target; Understanding pages and APG are informative. Do not announce every dynamic change, or use color alone.
- Consent is not universally the only lawful basis for processing; use applicable law and actual product requirements. Avoid claims of undo for irreversible actions.
- Do not adopt arbitrary 90% disclosure thresholds, unsupported Google Drive keyboard shortcuts, or unverified product examples from the report. The acceptance scenarios here are illustrative.
- Documentation names: RFC is a proposal/discussion mechanism, not a synonym for a pattern; RFC can be used internally for proposed UX changes. HCI Design Pattern Form is a general format, not a universally mandated schema.

## Catalog

### Asynchronous work and multitasking

- **Background Tasks / Non-blocking Interaction** (`background-execution`, contextual): Run long jobs without disabling unrelated work; only block genuinely conflicting operations. **Acceptance:** Start a job, open another view and continue editing; navigate away and verify actual job state. **Sources:** [nng-waits](#sources), [logrocket-async](#sources).
- **Concurrent Tasks** (`concurrent-task-management`, contextual): Separate each task's identity, status and results; respect concurrency limits. **Acceptance:** Run two independent tasks, switch between them, and verify neither state is overwritten. **Sources:** [nng-waits](#sources), [logrocket-async](#sources).
- **Task Center / Job Queue** (`task-tray`, contextual): Expose queued, running, awaiting input, finished and failed tasks; no fake ETA. **Acceptance:** Locate a job after navigation and inspect its actual status and result. **Sources:** [logrocket-async](#sources).
- **Modeless Progress** (`modeless-progress`, contextual): Show determinate progress when measurable; otherwise state or stage, without locking the workspace. **Acceptance:** Unknown work shows no invented percentage; measured progress agrees with backend. **Sources:** [nng-waits](#sources), [behavior-wcag22-status](#sources).
- **Cancellation / Retry** (`cancel-retry`, contextual): Allow cancel or retry only if supported; distinguish request, confirmed cancellation and completion. **Acceptance:** Race cancel against completion; no duplicate irreversible effect on retry. **Sources:** [nng-waits](#sources), [logrocket-async](#sources).
- **Completion Notification** (`completion-feedback`, contextual): Report outcome with task identity and link; interrupt only for consequential decisions. **Acceptance:** Find finished/failed work without watching its progress; don't steal focus unnecessarily. **Sources:** [nng-waits](#sources), [behavior-wcag22-status](#sources).
- **Partial Results / Streaming** (`partial-results`, contextual): Present available meaningful output, distinguish partial from final and preserve failure state. **Acceptance:** Interrupt stream and reconnect; distinguish saved output from incomplete output. **Sources:** [logrocket-async](#sources).

### Cross-device and session continuity

- **Device Handoff / Cross-Device Continuity / Continue On** (`device-handoff`, contextual): Resume the same authorized task on a second device; transfer context, not reusable authentication secrets. **Acceptance:** Open on mobile after desktop; restore permitted item, draft and stage; reject expired or unauthorized link. **Sources:** [behavior-device-handoff](#sources), [behavior-android-continue-on](#sources).
- **Session Restore / Workspace Persistence** (`session-restore`, contextual): Restore meaningful view, scroll, selection and drafts after reload or restart; avoid shared-device leakage. **Acceptance:** Reload and relaunch, verify expected state and account isolation. **Sources:** [behavior-device-handoff](#sources), [nng-complex](#sources).
- **Cross-device State Synchronization** (`state-sync`, contextual): Synchronize committed state across authorized clients; distinguish local drafts, pending sync and conflicts. **Acceptance:** Edit on A; resume B; resolve concurrent edits without silent overwrite. **Sources:** [behavior-device-handoff](#sources), [ink-localfirst](#sources).
- **Persistent Task State / Task Re-entry** (`durable-task-state`, contextual): Jobs survive navigation and, if supported by backend, closing client; reopen same task identity. **Acceptance:** Close browser, open another device and query job; never promise durability without support. **Sources:** [nng-waits](#sources), [logrocket-async](#sources).
- **Handoff Confirmation** (`handoff-confirmation`, contextual): Clearly indicate source/target transfer status; expire transfer links and enforce permissions. **Acceptance:** Failed or expired transfer explains recovery without losing original work. **Sources:** [behavior-device-handoff](#sources), [behavior-android-continue-on](#sources).

### Navigation and workspace

- **Deep Linking / Addressable State** (`deep-link`, contextual): Provide stable authorized URLs for shareable content and meaningful view state; keep secrets out of URLs. **Acceptance:** Open link in fresh authorized client, back/forward works; unauthorized user denied. **Sources:** [nng-complex](#sources), [behavior-device-handoff](#sources).
- **State-preserving Navigation** (`state-preserving-navigation`, contextual): Preserve relevant scroll, filters, selection and navigation history where expected. **Acceptance:** Open detail then Back; return to prior list location and filters. **Sources:** [nng-complex](#sources).
- **Wizard / Stepper / Progressive Navigation** (`staged-flow`, contextual): Show step and progress; preserve valid data when going back or pausing. **Acceptance:** Back/next, reload or validation failure does not erase draft. **Sources:** [nng-waits](#sources), [nng-complex](#sources).
- **Tabbed Workspace / Split View** (`workspace-tabs`, contextual): Use independent stateful document views where multiple work items are needed; not identical to section tabs. **Acceptance:** Switch panels/tabs without losing edits; keyboard navigation and close behavior consistent. **Sources:** [nng-complex](#sources), [apg](#sources), [behavior-nng-tabs-accordions](#sources).
- **Command Palette** (`command-palette`, contextual): Search actions and objects via keyboard and discoverable button; avoid shortcut conflicts. **Acceptance:** Find/execute via keyboard and touch alternative; Escape restores focus. **Sources:** [command-palette-detail](#sources), [apg](#sources).
- **Global Search / Faceted Search** (`global-search`, contextual): Find relevant items with clear scope, filters, meaningful empty/error results. **Acceptance:** Search across permitted content, distinguish zero results from network failure. **Sources:** [nng-complex](#sources).
- **Keyboard Accelerators** (`keyboard-shortcuts`, contextual): Offer discoverable shortcuts for frequent actions with equivalent visible controls. **Acceptance:** Operate common actions without pointer; respect system/browser and assistive shortcuts. **Sources:** [apg](#sources), [behavior-wcag22](#sources).

### Editing and data protection

- **Autosave / Draft Persistence** (`autosave`, contextual): Save drafts reliably and show saving/saved/pending/error; distinguish drafts from published changes. **Acceptance:** Edit, disconnect, reload; show true save state; prevent silent loss. **Sources:** [behavior-nng-expectations](#sources), [ink-localfirst](#sources).
- **Explicit Save / Apply / Publish** (`explicit-commit`, fundamental): Use explicit commit when changes have meaningful side effects or expectation of cancellation. **Acceptance:** Cancel does not commit unintended changes; autosave can coexist with publish. **Sources:** [behavior-nng-expectations](#sources), [behavior-nng-reset-cancel](#sources).
- **Undo / Redo** (`undo-redo`, contextual): Support reversible meaningful edits with appropriate scope and clear limits. **Acceptance:** Undo/redo via keyboard and touch; no claim of undo for irreversible external effects. **Sources:** [behavior-nng-reset-cancel](#sources).
- **Optimistic UI / Optimistic Update** (`optimistic-ui`, contextual): Show provisional low-risk reversible effects; reconcile with authoritative response and explain failure. **Acceptance:** Force rejection and concurrent changes; rollback or resolve and preserve user intent. **Sources:** [behavior-optimistic-ui](#sources).
- **Cancel / Discard Changes** (`cancel-discard`, fundamental): Provide explicit safe exit; confirm discarding unsaved meaningful work only when needed. **Acceptance:** Escape and Cancel perform intended semantics; no silent commit or data loss. **Sources:** [behavior-nng-reset-cancel](#sources), [behavior-nng-expectations](#sources).
- **Version History / Restore** (`version-history`, contextual): Expose relevant prior versions and recovery when durable history is needed. **Acceptance:** Restore intended version with authorization; do not silently overwrite newer work. **Sources:** [nng-waits](#sources), [ink-localfirst](#sources).

### Connectivity and recovery

- **Offline-capable / Local-first UX** (`offline-capability`, contextual): Choose offline reading or editing based on actual needs and security; communicate limits. **Acceptance:** Disconnect, perform supported actions and verify actual local persistence and sync. **Sources:** [ink-localfirst](#sources).
- **Reconnect and Resume** (`reconnection`, contextual): Recover connection transparently when safe, show stale/pending status and allow retry. **Acceptance:** Drop network during edit/job; reconnect without duplicate submission or loss. **Sources:** [ink-localfirst](#sources), [logrocket-async](#sources).
- **Pending Sync / Outbox** (`pending-sync`, contextual): Queue eligible operations durably; display pending, blocked and conflict states. **Acceptance:** Restart while offline; reconnect and replay idempotently with authorization. **Sources:** [ink-localfirst](#sources).
- **Conflict Resolution** (`conflict-resolution`, contextual): Avoid silent last-write-wins for consequential conflicts; present merge or recovery options. **Acceptance:** Concurrent conflicting edits give predictable resolution without hiding discarded changes. **Sources:** [ink-localfirst](#sources).
- **Graceful Degradation** (`offline-constraints`, fundamental): Explain unavailable network-dependent actions and offer useful alternatives; no fake success. **Acceptance:** Attempt payment offline; prevent unsafe submission, explain next step. **Sources:** [ink-localfirst](#sources).

### Visibility and feedback

- **Immediate Action Feedback** (`immediate-feedback`, fundamental): Acknowledge meaningful interactions without excessive animation; do not conflate acknowledgement with success. **Acceptance:** Slow network: pending state appears; actual outcome subsequently shown. **Sources:** [behavior-nng-expectations](#sources), [behavior-wcag22-status](#sources).
- **Accessible Status Messages** (`status-messages`, fundamental): Expose status messages programmatically without forcing focus, as WCAG 4.1.3 applies. **Acceptance:** Screen reader announces meaningful waiting, result and error messages without spam. **Sources:** [behavior-wcag22-status](#sources), [behavior-wcag22](#sources).
- **Contextual Success and Error Feedback** (`contextual-outcome`, fundamental): Describe affected object, outcome and next action where useful. **Acceptance:** User can tell which of multiple operations succeeded or failed. **Sources:** [nng-waits](#sources), [behavior-nng-expectations](#sources).
- **Interruption Management / Notification Prioritization** (`interruption-management`, contextual): Prefer noninterruptive notices for ordinary results; use blocking dialogs only when context warrants. **Acceptance:** Background completion does not disrupt unrelated typing; urgent required decision remains findable. **Sources:** [nng-waits](#sources).

### Discoverability and contextual interaction

- **Progressive Disclosure** (`progressive-disclosure`, contextual): Reveal secondary complexity without hiding essential controls; labels indicate available options. **Acceptance:** Novice completes primary path; expert discovers advanced options using keyboard/touch. **Sources:** [behavior-nng-disclosure](#sources).
- **Contextual Actions / Hover-Reveal / Focus-Reveal** (`contextual-actions`, contextual): Expose object-specific secondary commands on hover/focus with explicit touch fallback. **Acceptance:** Keyboard and touch can discover and invoke every action; no lost focus or hover-only essential control. **Sources:** [nng-context-guidelines](#sources), [wcag-hover](#sources), [apg](#sources).
- **Tooltips / Contextual Help** (`tooltips`, contextual): Use supplementary concise help; essential instructions must be available without hover. **Acceptance:** Keyboard focus and touch equivalent; dismissible/hoverable/persistent where SC 1.4.13 applies. **Sources:** [wcag-hover](#sources), [apg](#sources).
- **Just-in-time Permission Prompt** (`contextual-permission`, contextual): Explain permission purpose when relevant; offer safe refusal path. **Acceptance:** Reject optional permission; core unaffected functionality remains usable. **Sources:** [hax-patterns](#sources).

### Accessibility and responsive interaction

- **Keyboard Operability / Focus Management** (`keyboard-access`, fundamental): Support all applicable functionality by keyboard, logical focus order and visible focus; no traps. **Acceptance:** Keyboard-only complete tasks, dialogs return focus, tab order logical. **Sources:** [behavior-wcag22](#sources), [apg](#sources).
- **Contrast and Readability** (`contrast`, fundamental): Use WCAG thresholds and exceptions as applicable; normal text AA generally 4.5:1. **Acceptance:** Measure contrast and test zoom/reflow; do not rely on color alone. **Sources:** [behavior-wcag22](#sources).
- **Responsive Reflow / Adaptive Layout** (`responsive-reflow`, fundamental): Adapt by content and input capability; maintain task parity and accessible reflow. **Acceptance:** Test narrow viewport, 400% zoom where applicable, touch and mixed input. **Sources:** [behavior-wcag22](#sources), [wcag-hover](#sources).
- **Touch Target Size / Pointer Alternatives** (`target-size`, fundamental): Use adequate target sizes and alternatives for dragging and complex gestures; apply WCAG exceptions. **Acceptance:** Test touch targets, dragging alternatives and single-pointer access. **Sources:** [behavior-wcag22](#sources).
- **Motion Sensitivity / Reduced Motion** (`reduced-motion`, fundamental): Avoid flashing and unnecessary motion; respect preferences and applicable criteria. **Acceptance:** Reduced-motion setting preserves information and interaction; pause applicable moving content. **Sources:** [behavior-wcag22](#sources).
- **Accessible Names and Semantic Controls** (`semantic-labels`, fundamental): Use native semantic controls and correct roles, labels, relationships and error descriptions. **Acceptance:** Inspect accessible tree and screen reader controls; keyboard interaction matches role. **Sources:** [behavior-wcag22](#sources), [apg](#sources).

### Error prevention and recovery

- **Inline Validation / Error Identification** (`inline-validation`, fundamental): Validate at appropriate timing, identify field and explain correction; preserve entered data. **Acceptance:** Invalid submission gives precise accessible message, retained data and valid correction path. **Sources:** [behavior-wcag22](#sources), [behavior-nng-expectations](#sources).
- **Destructive Action Safeguards** (`destructive-action`, fundamental): Use proportionate confirmation, preview or undo for consequential changes. **Acceptance:** Accidental action has safe exit/recovery; irreversible operation explicitly explained. **Sources:** [behavior-nng-reset-cancel](#sources), [behavior-wcag22](#sources).
- **Actionable Error Recovery** (`error-recovery`, fundamental): Explain what happened, impact and recovery; avoid raw internal errors and sensitive data. **Acceptance:** Force failure, retain relevant input, retry safely; support accessible feedback. **Sources:** [behavior-wcag22-status](#sources), [logrocket-async](#sources).
- **Unsaved Changes Protection** (`unsaved-warning`, contextual): Warn only when real unsaved work may be lost; don't rely solely on unload events. **Acceptance:** Reload/close, crash simulation and mobile suspension; durable draft or truthful warning. **Sources:** [behavior-nng-expectations](#sources), [ink-localfirst](#sources).

### Privacy, security and user control

- **Privacy Controls / Consent Management** (`privacy-control`, fundamental): Make choices transparent and reversible where applicable; lawful basis and jurisdiction matter, consent is not universal. **Acceptance:** Inspect permissions, withdraw optional consent, preserve account isolation. **Sources:** [hax-patterns](#sources).
- **Risk-based Reauthentication** (`risk-based-auth`, contextual): Apply proportionate additional verification for sensitive operations; do not transfer credentials via handoff links. **Acceptance:** Attempt unauthorized and expired handoff; high-risk operation follows actual security policy. **Sources:** [behavior-device-handoff](#sources).
- **User Control and Freedom** (`user-control`, fundamental): Provide understandable options, safe exit and ability to correct or stop where possible. **Acceptance:** User can dismiss, change settings or recover from unintended state. **Sources:** [behavior-nng-reset-cancel](#sources).

### Collaboration and sharing

- **Real-time Collaboration / Presence** (`real-time-collaboration`, contextual): Synchronize shared objects, surface meaningful presence and changes only where collaborative work is needed. **Acceptance:** Two authorized editors see expected changes; conflicts and offline cases are handled. **Sources:** [ink-localfirst](#sources).
- **Permission-aware Sharing / Share Links** (`sharing`, contextual): Allow sharing via stable links with explicit access scope, revocation and no accidental disclosure. **Acceptance:** Test invite, revoke and unauthorized access; link does not grant more than intended. **Sources:** [behavior-device-handoff](#sources), [ink-localfirst](#sources).
- **Contextual Comments / Historical Activity** (`comments`, contextual): Attach notes to relevant objects; show provenance and useful history to resume interrupted work. **Acceptance:** Return to item, locate prior decisions/notes and relevant activity; respect permissions. **Sources:** [nng-waits](#sources).

### Human-AI interaction

- **AI Transparency / Capability Disclosure** (`ai-transparency`, contextual): Distinguish generated content, supported actions and limitations; show meaningful execution status. **Acceptance:** User can identify AI output and understand actions and limitations. **Sources:** [hax-patterns](#sources).
- **Action Preview / Human Approval** (`ai-action-review`, contextual): Preview consequential agent actions with scope and effects before approval as appropriate. **Acceptance:** Reject or edit proposed action; nothing executes beyond authorized scope. **Sources:** [hax-patterns](#sources).
- **Human Override / Stop / Correction** (`ai-interruption`, contextual): Allow interrupt, steer, correct or restart where supported; distinguish stop request and actual cessation. **Acceptance:** Stop agent, verify side effects and subsequent state; offer safe recovery. **Sources:** [hax-patterns](#sources), [logrocket-async](#sources).
- **Calibrated Uncertainty / Graceful Failure** (`ai-uncertainty`, contextual): Communicate meaningful uncertainty and evidence; offer correction or human escalation. **Acceptance:** Unsupported or low-confidence request produces honest limits, not invented certainty. **Sources:** [hax-patterns](#sources).

## Formal documentation taxonomy

- **Design Principle:** General design objective or underlying concept.
- **Usability Heuristic:** Evaluation criterion.
- **Design Guideline / UX Best Practice Guideline:** Contextual recommendation; cite evidence and conditions.
- **Interaction Design Pattern / HCI Design Pattern:** Reusable problem-context-solution with rationale and examples.
- **Pattern Language:** Related patterns, dependencies and alternatives.
- **Standard:** Normative document in its specified scope.
- **Interaction Design Specification:** Precise expected states, inputs, outputs and acceptance.
- **Anti-pattern:** Recurring harmful approach and alternative.
- **RFC:** Proposed change for review.
- **DDR / ADR:** Recorded decision and rationale.
- **Research Report:** Methods, evidence, results and limitations.

Recommended entry form: stable local ID, canonical name and aliases, problem, context, forces, solution, rationale, alternatives/anti-patterns, evidence and date, product examples only if verified, accessibility, acceptance criteria, related patterns and separate implementation prerequisites. Local IDs are not official RFC numbers.

## Quality review checklist

Use each catalog acceptance scenario, mark applicable / not applicable / pass / fail / not tested, link evidence and record owner. Include two simultaneous tasks; navigation during work; reload and reconnect; close client only if job durability is supported; resume on another authorized device; autosave and explicit publish; concurrent edits; error recovery; keyboard, touch and screen reader; reduced motion; accessible status; authorization and revocation; agent approval and stop. Validate measured performance and actual backend truth. Don't confuse architecture choices (queues, storage, idempotency, SSE/WebSockets) with user-facing outcomes.

## Sources

- [NN/g — Designing for Long Waits and Interruptions](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/) — `nng-waits`; independent-ux-research; Opened article; 2021-09-05.
- [LogRocket — UI patterns for async workflows](https://blog.logrocket.com/ux-design/ui-patterns-for-async-workflows-background-jobs-and-data-pipelines) — `logrocket-async`; practitioner-article; Opened article; 2026-02-13.
- [UI Patterns — Device Handoff](https://ui-patterns.com/patterns/DeviceHandoff) — `behavior-device-handoff`; pattern-library; Cited in completed deep-research report; not independently re-fetched in this consolidation.
- [Android — Enable and customize cross-device handoff](https://developer.android.com/develop/better-together/continue-on/enable-support) — `behavior-android-continue-on`; primary-platform; Cited in completed deep-research report; not independently re-fetched in this consolidation.
- [NN/g — Reset and Cancel Buttons](https://www.nngroup.com/articles/reset-and-cancel-buttons/) — `behavior-nng-reset-cancel`; usability-guidance; Cited in completed deep-research report; not independently re-fetched in this consolidation.
- [NN/g — Don’t Prioritize Efficiency Over Expectations](https://www.nngroup.com/articles/efficiency-vs-expectations/) — `behavior-nng-expectations`; usability-guidance; Cited in completed deep-research report; not independently re-fetched in this consolidation.
- [NN/g — Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) — `behavior-nng-disclosure`; usability-guidance; Cited in completed deep-research report; not independently re-fetched in this consolidation.
- [Smashing Magazine — True Lies of Optimistic User Interfaces](https://www.smashingmagazine.com/2016/11/true-lies-of-optimistic-user-interfaces/) — `behavior-optimistic-ui`; practitioner-article; Cited in completed deep-research report; not independently re-fetched in this consolidation.
- [W3C — Understanding SC 4.1.3 Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) — `behavior-wcag22-status`; accessibility-standard-guidance; Cited in completed deep-research report; not independently re-fetched in this consolidation.
- [NN/g — Tabs vs. Accordions](https://www.nngroup.com/videos/tabs-vs-accordions/) — `behavior-nng-tabs-accordions`; usability-guidance; Cited in completed deep-research report; not independently re-fetched in this consolidation.
- [NN/g — Design Guidance](https://www.nngroup.com/articles/design-guidance/) — `behavior-nng-design-guidance`; usability-guidance; Prior conversation or reference catalog; revalidate before reuse.
- [NN/g — Design-Pattern Guidelines](https://www.nngroup.com/articles/design-pattern-guidelines/) — `behavior-nng-pattern-guidelines`; usability-guidance; Prior conversation or reference catalog; revalidate before reuse.
- [IxDF — Interaction Design Patterns](https://ixdf.org/literature/book/the-glossary-of-human-computer-interaction/interaction-design-patterns) — `behavior-ixdf-pattern-language`; education; Prior conversation or reference catalog; revalidate before reuse.
- [Baymard — UX Best Practice Guidelines](https://baymard.com/product/ux-best-practice-guidelines) — `behavior-baymard-guidelines`; research-catalog; Prior conversation or reference catalog; revalidate before reuse.
- [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/) — `behavior-wcag22`; accessibility-standard; Prior conversation or reference catalog; revalidate before reuse.
- [Ink & Switch — Local-first software](https://www.inkandswitch.com/essay/local-first/) — `ink-localfirst`; research-essay; search-index evidence; revalidate full source before specific claims.
- [Microsoft HAX — Design patterns](https://www.microsoft.com/en-us/haxtoolkit/design-patterns/) — `hax-patterns`; primary-guidance; search-index evidence; full page not audited.
- [W3C — ARIA APG example index](https://www.w3.org/WAI/ARIA/apg/example-index/) — `apg`; primary-guidance; undefined.
- [NN/g Contextual Menu Guidelines](https://www.nngroup.com/articles/contextual-menus-guidelines/) — `nng-context-guidelines`; usability-guidance; verified.
- [WCAG 2.2 Content on Hover or Focus](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus) — `wcag-hover`; normative-support; carried forward; not revalidated in this batch.
- [UX Patterns — Command Palette](https://uxpatterns.dev/patterns/advanced/command-palette) — `command-palette-detail`; community-pattern-library; search-index evidence; revalidate full source before specific claims.
- [NN/g — 8 Design Guidelines for Complex Applications](https://www.nngroup.com/articles/complex-application-design/) — `nng-complex`; usability-guidance; search-index evidence; revalidate full source before specific claims.
- [ISO 9241-110 — Interaction principles](https://www.iso.org/standard/75258.html) — `behavior-iso110`; standard-catalog; Prior conversation or reference catalog; revalidate before reuse.
- [Research-Based Web Design & Usability Guidelines](https://www.govinfo.gov/app/details/GOVPUB-HE-PURL-LPS73842) — `behavior-gov-guidelines`; historical-guidance; Prior conversation or reference catalog; revalidate before reuse.
- [Hillside — A Pattern Language for Pattern Writing](https://www.hillside.net/index.php/a-pattern-language-for-pattern-writing) — `behavior-pattern-form`; pattern-writing-guidance; Prior conversation or reference catalog; revalidate before reuse.

Related: [Asynchronous and non-blocking UX](asynchronous-non-blocking-ux.md); [general catalog](../interface-pattern-library/README.md).
