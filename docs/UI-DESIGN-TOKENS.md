# UI Design Tokens Specification

Document Version: 1.0.0  
Date: 2026-11-24  
Issue Reference: #24 (Consolidar docs, recuperacao de motion, busca e sincronizacao multiagente)  
Zero Emoji Policy: Verified compliant. No Unicode emojis in range U+10000 to U+10FFFF.

---

## 1. Overview and Core Philosophy

The Exams App Archive design token system establishes a unified, reproducible visual and spatial contract across all workspace interfaces, exam viewers, flashcard review decks, knowledge graphs, and multi-agent previews.

The system is derived directly from historical implementations in `ianmaciel7/notes-app` (branches `old-5`, `old-10`, `dev`), `ianmaciel7/exams-app` (`dev`), and `ianmaciel7/shadcn-template`. It reflects a quiet, calm, object-centric workspace model characterized by:
- Neutral, low-glare surface luminance in both Light and Dark modes.
- Subtle contrast steps rather than decorative borders or heavy drop shadows.
- Dense vertical and horizontal rhythms optimized for information density without feeling cramped.
- Deterministic token definitions declared in CSS custom properties using the modern `oklch` color space.

---

## 2. Color Tokens (OKLCH Color Model)

All color tokens are formally declared in `src/app/globals.css` and mapped into Tailwind v4 theme variables. The `oklch` model ensures perceptual uniformity, accurate lightness ramps, and predictable chroma gradients across display gamuts.

### 2.1 Canonical Semantic Surface Tokens

| Token Name | Light Theme Value | Dark Theme Value | Semantic Purpose and Usage |
|---|---|---|---|
| `--background` / `--surface-canvas` | `oklch(0.985 0.005 80)` | `oklch(0.17 0.012 80)` | Base application canvas, outer margins, full-viewport backdrop |
| `--surface-panel` | `oklch(1 0 0)` | `oklch(0.205 0.012 80)` | Workspace panels, cards, sidebar sheets, popover containers |
| `--surface-panel-muted` | `oklch(0.975 0.008 80)` | `oklch(0.19 0.012 80)` | Inactive tab bars, rail sidebars, secondary panel headers |
| `--surface-hover` | `oklch(0.945 0.012 80)` | `oklch(0.27 0.012 80)` | Hover micro-interaction state for rows, buttons, list items |
| `--surface-active` | `oklch(0.925 0.016 80)` | `oklch(0.31 0.016 80)` | Pressed state, active navigation item, selected row background |

### 2.2 Canonical Content and Foreground Tokens

| Token Name | Light Theme Value | Dark Theme Value | Semantic Purpose and Usage |
|---|---|---|---|
| `--content-primary` | `oklch(0.22 0.012 80)` | `oklch(0.94 0.008 80)` | Primary headings, titles, active tab text, high-emphasis text |
| `--content-secondary` | `oklch(0.42 0.012 80)` | `oklch(0.76 0.012 80)` | Body text, navigational labels, active control icons |
| `--content-tertiary` | `oklch(0.58 0.012 80)` | `oklch(0.62 0.012 80)` | Metadata, timestamp captions, keyboard shortcuts, disabled hints |
| `--content-active` | `oklch(0.55 0.12 275)` | `oklch(0.75 0.11 275)` | Active tab accent, focused item indicator, primary highlight |

### 2.3 Structural Border and Focus Tokens

| Token Name | Light Theme Value | Dark Theme Value | Semantic Purpose and Usage |
|---|---|---|---|
| `--border` | `oklch(0.922 0 0)` | `oklch(0.269 0 0)` | Structural pane dividers, card contours |
| `--border-subtle` | `oklch(0.22 0.012 80 / 12%)` | `oklch(0.985 0.008 80 / 14%)` | Low-contrast row dividers, list separators, subtle tab boundaries |
| `--ring` | `oklch(0.708 0 0)` | `oklch(0.439 0 0)` | Keyboard navigation `focus-visible` outline ring |
| `--input` | `oklch(0.922 0 0)` | `oklch(0.269 0 0)` | Form controls and search input borders |

### 2.4 Object-Type Identity Chip Palette

Identity chips for entities, topics, question categories, and file types use fixed semantic color tones. Chips must not be generated with arbitrary runtime colors:

