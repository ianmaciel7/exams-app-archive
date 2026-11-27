# ClickUp — product-specific coverage audit and documented UX inventory

Review: 2026-11-27. Baseline: `7eaaee7954fbea2eae884862d04a5e12b6cea09a`. Public official documentation only; no authenticated application session, screenshots, motion recordings, DOM/CSS or usability testing. Current layout and ClickUp 4.0 documentation may represent different rollout states; record platform, plan and release when collecting runtime evidence.

## Archive baseline

Recursive tree at 7eaaee7954fbea2eae884862d04a5e12b6cea09a: 665 entries, not truncated; no ClickUp-named path. GitHub code and issue searches returned no matches (index availability not established). Ten checked research/catalog files (RESEARCH-INDEX, both research/interface source registers, UI/UX references, three discovery reports, domain research, component interaction research and knowledge coverage audit) contained no case-insensitive ClickUp mention. This is a bounded negative finding, not proof of absence from every historical blob. Existing generic patterns remain useful.

## Documented behavior and open evidence gaps

| Priority | Area | Documented behavior | Further evidence needed |
|---|---|---|---|
| P0 | Shell/navigation | Global navigation and contextual Home/Library/Chat/AI sidebars; hover preview when collapsed; recent items pinning | Capture expanded/collapsed/hover/pinned, keyboard and narrow widths |
| P0 | Hierarchy | Workspace, Space, Folder, Subfolder, List and task context | Tree selection, breadcrumbs, nesting, move, permissions and recovery |
| P0 | Views | Multiple views per location; views bar, pin, reorder, groups, search | Tab overflow, drag, keyboard, URL and persistence behavior |
| P0 | View settings | Filter, sort, group, search, autosave and protection | Private/shared state, reset, invalid filters, zero results, concurrency |
| P0 | Object inspector | Full-screen, modal and right-side opening; preferred mode persists | Focus, resize, scroll, navigation history, unsaved edits |
| P0 | Object relationships | Custom fields, comments/activity, dependencies and related objects | Add/remove/link, rollup, empty/error and permission cases |
| P1 | Library/hubs/create | Search/filter collections and global/contextual creation | Discoverability, templates, recent items, empty states |
| P1 | Docs/forms/whiteboard | Page views alongside task views; forms create tasks | Editor blocks, links, collaboration, canvas, undo, validation |
| P1 | Dashboard | Card-based composition | Data contract, chart encodings, drilldown, loading and zero data |
| P1 | Automation/AI | Triggers, conditions, actions, agents | Preview, consent, failure, retry, audit and safe cancellation |
| P1 | Mobile | Dedicated navigation and user-specific task layout | Touch alternatives, responsive states, accessibility |
| P1 | Visual/motion | Documentation describes controls; not runtime verified | Source-linked screenshots/video, version, rights, timing only when measured |

View candidates from official overview: List, Board, Calendar, Team, Gantt, Artifact, Activity, Timeline, Workload, Mind Map, Table, Map, Dashboard, Doc, Form, Whiteboard, Embed. Availability varies by plan/role. No invented usage metrics.

## Transfer hypotheses (not product decisions)

For a study workspace, explore shared object identity across list/board/table/calendar, separate collection views from open object tabs, a contextual inspector, and persistent per-view settings. Do not copy the entire ClickUp feature surface. Acceptance: same object ID across views; filters do not mutate source data; keyboard/touch can access hover actions; empty/error/loading/permission states are specified; inspect and verify task opening modes and focus restoration.

## Sources

