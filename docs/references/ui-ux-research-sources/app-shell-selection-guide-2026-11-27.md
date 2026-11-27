# App Shell selection guide and taxonomy audit — 2026-11-27

Companion to [taxonomy gap review](app-shell-taxonomy-2026-11-27.md). Original applied synthesis of public documentation/search excerpts, not a universal taxonomy, normative thresholds, product decision or tested effectiveness. The prior 48 labels mix geometry, navigation, relationships, behaviors and domain compositions. Select orthogonal axes, not a single winner across unlike alternatives.

## Decision method

1. Identify tasks, destinations, object relationships, frequency of switching, simultaneous context, independent documents, input modality, available window width and user expertise. Tree-test the information architecture independently of chrome.
2. Choose navigation topology (flat, hierarchical, hub, global/local, task flow) then placement (top, side, rail, bottom, drawer) and disclosure. Keep frequent destinations visible; use drawer for constraints, not just aesthetics.
3. Choose pane semantics: single focused task; list/detail if selection controls details; hierarchical third pane for child content; supporting pane for auxiliary information; peer split for comparison; tabs for switching independent objects; docking/windows only when workflows need rearrangement.
4. Choose chrome ownership (header-first/sidebar-first), scroll boundaries, reflow order, focus/resize/close, width budget and state ownership. Define minimum usable pane widths using representative content, zoom and localization rather than arbitrary universal breakpoints.
5. Add domain composition and only justified behavior. Prototype 2 plausible alternatives if evidence is uncertain; compare task completion, time, navigation errors, context switches, state loss, perceived effort and accessibility. Do not assign fabricated scores or thresholds.

## Selection matrix (48 previous labels)

| Label | Prefer when | Avoid / alternative when |
|---|---|---|
| Single Column | isolated task | frequent module switching |
| Top Navigation | few stable top-level destinations | broad/deep IA; sidebar |
| Sidebar | broad/growing IA and frequent navigation | simple isolated task |
| Right Sidebar | auxiliary actions or properties | confusing contextual tools with primary navigation |
| Three-Pane | primary nav, work and contextual information concurrently needed | central region too narrow |
| Navigation Rail | few recognizable destinations, width constrained | unfamiliar icons or deep hierarchy |
| Dual Sidebar | global/local navigation genuinely independent | duplicate nav; one sidebar suffices |
| Hybrid Navigation | complex global/local scopes | redundant menus |
| Tabbed Workspace | switch independently opened documents/objects | sequential task or section tabs suffice |
| Bottom Navigation | frequently accessed mobile destinations | too many destinations or desktop-only |
| Split View | concurrent comparison or complementary work | rarely simultaneous; tabs suffice |
| Multi-Pane Workspace | expert work needs several visible regions | occasional simple tasks |
| Dashboard | monitoring and decisions | primary task is editing |
| Master–Detail | collection selection drives detail | parallel documents or unrelated tool panel |
| IDE | code/edit/run/debug | lightweight single task |
| Document Editor | authoring and formatting | simple read-only consumption |
| Canvas | spatial authoring and relationships | ordinary list/form task |
| Node-Based Editor | graph workflow or dependency manipulation | simple sequential flow |
| Object-Based Workspace | typed linked objects, collections and properties | isolated linear task |
| Chat | conversation is primary task | stable visual/direct manipulation dominates |
| Chat + Artifact | iterative creation beside conversation | no durable output |
| AI Copilot | embedded assistance to existing workflow | AI not needed; avoid permanent chrome |
| AI Studio | experiment with model inputs/config/results | ordinary consumer workflow |
| Agent Control Center | supervise concurrent agents and approvals | simple single request |
| Media Editor | timelines, tracks, previews | text-only task |
| Reader | uninterrupted reading and optional annotation | content editing dominates |
| Search-First | retrieval/discovery is primary | users know stable destinations |
| Wizard / Stepper | dependent sequential steps | non-linear independent tasks |
| Focus / Immersive | concentrate on a task | frequent navigation or critical status obscured |
| Adaptive / Generative | context/viewport materially changes needs | inconsistent layout harms predictability |
| Holy Grail | header/footer and bilateral support regions justified | unnecessary sidebars |
| Header-First | global header owns full width | sidebar owns root hierarchy |
| Sidebar-First | persistent navigation dominates layout | suite-global header dominates |
| Horizontal Split | stacked editor/output or timeline | side-by-side comparison needed |
| Mixed Split | both axes justified | simpler split sufficient |
| List–Detail–Detail | parent collection → child list → details | inspector is complementary, not hierarchy |
| Supporting Pane | task-related auxiliary content | unrelated tools or critical primary content |
| Feed | ongoing content exploration | known item retrieval, structured workflow |
| Flexible Column | adaptive hierarchy/depth and variable space | fixed independent peer panes |
| Constrained Content | readability, comfortable form measure | wide tables/diagram workspace |
| Drawer-First | compact viewport, less frequent destinations | desktop discoverability, essential frequent nav |
| Workbench | specialized editors and tools | simple workflow |
| Dockable Workspace | users repeatedly customize pane layout | complexity and drag accessibility not justified |
| Multi-Window | simultaneous windows/monitors | one workspace suffices |
| Console Workspace | related work records, tabs/subtabs/utilities | simple independent pages |
| Hub-and-Spoke | central orientation, independent tasks | rapid lateral switching |
| Hierarchical Drill-Down | parent-child navigation | flat independent destinations |
| Suite Navigation | multiple products, global/local scope | single product and no distinct scope |