| Identity Tone | Badge Background | Badge Text / Icon Foreground | Intended Domain Concept |
|---|---|---|---|
| `blue-file` | `#e8f0ff` | `#3f6fce` | Standard note, question item, document page |
| `amber-folder` | `#fff0d6` | `#b96b0e` | Collection, topic folder, question category |
| `rose-citation` | `#ffe8ed` | `#d74b67` | Exam source, formal citation, reference link |
| `emerald-verified`| `#e6f7ed` | `#1e824c` | Correct question answer, verified mastery state |
| `violet-graph` | `#f0ebfc` | `#6b3ba7` | Graph node, concept cluster, associative relation |
| `slate-meta` | `#f1f3f5` | `#495057` | Auxiliary metadata, flashcard review rating |

---

## 3. Typography System

The typography scale utilizes `Geist Sans` for structural UI components and `Geist Mono` for timestamps, metadata counts, keyboard shortcuts, and code blocks.

### 3.1 Type Scale Hierarchy

| Token / Class | Font Size | Line Height | Tracking | Recommended Use |
|---|---|---|---|---|
| `text-2xs` | `10px (0.625rem)` | `14px (0.875rem)` | `+0.02em` | Micro badges, status pills, keyboard keycaps (`kbd`) |
| `text-xs` | `12px (0.75rem)` | `16px (1.0rem)` | `+0.01em` | Timestamps, secondary metadata, breadcrumbs, tooltips |
| `text-sm` | `14px (0.875rem)` | `20px (1.25rem)` | `0` | Primary table rows, sidebar item labels, buttons, controls |
| `text-base` | `16px (1.0rem)` | `24px (1.5rem)` | `-0.01em` | Section headers, card titles, dialogue body text |
| `text-lg` | `18px (1.125rem)` | `28px (1.75rem)` | `-0.015em` | Exam question enunciation, drawer panel title |
| `text-xl` | `20px (1.25rem)` | `28px (1.75rem)` | `-0.02em` | Workspace modal titles, exam completion headline |
| `text-2xl` | `24px (1.5rem)` | `32px (2.0rem)` | `-0.025em` | Dashboard primary view header |

### 3.2 Font Weight Standards

- `font-normal` (400): Standard prose, question body, inactive row text.
- `font-medium` (500): Control labels, table header titles, tab labels, interactive buttons.
- `font-semibold` (600): Active tab title, modal headers, question alternative identifiers (A, B, C, D).
- `font-bold` (700): Reserved strictly for high-impact metric counters and score summaries.

---

## 4. Spacing Scale and Spatial Geometry

Spatial layout is constructed around an 8-point base grid with 4-point micro-adjustments for compact interface controls.

### 4.1 Spacing Tokens

| Tailwind Token | Pixel Equivalent | Layout Function |
|---|---|---|
| `p-0.5` / `gap-0.5` | `2px` | Sub-element spacing, micro icon margins |
| `p-1` / `gap-1` | `4px` | Compact button internal padding, list row gap |
| `p-1.5` / `gap-1.5` | `6px` | Icon-to-text gap in compact sidebar rows |
| `p-2` / `gap-2` | `8px` | Standard compact control padding, toolbar item gap |
| `p-3` / `gap-3` | `12px` | Card internal padding, popover header margins |
| `p-4` / `gap-4` | `16px` | Modal dialog interior gutters, panel margin |
| `p-6` / `gap-6` | `24px` | Workspace canvas padding, exam viewer margins |

### 4.2 Exact Component Height Rhythms

To eliminate layout jank and maintain strict visual vertical alignment:
- **Sidebar Entity Row**: `29px` desktop rhythm (fixed height container, vertically centered content).
- **Utility and Action Controls**: `32px` (`h-8`, `min-h-[32px]`).
- **Application Header (`AppHeader`)**: `46px` (`h-[46px]`, `border-b`).
- **Global Search / Command Palette Input**: `58px` (`h-[58px]`, `px-4`).
- **Collapsed Sidebar Rail Width**: `48px` (`w-12`).
- **Standard Expanded Sidebar Width**: `240px` (clamped between `160px` minimum and `360px` maximum).

### 4.3 Border Radius Tokens

