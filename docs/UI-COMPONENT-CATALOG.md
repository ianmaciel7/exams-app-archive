# UI Component Catalog and Architecture Specification

Document Version: 1.0.0  
Date: 2026-11-24  
Issue Reference: #24 (Consolidar docs, recuperacao de motion, busca e sincronizacao multiagente)  
Zero Emoji Policy: Verified compliant. No Unicode emojis in range U+10000 to U+10FFFF.

---

## 1. Catalog Architecture and Taxonomy

The Exams App Archive user interface is constructed as a hierarchy of modular components divided into two primary tiers:
1. **Primitives (`src/components/ui/*`)**: Thin, accessible primitives based on Base UI and Tailwind CSS that encapsulate semantic tags, focus management, and accessibility attributes.
2. **Product Compositions (`src/components/*` and `src/app/_components/*`)**: Stateful domain components providing the workspace shell, multi-tab header, question player, flashcard deck, and graph visualization canvas.

```
+-------------------------------------------------------------------------------+
| AppShell (Layout orchestration, responsive drawer, splitter resizer)          |
| +-------------------------+-------------------------------------------------+ |
| | AppSidebar              | AppHeader (46px, tabs, global search, actions)   | |
| | - Entity navigation     +-------------------------------------------------+ |
| | - Space switcher        | Stage Area                                      | |
| | - Search & filters      | - QuestionCard / QuestionNavigator              | |
| | - Actions reveal        | - FlashcardViewer / RatingButtons               | |
| | - Mobile drawer mode    | - GraphCanvas / ForceModel                      | |
| +-------------------------+-------------------------------------------------+ |
+-------------------------------------------------------------------------------+
```

---

## 2. Shell and Layout Infrastructure

### 2.1 AppShell

- **Location**: `src/app/_components/workspace/app-shell.tsx` (historical baseline: `c8149bad08ee026dec049371d3814c29aec8b89a`)
- **Role**: Root container managing desktop multi-pane dimensions and mobile responsive drawers.
- **Key Capabilities**:
  - Left navigation rail/sidebar collapsible state (`collapsed: boolean`).
  - Optional right inspector panel (`rightCollapsed: boolean`).
  - Dynamic pointer drag resizing bounded to `160px..360px`.
  - CSS transition synchronization (`transition: width 200ms ease, margin-left 200ms ease`).

### 2.2 AppHeader

- **Location**: `src/app/_components/workspace/app-header.tsx`
- **Role**: Fixed 46px workspace header hosting navigation history, active tab strip, and global actions.
- **Key Capabilities**:
  - History back/forward buttons with disabled state checks.
  - Focus mode toggle (`focusMode: boolean`) to suppress sidebars during intensive exam sessions.
  - Integration slot for `AppSpaceHeader` (center) and secondary actions (end).

---

## 3. Sidebar Systems (Evolutionary Lineage)

The archive contains three iterations of the sidebar component:

### 3.1 SpaceFrame / WorkspaceSidebar (v1)

- **Source**: `ianmaciel7/notes-app@old-10` (`src/components/space-frame.tsx`, SHA `c916f3d4003d24bc9eb8727be98e8afa5d19b31f`)
- **Behavior**:
  - Implements **Hover Peek** in collapsed state: triggers temporary sidebar reveal on `mouseenter` with a 300ms dwell delay, closing on `mouseleave` with a 150ms dwell delay.
  - Uses Web Animations API (WAAPI) for smooth FLIP reordering of space cards.

### 3.2 AppSidebarOverview (v2)

- **Source**: `ianmaciel7/notes-app@old-5` (`src/app/_components/workspace/app-sidebar-overview.tsx`, SHA `a020d635de368b755992e1282e18af9fdc2b8a03`)
- **Behavior**:
  - Fixed `29px` vertical entity row rhythm.
  - Hover action reveal: row action menu button remains invisible (`opacity-0 pointer-events-none`) until hover or focus (`group-hover:opacity-100 group-hover:pointer-events-auto`).
  - Active state distinction using background contrast (`bg-surface-active`) and semantic typography color.

### 3.3 Standalone Sidebar Prototype (v3)

- **Source**: `ianmaciel7/exams-app@dev` (`docs/Documentos/01-planejamento/revisao/sidebar-prototipo/prototipo-sidebar.html`, SHA `783b7041913a8ddc01c7bd2aa1ee6bbf6eeb7e1a`)
- **Behavior**:
  - Standalone vanilla CSS/JS implementation.
  - Collapsible accordion sections with animated chevrons (`rotate(-90deg)` in 150ms).
  - Off-canvas drawer for viewports under 768px (`transform: translateX(-105%)` to `translateX(0)`).
  - Skeleton loading states with `@keyframes skeletonPulse` (1200ms ease-in-out infinite).

