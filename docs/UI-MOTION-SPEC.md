# UI Motion and Animation Specification

Document Version: 1.0.0  
Date: 2026-11-24  
Issue Reference: #24 (Consolidar docs, recuperacao de motion, busca e sincronizacao multiagente)  
Zero Emoji Policy: Verified compliant. No Unicode emojis in range U+10000 to U+10FFFF.

---

## 1. Architectural Philosophy and Principles

Motion in the Exams App Archive is functional, intentional, and strictly non-decorative. Animations exist to:
1. Provide spatial continuity during layout shifts (collapsing sidebars, opening drawers).
2. Clarify causal relationships between user input and interface feedback.
3. Prevent disorientation when switching contexts or navigating complex graph hierarchies.

### Critical Distinction: Dwell Delay vs Transition Duration

A recurring flaw in naive UI recovery is confusing timer dwell delays with animation transition durations. This specification establishes a hard architectural boundary:

```
[User Event: Pointer enters sidebar trigger zone]
  |
  |---> (1) Dwell Delay (Wait Period: e.g. 180ms - 300ms)
  |         No layout motion occurs; debounce prevents accidental triggers.
  |
  +---> [Timer Expires: State flips to active]
        |
        |---> (2) Transition Duration (Active Animation: e.g. 200ms)
                  CSS transition or Web Animations API executes easing curve.
                  Element reaches final geometry.
```

- **Dwell Delay (Tempo de Espera)**: An intentional JavaScript timer window (`setTimeout`) required before an intent is confirmed. During the dwell delay, the interface remains visually stable. If the user moves away before the timer expires, the pending action is canceled with zero screen flicker.
- **Transition Duration (Duracao de Transicao)**: The subsequent time window during which CSS properties (`transform`, `opacity`, `width`, `margin-left`) interpolate from initial to target values along a specified easing curve.

---

## 2. Master Motion Contracts Matrix

The following table consolidates the verified behavioral contracts extracted from `docs/UI-MOTION-EVIDENCE.json` and historical workspace implementations:

| Contract ID | Component & Concept | Trigger Event | From State | To State | Dwell Delay (ms) | Transition Duration (ms) | Easing Curve | Animated CSS Properties | Reduced Motion Behavior |
|---|---|---|---|---|---|---|---|---|---|
| `shell-surface-transition` | AppShell Panels | Resize / Collapse toggle | Previous dimension | New dimension | 0 ms | 200 ms | `ease-out` (`cubic-bezier(0, 0, 0.2, 1)`) | `width`, `height`, `transform`, `opacity` | `transition: none`, `animate-none` |
| `row-hover-active` | Sidebar Row Highlight | Pointer enter / active tap | Inactive row | Highlighted row | 0 ms | 200 ms | `ease-out` | `background-color`, `color`, `opacity` | `transition: none` |
| `reveal-overflow` | Sidebar Actions Reveal | Row hover / keyboard focus | `opacity-0 invisible` | `opacity-100 visible` | 0 ms | 200 ms | `ease-out` | `opacity`, `visibility` | `transition: none` |
| `reorder-flip` | Sidebar Card Reorder | Drag release / drop event | `translateY(delta)` | `translateY(0)` | 0 ms | 200 ms | `ease-out` | `transform` (WAAPI) | Instant snap to new position |
| `tooltip-open-close` | Tooltip Reveal | Pointer hover over icon | `opacity: 0` | `opacity: 1` | 200 ms | 180 ms | `ease-out` | `opacity`, `transform` | `opacity: 1` instant on hover |
| `popover-open-close` | Popover Menu Flyout | Button trigger click | Closed (`opacity: 0, scale: 0.95`) | Open (`opacity: 1, scale: 1.0`) | 0 ms | Open: 150 ms, Close: 100 ms | `ease-out` (enter), `ease-in` (exit) | `opacity`, `transform` | Instant appearance without scale |
| `peek-open` | Sidebar Hover Peek (v1/v2) | Hover over collapsed rail | Collapsed rail (`peek: false`) | Temporary reveal (`peek: true`) | 180 ms (v2) / 300 ms (v1) | 200 ms | `ease-out` | `transform`, `width`, `box-shadow` | Peek disabled; click required |
| `peek-close` | Hover Peek Dismissal | Pointer leaves peek area | Temporary reveal (`peek: true`) | Collapsed rail (`peek: false`) | 150 ms | 200 ms | `ease-in` | `transform`, `width`, `box-shadow` | Instant close |
| `standalone-sidebar-collapse` | Prototype Sidebar | Collapse trigger click | `margin-left: 0` | `margin-left: -240px` | 0 ms | 200 ms | `ease` (`cubic-bezier(0.25, 0.1, 0.25, 1)`) | `margin-left`, `width` | Instant layout shift |
| `standalone-section-toggle` | Accordion Chevron | Section header click | `rotate(0deg)` | `rotate(-90deg)` | 0 ms | 150 ms | `ease` | `transform` | Instant rotation |
| `standalone-skeleton` | Skeleton Placeholder | Loading initial data | `opacity: 1, scale: 1` | `opacity: 0.5, scale: 0.99` (at 50%) | 0 ms | 1200 ms (infinite) | `ease-in-out` | `opacity`, `transform` | Static neutral background |
| `standalone-drawer` | Mobile Sidebar Drawer | Hamburger toggle click | `translateX(-105%)` | `translateX(0)` | 0 ms | 200 ms | `ease` | `transform` | Instant overlay appearance |
| `standalone-resize-gesture` | Splitter Drag Resize | Pointer drag on divider | Current width | Clamped width (`160..360px`) | 0 ms (active drag) | 0 ms during drag / 200 ms snap | Linear during drag, `ease-out` on snap | `width` | Continuous update without transition |

