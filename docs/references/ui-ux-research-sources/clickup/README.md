# ClickUp — expanded product and interaction inventory

2026-11-27. Companion to [initial audit](../clickup-coverage-audit-2026-11-27.md). Baseline commit: `54e69caf21ff29069bd50e4fa6d3650a0cee450d`. 10 research families; 113 additional source entries; 8 opened official screenshot references. Public documentation and static vendor imagery, not authenticated runtime or full crawl. Some UI revisions coexist. Experimental and beta features remain labeled. All source imagery is link-only because redistribution rights are not established.

## New findings versus initial audit

- Gallery is a newly located view; do not treat the initial 17-item overview as exhaustive. Official view directory also lists Chat view; historical availability and current creation surfaces require verification.
- Library includes Favorites, Artifacts, Docs, Meeting Notes, Sheets, Dashboards, Whiteboards, Forms, Clips, Images, PDFs, Audio, Videos, and Spaces. Agents sidebar has its own tools, creation and management surfaces. The current layout is under Labs documentation: do not generalize rollout to all accounts.
- Separate database Table view from standalone Sheets; separate page views from task views; separate app-level tabs from browser tab sleeping.
- Gallery card size/cover/fields, contextual group creation, drag, shared saving, personal autosave, protected/private views are separable state contracts.

## Shell, navigation and discovery (P0)

Persistent rail and contextual panels; preview of collapsed panel by hover; pin Recents on page or everywhere; filtered sections; library by asset type; optional page navigation in sidebar. Keep layout revisions distinct.

**Pending validation:** Capture rail, sidebar, preview, pin/unpin, scroll, search, keyboard focus, touch alternative, back/forward and tab persistence.

