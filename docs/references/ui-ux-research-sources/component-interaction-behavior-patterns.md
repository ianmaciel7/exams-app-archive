# Component Interaction & Behavior Patterns

Review: 2026-11-25. 29 indexed patterns, including cross-references to existing knowledge. No product-specific changes.

## Interpretation and evidence

- Component Interaction & Behavior Patterns is a proposed internal catalog name; established umbrella is Interaction Design Patterns / Application Design Patterns / HCI Design Patterns.
- Workspace Customization, Navigation Interaction Patterns, Direct Manipulation, Alternative Views, Saved Views and Display Options are useful research terms. Alternative Views is historical; the 2026 date is review date, not invention date.
- A component is a UI structure; a pattern solves a recurring interaction problem; a capability is a specific behavior. Do not mandate all capabilities on every component. Separate UI presentation, domain data, permissions, and personal/shared view configuration.
- Capacities sections are shortcuts, not necessarily folders; moving a ChatGPT chat into a project may change project context. Antigravity documented conversation commands do not establish identical web-sidebar affordances; Claude features vary with rollout. No authenticated DOM inspection or icon-library identification.
- WCAG 2.2 SC 2.5.7 requires a non-drag single-pointer alternative where applicable, with stated exceptions; keyboard accessibility is separate. Do not rely on hover or drag alone. Validate focus, touch, status announcements, error recovery, and permissions.
- The component matrix is a discovery checklist, not independently researched prescriptions for every component. Cross-index existing patterns instead of treating all entries as net-new. Prior links not revalidated are labeled.

## Pattern catalog

### navigation

- **Persistent Sidebar Navigation** (`persistent-sidebar`; Sidebar navigation; navigation rail): Keep primary destinations reachable while working; collapse when space is scarce. **Acceptance:** Navigate without losing work; test compact/mobile presentation. Sources: component-sidebar, component-capacities-ui.
- **Collapsible Sections** (`collapsible-sections`; Disclosure; expandable groups): Expand or collapse secondary groups; preserve essential paths and expose expanded state. **Acceptance:** Keyboard/touch toggle, meaningful accessible name and state; reopening restores group. Sources: component-sidebar, component-notion-sidebar.
- **Pinned Items** (`pinned-items`; Pin/unpin; quick access): Keep selected references prominent independently of recency; pinning is not moving the underlying object. **Acceptance:** Pin and unpin without duplication or deletion; reload preserves intended preference. Sources: component-capacities, component-linear-mobile, component-antigravity-search.
- **Favorites** (`favorites`; Starred items; bookmarks): Provide user-controlled quick access to frequently used objects; distinguish favorite from pin if both exist. **Acceptance:** Toggle favorite from accessible control; reflect same status in other views. Sources: component-favorites, component-linear-favorites, component-claude-projects.
- **Custom Sections** (`custom-sections`; User-defined groups; sidebar sections): Let people create, rename, order and remove navigation groups where workflows differ. **Acceptance:** Create section, move links, remove section with clear consequences; do not delete underlying objects inadvertently. Sources: component-capacities, component-slack, component-linear-sidebar.
- **Nested Navigation** (`nested-navigation`; Tree navigation; favorite folders): Use hierarchy for real parent-child organization or explicitly labeled shortcut grouping. **Acceptance:** Expand/collapse with keyboard and touch; avoid cycles and unbounded depth. Sources: component-sidebar, component-notion-sidebar, component-linear-favorites.
- **Workspace Switcher** (`workspace-switcher`; Space switcher; context selector): Switch workspace scope with visible active context; preserve authorized state per workspace. **Acceptance:** Switch A/B; check no stale or unauthorized content; restore prior view where supported. Sources: component-capacities-ui, component-notion-sidebar.
- **Recently Visited Items** (`recent-items`; Recents; history): Offer recent destinations as dynamic shortcuts without implying stable pin order. **Acceptance:** Recent items reflect visits and permissions; provide clear empty state. Sources: component-notion-sidebar.
- **Navigation Personalization** (`navigation-personalization`; Customizable sidebar; hide/show destinations): Permit reordering or hiding secondary destinations; preserve a recoverable default. **Acceptance:** Hide and restore navigation; refresh and verify preference scope. Sources: component-linear-sidebar, component-linear-mobile.
- **Navigation Badges** (`navigation-badges`; Unread dot; counters): Use meaningful counts or status markers, not ornamental noise. **Acceptance:** Status is readable without color alone and reflects actual count semantics. Sources: component-linear-sidebar.
- **Overflow Navigation** (`overflow-navigation`; More menu; secondary destinations): Keep frequent actions discoverable and group less-used actions in a labeled overflow. **Acceptance:** Keyboard/touch can access hidden items; active destination remains apparent. Sources: component-sidebar, component-linear-sidebar.
- **Resizable / Collapsible Sidebar and Sidebar Peek** (`sidebar-sizing-peek`; Panel resize; temporary reveal): Offer size adjustment or temporary reveal when useful; separate peek from persistent open state. **Acceptance:** Test min/max size, keyboard/touch alternative, focus, and no inadvertent overlay. Sources: component-sidebar.