---

## 3. Detailed Specifications for Critical Motion Behaviors

### 3.1 Hover Peek Mechanism (180ms Optimized Dwell)

The Hover Peek interaction allows quick inspection of workspace navigation without requiring full sidebar expansion.

#### State Machine Flow:
```
           +-----------------------------------------------+
           |                Collapsed Rail                 |
           +-----------------------------------------------+
              |                                          ^
              | mouseenter                               | mouseleave (timer < 180ms)
              v                                          | [Cancel Open Timer]
   [Open Timer: 180ms Dwell] ----------------------------+
              |
              | timer fires
              v
   [Transition: 200ms ease-out]
              |
              v
   +-----------------------------------------------+
   |              Peek Open (Floating)             |
   +-----------------------------------------------+
              |                                          ^
              | mouseleave                               | mouseenter (timer < 150ms)
              v                                          | [Cancel Close Timer]
   [Close Timer: 150ms Tolerance] -----------------------+
              |
              | timer fires
              v
   [Transition: 200ms ease-in]
              |
              v
           (Collapsed)
```

#### Code Implementation Standard:
```typescript
const PEEK_DWELL_MS = 180;
const PEEK_CLOSE_TOLERANCE_MS = 150;

function handleMouseEnter() {
  if (!isCollapsed) return;
  if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
  openTimerRef.current = window.setTimeout(() => {
    setPeekState(true);
  }, PEEK_DWELL_MS);
}

function handleMouseLeave() {
  if (openTimerRef.current) clearTimeout(openTimerRef.current);
  closeTimerRef.current = window.setTimeout(() => {
    setPeekState(false);
  }, PEEK_CLOSE_TOLERANCE_MS);
}
```

### 3.2 Mobile Drawer Motion (Viewport <= 767px)

- **Entry**: Off-canvas left `transform: translateX(-105%)` translating to `translateX(0)` in 200ms `ease`. The 5% extra offset ensures box shadows remain completely invisible outside the viewport.
- **Exit**: Returns to `translateX(-105%)` in 200ms `ease`.
- **Backdrop Overlay**: Fades in simultaneously with `opacity: 0` to `opacity: 0.5` (`bg-black/50`) over 200ms.
- **Touch Swipe**: Direct 1:1 gesture tracking. If drag velocity exceeds 0.5px/ms or translation crosses 40% threshold upon release, the drawer snaps open; otherwise it springs shut in 150ms.

### 3.3 FLIP Reorder Motion (Web Animations API)

To prevent visual stutter when reordering space cards or tabs:
1. **First**: Record bounding client rectangle before state reorder: `const first = el.getBoundingClientRect()`.
2. **Last**: Re-render DOM and record new position: `const last = el.getBoundingClientRect()`.
3. **Invert**: Calculate displacement: `const deltaY = first.top - last.top`.
4. **Play**: Animate transform back to origin:
   ```javascript
   el.animate(
     [{ transform: `translateY(${deltaY}px)` }, { transform: 'translateY(0)' }],
     { duration: 200, easing: 'cubic-bezier(0, 0, 0.2, 1)', fill: 'both' }
   );
   ```

