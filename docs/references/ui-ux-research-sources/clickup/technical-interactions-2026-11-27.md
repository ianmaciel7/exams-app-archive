# ClickUp — technical architecture, interaction contracts and documentation map

Reviewed 2026-11-27; baseline `cf3f5572431feb214436c8210b9ed279ec4c1525`. Public research only. 9 official top-level Help categories inspected; section samples below are not complete article lists. 25 new unique sources; 13 documented behavior records; 3 opened visual references and 1 failed image retrieval. No private data or proprietary media copied.

## Documentation map

- [Get started](https://help.clickup.com/hc/en-us/categories/5735245366551-Get-started): Setup, Navigation, Import/export, Hierarchy, Tasks, Teams, Use cases.
- [Agents](https://help.clickup.com/hc/en-us/categories/37728141474071-ClickUp-Agents): Agent setup and management.
- [AI](https://help.clickup.com/hc/en-us/categories/37648258297623-ClickUp-AI): Brain, Brain MAX desktop/mobile/Chrome, Content generation.
- [Features](https://help.clickup.com/hc/en-us/categories/5414365970455-Features-and-ClickApps): Automations, Cards, Labs, Planner, Clips, Connected Search, Creative Studio, Custom Fields, Custom Task IDs, Dashboards, Docs, Goals, My Tasks, Personal List, Relationships, Scheduling, Sheets, Sprints, Tags, Templates, Time tracking, Whiteboards, Work in Progress limits.
- [Chat](https://help.clickup.com/hc/en-us/categories/29564258203671-Chat): Messages, Direct messages, Channels, Posts, SyncUps.
- [Integrations](https://help.clickup.com/hc/en-us/categories/5735460831255-ClickApps-and-Integrations): Sync, Integrations, API, MCP.
- [Mobile](https://help.clickup.com/hc/en-us/categories/5852957874455-Mobile): Home, Inbox, Docs, Search, Sharing, Launch page.
- [Technical support](https://help.clickup.com/hc/en-us/categories/5927901136151-Technical-Support): Troubleshooting.
- [Data and security](https://help.clickup.com/hc/en-us/categories/19621427111447-Data-privacy-and-security): Audit logs, SSO, Backup, Retention, Prompt injection, Public view authentication.

The public Help Center article API pagination attempt was inaccessible in the web tool. Do not infer that the API is universally unavailable, or claim an exhaustive article inventory. Use the category tree to expand further.

## Developer reference

[Official agent index](https://developer.clickup.com/llms.txt) points to Markdown documentation and REST API references. [OpenAPI guide](https://developer.clickup.com/docs/open-api-spec) links to [v2 JSON](https://developer.clickup.com/openapi/clickup-api-v2-reference.json) and [v3 specification](https://developer.clickup.com/openapi/ClickUp_PUBLIC_API_V3.yaml). These were retrieved as web references, not parsed and validated locally.

- v2: Authorization, Attachments, Comments, Custom Task Types, Custom Fields, Folders, Goals, Guests, Lists, Members, Roles, Shared Hierarchy, Spaces, Tags, Tasks, Task Checklists, Task Relationships, Templates, Workspaces, User Groups, Time Tracking, Time Tracking (Legacy), Users, Views, Webhooks.
- v3: Privacy and access, Attachments, Audit Logs, Chat, Docs, Tasks.
- REST supports personal tokens and OAuth; [MCP](https://help.clickup.com/hc/en-us/articles/33335772678423-What-is-ClickUp-MCP) uses OAuth only. Keep authentication, capabilities and availability separate.
- [MCP tool catalog](https://developer.clickup.com/docs/mcp-tools) documents object operations, bulk operator, search and time records. No authenticated tool invocation.
- [Rate limits](https://developer.clickup.com/docs/rate-limits): 100/min/token for Free, Unlimited and Business; 1,000 for Business Plus; 10,000 for Enterprise/Enterprise Plus. Handle 429 and rate-limit headers; revalidate plans.
- [Connected Search](https://help.clickup.com/hc/en-us/articles/14642390285463-Connected-Search): personal and shared connections differ in scope; shared connection may expose indexed content accessible to connecting account. Show scope before consent.

## Interaction contracts

### clickup-synced-blocks

One source block, multiple live instances. Source ACL controls read/edit; instance protection is local. Unsync copy retains text; deleting source can preserve or remove copies; history at original; mobile read-only.

Proposed QA (not a ClickUp test result): Test inaccessible original, stale permission, deletion confirmation, detach, sync conflicts and mobile.

Source: [clickup-synced-content](https://help.clickup.com/hc/en-us/articles/42375806482711-Use-Synced-Content).

### clickup-block-editor

Block drag handle reveals contextual actions, insertion guideline, keyboard movement; heading collapse and two-stage Select All when enabled.

Proposed QA (not a ClickUp test result): Test keyboard/touch discovery, multi-selection, focus, undo and collapsed range.

Source: [clickup-content-blocks](https://help.clickup.com/hc/en-us/articles/31672686246807-Content-Blocks).

### clickup-dashboard-reflow

Drag/resize causes neighboring cards to adjust; optional compaction; up to five recent layout undos, reset by other edits; per-card refresh and freshness label.

Proposed QA (not a ClickUp test result): Test grid reflow, responsive constraints, undo boundary, failed refresh and stale data.

Source: [clickup-dashboard-layout](https://help.clickup.com/hc/en-us/articles/34275916892951-Move-and-resize-cards-on-Dashboards).

### clickup-dependency-warning

Configurable warning when attempting to close work blocked by dependencies.

Proposed QA (not a ClickUp test result): Test allowed override, cancellation, source permissions and keyboard.

Source: [clickup-dependency-warning](https://help.clickup.com/hc/en-us/articles/6304410420759-Dependency-Warnings).

### clickup-completion-warning

Warn before closing if unresolved subtasks, comments or checklist items remain; scope configured by Space.

Proposed QA (not a ClickUp test result): Test resolve versus continue, navigation to offending items, counts, and no warning when complete.

Source: [clickup-incomplete-warning](https://help.clickup.com/hc/en-us/articles/6304420229527-Incomplete-Warning).

### clickup-scoped-tag-manager

Central manager organized by Space; current context selected based on entry point; task tags distinct from document and time tags.

Proposed QA (not a ClickUp test result): Test global versus local scope, renaming impact, empty results and deletion.

Source: [clickup-tag-manager](https://help.clickup.com/hc/en-us/articles/41121088087319-What-is-the-Tag-Manager).

### clickup-embedded-live-object

Canvas references to tasks and Docs allow edits; convert freeform items to tasks; export excludes embedded tasks/Docs.

Proposed QA (not a ClickUp test result): Test same object identity, access, remove reference versus delete source and export disclosure.

Source: [clickup-whiteboard-objects](https://help.clickup.com/hc/en-us/articles/17217215332887-Add-tasks-and-Docs-to-a-Whiteboard).

### clickup-draft-lifecycle

Draft, scheduled and sent tabs; draft stays local to originating device and expires after 90 days; row actions for edits, reschedule, send or delete.

Proposed QA (not a ClickUp test result): Test accidental navigation, cross-device limitation, time zone, failure and expiry disclosure.

Source: [clickup-drafts-sent](https://help.clickup.com/hc/en-us/articles/30093730138263-View-draft-scheduled-and-sent-messages-and-comments).

### clickup-mobile-entry

A user can choose a preferred mobile launch destination.

Proposed QA (not a ClickUp test result): Test permission changes, deleted destination and fallback.

Source: [clickup-mobile-launch](https://help.clickup.com/hc/en-us/articles/16765947283991-Choose-your-mobile-launch-page).

### clickup-action-gate

Vendor describes parallel inspection of untrusted content and confirmation before flagged writes/external actions; autonomous runs are policy-dependent.

Proposed QA (not a ClickUp test result): Test false positives, denial, audit trace and noninteractive policy. Not security certification.

Source: [clickup-prompt-injection](https://help.clickup.com/hc/en-us/articles/42114128067095-How-ClickUp-protects-against-prompt-injection).

### clickup-index-lifecycle

Index begins after connection, updates periodically or via events, and is removed on disconnect. Personal vs organizational connections have different visibility.

Proposed QA (not a ClickUp test result): Test index progress, source ACL change, disconnect, stale results and cross-user access.

Source: [clickup-connected-search](https://help.clickup.com/hc/en-us/articles/14642390285463-Connected-Search).

### clickup-mcp-boundary

ClickUp server uses OAuth and exposes permitted actions; Connected Search from external apps remains in-workspace.

Proposed QA (not a ClickUp test result): Test tool scope, consent, revocation, destructive actions and authorization failure.

Source: [clickup-mcp-outbound](https://help.clickup.com/hc/en-us/articles/33335772678423-What-is-ClickUp-MCP).

### clickup-webhook-recovery

Delivery health changes to failing after non-success or over seven seconds; up to five retries per event; suspension at fail count 100 or 401/410. Exhausted events not replayed automatically.

Proposed QA (not a ClickUp test result): Test deduplication, reconciliation, queue, retry policy and observability.

Source: [clickup-webhook-health](https://developer.clickup.com/docs/webhookhealth).

## Visual evidence

- [clickup-block-drag](https://help.clickup.com/hc/article_attachments/31672686242967) — Visible block handle, dragged text and horizontal insertion marker. Status: source-image-opened-and-inspected. Link-only.
- [clickup-dashboard-layout-menu](https://help.clickup.com/hc/article_attachments/34275970785175) — Menu showing auto layout and auto refresh toggles alongside grouped actions. Status: source-image-opened-and-inspected. Link-only.
- [clickup-incomplete-warning-modal](https://help.clickup.com/hc/article_attachments/39240807056535) — Three unresolved-item rows and distinct resolve/continue actions. Status: source-image-opened-and-inspected. Link-only.
- [clickup-synced-content-example](https://help.clickup.com/hc/article_attachments/42379359154711) — Article labels this as a synced content screenshot; image fetch failed. Status: source-linked-fetch-failed. Link-only.

## Remaining gaps

- Help Center article API pagination URL was inaccessible in web tool; no complete denominator or recall percentage
- Raw OpenAPI references linked, not locally parsed or schema-validated
- No runtime sessions, screenshots across plans, CSS tokens or motion timings
- Synced content image fetch failed
- Integration-by-integration and feature article-by-article extraction remains incomplete

Machine-readable companion: [technical-interactions-2026-11-27.json](technical-interactions-2026-11-27.json). The source registry deduplicates article/category IDs regardless of slug. No claim of complete product coverage.
