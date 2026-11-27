# ClickUp — component and state contracts (batch 4)

Reviewed 2026-11-27. Baseline: `e6603012b7cb0895c4ec2d72039bff6c0aca372f`. 38 unique new sources (12 opened article records, 23 search previews, 3 section listings). 14 interaction contracts. State models are analytical abstractions; acceptance tests are proposals, not verified ClickUp runtime results. New layout belongs to Labs. No proprietary media copied.

## Pinned object strip (P0)

Object is pinned at bottom until explicitly removed. Reordering uses drag; hovering exposes unpin. This is not proof of app tab history or preservation of unsaved state.

State model: unpinned → / pinned → / hovered → / reordered → / unpinned (alternatives, not necessarily sequential).

Proposed validation: Pin same ID twice, reopen existing object, reorder by keyboard, narrow overflow, permission revoked, deleted item.

Sources: [clickup-bottom-pin](https://help.clickup.com/hc/en-us/articles/6309949834263-Pin-tasks-or-Docs-to-the-bottom-of-your-Workspace).

## Structured query editor (P0)

Select field/operator/value and combine with AND/OR nested groups. Text search scope can be selected; visible custom fields are searched. Some filter values prefill newly created records. AI-built filters remain editable and can be reverted.

State model: empty → / draft → / applied → / nested → / generated → / reverted → / zero matches (alternatives, not necessarily sequential).

Proposed validation: Boolean truth table, invalid values, no matches versus failure, clear group, contextual creation preview, AI unmatched constraint disclosure.

Sources: [clickup-filter-builder](https://help.clickup.com/hc/en-us/articles/6308875427223-Use-filters-to-search-tasks).

## Draft versus shared configuration (P0)

Changed view displays save control. Save updates all with access, autosave persists future changes, save-as creates separate view, revert removes latest change. Concurrent viewers may need reload; guests cannot save.

State model: clean → / dirty → / save → / autosave → / duplicate → / revert → / protected (alternatives, not necessarily sequential).

Proposed validation: Permission rejection, concurrent change, no accidental duplicate, draft navigation and reload; no assumption of real-time shared propagation.

Sources: [clickup-save-view](https://help.clickup.com/hc/en-us/articles/6310370965911-Save-view-changes).

## One object in multiple groups (P0)

List can show same item in each matching multi-value group rather than a combined group. The default is combined; setting saved per view, unavailable on Board. All appearances represent one object.

State model: combined → / single value → / filtered → / collapsed → / ungrouped (alternatives, not necessarily sequential).

Proposed validation: Same ID across groups, edit reflected everywhere, counts distinct IDs versus occurrences, selection deduplication.

Sources: [clickup-grouping](https://help.clickup.com/hc/en-us/articles/6310202447511-Use-grouping-in-views).

## Semantic status and scoped inheritance (P0)

Active, Done and Closed have distinct meaning; optional Not Started group. Children inherit statuses unless customized. Done clears dependencies and is not overdue; Closed hidden by default in List. Custom Closed states unavailable; rename possible.

State model: active → / done → / closed → / optional not started → / inherited → / override (alternatives, not necessarily sequential).

Proposed validation: Move between location schemas, reject unauthorized edit, preserve stable status ID, visible closed toggle, dependency semantics.

Sources: [clickup-status-management](https://help.clickup.com/hc/en-us/articles/6309452618647-Manage-task-statuses).

## Configurable template application (P1)

Template can copy selected properties and settings, including dependencies, dates and subtasks. Formula fields excluded. Same-name distinct custom fields may coexist. Applying a task template cannot be undone; update cannot revert to previous version.

State model: browse → / preview → / select fields → / apply → / success → / limit failure (alternatives, not necessarily sequential).

Proposed validation: Preview destructive effects, schema mapping, duplicate property names, limits, failure atomicity, explicit irreversible confirmation (proposal).

Sources: [clickup-task-template](https://help.clickup.com/hc/en-us/articles/6309918176535-Use-task-templates).

## Offline capability boundary (P0)

Notice appears on disconnect. Previously opened tasks and notes readable but not editable; offline task creation syncs on reconnect. Reminders not creatable offline on mobile; subtasks not creatable offline. Tray tasks cached.

State model: online → / disconnected → / cached read → / offline created → / reconnected (alternatives, not necessarily sequential).

Proposed validation: Queue idempotency, reconnect conflict, failed sync, status visible, mobile capability differences; documentation does not establish conflict algorithm.

Sources: [clickup-offline](https://help.clickup.com/hc/en-us/articles/6308895791127-Offline-Mode).

## Attachment review (P0)

Add comments at points on image/PDF and at video time; assign, reply and resolve. Video shows timestamps in playback; unavailable for cloud attachments.

State model: preview → / add comment → / selected point → / draft → / posted → / assigned → / resolved (alternatives, not necessarily sequential).

Proposed validation: Coordinate transforms with zoom/rotation; page index, media time seek, accessible comment navigation, deleted file/version, permission.

Sources: [clickup-proofing](https://help.clickup.com/hc/en-us/articles/6325985679383-Annotate-images-videos-and-PDFs-with-Proofing).

## Conversation versus audit feed (P0)

New Comments default panel contains discussion and selected high-level updates; Activity retains full history. Task comments now support Chat-style threading, forward and scheduled send. Other comment surfaces not migrated.

State model: comments → / activity → / unread → / thread → / reply → / scheduled (alternatives, not necessarily sequential).

Proposed validation: Unread counts, deep link, audit completeness, no duplicate events, legacy surface support and migration.

Sources: [clickup-comments-revision](https://help.clickup.com/hc/en-us/articles/44421277995415-Task-comments-now-work-like-Chat).

## Conversation to actionable item (P1)

Assign a new/existing comment; notify recipient; resolve using checkbox; links from action items navigate to comment. Resolution notification shows actor. Assignment integrates with task closure warning where configured.

State model: unassigned → / assigned → / unresolved → / resolved (alternatives, not necessarily sequential).

Proposed validation: Assignment change, permissions, notification, jump to source, duplicate assignment and reopen behavior (unverified).

Sources: [clickup-assign-comment](https://help.clickup.com/hc/en-us/articles/6311126397591-Assign-comments).

## Contextual or pinned editor toolbar (P1)

Default toolbar appears near selected text; user may pin to top. Commands vary by surface; undo, redo, insert, clear format and Markdown copy documented.

State model: no selection → / selection → / toolbar → / pinned → / command (alternatives, not necessarily sequential).

Proposed validation: Focus, selection preservation, keyboard, clipping, touch, disabled command, formatting undo.

Sources: [clickup-text-toolbar](https://help.clickup.com/hc/en-us/articles/6325395888023-Format-text-using-the-text-toolbar).

## Visual accessibility preference (P1)

User enables contrast mode. Authenticated Docs toggle-list treatment additionally described in text toolbar article; do not generalize to public or mobile surfaces.

State model: normal → / high contrast → / light → / dark (alternatives, not necessarily sequential).

Proposed validation: Measure contrast, visible focus, reduced motion, screen reader and zoom independently; no WCAG conformance assertion.

Sources: [clickup-high-contrast](https://help.clickup.com/hc/en-us/articles/6310793610391-Activate-High-Contrast-mode), [clickup-text-toolbar](https://help.clickup.com/hc/en-us/articles/6325395888023-Format-text-using-the-text-toolbar).

## Notification grouping and reversible clearing (P1)

Primary, Other, Later and Cleared tabs; same object notifications grouped; filters persist. Cleared groups recoverable for 30 days; clear-all respects active filter. Open group displays related object/details.

State model: unread → / read → / snoozed → / cleared → / restored → / expired (alternatives, not necessarily sequential).

Proposed validation: No duplicate notifications, keyboard parity, filtered bulk scope, restore order, time zone and accessible badge.

Sources: [clickup-inbox](https://help.clickup.com/hc/en-us/articles/33947959867543-What-is-the-Inbox).

## Experimental layout provenance (P0)

Global rail remains visible; contextual sidebar can collapse and preview on hover. Labs toggle can restore older layout. Recents can pin current page or everywhere. Page navigation can nest under sidebar shortcuts.

State model: legacy → / Labs enabled → / expanded → / collapsed → / preview → / pinned (alternatives, not necessarily sequential).

Proposed validation: Pointer, keyboard, touch, width, permission, settings persistence and old/new layout migration; not all accounts have same UI.

Sources: [clickup-layout](https://help.clickup.com/hc/en-us/articles/45167704482583-Use-the-new-ClickUp-layout).

## Directory expansion

- [ClickUp Help — Tasks](https://help.clickup.com/hc/en-us/sections/17043616404631-Tasks): Section listing opened; parent article advertises 72 articles; not all pages traversed.
- [ClickUp Help — Intro to views](https://help.clickup.com/hc/en-us/sections/17044387445399-Intro-to-views): Section listing opened; parent article advertises 28 articles; not all pages traversed.
- [ClickUp Help — Communicating in ClickUp](https://help.clickup.com/hc/en-us/sections/17043486267927-Communicating-in-ClickUp): Section listing opened; parent article advertises 20 articles; not all pages traversed.

Search-only references are marked separately in [sources.json](../sources.json); do not present them as full article extraction. No new screenshots were inspected in this batch. No exhaustive article denominator. No changes to the application or plugin.

[Structured inventory](component-states-2026-11-27.json).
