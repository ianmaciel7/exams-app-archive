# Microinteraction Design Patterns — States, Contextual Interaction and Motion Polish

Review: 2026-11-25. 33 indexed records; overlap existing patterns intentionally. General reusable guidance, no product modification.

## Interpretation and evidence

- Microinteraction Design Patterns, Component Interaction States, Interaction Design Details, UI Craft, Interaction Polish and Design Engineering Guidelines are search terms; the umbrella taxonomy here is a proposed knowledge organization, not a formal universal standard.
- Static user screenshot supports an observed row highlight, visible secondary actions and tooltip label, not causation, exact hover trigger, timings, CSS, actual motion or component library; no private image or labels published.
- Use a behavior contract: trigger, state before/after, rules, visual feedback, input modality, timing/interruptibility, persistence, accessibility, failure and acceptance. Distinguish observable interaction from implementation choice.
- Tooltip is noninteractive explanatory content; an interactive hover card needs appropriate semantics. APG tooltip pattern is still work in progress. WCAG 1.4.13 applies to additional hover/focus content where applicable: dismissible, hoverable and persistent, subject to exceptions. Test touch and keyboard separately.
- Do not prescribe a universal duration, delay, scale, opacity or animation for all controls. Use feedback without blocking action; reduced-motion preference must preserve essential cues. State layers and safe polygon are techniques, not formal UX standards.
- An outline icon, hidden controls or dark theme is not evidence that an application uses a specific library. Design galleries are existence evidence; examples are not population-level adoption or usability findings.
- Cross-reference prior contextual-tool, motion, accessibility and component-behavior catalogs. Counts are indexed entries, not net-new distinct patterns. Preserve original URLs and prior metadata.

## Pattern catalog

### states

- **Hover State / Hover Highlight** (`hover-state`): Pointer over an interactive target; distinguish from persistent selection. **Acceptance:** Visual feedback changes only relevant affordance; mouseout restores prior state; no hover-only access. Sources: natural, micro-vercel.
- **Pressed State** (`pressed-state`): Transient press feedback distinct from toggle's persistent pressed semantics. **Acceptance:** Pointer down/up and keyboard activation work; cancel press when appropriate; no layout shift. Sources: natural, micro-vercel.
- **Focus Visible** (`focus-visible`): Visible keyboard focus, not merely pointer hover. **Acceptance:** Tab through controls; focus is visible and not obscured; avoid removing outline without replacement. Sources: micro-vercel, behavior-wcag22.
- **Focus Within** (`focus-within`): Highlight parent or reveal actions when a descendant receives focus. **Acceptance:** Move focus among actions; row remains usable until focus leaves; no keyboard-only disappearing controls. Sources: micro-vercel.
- **Selected State** (`selected-state`): Persistent selection separate from hover, focus and current destination. **Acceptance:** Selection survives pointer movement; accessible semantics fit actual widget; combine states coherently. Sources: apg, behavior-wcag22.
- **Disabled State** (`disabled-state`): Communicate unavailable action and reason where useful; use actual semantics. **Acceptance:** Disabled action cannot accidentally execute; explain missing prerequisites accessibly. Sources: apg, behavior-wcag22.
- **Loading / Busy State** (`loading-state`): Represent ongoing work without implying success or blocking unrelated actions. **Acceptance:** Loading and completion match actual work; screen reader receives relevant updates; failure recoverable. Sources: behavior-wcag22, natural.
- **Dragging State** (`dragging-state`): Show held item, original position and relevant drag feedback. **Acceptance:** Drag cancel restores state; touch/keyboard and single-pointer alternative available. Sources: natural, behavior-wcag22.
- **Drop Target / Insertion Indicator** (`drop-target-state`): Distinguish valid target and insertion position; do not rely only on color. **Acceptance:** Valid and invalid drop targets clear; no accidental reorder; alternative move command works. Sources: natural, behavior-wcag22.
- **State Layers** (`state-layers`): Compose state-dependent surface or overlay styling for interaction feedback; design-system technique rather than universal requirement. **Acceptance:** Selected+hover+focus combination stays legible in light/dark modes. Sources: natural, micro-vercel.

### contextual