## Additional dimensions / gap candidates

- Single Document Interface (SDI), Multiple Document Interface (MDI) and Tabbed Document Interface (TDI) describe document/window management, not geometry. SDI: one document per top-level window; MDI: internal child document windows; TDI: open document tabs. Prefer MDI only when overlapping internal document windows serve a proven expert task; distinguish from multi-window and split.
- Ribbon/command-centric composition: persistent categorized command tabs and tool groups for many document operations; avoid for few commands or mobile. Command tabs differ from page/document tabs.
- Map + List/Map + Detail: synchronized spatial view and list/details for location-driven discovery. Domain recipe, not independent geometric shell. Keyboard, text alternative and selection synchronization.
- Resource Detail Hub: overview, related resources and actions on a dedicated resource page; choose when complete details/actions exceed contextual preview. Content template and hub subtype, not an independent shell.
- Shell region role vs placement: global nav, local nav, document tabs, primary task, supporting context, tool/inspector, action bar, utility/status bar. Right placement does not imply inspector or global utility. Leading/trailing support RTL.
- Responsive transition policy is an explicit decision: compact uses one primary pane, navigation drawer/bar if appropriate; expanded rail/sidebar + secondary pane as task requires. Preserve route, selected object, unsaved work, focus, scroll, browser back and consistent destination identity. Do not dictate a single global breakpoint.
- Distinguish route shell from content layout: dashboard cards, kanban, timeline, feed, table, graph and map are often views within a stable shell. Distinguish modal workflow from persistent navigation. Document role, ownership, close behavior, independent scroll and keyboard landmarks.

## Acceptance and choice record
Record problem/task, IA, users, platform/window width, navigation frequency, simultaneous context, candidate axes, alternatives rejected, trade-offs, accessibility/RTL, long labels/zoom, responsive transitions, persistence, representative tasks and measured results. Test keyboard, visible focus, accessible names, reflow, back, selection, unsaved changes, resize minimums, mobile drawer close/return, dock/popout recovery and no duplicate destinations. Score optional alternatives only with explicit criteria and weights supplied by product stakeholders; veto a candidate that fails critical task/accessibility constraints.

## Source references and scope
- https://learn.microsoft.com/windows/apps/design/basics/navigation-basics — navigation topology and tabs.
- https://developer.android.com/develop/adaptive-apps/guides/canonical-layouts — list-detail, feed, supporting pane.
- https://developer.android.com/develop/adaptive-apps/guides/build-adaptive-navigation — adaptive bottom bar/rail.
- https://developer.android.com/develop/adaptive-apps/guides/adaptive-dos-and-donts — window adaptation, pane arrangement and inputs.
- https://developer.apple.com/design/human-interface-guidelines/split-views — hierarchical panes and resizing.
- https://developer.apple.com/design/human-interface-guidelines/sidebars — sidebar vs tab bar and hierarchy.
- https://developer.apple.com/design/human-interface-guidelines/tab-bars — predictable primary destinations.
- https://www.carbondesignsystem.com/building-blocks/core/patterns/global-header — global/local navigation roles and responsive behavior.
- https://www.carbondesignsystem.com/building-blocks/core/components/ui-shell-header/guidelines — header/panel shell.
- https://cloudscape.design/patterns/general/secondary-panels/ — secondary panel relevance and split detail.
- https://cloudscape.design/patterns/resource-management/details/ — dedicated resource details and hub.
- https://www.nngroup.com/articles/vertical-nav/ — vertical navigation for broad IA, space trade-off.
- https://www.nngroup.com/articles/hamburger-menu-icon-recognizability/ — hidden navigation interaction cost.
- https://www.nngroup.com/articles/ia-study-guide/ — IA and tree testing.
- https://atlassian.design/components/navigation-system/layout/usage — layout regions.
- https://atlassian.design/components/panel/usage — contextual dismissible panels.
- https://learn.microsoft.com/en-us/office/vba/excel/concepts/programming-for-the-single-document-interface-in-excel — SDI/MDI distinction.
- https://learn.microsoft.com/en-us/windows/win32/windowsribbon/windowsribbon-controls-entry — ribbon command groups.
- https://developers.google.com/maps/documentation/javascript/examples/place-search-pagination — map/list example.
- https://developer.mozilla.org/en-US/docs/Web/CSS/How_to/Layout_cookbook — CSS recipes are not shell taxonomy.
Evidence: search excerpts and existing archive research; no runtime UI inspection, participant tests, screenshot reproduction or verified universal thresholds. Additional candidates are categorized, not all independent shell families. No active app changes.
