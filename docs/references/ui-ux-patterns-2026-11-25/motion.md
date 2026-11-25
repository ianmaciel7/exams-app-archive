# Motion design

Official Motion docs M1–M4. OpenAI O1 documents a streaming shimmer in a fullscreen composer; do not generalize it to every response. No exact timing, easing or library usage was measured for Capacities, ChatGPT or Claude. Third-party speculation from the original report is not accepted as measured evidence.

## Proposed tokens, not observed values
| Interaction | Suggested duration | Mechanism |
|---|---|---|
| Hover/focus feedback | 100–150ms | CSS opacity/background |
| Menu/popover | 120–180ms | opacity + small translate |
| Panel open/close | 180–240ms | layout or transform |
| Tab reorder | 180–250ms | layout transition |
| Shared object expansion | 200–300ms | layoutId |
| Loading | while actual work continues | explicit status, optional skeleton |

Prefer CSS for simple transitions. Use Motion layout for real spatial changes, AnimatePresence for exits and layoutId for stable shared identity when justified. Avoid animation per streamed token, decorative perpetual motion, or hiding required controls behind animation. Respect user interruption; cancel stale transitions and preserve focus. Reduced motion should remove nonessential transform/layout transitions and use static status where appropriate.

Example (original React proposal, untested):
```tsx
import { AnimatePresence, MotionConfig, motion } from "motion/react";

export function SecondaryPanel({ open, children }: {
  open: boolean;
  children: React.ReactNode;
}) {
  return (
    <MotionConfig reducedMotion="user">
      <AnimatePresence initial={false}>
        {open && (
          <motion.aside
            key="panel"
            aria-label="Secondary workspace"
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12 }}
            transition={{ duration: 0.2 }}
          >
            {children}
          </motion.aside>
        )}
      </AnimatePresence>
    </MotionConfig>
  );
}
```

Production must add keyboard-accessible toggling, focus restoration when the panel closes, responsive placement, and tests for reduced-motion preferences. For reorder provide non-drag controls. For actual streaming provide accessible status without announcing every token.