- **Hover-Reveal Actions** (`hover-reveal`): Reveal secondary row controls on pointer intent without hiding essentials. **Acceptance:** No row resizing or click interception; move pointer to child action without disappearance. Sources: natural, rauno-interaction.
- **Focus-Reveal Actions** (`focus-reveal`): Reveal equivalent controls via keyboard; touch fallback through explicit affordance. **Acceptance:** Tab to actions; controls remain visible and operable on touch-only device. Sources: micro-vercel, wcag-hover.
- **Overflow Menu Trigger / More Actions** (`overflow-trigger`): Use recognizable control to access secondary actions in context. **Acceptance:** Accessible name, keyboard open/close, correct item scope, focus return; label ambiguous icons. Sources: apg, micro-vercel.
- **Hover Intent** (`hover-intent`): Delay or infer intentional hover for secondary surfaces to reduce accidental activation. **Acceptance:** Rapid cursor transit doesn't open unwanted panels; deliberate dwell works; no fixed universal delay. Sources: micro-floating-hover.
- **Delayed Tooltip** (`delayed-tooltip`): Short noninteractive explanation for a labeled or unfamiliar control; not sole source of essential information. **Acceptance:** Pointer/focus opens; Escape dismisses; no interactive controls inside tooltip; preserve accessible name. Sources: micro-nng-tooltip, micro-radix-tooltip, micro-apg-tooltip, wcag-hover.
- **Tooltip Delay Group / Skip Delay** (`tooltip-delay-group`): After deliberate opening, allow faster neighboring tooltips during a bounded group interval. **Acceptance:** First opening delayed; adjacent labels appear promptly; delay resets after leaving group; no focus stealing. Sources: micro-floating-delay, micro-radix-tooltip.
- **Hover Card** (`hover-card`): Contextual preview beyond a brief label; interactive content requires suitable popover/dialog semantics. **Acceptance:** Preview can be dismissed; keyboard/touch path; important information accessible without hover. Sources: micro-floating-hover, wcag-hover, micro-apg-tooltip.
- **Interest-Triggered Preview** (`interest-preview`): Preview an item before committing navigation; product-specific trigger may be hover, focus or explicit action. **Acceptance:** Preview does not change committed selection or navigation; explicit opening path works. Sources: natural, micro-floating-hover.
- **Anchored Popover** (`anchored-popover`): Position contextual surface relative to its trigger; semantics depend on content. **Acceptance:** Scroll/resize keeps anchor relationship; Escape, focus behavior and touch supported. Sources: micro-floating-hover, apg.
- **Safe Polygon / Pointer Travel Corridor** (`safe-polygon`): Implementation technique to preserve hover surface during intentional pointer travel. **Acceptance:** Diagonal movement into menu stays open; moving away closes; no reliance on pointer-only interaction. Sources: micro-floating-hover.
- **Adaptive Placement / Collision Avoidance** (`adaptive-placement`): Flip or shift overlay to remain available near viewport boundaries. **Acceptance:** Test edges, scroll, zoom, narrow viewport and content clipping. Sources: micro-floating-shift, micro-floating-flip.
- **Expanded Hit Area** (`expanded-hit-area`): Increase operable target around small visual icon while preserving distinct targets. **Acceptance:** Test adjacent target overlap, touch and keyboard; apply WCAG target-size criteria and exceptions. Sources: micro-vercel, behavior-wcag22.

### motion

- **Color Transition** (`color-transition`): Animate changes of visual state when helpful; prioritize instant semantic feedback. **Acceptance:** Rapid enter/leave reverses smoothly; contrast and selected/focus distinction remain clear. Sources: natural, emil-great-animation.
- **Opacity Transition** (`opacity-transition`): Fade nonessential visuals on state change; distinguish invisible from noninteractive. **Acceptance:** Hidden controls don't capture input invisibly; reveal on focus/touch; no delayed essential feedback. Sources: natural, micro-vercel.
- **Press Feedback** (`press-feedback`): Subtle response to activation; avoid compulsory scaling or movement. **Acceptance:** Keyboard and touch receive feedback; reduced-motion alternative retains state cue. Sources: natural, micro-vercel.
- **Icon Morphing** (`icon-morphing`): Transition icon shape for closely related states only if meaning remains obvious. **Acceptance:** Accessible name/state update immediately; reduced-motion alternative; no unrelated visual confusion. Sources: emil-great-animation, rauno-interaction.
- **Origin-Aware Animation** (`origin-aware`): Maintain spatial link from triggering control to resulting surface. **Acceptance:** Popover enters/exits from meaningful anchor; works after collision reposition; no animation prerequisite. Sources: emil-origin.
- **Interruptible / Reversible Animation** (`interruptible`): New user input supersedes ongoing transition rather than queues stale motion. **Acceptance:** Rapid reopen/close and repeated toggles converge on current state; no delayed input. Sources: emil-great-animation, emil-animation-frequency.
- **Layout Animation** (`layout-animation`): Preserve spatial continuity when items add, remove or reorder. **Acceptance:** Actual order and focus stay correct; no overlap or blocked interactions. Sources: motion, natural.
- **Shared Element Transition** (`shared-element`): Preserve visible identity between two presentations of same element. **Acceptance:** No duplicate accessible objects or stale focus; skip safely when identity or support missing. Sources: motion.
- **Spring Animation** (`spring-animation`): Physics-inspired easing for appropriate direct manipulation, not universal motion default. **Acceptance:** Tune to task; avoid excessive oscillation; repeated interactions remain responsive. Sources: emil-great-animation, motion.
- **Enter / Exit Transition** (`enter-exit`): Reveal or dismiss contextual surface without interrupting interaction. **Acceptance:** Exit doesn't leave hidden focusable controls or intercept input; interruption supported. Sources: micro-floating-transition, emil-origin.
- **Reduced Motion** (`reduced-motion`): Respect motion preference and applicable accessibility requirements; preserve meaning. **Acceptance:** With reduced motion enabled, all actions, state cues and content remain available. Sources: micro-vercel, behavior-wcag22.