### manipulation

- **Drag-and-Drop Reordering** (`drag-reorder`; Sortable items; manual ordering): Reorder within a collection; make target, drag state, insertion and result clear. **Acceptance:** Drag and non-drag pointer alternative; keyboard reorder; persist order and handle failures. Sources: component-drag, component-linear-reorder, component-wcag-drag.
- **Move Between Groups** (`cross-section-move`; Cross-section drag/drop; Move to menu): Move reference or underlying object with clear destination and consequences; distinguish copy, move, pin and grouping. **Acceptance:** Move via menu or drag; validate permissions and consequences; preserve identity. Sources: component-chatgpt-projects, component-claude-projects, component-slack, component-wcag-drag.
- **Inline Creation** (`inline-creation`; Quick create; section-level create): Create in current context without unnecessary navigation; make default destination visible. **Acceptance:** Create in correct group; allow cancel; invalid data remains recoverable. Sources: component-notion-sidebar.
- **Inline Renaming** (`inline-rename`; In-place edit; quick rename): Edit simple name near object; explicit save/cancel semantics. **Acceptance:** Rename via keyboard/touch, cancel restores old title, error retains edit. Sources: component-antigravity-changelog.
- **Contextual Tools** (`contextual-tools`; Hover-reveal actions; focus-reveal; context menu): Keep secondary commands close to object; visible essential actions and accessible alternative to hover/right-click. **Acceptance:** Focus and touch reveal same relevant actions; no accidental selection or focus loss. Sources: component-sidebar, component-slack, component-antigravity-search.
- **Multi-selection and Bulk Actions** (`multi-selection-bulk`; Batch selection; batch toolbar): Select multiple items with clear selection scope and applicable actions. **Acceptance:** Count selected, select/clear range, bulk failure reports partial outcomes; keyboard and touch supported. Sources: component-drag.
- **Direct Manipulation** (`direct-manipulation`; Move; resize; reorder): Manipulate visible objects with immediate feedback and reversible edits where practical. **Acceptance:** Input targets and feedback remain clear; cancel drag; offer pointer and keyboard alternatives. Sources: component-drag, component-wcag-drag.

### views

