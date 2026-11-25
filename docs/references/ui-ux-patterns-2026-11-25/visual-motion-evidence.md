# Visual and motion evidence — expanded research

[Structured evidence manifest](visual-motion-evidence.json) · [Original research](README.md)

## Capacities: object vs collection vs graph

The official Views reference distinguishes three levels of visualization. A single object has inline links, block links, small cards, wide cards, embeds and pages. Collections have list/table/gallery/wall/embed presentations; Kanban is also documented in related query and view material. Graphs show relationships rather than item properties. Do not equate these with navigation placement.

Visual observations from six successfully rendered official screenshots:
- [small-card](https://docs.capacities.io/_ipx/_/reference/media/views/small-card.jpg): Type badge, title and prominent image in a compact card.
- [wide-card](https://docs.capacities.io/_ipx/_/reference/media/views/wide-card.jpg): Horizontal arrangement of identity, description and media.
- [gallery](https://docs.capacities.io/_ipx/_/reference/media/views/gallery.jpeg): Equal-height media cards aligned in a grid with a view selector.
- [wall](https://docs.capacities.io/_ipx/_/reference/media/views/wall.jpeg): Variable-height image cards retaining differing aspect ratios.
- [explore](https://docs.capacities.io/_ipx/_/reference/media/navigation/explore.png): Object on left, contextual destinations in a compact tile grid and relevant content below.
- [side-panel-drop](https://capacities.io/_ipx/q_75/releases/release-60/drag-drop.jpeg): Graph and object side-by-side with bottom tab drop target.

Three linked assets could not be rendered: [inline-link](https://docs.capacities.io/_ipx/_/reference/media/views/in-line-view.jpg), [table](https://docs.capacities.io/_ipx/_/reference/media/views/table.png), [swap](https://capacities.io/_ipx/q_75/releases/release-60/swap.png). They remain unverified links. Images are not redistributed because a redistribution license was not established.

### Interaction inventory
- [object-rendering](https://docs.capacities.io/reference/views): Separate single-object representations (inline link, link block, small card, wide card, embed, page) from group views and graph.
- [navigation](https://docs.capacities.io/reference/navigation): Tab-local history and restoration of view filters/scroll, preview modal, up to three resizable side-panel stacks, drop-to-open, tab swap, pin, overflow and hover preview.
- [sections](https://docs.capacities.io/reference/sections): Sidebar pins and dashboard sections serve navigation, not object identity.
- [graph](https://docs.capacities.io/reference/graph-view): Explore connections from individual objects, collections and queries.
- [release-60](https://capacities.io/whats-new/release-60): Side panel redesign, stackable content and graph, swap action and object outline.
- [release-65](https://capacities.io/whats-new/release-65): Explore as default contextual tab.
- [release-66](https://capacities.io/whats-new/release-66): Drag tab to right edge and drop objects from views.
- [release-74](https://capacities.io/whats-new/release-74): Manual ordering and interactive embedded media on whiteboards.
- [getting-started](https://docs.capacities.io/tutorials/getting-started): Official tutorial with video reference.
- [editor](https://docs.capacities.io/tutorials/using-the-editor): Official editor tutorial with video reference.
- [study](https://docs.capacities.io/reference/use-cases/studying-with-capacities): Study-oriented dashboard and query examples.
- [presentation](https://docs.capacities.io/reference/presentation-mode): Presentation layout and toolbar behavior.

### Proposed validation for Exams App
Test opening the same object without duplicate tabs, tab-local history, restoration of filters and scrolling, editable preview with Escape and focus restoration, side-panel drag targets, stack resizing, swap behavior, pin/overflow, hover preview with keyboard alternative, and a touch layout without desktop-only gestures. Keep object data, view configuration, and panel placement separate. These are implementation proposals, not measured Capacities animation timings.

## Motion
- [shared-layout](https://motion.dev/examples/react-shared-layout-animation): Moving selection indicator across tabs; layoutId
- [layout](https://motion.dev/examples/react-layout-animation): Position/size transitions; layout
- [presence](https://motion.dev/examples/react-animate-presence-modes): Compare sync, wait, popLayout
- [gestures](https://motion.dev/examples/react-gestures): Hover and press feedback
- [reorder](https://motion.dev/docs/react-reorder): Reorder lists, tabs and grids; keyboard controls
- [sheet](https://motion.dev/examples/react-sheet-modal): Draggable sheet; source access may require Motion+
- [vue-reorder](https://motion.dev/examples/vue-reorder-items): Reordering with layout
- [vue-shared](https://motion.dev/examples/vue-shared-layout-animation): Shared selection indicator
- [vue-presence](https://motion.dev/examples/vue-animate-presence-modes): Enter/exit modes
- [catalog](https://motion.dev/examples): Full catalog: 542 patterns shown at research time; premium access applies

The public catalog showed 542 patterns at research time, including navigation, overlays, loading, layout animation, galleries, dialogs, lists, interactions, forms and carousels. This is a catalog reference, not a claim that all examples were downloaded or played. Motion+ source is not archived.

### Archived open source
The Motion repository is MIT-licensed. The following files were retrieved from the pinned commit `1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc`, preserving their source and license:
- [motion-source/LICENSE.md](motion-source/LICENSE.md) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/LICENSE.md))
- [motion-source/AnimatePresence-image-gallery.tsx](motion-source/AnimatePresence-image-gallery.tsx) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/dev/react/src/examples/AnimatePresence-image-gallery.tsx))
- [motion-source/AnimatePresence-notifications-list.tsx](motion-source/AnimatePresence-notifications-list.tsx) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/dev/react/src/examples/AnimatePresence-notifications-list.tsx))
- [motion-source/Drag-to-reorder.tsx](motion-source/Drag-to-reorder.tsx) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/dev/react/src/examples/Drag-to-reorder.tsx))
- [motion-source/Events-whileHover.tsx](motion-source/Events-whileHover.tsx) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/dev/react/src/examples/Events-whileHover.tsx))
- [motion-source/Events-whileTap.tsx](motion-source/Events-whileTap.tsx) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/dev/react/src/examples/Events-whileTap.tsx))
- [motion-source/Reorder-grid.tsx](motion-source/Reorder-grid.tsx) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/dev/react/src/examples/Reorder-grid.tsx))
- [motion-source/Shared-layout-lightbox.tsx](motion-source/Shared-layout-lightbox.tsx) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/dev/react/src/examples/Shared-layout-lightbox.tsx))
- [motion-source/Shared-layout-toggle-details.tsx](motion-source/Shared-layout-toggle-details.tsx) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/dev/react/src/examples/Shared-layout-toggle-details.tsx))
- [motion-source/Shared-layout-reparenting.tsx](motion-source/Shared-layout-reparenting.tsx) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/dev/react/src/examples/Shared-layout-reparenting.tsx))
- [motion-source/Animation-layout-size.tsx](motion-source/Animation-layout-size.tsx) ([upstream](https://github.com/motiondivision/motion/blob/1fa0e141f7b3f0a4eea258d5debc7dfbe5af6ffc/dev/react/src/examples/Animation-layout-size.tsx))

These are development examples and may depend on the upstream harness; they were not executed here. No claim that Capacities, Claude or ChatGPT use Motion internally.

## Remaining capture work
Record desktop and mobile interaction footage only with authorized access and appropriate redistribution rights. Track viewport, app version, interaction trigger, before/after states, actual duration/easing if measured, reduced motion, source URL, checksum, and capture date. Distinguish observed motion from proposals.