| Radius Token | Calculation / Value | Element Application |
|---|---|---|
| `--radius-sm` | `calc(var(--radius) * 0.6) = 4.8px` | Tags, micro pills, inline code containers |
| `--radius-md` | `calc(var(--radius) * 0.8) = 6.4px` | Compact buttons, list row hover highlights |
| `--radius-lg` | `var(--radius) = 8.0px` | Cards, popovers, dropdown containers |
| `--radius-xl` | `12.0px` | Dialog windows, command palette modals |
| `--radius-full`| `9999px` | Circular avatar badges, floating action round buttons |

---

## 5. Elevations and Depth Hierarchy

Depth in this system is conveyed through subtle borders and restrained shadows. Excessive elevation blurs and dark drop shadows are intentionally omitted to avoid visual fatigue during prolonged study sessions.

```
+-------------------------------------------------------------+
| Elevation Level 4: Modals & Command Overlays (shadow-2xl)   |
|   +-------------------------------------------------------+ |
|   | Elevation Level 3: Drawers & Floating Toasts (shadow-lg) | |
|   |   +-------------------------------------------------+ | |
|   |   | Elevation Level 2: Popovers & Tooltips (shadow-md)| | |
|   |   |   +-------------------------------------------+ | | |
|   |   |   | Elevation Level 1: Cards & Panels (shadow-sm)| | |
|   |   |   |   +-------------------------------------+ | | | |
|   |   |   |   | Elevation Level 0: Canvas (flat)    | | | | |
+---+---+---+---+-------------------------------------+---+---+-+
```

| Elevation Level | CSS Shadow Class | Border Treatment | Applied Components |
|---|---|---|---|
| **Level 0 (Flat)** | `shadow-none` | None or `border-transparent` | Application canvas, background panels |
| **Level 1 (Surface)** | `shadow-sm` | `1px solid var(--border-subtle)` | Content cards, question options, resting buttons |
| **Level 2 (Popout)** | `shadow-md` | `1px solid var(--border)` | Tooltip bubbles, flyout menus, action dropdowns |
| **Level 3 (Overlay)** | `shadow-lg` | `1px solid var(--border)` | Mobile drawer, floating notifications, status toasts |
| **Level 4 (Modal)** | `shadow-2xl` | `1px solid var(--border)` + backdrop | Command palette (`SidePanelSearchOverlay`), dialogs |

---

## 6. Iconography System

Icons reinforce navigation and functional affordances without competing with written text.

### 6.1 Sizing Grid

- `size-2.5` (`10px`): Nested chevron arrows, disclosure triangles.
- `size-3` (`12px`): Close buttons inside tabs, auxiliary dismiss actions.
- `size-4` (`16px`): Standard interface actions (search, pin, duplicate, trash, split).
- `size-5` (`20px`): Section headings, rail bar icons, navigation indicators.
- `size-6` (`24px`): Empty state illustrations, modal header emblems.

### 6.2 Stroke and Interaction Rules

- All SVG icons use standard `stroke-width="1.5"` or `stroke-width="2.0"`.
- Icons must specify `aria-hidden="true"` when paired with descriptive text, or provide explicit `aria-label` / `tooltip` when rendered standalone.
- Icon colors inherit `currentColor` or reference `--content-secondary`, transitioning to `--content-primary` on hover.

---

## 7. Data Density and Viewport Adaptation

The design system supports three density tiers tailored to viewport sizes:

### 7.1 Viewport Breakpoints

1. **Desktop Viewport (>= 1024px)**:
   - High data density.
   - Dual-panel layout (Left Navigation Sidebar + Center Stage + Optional Right Side Panel).
   - Sidebar entity rows at `29px` height.
   - Inline action triggers reveal on row hover (`opacity-0` -> `group-hover:opacity-100`).

2. **Tablet Viewport (768px to 1023px)**:
   - Medium data density.
   - Left sidebar collapsible to 48px rail or overlay drawer.
   - Stage occupies full remaining width; side panel shifts to stacked tab or modal overlay.
   - Touch-friendly tap targets (`min-h-[36px]`).

3. **Mobile Viewport (<= 767px, targeting 390px iPhone baseline)**:
   - Optimized mobile density.
   - Off-canvas drawer layout with backdrop blur (`translateX(-105%)` to `translateX(0)`).
   - Tap targets strictly meet accessibility requirements (`min-h-[44px]`).
   - Sticky navigation footer for exam question switching and timer control.