- **Alternative Views** (`alternative-views`; View Switching; View Toggle; Multiple Views): Present same underlying objects in task-appropriate list, table, card/grid, board, calendar or timeline views; view toggle changes presentation, not object identity. **Acceptance:** Switch layouts, preserve shared filters/selection where meaningful; clarify per-view settings and no data duplication. Sources: component-tidwell-preview, component-linear-display, component-notion-views.
- **Saved Views** (`saved-views`; Custom Views; named views; saved search): Persist a named query/layout configuration independent of underlying data; define personal/shared scope. **Acceptance:** Save, rename and reopen a filtered view; permissions and changes remain explicit. Sources: component-linear-views, component-notion-views.
- **Sorting, Filtering and Grouping** (`sorting-filtering-grouping`; Sort; faceted filter; group by): Allow task-relevant query refinement; visible active criteria, reset and clear results. **Acceptance:** Combine filters, change sort/group, clear; distinguish zero matches from loading/error. Sources: component-linear-display, component-notion-views.
- **Display Options** (`display-options`; Property visibility; density; field selection): Configure visible fields and layout density as appropriate without changing data or access. **Acceptance:** Hide/show field, restore defaults; personal/shared scope and accessibility preserved. Sources: component-linear-display, component-notion-views.
- **Swimlanes and Sub-grouping** (`swimlanes`; Board lanes; nested grouping): Use a second grouping dimension only when it improves understanding of work. **Acceptance:** Group and regroup same records; keep accessible navigation across lanes and avoid lost items. Sources: component-linear-board, component-linear-reorder.
- **Persistent View State** (`persistent-view-state`; Remember layout; personal preferences): Persist chosen layout, sorting, grouping and filters at the intended user/view scope. **Acceptance:** Reload, return from detail and switch devices if supported; do not overwrite shared defaults silently. Sources: component-linear-display, component-linear-views, component-notion-views.
- **Customizable Dashboard Layout** (`dashboard-composition`; Widget arrangement; multi-view composition): Arrange different views of shared data for a task; widgets retain permissions and meaningful filters. **Acceptance:** Change layout and inspect each widget; view configuration does not bypass underlying access. Sources: component-notion-dashboard.

### iconography