### 3.4 Skeleton Loading Pulse

Used during asynchronous data fetching (questions, spaces, graph nodes):
```css
@keyframes skeletonPulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.99);
  }
}
.skeleton-row {
  animation: skeletonPulse 1200ms ease-in-out infinite;
}
```

---

## 4. Accessibility and `prefers-reduced-motion`

Under WCAG 2.2 Success Criterion 2.3.3 (Animation from Interactions), all non-essential motion must be disabled when requested by the operating system.

### 4.1 Global Media Query Fallback
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  .skeleton-row {
    animation: none !important;
    opacity: 0.75 !important;
  }
}
```

### 4.2 Tailwind Utility Implementation
All interactive elements specify Tailwind motion reduction classes:
```html
<aside className="transition-all duration-200 ease-out motion-reduce:transition-none motion-reduce:animate-none">
  ...
</aside>
```

---

## 5. Playwright Measurement Protocol and Browser Verification

To guarantee that documentation reflects empirical browser reality rather than speculative CSS classes, the repository specifies an automated Playwright testing protocol:

### 5.1 Measurement Matrix

| Parameter | Tested Values |
|---|---|
| Viewport Resolutions | Desktop: 1366x768, Tablet: 768x1024, Mobile: 390x844 |
| Theme Modes | `theme="light"`, `theme="dark"` |
| Motion Preferences | `prefers-reduced-motion: no-preference`, `prefers-reduced-motion: reduce` |
| Browser Engines | Chromium (V8/Blink), Firefox (Gecko), WebKit |

### 5.2 Verification Script Structure (Reference Protocol)

```typescript
import { test, expect } from '@playwright/test';

test.describe('UI Motion Protocol - Peek and Drawer Verification', () => {
  test('verify hover peek dwell delay and transition duration', async ({ page }) => {
    await page.goto('/workspace');
    const trigger = page.locator('[data-slot="sidebar-rail-trigger"]');
    const sidebar = page.locator('[data-slot="app-sidebar"]');

    // Step 1: Hover over trigger area
    const hoverTime = Date.now();
    await trigger.hover();

    // Step 2: Sample intermediate state at 100ms (Must NOT be open yet)
    await page.waitForTimeout(100);
    let isOpen = await sidebar.getAttribute('data-peek-open');
    expect(isOpen).toBe('false');

    // Step 3: Wait until dwell threshold (180ms) expires
    await page.waitForFunction(() => {
      const el = document.querySelector('[data-slot="app-sidebar"]');
      return el && el.getAttribute('data-peek-open') === 'true';
    }, { timeout: 500 });
    const openTime = Date.now();
    const elapsedDwell = openTime - hoverTime;
    expect(elapsedDwell).toBeGreaterThanOrEqual(170);
    expect(elapsedDwell).toBeLessThanOrEqual(250);

    // Step 4: Verify CSS transition duration matches 200ms
    const computedTransition = await sidebar.evaluate((el) => {
      return window.getComputedStyle(el).transitionDuration;
    });
    expect(computedTransition).toMatch(/0\.2s|200ms/);
  });

  test('verify prefers-reduced-motion disables transitions', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/workspace');
    const sidebar = page.locator('[data-slot="app-sidebar"]');

    const computedDuration = await sidebar.evaluate((el) => {
      return window.getComputedStyle(el).transitionDuration;
    });
    // In reduced motion, transition duration must be 0s or none
    expect(['0s', '0.00001s', '0ms', 'none']).toContain(computedDuration);
  });
});
```

### 5.3 Acceptance Criteria for Motion Verification
1. **Frame Rate Budget**: Animations must sustain 60 frames per second (frame interval <= 16.6ms) with zero dropped frames during sidebar toggles.
2. **Cumulative Layout Shift (CLS)**: Peak CLS during drawer or sidebar expansion must remain below `0.01` within the main content container.
3. **Timer Cleanup**: All `setTimeout` IDs must be cleared on component unmount or state reversal to prevent memory leaks or dangling execution.
