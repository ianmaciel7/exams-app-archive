# App shell taxonomy — gap review
Research date: 2026-11-27. Original synthesis from public documentation and search excerpts; not a normative or exhaustive industry taxonomy. No third-party media copied, live UI inspection, runtime tests or private evidence. Related: [interface patterns](../interface-pattern-library/catalog.md), [AI-native layouts](ai-native-product-design.md), [historical component catalog](../../UI-COMPONENT-CATALOG.md).

## Classification axes
- Geometry: single region; stacked/top navigation; sidebar; trailing sidebar; navigation rail; rail + local sidebar; three-pane; hybrid; bottom navigation; header-first/sidebar-first; header + footer + bilateral sidebars (Holy Grail); vertical, horizontal and mixed split; full-bleed or width-constrained content.
- Navigation structure: flat tabs, hierarchical drill-down/stack, hub-and-spoke, global suite/product switcher + local navigation, nested tabs/subtabs, drawer-first. Do not conflate navigation topology with chrome.
- Pane relationship: list-detail (master-detail alias), list-detail-detail, primary content + supporting pane, equal/parallel comparison, adaptive flexible columns, feed. Same geometry can have distinct semantics.
- Workspace management: tabbed workspace, multi-pane workbench/IDE (including bottom panel and status bar), dockable/tiling, multi-window/popout, console with workspace tabs/subtabs and utility bar.
- Domain compositions: dashboard, object-based workspace, document editor, canvas, node editor, media editor, reader, chat, chat + artifact, copilot, AI studio, agent control center, search-first, wizard, focus/immersive, adaptive/generative. Domain labels are combinations, not unique geometry.
- Behavior: collapse, resize, peek, overlay/drawer, pin, auto-hide, floating, dock/undock, focus/fullscreen, responsive reflow and state persistence. Fixed/sticky are positioning strategies. PWA app shell caching is a technical architecture, not a visual type.

## Gap records
| ID | Label | Kind | Evidence |
|---|---|---|---|
| shell.holy-grail | Holy Grail | geometric composition | S1 |
| shell.header-first | Header-first | chrome ownership subtype | S2 |
| shell.sidebar-first | Sidebar-first | chrome ownership subtype | S2 |
| shell.horizontal-split | Horizontal split | orientation subtype | S3,S4 |
| shell.mixed-split | Mixed split | multi-pane subtype | S3,S4 |
| shell.list-detail-detail | List-detail-detail | hierarchical relation | S5,S6 |
| shell.supporting-pane | Supporting pane | complementary relation | S7,S8 |
| shell.feed | Feed | content composition | S7 |
| shell.flexible-column | Flexible column | adaptive multi-pane subtype | S5 |
| shell.constrained-width | Constrained content | sizing modifier | S9 |
| shell.drawer-first | Drawer-first | navigation composition | S10 |
| shell.workbench | Workbench | IDE-like domain composition | S3 |
| shell.dockable | Dockable/tiling workspace | workspace arrangement | S4 |
| shell.multi-window | Multi-window/popout | window management | S4,S11 |
| shell.console | Console workspace | nested tabs + utilities | S12 |
| shell.hub-spoke | Hub-and-spoke | navigation topology | S13 |
| shell.drill-down | Hierarchical drill-down | navigation topology | S6,S13 |
| shell.suite | Suite navigation | global/local navigation scope | S14 |

## Selection / QA
Prefer describing a shell as a composition of orthogonal axes instead of counting every combination as a new independent type. Check persistent destinations, focus/keyboard, resize and minimum widths, independent vs shared scroll, small-screen collapse order and back behavior, accessible pane controls, preservation of unsaved work/tab/selection state, and no duplicate navigation. Dock/popout needs explicit ownership, close/restore and focus tests. Distinguish content list/detail navigation from contextual inspector. For an object-oriented workspace, consider an optional inspector and a list-detail view only where justified; not a product decision.

## Public sources (reviewed search excerpts, not runtime validation)
- S1: https://ui.wei-dev.com/docs/patterns/layouts — community layout catalog.
- S2: https://design.tinyrack.net/en/web/components/app-shell/ — design system component variants.
- S3: https://code.visualstudio.com/docs/editing/getting-started/userinterface — official workbench regions and editor groups.
- S4: https://golden-layout.github.io/golden-layout/structure/ and https://golden-layout.github.io/golden-layout/ — layout manager structure and popouts.
- S5: https://www.sap.com/design-system/fiori-design-web/v1-154/page-types/page-layouts/flexible-column-layout — official flexible column.
- S6: https://developer.apple.com/design/human-interface-guidelines/split-views — official hierarchical split panes.
- S7: https://developer.android.com/develop/adaptive-apps/guides/canonical-layouts — official list-detail, feed, supporting pane.
- S8: https://cloudscape.design/patterns/general/secondary-panels/ — contextual secondary panel relationships.
- S9: https://tailwindcss.com/docs/responsive-design — width adaptation, not a named shell standard.
- S10: https://developer.android.com/design/ui/mobile/guides/layout-and-content/layout-and-nav-patterns — navigation pairings and drawer.
- S11: https://developer.apple.com/design/human-interface-guidelines/windows — window management.
- S12: https://developer.salesforce.com/docs/service/api-console/guide/sforce-api-console-js-lex-intro.html — console workspace tabs and subtabs.
- S13: https://learn.microsoft.com/windows/apps/design/basics/navigation-basics — flat and hierarchical topology; https://learn.microsoft.com/en-us/archive/msdn-magazine/2013/august/modern-apps-navigation-essentials-in-windows-store-apps — historical hub navigation.
- S14: https://dx.dev.rockymountaineer.com/docs/patterns/app-shell-navigation — suite rail and local nav example.
- Additional: https://tailwindcss.com/plus/ui-blocks/application-ui — stacked/sidebar/multi-column catalog; https://cloudscape.design/components/app-layout/ — collapsible nav and tools; https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Tutorials/js13kGames/App_structure — technical shell distinction.

Limit: only a gap review; no claim all labels are official names or that all combinations have equal evidence. Historical files unchanged. Structured index/plugin release requires separate review and validation.

## Selection guide and additional dimensions — 2026-11-27

See [App Shell selection guide](app-shell-selection-guide-2026-11-27.md) for decision criteria for all 48 prior labels, trade-offs, SDI/MDI/TDI, ribbon commands, map/list, resource detail hubs, region responsibilities, responsive transition and acceptance tests. This is documentary synthesis, not a product decision or an exhaustive standard.