- **Semantic Iconography** (`semantic-iconography`; Familiar symbols; icon-and-label navigation): Use consistent understandable symbols for actions and destinations; label ambiguous icons. **Acceptance:** Compare icon stroke, size and meaning; accessible names and visible text for ambiguous actions. Sources: component-apple-icons, component-nng-consistency.
- **Monochromatic Outline Iconography** (`outline-iconography`; Outline icons; low-chrome UI): Use restrained coherent visual language where it improves clarity; outline style is a choice, not standard. **Acceptance:** Contrast and active state clear; no inference of specific icon library from appearance. Sources: component-apple-icons.
- **Consistency and Standards** (`consistent-navigation`; Jakob's Law; familiar conventions): Reuse learned conventions unless evidence justifies a departure; consistency is not identical visuals. **Acceptance:** Same action has same meaning, labels, and behavior; validate unfamiliar symbols with users. Sources: component-nng-consistency, component-nng-heuristics.

## Component capability discovery matrix

| Component | Candidate behaviors |
|---|---|
| Lists | Alternative Views; sorting/filtering/grouping; multi-selection; bulk actions |
| Tables | Column resizing/reordering; inline edit; frozen columns; sorting/filtering; selection |
| Sidebars | Pin/favorite; sections; move/reorder; contextual tools; peek; width |
| Cards | Quick actions; expandable details; move/reorder |
| Tabs | Pin; reorder; duplicate; split view; state preservation |
| Dashboards | Widget layout; resize/reorder; drill-down; multi-view |
| Editors | Autosave; undo/redo; version history; inline formatting |
| Search | Autocomplete; recent/saved searches; scope |
| Calendars | Alternative Views; move/resize events |
| Forms | Inline validation; conditional fields; draft persistence |

## Sources

- [UX Patterns — Sidebar](https://uxpatterns.dev/patterns/navigation/sidebar) — `component-sidebar`; pattern-library; Public search-index evidence; revalidate scope before reuse.
- [UI Patterns — Favorites](https://ui-patterns.com/patterns/favorites) — `component-favorites`; pattern-library; Public search-index evidence; revalidate scope before reuse.
- [UI Patterns — Drag and drop](https://ui-patterns.com/patterns/drag-and-drop) — `component-drag`; pattern-library; Public search-index evidence; revalidate scope before reuse.
- [Linear — Favorites](https://linear.app/docs/favorites) — `component-linear-favorites`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Linear — Personalized sidebar](https://linear.app/changelog/2024-12-18-personalized-sidebar) — `component-linear-sidebar`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Linear — Customize mobile navigation (2026-01-22)](https://linear.app/changelog/2026-01-22-customize-your-navigation-in-linear-mobile) — `component-linear-mobile`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Capacities — Sections](https://docs.capacities.io/reference/sections) — `component-capacities`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Capacities — User interface](https://docs.capacities.io/reference/user-interface) — `component-capacities-ui`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Notion — Navigate with sidebar](https://www.notion.com/help/navigate-with-the-sidebar) — `component-notion-sidebar`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Slack — Custom sections](https://slack.com/help/articles/360043207674) — `component-slack`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Linear — Display options](https://linear.app/docs/display-options) — `component-linear-display`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Linear — Board layout](https://linear.app/docs/board-layout) — `component-linear-board`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Linear — Custom views](https://linear.app/docs/custom-views) — `component-linear-views`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Linear — Group reordering (2026-05-21)](https://linear.app/changelog/2026-05-21-project-slack-channels) — `component-linear-reorder`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Notion — Database views, filters, sorts and groups](https://www.notion.com/help/views-filters-and-sorts) — `component-notion-views`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Notion — Dashboards](https://www.notion.com/help/dashboards) — `component-notion-dashboard`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [ChatGPT — Projects](https://help.openai.com/en/articles/10169521-projects-in-chatgpt) — `component-chatgpt-projects`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Claude — Create and manage projects](https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects) — `component-claude-projects`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Antigravity — Search and command palette](https://antigravity.google/docs/search) — `component-antigravity-search`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [Antigravity — Changelog, conversation management](https://antigravity.google/docs/changelog?tab=hub&version=2.29.0) — `component-antigravity-changelog`; primary-product; Public search-index evidence; revalidate scope before reuse.
- [W3C — Understanding SC 2.5.7 Dragging Movements](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements) — `component-wcag-drag`; accessibility-standard-guidance; Public search-index evidence; revalidate scope before reuse.
- [Apple HIG — Icons](https://developer.apple.com/design/human-interface-guidelines/icons) — `component-apple-icons`; primary-platform; Public search-index evidence; revalidate scope before reuse.
- [NN/g — Consistency and Standards](https://www.nngroup.com/articles/consistency-and-standards/) — `component-nng-consistency`; usability-guidance; Public search-index evidence; revalidate scope before reuse.
- [NN/g — Ten Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) — `component-nng-heuristics`; usability-guidance; Public search-index evidence; revalidate scope before reuse.
- [Designing Interfaces, 3rd edition](https://www.oreilly.com/library/view/designing-interfaces-3rd/9781492051954/) — `tidwell-book`; book-reference; search-index evidence; full page not audited.
- [Designing Interfaces — historical Alternative Views entry (publisher preview)](https://api.pageplace.de/preview/DT0400.9780596519087_A23629407/preview-9780596519087_A23629407.pdf) — `component-tidwell-preview`; book-preview; Historical book preview, search-index only; full text not inspected.
- [Lucide](https://lucide.dev/) — `component-lucide`; icon-library; Prior conversation; not independently re-fetched in this consolidation.
- [Phosphor Icons](https://phosphoricons.com/) — `component-phosphor`; icon-library; Prior conversation; not independently re-fetched in this consolidation.
- [Tabler Icons](https://tabler.io/icons) — `component-tabler`; icon-library; Prior conversation; not independently re-fetched in this consolidation.
- [Heroicons](https://heroicons.com/) — `component-heroicons`; icon-library; Prior conversation; not independently re-fetched in this consolidation.
- [Apple — SF Symbols](https://developer.apple.com/sf-symbols/) — `component-sf-symbols`; icon-library; Prior conversation; not independently re-fetched in this consolidation.
- [Setproduct — Sidebar navigation UI design](https://www.setproduct.com/blog/sidebar-navigation-ui-design) — `component-setproduct`; editorial; Prior conversation; not independently re-fetched in this consolidation.
- [Uxcel — Navigation architecture](https://uxcel.com/lessons/navigation-architecture-159) — `component-uxcel`; education; Prior conversation; not independently re-fetched in this consolidation.
- [SaaSUI — Sidebar UX patterns](https://www.saasui.design/blog/saas-sidebar-navigation-ux-patterns) — `component-saasui`; editorial; Prior conversation; not independently re-fetched in this consolidation.
- [The UI Index — Patterns](https://theuiindex.com/patterns) — `component-uiindex`; pattern-library; Prior conversation; not independently re-fetched in this consolidation.

Related: [Behavioral UX quality](behavioral-ux-quality-2026.md), [Async and non-blocking UX](asynchronous-non-blocking-ux.md), [general interface pattern library](../interface-pattern-library/README.md).