Sources: [clickup-global-nav](https://help.clickup.com/hc/en-us/articles/32050886697495-What-is-Global-Navigation) · [clickup-home-sidebar](https://help.clickup.com/hc/en-us/articles/32057009861271-What-is-the-Home-Sidebar) · [clickup-sidebar-defaults](https://help.clickup.com/hc/en-us/articles/32854720651543-Default-Home-Sidebar-sections-and-settings) · [clickup-sidebar-custom](https://help.clickup.com/hc/en-us/articles/32855333466903-Create-custom-Home-Sidebar-sections) · [clickup-sidebar-search](https://help.clickup.com/hc/en-us/articles/32490367010839-Create-and-search-items-in-the-Home-and-Spaces-Sidebars) · [clickup-favorites](https://help.clickup.com/hc/en-us/articles/6308862167575-Favorites) · [clickup-location-header](https://help.clickup.com/hc/en-us/articles/33801223563415-Expand-the-location-header) · [clickup-command](https://help.clickup.com/hc/en-us/articles/6533695640343-What-is-the-AI-Command-Bar) · [clickup-search](https://help.clickup.com/hc/en-us/articles/6311703331479-Search-your-Workspace) · [clickup-search-filter](https://help.clickup.com/hc/en-us/articles/12609594406679-Sort-and-filter-AI-Command-Bar-results) · [clickup-toolbar](https://help.clickup.com/hc/en-us/articles/11583054545303-Intro-to-the-toolbar) · [clickup-customize](https://help.clickup.com/hc/en-us/articles/35709363436823-Customize-your-ClickUp-experience) · [clickup-layout](https://help.clickup.com/hc/en-us/articles/45167704482583-Use-the-new-ClickUp-layout) · [clickup-intro-4](https://help.clickup.com/hc/en-us/articles/31142608907543-Intro-to-ClickUp-4-0) · [clickup-create](https://help.clickup.com/hc/en-us/articles/6309854442391-Create-items) · [clickup-hubs](https://help.clickup.com/hc/en-us/articles/35206995778711-What-are-Hubs?).

## Views, query and visualization (P0)

One collection projected into multiple views. Gallery adds responsive cards, three card sizes, optional covers, field ordering, one group dimension (no subgroup), field/operator/value filtering, shared save vs autosave vs revert; view menu pin, private, protect, default, duplicate, move and delete. Table offers spreadsheet-like editing; Board changes grouping property via drag; distinguish task views from page content and legacy Chat view.

**Pending validation:** Validate each view, grouping/filter semantics, multi-select, drag/keyboard equivalence, large collections, empty/loading/error, personal/shared persistence, overflow menu and permission restrictions.

Sources: [clickup-gallery](https://help.clickup.com/hc/en-us/articles/45014882844567-Create-and-customize-Gallery-view) · [clickup-add-view](https://help.clickup.com/hc/en-us/articles/26032576190615-Add-a-view) · [clickup-list-customize](https://help.clickup.com/hc/en-us/articles/7255389296919-Customize-List-view) · [clickup-board](https://help.clickup.com/hc/en-us/articles/6310080798615-Create-and-share-a-Board-view) · [clickup-board-customize](https://help.clickup.com/hc/en-us/articles/35342044832279-Customize-Board-view) · [clickup-table](https://help.clickup.com/hc/en-us/articles/6329890854935-Create-and-share-a-Table-view) · [clickup-calendar](https://help.clickup.com/hc/en-us/articles/6310085740183-Intro-to-Calendar-view) · [clickup-gantt](https://help.clickup.com/hc/en-us/articles/6310249474967-Create-and-share-a-Gantt-view) · [clickup-timeline](https://help.clickup.com/hc/en-us/articles/6310399909143-Create-and-share-a-Timeline-view) · [clickup-mind-map](https://help.clickup.com/hc/en-us/articles/6310295262231-Create-and-share-a-Mind-Map) · [clickup-workload](https://help.clickup.com/hc/en-us/articles/6310449699735-Use-Workload-view) · [clickup-create-from-views](https://help.clickup.com/hc/en-us/articles/31463619842711-Create-a-task-from-views) · [clickup-view-private](https://help.clickup.com/hc/en-us/articles/6310155254039-Create-and-share-a-private-view) · [clickup-view-export](https://help.clickup.com/hc/en-us/articles/6310174308631-Export-List-and-Table-views) · [clickup-tag-filter](https://help.clickup.com/hc/en-us/articles/6310140728855-Filter-tags-in-views) · [clickup-views](https://help.clickup.com/hc/en-us/articles/6329880717719-Intro-to-views) · [clickup-page-views](https://help.clickup.com/hc/en-us/articles/6310347914263-Use-Page-views) · [clickup-view-limits](https://help.clickup.com/hc/en-us/articles/32274881672599-Views-feature-availability-and-limits) · [clickup-view-bar](https://help.clickup.com/hc/en-us/articles/19063083658135-Intro-to-the-Views-Bar) · [clickup-view-control](https://help.clickup.com/hc/en-us/articles/35368731425175-The-views-control-bar) · [clickup-task-views](https://help.clickup.com/hc/en-us/articles/6310172583831-Use-Task-views) · [clickup-protect](https://help.clickup.com/hc/en-us/articles/6310368663447-Protect-a-view).

## Objects, properties, relationships and bulk operations (P0)

Hierarchy: Workspace > Space > Folder/Subfolder > List > task/subtask, with multiple-list projection where enabled. Typed fields scoped by type and location; collapsible sections; relationships and dependencies; comments/activity separate; open full screen, modal, sidebar; preference reused. Bulk selection changes status, fields, links or location subject to permission.

**Pending validation:** Verify focus restoration, editing conflicts, pending/rollback, no relationship state, validation, field conversion warnings, type change, deletion and selection scope.

Sources: [clickup-task-type](https://help.clickup.com/hc/en-us/articles/17564381376919-Custom-task-types) · [clickup-field-types](https://help.clickup.com/hc/en-us/articles/6303499162647-Custom-Field-types) · [clickup-field-manager](https://help.clickup.com/hc/en-us/articles/13066263096727-Intro-to-Custom-Field-Manager) · [clickup-field-create](https://help.clickup.com/hc/en-us/articles/6303481086487-Create-Custom-Fields) · [clickup-field-by-type](https://help.clickup.com/hc/en-us/articles/30974227164311-Create-Custom-Fields-by-task-type) · [clickup-field-defaults](https://help.clickup.com/hc/en-us/articles/30406587945879-Set-default-values-for-Custom-Fields) · [clickup-field-convert](https://help.clickup.com/hc/en-us/articles/14277190461207-Convert-Custom-Fields) · [clickup-field-merge](https://help.clickup.com/hc/en-us/articles/14277239882519-Merge-Custom-Fields) · [clickup-task-menu](https://help.clickup.com/hc/en-us/articles/34908401465111-Task-settings-menu) · [clickup-task-description](https://help.clickup.com/hc/en-us/articles/34958796358039-Task-fields-and-the-task-description) · [clickup-bulk](https://help.clickup.com/hc/en-us/articles/6309768265495-Manage-tasks-with-the-Bulk-Action-Toolbar) · [clickup-bulk-subtasks](https://help.clickup.com/hc/en-us/articles/6309490332695-Manage-subtasks-in-a-task-window-using-the-Bulk-Action-Toolbar) · [clickup-link-task](https://help.clickup.com/hc/en-us/articles/6309896464407-Link-tasks) · [clickup-recurring](https://help.clickup.com/hc/en-us/articles/6309885016471-Use-recurring-tasks) · [clickup-lists](https://help.clickup.com/hc/en-us/articles/6311877646999-Intro-to-Lists) · [clickup-hierarchy](https://help.clickup.com/hc/en-us/articles/20480724378135-Hierarchy-best-practices) · [clickup-tasks](https://help.clickup.com/hc/en-us/articles/10552031987735-Intro-to-tasks) · [clickup-task-layout](https://help.clickup.com/hc/en-us/articles/29665520762647-Task-layouts) · [clickup-task-sidebar](https://help.clickup.com/hc/en-us/articles/35041742373015-Tasks-right-sidebar) · [clickup-task-fields](https://help.clickup.com/hc/en-us/articles/34958820098839-Custom-Fields-subtasks-relationships-and-attachments) · [clickup-relationships](https://help.clickup.com/hc/en-us/articles/29728065999383-Relationships-on-tasks).

## Docs, wiki, rich text and knowledge (P1)

Nested document pages, content blocks, wikis, style controls, task creation from text, slash commands, hub, bulk actions and linked knowledge. Export formats are documented, not fidelity tested.

**Pending validation:** Capture selection toolbar, slash menu, nested page tree, block movement, undo, link navigation, editor keyboard/clipboard, collaboration and export fidelity.

Sources: [clickup-docs](https://help.clickup.com/hc/en-us/articles/6328174371351-Intro-to-Docs) · [clickup-doc-page-settings](https://help.clickup.com/hc/en-us/articles/6325436135191-Page-Settings-Menu) · [clickup-doc-settings](https://help.clickup.com/hc/en-us/articles/6325168155415-Doc-settings) · [clickup-docs-hub](https://help.clickup.com/hc/en-us/articles/14235667017495-Docs-Hub) · [clickup-slash](https://help.clickup.com/hc/en-us/articles/6308960837911-Use-Slash-Commands) · [clickup-text-format](https://help.clickup.com/hc/en-us/articles/6311721231639-Intro-to-text-formatting).

## Whiteboards, forms and sheets (P1)

Canvas main toolbar plus selection toolbar; form builder separates creation from submission, maps fields into tasks; Sheets add spreadsheet objects distinct from Table views (formulas, charts, conditional formatting).

**Pending validation:** Verify zoom/pan, object selection, keyboard, pointer and touch, undo, form preview/validation/submission/retry, Sheets formula errors and range selection.

Sources: [clickup-whiteboard-items](https://help.clickup.com/hc/en-us/articles/6326217118615-Add-items-to-a-Whiteboard) · [clickup-whiteboard-create](https://help.clickup.com/hc/en-us/articles/6326337792023-Create-a-Whiteboard) · [clickup-whiteboard-limits](https://help.clickup.com/hc/en-us/articles/29295148751639-Whiteboards-feature-availability-and-limits) · [clickup-form-logic](https://help.clickup.com/hc/en-us/articles/30720189184791-Use-conditional-logic-in-Forms) · [clickup-form-questions](https://help.clickup.com/hc/en-us/articles/30688109079191-Add-questions-to-a-Form) · [clickup-form-design](https://help.clickup.com/hc/en-us/articles/30720459329047-Customize-a-Form-s-design) · [clickup-form-create](https://help.clickup.com/hc/en-us/articles/30687934700055-Create-and-access-Forms) · [clickup-form-hub](https://help.clickup.com/hc/en-us/articles/26301017413911-Forms-Hub) · [clickup-sheets-hub](https://help.clickup.com/hc/en-us/articles/44459955883799-Sheets-Hub) · [clickup-sheets-limits](https://help.clickup.com/hc/en-us/articles/44538262976791-Sheets-feature-availability-and-limits) · [clickup-forms](https://help.clickup.com/hc/en-us/articles/6310233090711-Intro-to-Forms-and-Form-view).

## Dashboard, reporting, time and planning (P1)

Composable dashboards, card data contracts, chart drilldown, auto-layout, timeline capacity, tracked/estimated time, planner and calendar sync. Distinguish aggregate chart from its source records.

**Pending validation:** Validate filter scope, date/time zone, empty/zero/loading/error, stale data, drilldown consistency, accessible chart tables and export.

Sources: [clickup-cards](https://help.clickup.com/hc/en-us/articles/25757497269143-Intro-to-cards) · [clickup-card-data](https://help.clickup.com/hc/en-us/articles/29783222444823-Data-available-on-cards) · [clickup-dashboard-drill](https://help.clickup.com/hc/en-us/articles/14995002699927-Drill-down-view-for-Dashboard-cards) · [clickup-dashboard-settings](https://help.clickup.com/hc/en-us/articles/35663348616343-Dashboard-settings) · [clickup-resource](https://help.clickup.com/hc/en-us/articles/6310374956439-Resource-management) · [clickup-time-track](https://help.clickup.com/hc/en-us/articles/6304106812823-Track-time-on-tasks) · [clickup-time-report](https://help.clickup.com/hc/en-us/articles/15479699552151-Use-views-for-time-reporting) · [clickup-planner](https://help.clickup.com/hc/en-us/articles/29051586233879-What-is-the-Planner) · [clickup-planner-open](https://help.clickup.com/hc/en-us/articles/35975772703767-Open-your-Planner) · [clickup-planner-customize](https://help.clickup.com/hc/en-us/articles/35975729722519-Customize-your-Planner) · [clickup-dashboard](https://help.clickup.com/hc/en-us/articles/14237901038231-Create-a-Dashboard).

## Collaboration, inbox, sharing and lifecycle (P1)

Inbox and notifications, chat, comments, sharing by resource and role, restore lifecycle, activity/audit history. Permission gating is distinct from visibility and actual access enforcement.

**Pending validation:** Verify notification read/snooze behavior, deep links, conflict states, invite/role changes, private content access, recovery, keyboard and destructive-action handling.

Sources: [clickup-inbox](https://help.clickup.com/hc/en-us/articles/33947959867543-What-is-the-Inbox) · [clickup-inbox-custom](https://help.clickup.com/hc/en-us/articles/16101057400471-Customize-your-Inbox) · [clickup-notifications](https://help.clickup.com/hc/en-us/articles/6325918957335-Notification-settings) · [clickup-permissions](https://help.clickup.com/hc/en-us/articles/6309225399703-Intro-to-permissions) · [clickup-permissions-detail](https://help.clickup.com/hc/en-us/articles/6309221065495-Permissions-in-detail) · [clickup-role-permissions](https://help.clickup.com/hc/en-us/articles/6309195687959-Manage-Custom-Role-permissions) · [clickup-share](https://help.clickup.com/hc/en-us/articles/6309266954263-Share-Spaces-Folders-Subfolders-Lists-and-tasks) · [clickup-trash](https://help.clickup.com/hc/en-us/articles/6311742742423-Restore-items-from-the-Trash) · [clickup-task-delete](https://help.clickup.com/hc/en-us/articles/6311358652951-Delete-a-task) · [clickup-audit](https://help.clickup.com/hc/en-us/articles/21929900448535-Workspace-audit-logs).

## Brain, agents, artifacts and creative tools (P1)

Manual mention/DM/assignment, schedule or automation triggers; per-trigger prompt; skills, tool access, recent/preference/intelligence memory modes as documented; preference memory approval; personal app knowledge may expose data to agent users. Artifact creation from chat and templates; Labs AI Drive and beta Agent Workflows must remain explicitly flagged. Creative Studio editor and export.

**Pending validation:** Capture agent builder, tool grants, schedule, logs, cancel/retry, artifact preview/editor/revision, execution sandbox, errors and approval behavior. No runtime security or memory-capacity claim.

Sources: [clickup-ai-intro](https://help.clickup.com/hc/en-us/articles/12578085238039-What-is-ClickUp-AI) · [clickup-ai-tools](https://help.clickup.com/hc/en-us/articles/33032484272023-What-are-ClickUp-AI-tools) · [clickup-brain-chat](https://help.clickup.com/hc/en-us/articles/28401383762455-Chat-with-Brain) · [clickup-brain-context](https://help.clickup.com/hc/en-us/articles/20658787666071-Collaborate-with-ClickUp-Brain-anywhere-in-your-Workspace) · [clickup-brain-in-chat](https://help.clickup.com/hc/en-us/articles/28287152693783-Use-ClickUp-Brain-in-Chat) · [clickup-agent-chat](https://help.clickup.com/hc/en-us/articles/37131966192151-Use-ClickUp-Agents-in-Chat) · [clickup-agent-overview](https://help.clickup.com/hc/en-us/articles/36487554975255-How-can-Super-Agents-help-your-team) · [clickup-agent-config](https://help.clickup.com/hc/en-us/articles/37092796379927-Super-Agent-instructions-Skills-triggers-knowledge-and-memory) · [clickup-ai-access](https://help.clickup.com/hc/en-us/articles/44785311467671-Manage-ClickUp-AI-access-for-roles-and-people) · [clickup-agent-workflow](https://help.clickup.com/hc/en-us/articles/44785851374487-Create-and-run-an-Agent-Workflow) · [clickup-agent-workflow-limits](https://help.clickup.com/hc/en-us/articles/44786053516439-Agent-Workflows-feature-availability-and-limits) · [clickup-ai-drive](https://help.clickup.com/hc/en-us/articles/45020575265687-Use-AI-Drive) · [clickup-artifacts](https://help.clickup.com/hc/en-us/articles/40440126306199-Create-custom-apps-dashboards-prototypes-and-other-Artifacts) · [clickup-creative-studio](https://help.clickup.com/hc/en-us/articles/44786325764247-Use-Creative-Studio) · [clickup-automation-modal](https://help.clickup.com/hc/en-us/articles/34136507954583-Access-the-Automations-modal) · [clickup-calendar-automation](https://help.clickup.com/hc/en-us/articles/29626553900951-Google-Calendar-Automations) · [clickup-automation-triggers](https://help.clickup.com/hc/en-us/articles/6312128853015-Use-Automation-Triggers) · [clickup-automation-actions](https://help.clickup.com/hc/en-us/articles/6312097314199-Use-Automation-Actions) · [clickup-automation-conditions](https://help.clickup.com/hc/en-us/articles/6312136485527-Use-Automation-Conditions).

## Platforms, accessibility and integration (P1)

Web, desktop and mobile differ; high-contrast preference and documented shortcuts do not establish WCAG compliance. Mobile task tabs differ from browser tabs; test in-app open-object history separately.

**Pending validation:** Capture breakpoints, zoom, reduced motion, focus order, screen reader names, keyboard traps, touch, offline/reconnect and internationalization.

Sources: [clickup-keyboard](https://help.clickup.com/hc/en-us/articles/6309030550167-Use-keyboard-shortcuts) · [clickup-my-settings](https://help.clickup.com/hc/en-us/articles/6311968998167-My-Settings) · [clickup-theme](https://help.clickup.com/hc/en-us/articles/6310791806359-Change-your-Workspace-appearance-and-theme) · [clickup-mobile-menu](https://help.clickup.com/hc/en-us/articles/34981300374679-Access-your-work-from-the-More-menu-on-mobile) · [clickup-mobile-inbox](https://help.clickup.com/hc/en-us/articles/15147158275735-Intro-to-Inbox-on-mobile) · [clickup-browser-tabs](https://help.clickup.com/hc/en-us/articles/30999959024151-Browser-tab-limits) · [clickup-mobile](https://help.clickup.com/hc/en-us/articles/15145935126679-Intro-to-the-mobile-app) · [clickup-mobile-layout](https://help.clickup.com/hc/en-us/articles/22374093529751-Customize-your-task-layout-on-mobile).

## Integrations, API and MCP (P1)

Public API and webhook subscriptions, OAuth and token authentication, rate limits per token; directory includes MCP and app integrations. No live API calls or endpoint-by-endpoint extraction.

**Pending validation:** Verify API schemas/version, permissions, retries, idempotency, rate limits, webhook signatures and exact MCP capabilities before implementation.

Sources: [clickup-integrations-index](https://help.clickup.com/hc/en-us/categories/5735460831255-Integrations-API-and-MCP) · [clickup-api](https://developer.clickup.com/docs/Getting%20Started) · [clickup-api-auth](https://developer.clickup.com/docs/authentication) · [clickup-api-webhooks](https://developer.clickup.com/docs/webhooks) · [clickup-api-errors](https://developer.clickup.com/docs/common_errors).

## Verified visual reference links

| Evidence | Observed detail | Limit |
|---|---|---|
| [clickup-global-navigation](https://help.clickup.com/hc/article_attachments/45167884715543) | Home sidebar and icon rail, unread badges, hierarchy and sections. | Static, link-only |
| [clickup-library-preview](https://help.clickup.com/hc/article_attachments/45167886370967) | Floating Library preview overlays content; asset-type navigation with icons. | Static, link-only |
| [clickup-agents-sidebar](https://help.clickup.com/hc/article_attachments/45167775936151) | Agents sidebar shows workflows and creative tools marked beta, activity, memory and credits. | Static, link-only |
| [clickup-gallery-create](https://help.clickup.com/hc/article_attachments/45014919368343) | View picker with search, privacy/pin checkboxes and Gallery. | Static, link-only |
| [clickup-gallery-size](https://help.clickup.com/hc/article_attachments/45014923256215) | Customize panel with three card size options and selected checkmark. | Static, link-only |
| [clickup-gallery-menu](https://help.clickup.com/hc/article_attachments/45014927625367) | View tab context menu with pin/private/protect/autosave/default toggles and destructive actions. | Static, link-only |
| [clickup-agent-triggers](https://help.clickup.com/hc/article_attachments/42696534857879) | Manual, scheduled and automated trigger groups with toggles. | Static, link-only |
| [clickup-agent-edit-prompt](https://help.clickup.com/hc/article_attachments/42696518727703) | Hover-revealed edit prompt control on trigger row. | Static, link-only |

## Reusable hypotheses and QA

- Separate object identity, view query, per-user appearance and shared view settings. Test that switching views never creates duplicate objects; dragging across status groups updates the underlying property, subject to permissions.
- Contextual panels should preserve navigation context and restore focus when dismissed. Ensure hover previews have keyboard/touch equivalents. Verify close, reopen, pin scope, clipping, resize and history.
- Typed objects should expose only relevant fields, without losing location-based metadata. Explicitly test type change, defaults, invalid fields, permission failure and relationship removal.
- Composable reporting: chart drilldown should resolve to the same filtered dataset; track time zones, stale data, zero and empty states.
- Agent authoring needs inspectable instructions, scoped tools, knowledge, trigger, schedule, run status and audit. Test permissions, approval, cancellation, retry and memory visibility; do not infer behavior from screenshots.

## Remaining coverage

- Full article-by-article crawl and deduplication against official help taxonomy
- Authenticated product interaction across plans and platforms
- Complete screenshot/video coverage, visual measurements and motion timing
- Full API endpoint/field enumeration, release history, integrations catalog and plan matrix
- Cross-index into reusable semantic pattern catalog with acceptance tests

Machine-readable inventory: [inventory.json](inventory.json). Source registry: [sources.json](../sources.json). No proprietary media or product source code copied. No application implementation changed.

## Third extraction batch

- [Technical architecture and interaction contracts](technical-interactions-2026-11-27.md)
- [Structured technical inventory](technical-interactions-2026-11-27.json)

## Fourth extraction batch

- [Component and state contracts](component-states-2026-11-27.md)
- [Structured state inventory](component-states-2026-11-27.json)

## Fifth extraction batch

- [Visual system and evidence](visual-system-2026-11-27.md)
- [Structured visual evidence](visual-system-2026-11-27.json)

## Sixth extraction batch

- [Release-aware flows and motion discovery](flows-motion-2026-11-27.md)
- [Structured flow and release inventory](flows-motion-2026-11-27.json)
