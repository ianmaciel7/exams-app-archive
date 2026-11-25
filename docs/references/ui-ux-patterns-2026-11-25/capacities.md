# Capacities — object views and workspace

Official sources C1–C11 in [references](references.md).

## Object organization
- Object types define shared properties and type dashboards; the same objects may appear in multiple views.
- Collections manually group objects of one type. Queries select objects dynamically via rules. Tags and links offer other cross-context relationships.
- Dashboard sections may expose a collection or query. A view is not a duplicate of the underlying object.
- Views can appear in type dashboards, collections, queries, tags, embeds, backlinks and other contexts. Options vary by context.

| View | Selection purpose | Exams App proposal |
|---|---|---|
| List | Compact textual scan | Questions and exams |
| Table | Property comparison | Year, institution, discipline, status |
| Gallery | Image-oriented objects | Exam covers, flashcards |
| Wall | Varied visual material | Reference board |
| Kanban | Grouped workflow | Study status |
| Embed | Related content inside another object | Topic questions within study notes |

## Panels and navigation
Left navigation locates content; the main region displays open content; side-panel tabs support parallel work. Preview allows inspection without replacing the active page. Shift-click can open content in the side panel. Tabs share styling and history is scoped to the tab; official FAQ says an object can be open in only one main/side-panel tab at a time (C7). Avoid duplicate object tabs in the Exams App unless deliberately introducing multi-view instances.
Inspector is a distinct contextual surface, not equivalent to a full document side panel. Consult C3 for current inspector behavior. Bulk selection can open multiple objects in side-panel tabs (C11).
Phone uses bottom navigation (C8); tablet retains a desktop-like layout without the right side panel (C9). Do not simply squeeze three desktop columns into a phone.

## Implementation proposals
Separate view configuration (layout, visible fields, sort/group, density) from query definition and tab state. Persist active object and view separately; provide explicit open-in-side-panel and preview actions. Use stable IDs and preserve keyboard focus during navigation. Validate desktop, tablet and phone, including touch controls and empty/overflow states.
