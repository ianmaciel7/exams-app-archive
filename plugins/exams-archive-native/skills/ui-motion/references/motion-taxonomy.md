# Motion vocabulary and validation

| Intent / synonyms | Code signals | Required behavior |
|---|---|---|
| recolher / expandir / sidebar / collapse | `collapsed`, `transition`, `margin-left`, `transform` | initial/final geometry, duration/easing and focus |
| hover / microinteração / action reveal | `group-hover`, `focus-within`, `opacity`, `pointer-events` | timing, keyboard/touch parity and hit targets |
| peek / dwell / hover-sidebar | `peek`, `setTimeout`, `clearTimeout`, `mouseleave` | open/close **delay** distinct from duration; nonpersistent state |
| gaveta / drawer / mobile | `translateX`, `Sheet`, `backdrop`, `Escape` | enter/exit, dismiss and focus return |
| drag / drop / reorder / sortable | `requestAnimationFrame`, `.animate`, `pointermove`, dnd-kit | transform, cancel, pointer feedback, interrupted/reversed |
| popup / tooltip / popover / fade | `data-open`, `data-closed`, `animate-in`, `fade-in` | opening and closing timing separately, clipping |
| loading / skeleton / pulse | `@keyframes`, `animation`, `animate-pulse` | duration/repeat, reduced motion, timeout and error fallback |
| accordion / caret / expand | `aria-expanded`, `rotate`, `transition-transform` | rotation and content visibility without layout glitches |
| responsive / gesture / resize | `ResizeObserver`, `pointer`, `setWidth`, `clamp` | bounds, keyboard resize and layout state persistence |

Code might declare a transition without ever applying it; follow render usage. Static opacity is not timed motion. Some source evidence does not contain reduced-motion overrides; report missing evidence, never assume compliance.

For a ChatGPT preview, test desktop/mobile, theme, keyboard, hover, pointer, fast-repeat interruption, transform clipping and reduced motion. Never leave permanent loading animations or fake controls. Labels: `source-verified`, `runtime-verified`, `inferred`, `unknown`.