---

## 4. Header Tabs and Navigation Strip

### 4.1 AppHeaderTabs & AppSpaceHeader

- **Source**: `src/app/_components/workspace/app-header-tabs.tsx` (PR #38, PR #40, PR #41, SHA `4eb93c5013c27ba6724b4f116cc9fe5846398eb8`)
- **Tab Descriptor Contract**:
  ```typescript
  export interface AppHeaderTab {
    id: string;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    iconClassName?: string;
    preview?: React.ReactNode;
    pinned?: boolean;
    draggable?: boolean;
  }
  ```
- **Key Capabilities**:
  - Horizontal drag-and-drop tab reordering.
  - Tab pinning: pinned tabs display icon-only compact width and reject closure (`onCloseRequest` returns false with user feedback toast).
  - Shift-click or menu action to open tab in secondary side panel (`onShiftOpen`).
  - Tab hover preview peek showing contextual summary card.

---

## 5. Exam and Question Viewer Components

### 5.1 QuestionCard

- **Source**: `docs/Documentos/01-planejamento/revisao/insumos-design-system/questioncard-README.md` (SHA `812af0e91ebb17ba00723456923733445d38663a`)
- **Role**: Renders a complete exam question enunciation, associated figures/diagrams, and response alternatives.
- **Features**:
  - Enunciation container with Markdown and LaTeX math parsing.
  - Alternatives list (A, B, C, D, E) with explicit radio semantics and keyboard selection (keys `1`..`5` or `A`..`E`).
  - State rendering: Unanswered, Selected, Confirmed, Correct (green tone), Incorrect (red tone with explanation).
  - Question image viewer supporting click-to-zoom in an inert modal overlay.

### 5.2 QuestionNavigator

- **Source**: `docs/Documentos/01-planejamento/revisao/insumos-design-system/questionnavigator-README.md` (SHA `d1b5366d76b655eb73d21b5f833ff35530ac1aba`)
- **Role**: Matrix overview of all questions in an active simulation or exam.
- **Features**:
  - Compact number pill matrix with status coloring:
    - Neutral outline: Unanswered
    - Solid blue: Answered
    - Yellow corner flag: Marked for review
    - Green/Red: Graded mode
  - Keyboard arrow key navigation across question grid.
  - Quick jump button directly scrolling to target question.

### 5.3 TimerControl

- **Source**: `docs/Documentos/01-planejamento/revisao/insumos-design-system/timer-README.md` (SHA `4ce48fe0fc09f6f3c35169d8be9545d765c07705`)
- **Role**: Exam session duration countdown and elapsed time tracker.
- **Features**:
  - High-visibility monospace countdown (`Geist Mono`).
  - Pause/Resume controls with blurred stage overlay to prevent cheating during pauses.
  - Visual urgency alert when remaining time drops below 5 minutes (subtle amber border pulse).

---

## 6. Flashcard and Spaced Repetition Components

### 6.1 FlashcardViewer

- **Source**: `docs/Documentos/01-planejamento/revisao/insumos-design-system/flashcard-README.md` (SHA `52a06cbfa8b129f94411857eb07ffa4f8e8b38ee`)
- **Role**: Interactive two-sided revision card integrated with Free Spaced Repetition Scheduler (FSRS).
- **Features**:
  - 3D CSS perspective card flip (`transform: rotateY(180deg)` with `transform-style: preserve-3d`).
  - Prompt surface (Front) containing question, diagram, and concept tags.
  - Solution surface (Back) revealing answer explanation, reference citations, and rating buttons.
  - Spacebar toggle for reveal action.

### 6.2 RatingButtons

- **Source**: `docs/Documentos/01-planejamento/revisao/insumos-design-system/ratingbuttons-README.md` (SHA `1203053bd8ec60b8ffac3aff4c84a1bc103e19a1`)
- **Role**: Submits recall difficulty score to the FSRS algorithm.
- **Four-Grade Buttons**:
  1. `Again` (Key `1`, Red tone): Complete memory lapse, immediate redisplay.
  2. `Hard` (Key `2`, Orange tone): Recalled with significant effort, short interval increase.
  3. `Good` (Key `3`, Blue tone): Correct recall with normal effort, standard interval growth.
  4. `Easy` (Key `4`, Green tone): Instant effortless recall, maximum interval increase.

---

## 7. Knowledge Graph Canvas

### 7.1 GraphCanvas

- **Source**: `ianmaciel7/exams-app-antigo-2@feat/67-unified-graph-20261115` (`src/components/graph/graph-canvas.tsx`)
- **Role**: Interactive canvas visualizer connecting exams, questions, topics, notes, and citations.
- **Technical Capabilities**:
  - HTML5 Canvas 2D / WebGL rendering layer.
  - Smooth pan and pinch-to-zoom with viewport bounding boxes.
  - Force-directed physics convergence using velocity Verlet integration (`GraphForceModel` from `src/domain/graph_force.py`).
  - Node hover peeks showing entity metadata and connectivity degree.
  - Cluster color coding mapped to domain taxonomy.

---

## 8. Overlays, Modals, and Command Menus

### 8.1 SidePanelSearchOverlay (Command Palette)

- **Source**: `src/app/_components/workspace/app-header-tabs.tsx`
- **Role**: Quick search modal for entities, actions, and recent queries.
- **Geometry & Tokens**:
  - Centered modal container (`max-w-[50rem]`, rounded-xl, `elevation-4` `shadow-2xl`).
  - Top input bar (`h-[58px]`, `px-4`, font-size `17px`, autofocus).
  - Recent items list with semantic icon chips (`#e8f0ff` pages, `#fff0d6` collections, `#ffe8ed` citations).
  - Dismissal via backdrop click or `Escape` key.

### 8.2 CompactMenu

- **Source**: `src/components/ui/compact-menu.tsx` (PR #42, SHA `cd8765fa2f5257a27c446b1cf15cf4464d83e79a`)
- **Role**: Context menu for sidebar entities and tab strips.
- **Variants**: Semantic width options (`w-48`, `w-56`, `w-64`).

---

## 9. Interaction States and API Matrix

The following matrix documents the canonical props, state bindings, accessibility tokens, and error handling contracts for all catalog components:

| Component Name | Key Public Props | Internal State | Required ARIA Attributes | Supported Interaction States |
|---|---|---|---|---|
| `AppShell` | `defaultCollapsed?: boolean`, `children: ReactNode` | `collapsed`, `rightCollapsed`, `isMobile`, `peek` | `role="region"`, `aria-expanded` | Default, Collapsed, Peek, Drag-Resizing |
| `AppHeader` | `onBack?: () => void`, `onForward?: () => void`, `onFocus?: () => void` | `canGoBack`, `canGoForward` | `role="banner"`, `aria-label="Workspace header"` | Default, Focus-Mode, Scrolled |
| `AppSpaceHeader` | `tabs: AppHeaderTab[]`, `value: string`, `onValueChange: (id: string) => void` | `draggedTabId`, `hoveredTabId` | `role="tablist"`, `role="tab"`, `aria-selected` | Resting, Tab-Hover, Dragging, Pinned |
| `AppSidebarOverview`| `activeId: string`, `onSelect: (id: string) => void` | `filterQuery`, `hoveredRowId` | `role="navigation"`, `aria-current="page"` | Inactive, Row-Hover, Active, Action-Reveal |
| `QuestionCard` | `question: ExamQuestion`, `selectedChoice?: string`, `onSelect: (choice: string) => void` | `isZoomed`, `showExplanation` | `role="group"`, `aria-labelledby`, `role="radiogroup"` | Unanswered, Option-Hover, Selected, Evaluated |
| `QuestionNavigator` | `total: number`, `current: number`, `statuses: Map<number, QuestionStatus>` | `focusedIndex` | `role="navigation"`, `aria-label="Question grid"` | Default, Pill-Hover, Marked-Flag, Jump-Active |
| `FlashcardViewer` | `card: Flashcard`, `onGrade: (rating: number) => void` | `isFlipped: boolean` | `role="region"`, `aria-live="polite"` | Front-Prompt, Flipping, Back-Solution |
| `RatingButtons` | `disabled?: boolean`, `onRate: (score: 1\|2\|3\|4) => void` | `focusedRating` | `role="toolbar"`, `aria-label="Rating choices"` | Resting, Button-Hover, Pressed, Disabled |
| `GraphCanvas` | `nodes: GraphNode[]`, `edges: GraphEdge[]`, `onNodeClick: (id: string) => void` | `zoomLevel`, `panOffset`, `hoveredNodeId` | `role="application"`, `aria-label="Knowledge graph"` | Physics-Running, Node-Hover, Pan-Zoom, Static |
| `SidePanelSearchOverlay`| `isOpen: boolean`, `onClose: () => void`, `onSelect: (item: any) => void` | `query: string`, `highlightIndex: number` | `role="dialog"`, `aria-modal="true"` | Open, Typing, Item-Highlighted, Empty-Results |