- [ClickUp Help — Use the new ClickUp layout](https://help.clickup.com/hc/en-us/articles/45167704482583-Use-the-new-ClickUp-layout) — Global navigation, contextual sidebars, hover preview, recents, library and page navigation.
- [ClickUp Help — Intro to ClickUp 4.0](https://help.clickup.com/hc/en-us/articles/31142608907543-Intro-to-ClickUp-4-0) — Updated navigation and task layout; version boundary.
- [ClickUp Help — Hierarchy best practices](https://help.clickup.com/hc/en-us/articles/20480724378135-Hierarchy-best-practices) — Workspace hierarchy and view selection by work context.
- [ClickUp Help — Intro to views](https://help.clickup.com/hc/en-us/articles/6329880717719-Intro-to-views) — Task and page view inventory, including Artifact.
- [ClickUp Help — Use Page views](https://help.clickup.com/hc/en-us/articles/6310347914263-Use-Page-views) — Docs, dashboards, forms, whiteboards and embeds.
- [ClickUp Help — Views feature availability and limits](https://help.clickup.com/hc/en-us/articles/32274881672599-Views-feature-availability-and-limits) — Plan availability and feature boundaries.
- [ClickUp Help — Intro to the Views Bar](https://help.clickup.com/hc/en-us/articles/19063083658135-Intro-to-the-Views-Bar) — Reorder, pin, group, search and persist views.
- [ClickUp Help — The views control bar](https://help.clickup.com/hc/en-us/articles/35368731425175-The-views-control-bar) — Grouping, sorting, filtering and search.
- [ClickUp Help — Use Task views](https://help.clickup.com/hc/en-us/articles/6310172583831-Use-Task-views) — Multiple instances of views and autosave.
- [ClickUp Help — Protect a view](https://help.clickup.com/hc/en-us/articles/6310368663447-Protect-a-view) — Edit protection and permissions.
- [ClickUp Help — Task layouts](https://help.clickup.com/hc/en-us/articles/29665520762647-Task-layouts) — Full screen, modal and sidebar; preferred mode persists.
- [ClickUp Help — Tasks right sidebar](https://help.clickup.com/hc/en-us/articles/35041742373015-Tasks-right-sidebar) — Contextual panel, relationships, comments and integrations.
- [ClickUp Help — Custom Fields, subtasks, relationships, and attachments](https://help.clickup.com/hc/en-us/articles/34958820098839-Custom-Fields-subtasks-relationships-and-attachments) — Object detail sections and section navigation.
- [ClickUp Help — Relationships on tasks](https://help.clickup.com/hc/en-us/articles/29728065999383-Relationships-on-tasks) — Related objects, dependency links and dedicated relationship tabs.
- [ClickUp Help — Intro to tasks](https://help.clickup.com/hc/en-us/articles/10552031987735-Intro-to-tasks) — Object details, activity history and collaboration.
- [ClickUp Help — What are Hubs?](https://help.clickup.com/hc/en-us/articles/35206995778711-What-are-Hubs?) — Searchable and filterable hubs with collapsible sidebar.
- [ClickUp Help — Create items](https://help.clickup.com/hc/en-us/articles/6309854442391-Create-items) — Global and contextual creation.
- [ClickUp Help — Create a Dashboard](https://help.clickup.com/hc/en-us/articles/14237901038231-Create-a-Dashboard) — Dashboard card composition.
- [ClickUp Help — Intro to Forms and Form view](https://help.clickup.com/hc/en-us/articles/6310233090711-Intro-to-Forms-and-Form-view) — Input collection and task creation.
- [ClickUp Help — Intro to the mobile app](https://help.clickup.com/hc/en-us/articles/15145935126679-Intro-to-the-mobile-app) — Mobile feature scope.
- [ClickUp Help — Customize your task layout on mobile](https://help.clickup.com/hc/en-us/articles/22374093529751-Customize-your-task-layout-on-mobile) — Personal mobile task detail layout.
- [ClickUp Help — Use Automation Triggers](https://help.clickup.com/hc/en-us/articles/6312128853015-Use-Automation-Triggers) — Event-driven trigger examples.
- [ClickUp Help — Use Automation Actions](https://help.clickup.com/hc/en-us/articles/6312097314199-Use-Automation-Actions) — Actions, agents, permissions and webhooks.
- [ClickUp Help — Use Automation Conditions](https://help.clickup.com/hc/en-us/articles/6312136485527-Use-Automation-Conditions) — Conditional rules.

## Completion boundary

Documentation baseline only. No claim of complete ClickUp coverage, implementation fidelity or archived media. Next: enumerate each feature family from official docs, collect rights-permitted evidence by platform/version, validate live behaviors and cross-index semantic patterns. Do not reproduce proprietary screenshots without permission.