## Example interaction contract (generic navigation row)

Idle row: label and navigation icon; secondary actions may remain discreet. Hover or focus-within: background/state cue and secondary controls; keep layout stable. Moving from row to action: controls remain operable. Tooltip: brief delayed explanatory label, skip delay within a toolbar group when appropriate. Action: press feedback and correct semantic action; menu opening and closing manage focus. Touch: equivalent explicit access. Selected and current navigation state stay distinct; keyboard focus and contrast remain visible. Optional transitions follow the current state and reduced-motion setting. Verify actual behavior with recordings or instrumentation before assigning exact timing.

## Sources

- [Chrome — Natural interactions](https://developer.chrome.com/docs/modern-web-guidance/guides/user-experience/natural-interactions) — `natural`; primary-technical; carried forward.
- [Vercel — Web Interface Guidelines](https://vercel.com/design/guidelines) — `micro-vercel`; practitioner-guidance; Reopened 2026-11-25; living guidance, not a formal standard.
- [NN/g — Tooltip Guidelines](https://www.nngroup.com/articles/tooltip-guidelines/) — `micro-nng-tooltip`; usability-guidance; Reopened 2026-11-25.
- [Floating UI — useHover](https://floating-ui.com/docs/usehover) — `micro-floating-hover`; primary-library; Reopened 2026-11-25.
- [Floating UI — FloatingDelayGroup](https://floating-ui.com/docs/floatingdelaygroup) — `micro-floating-delay`; primary-library; Reopened 2026-11-25.
- [Radix — Tooltip](https://www.radix-ui.com/primitives/docs/components/tooltip) — `micro-radix-tooltip`; primary-library; Reopened 2026-11-25.
- [W3C APG — Tooltip Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/) — `micro-apg-tooltip`; accessibility-guidance; Reopened 2026-11-25; work in progress, no task force consensus.
- [Emil Kowalski — Agents with Taste](https://emilkowal.ski/ui/agents-with-taste) — `micro-emil-taste`; practitioner-essay; Reopened 2026-11-25.
- [Dan Saffer — Microinteractions](https://www.oreilly.com/library/view/microinteractions/9781449342760/) — `micro-saffer`; book-reference; Prior conversation; full book not inspected.
- [Rauno Freiberg — Invisible Details of Interaction Design](https://rauno.me/craft/interaction-design) — `rauno-interaction`; practitioner-essay; search-index evidence; revalidate full source before specific claims.
- [Emil Kowalski — Origin-aware animations](https://emilkowal.ski/ui/origin-aware-animations) — `emil-origin`; practitioner-guidance; search-index evidence; revalidate full source before specific claims.
- [Emil Kowalski — Great Animations](https://emilkowal.ski/ui/great-animations) — `emil-great-animation`; practitioner-guidance; search-index evidence; revalidate full source before specific claims.
- [Emil Kowalski — You Don’t Need Animations](https://emilkowal.ski/ui/you-dont-need-animations) — `emil-animation-frequency`; practitioner-guidance; search-index evidence; revalidate full source before specific claims.
- [Motion — Layout animations](https://motion.dev/docs/react-layout-animations) — `motion`; primary-library; carried forward.
- [WCAG 2.2 Content on Hover or Focus](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus) — `wcag-hover`; normative-support; carried forward; not revalidated in this batch.
- [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/) — `behavior-wcag22`; accessibility-standard; Prior conversation or reference catalog; revalidate before reuse.
- [W3C — ARIA APG example index](https://www.w3.org/WAI/ARIA/apg/example-index/) — `apg`; primary-guidance; carried forward.
- [Detail](https://detail.design/) — `detail`; independent-interaction-gallery; search-index result consulted; full-site audit and access/licence not verified.
- [Design Spells](https://designspells.com/) — `designspells`; microinteraction-gallery; verified.
- [UX Patterns for Developers](https://uxpatterns.dev/) — `uxpatterns`; pattern-library; verified.
- [Floating UI — shift](https://floating-ui.com/docs/shift) — `micro-floating-shift`; primary-library; Linked by reopened useHover documentation; individual body not re-fetched.
- [Floating UI — flip](https://floating-ui.com/docs/flip) — `micro-floating-flip`; primary-library; Linked by reopened useHover documentation; individual body not re-fetched.
- [Floating UI — useTransition](https://floating-ui.com/docs/usetransition) — `micro-floating-transition`; primary-library; Linked by reopened useHover documentation; individual body not re-fetched.

Related: [Component behavior](component-interaction-behavior-patterns.md), [Behavioral UX quality](behavioral-ux-quality-2026.md), [general pattern library](../interface-pattern-library/README.md).
