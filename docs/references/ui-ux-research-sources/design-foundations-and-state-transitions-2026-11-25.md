# Design foundations and state transition decisions — 2026-11-25

Research synthesis from the shared UI/UX discussion; not a complete literature review or proof of implementation. References are in the canonical source register. Distinguish standards, guidance, heuristics, trends and candidate sources. Existing [microinteraction catalog](microinteraction-state-and-polish.md), [behavioral UX](behavioral-ux-quality-2026.md), [component interactions](component-interaction-behavior-patterns.md) and [design system completeness](agent-ready-design-system-completeness.md) remain authoritative for their detailed scope. This cross-index does not replace them.

## Color selection and semantic roles

**Aliases:** cores, paleta, OKLCH, design tokens, color hierarchy.

**Decision:** Choose by task, brand, context, neutral surfaces, accent, semantic states, tonal scale and contrast. Primitive → semantic → component/state tokens.

**Limits:** Neutral-first for dense workspaces; expressive direction only if useful. 60/30/10 is optional, not a standard. Color psychology varies by context; never use color alone.

**Acceptance:** Test all real foreground/background pairs, light/dark/forced colors, focus, alpha composition and gamut; inspect #103 contrast failures.

**Sources:** [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/); [CSS Color Module Level 4](https://www.w3.org/TR/css-color-4/); [CSS Color Module Level 5](https://www.w3.org/TR/css-color-5/); [DTCG Color 2025.10](https://www.designtokens.org/TR/2025.10/color/); [Radix Colors scale](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale); [shadcn/ui Theming](https://ui.shadcn.com/docs/theming); [Apple HIG Color](https://developer.apple.com/design/human-interface-guidelines/color); [Android Material color](https://developer.android.com/design/ui/mobile/guides/styles/color); [Pantone Color of the Year 2026](https://www.pantone.com/color-of-the-year/2026).

## Data visualization color selection

**Aliases:** cores gráficos, categorical sequential diverging, daltonismo.

**Decision:** Categorical for unordered groups, sequential for magnitude, diverging around a meaningful midpoint.

**Limits:** Do not conflate status and identity, imply magnitude in categories, or rely solely on hue.

**Acceptance:** Test legend, labels, adjacent marks, missing data, color vision simulation and accessible data alternative.

**Sources:** [ColorBrewer schemes](https://colorbrewer2.org/learnmore/schemes.html); [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Motion and animation decision framework

**Aliases:** motion, animação, microinteração, easing, spring, tween.

**Decision:** Start with purpose: feedback, spatial continuity, reveal, progress, direct manipulation or emphasis. Choose fade/scale/slide/layout/shared element only when useful. Tween for predictable time; spring for spatial/direct manipulation with velocity.

**Limits:** Frequent actions should be quiet and fast; no decorative delay or motion-dependent feedback. Productive vs expressive is guidance; 0/50/100/150/250/400/600ms illustrative only, not universal.

**Acceptance:** Test entry/exit asymmetry, interruption, reversal, rapid input, reduced motion, transform/opacity where appropriate and frame cost.

**Sources:** [Atlassian Motion](https://atlassian.design/foundations/motion); [Carbon Motion](https://www.carbondesignsystem.com/building-blocks/foundations/motion/overview); [Motion documentation](https://motion.dev/docs); [Emil Kowalski — Great Animations](https://emilkowal.ski/ui/great-animations); [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Attention and visual hierarchy

**Aliases:** foco visual, atenção, saliência, scale, gestalt, contrast.

**Decision:** Use scale, contrast, typography, alignment, proximity, common region, whitespace, position and limited accents to establish order.

**Limits:** Avoid competing highlights and obligatory F/Z layout; distinguish observed reading behavior from design rule. Preserve meaningful content.

**Acceptance:** Compare alternatives with realistic tasks, comprehension, visual search and keyboard order.

**Sources:** [NN/g Principles of Visual Design](https://www.nngroup.com/articles/principles-visual-design/); [GOV.UK Service Manual](https://www.gov.uk/service-manual).

## Keyboard focus and selection management

**Aliases:** focus-visible, focus-within, foco, seleção, active, modal.

**Decision:** Keyboard focus is not hover, selection or active route. Visible focus, meaningful order, return focus on dismissal; move focus logically when element removed. Avoid stealing focus on async updates.

**Limits:** WCAG 2.2 2.4.3 A, 2.4.7 and 2.4.11 AA, 2.4.13 AAA; 1.4.11 when applicable; follow widget APG. Focus trapping only appropriate modal context.

**Acceptance:** Test keyboard, screen reader, focus visibility/adjacency, sticky header obstruction, modal open/close and preservation across refresh.

**Sources:** [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/); [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/).

## Screen architecture and composition

**Aliases:** estrutura tela, layout, app shell, list-detail, supporting pane, dashboard, canvas.

**Decision:** Map tasks, objects, flows and information hierarchy before visual design. Choose single-column for focused reading/form, list-detail for browsing, supporting pane for related context, tabbed workspace/split for multiple objects, dashboard for analytics, canvas for spatial tasks.

**Limits:** Do not force 3 panes, cards or borders everywhere. Use modular spacing, meaningful groups, readable type, consistent iconography, progressive disclosure and task-driven density.

**Acceptance:** Test multiple layouts via sketch/wireframe; verify mobile/tablet/desktop, container reflow, zoom, input modalities, preservation of state, scroll and focus.

**Sources:** [Android canonical layouts](https://developer.android.com/design/ui/mobile/guides/layout-and-content/canonical-layouts); [Carbon 2x Grid](https://www.carbondesignsystem.com/building-blocks/foundations/2x-grid/overview); [NN/g Principles of Visual Design](https://www.nngroup.com/articles/principles-visual-design/); [GOV.UK Service Manual](https://www.gov.uk/service-manual); [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Interaction and component state modeling

**Aliases:** mudança de estado, state, hover, pressed, disabled, selected, expanded.

**Decision:** Define default, hover, focus-visible, pressed, selected, checked/indeterminate, expanded, open, dragging, readonly, invalid and disabled where relevant. Separate variant, event and semantic state; document simultaneous states and precedence.

**Limits:** Do not infer behavior from screenshots; don't force irrelevant states. Focus and selection remain separate; touch/no-hover alternatives.

**Acceptance:** Matrix of real component states, keyboard/touch/assistive tech, accessibility semantics, styling precedence, before/after evidence.

**Sources:** [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/); [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Data and asynchronous state modeling

**Aliases:** loading, empty, pending, optimistic, retry, streaming, rollback, offline.

**Decision:** Distinguish initial loading, refresh, empty, partial, stale, pending, optimistic, success, error, timeout, retry, offline, conflict, permission denied, cancel, undo and unsaved. Track operation state separately from data and visual animation.

**Limits:** Never report success or progress without confirmation; preserve data/context on refresh; avoid race and duplicate submission.

**Acceptance:** Test out-of-order response, double click, cancel, retry, timeout, rollback, permission, offline, stale data, status messages and focus.

**Sources:** [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/); [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/); [W3C SCXML](https://www.w3.org/TR/scxml/); [Stately XState documentation](https://stately.ai/docs).

## Logical state transition contract

**Aliases:** state machine, statechart, evento, guarda, transição lógica.

**Decision:** Specify from, event, guard, to, effects, invariants, timers, concurrency and cancellation. State machine/statechart useful for complex workflows; no required library for simple state.

**Limits:** Separate logical change from visual duration; valid states and unreachable transitions must be defined. Model example: selected → submitting → correct/incorrect/error; retry and cancel explicit.

**Acceptance:** Test allowed/disallowed transitions, guards, rapid repeated actions, abort, racing requests, rollback, idempotence and invariant checks; don't pass expected state into runtime.

**Sources:** [W3C SCXML](https://www.w3.org/TR/scxml/); [Stately XState documentation](https://stately.ai/docs); [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/).

## Visual transition and motion choreography

**Aliases:** transição visual, fade, slide, morph, FLIP, view transition, enter exit, stagger.

**Decision:** Choose visual transition by source/destination, spatial relationship, intent and input. Document enter/exit, crossfade, push, reveal, scale, expand/collapse, reorder, shared element, gesture/spring and route transitions.

**Limits:** CSS transitions, CSS animation, WAAPI and View Transition API are techniques, not semantic state. Verify support and fallback. Don't defer focus, result or interaction until animation completion.

**Acceptance:** Capture before/during/after, durations and easing only if measured or source verified; test cancel/reverse, rapid input, reduced motion and keyboard.

**Sources:** [CSS Transitions Level 2](https://www.w3.org/TR/css-transitions-2/); [CSS Animations Level 1](https://www.w3.org/TR/css-animations-1/); [CSS View Transitions Level 1](https://www.w3.org/TR/css-view-transitions-1/); [MDN View Transition API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API); [MDN Web Animations API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API); [Motion documentation](https://motion.dev/docs); [Atlassian Motion](https://atlassian.design/foundations/motion); [Carbon Motion](https://www.carbondesignsystem.com/building-blocks/foundations/motion/overview); [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Iterative design and validation workflow

**Aliases:** fundamentos, processo, sketch, wireframe, protótipo, usability.

**Decision:** User needs → tasks → IA → flows → sketches/wireframes → visual direction → states/motion → tokens → prototype → testing → iteration. Typography, iconography, shape, elevation, copy, density and perceived performance are cross-cutting.

**Limits:** Iterative, not mandatory linear process; design systems and aesthetics do not prove usability.

**Acceptance:** Evidence packet with alternatives, rationale, contraindications, accessibility, source/version, tests and unresolved gaps; #94 prevents synthetic benchmarks claiming real quality.

**Sources:** [GOV.UK Service Manual](https://www.gov.uk/service-manual); [NN/g Principles of Visual Design](https://www.nngroup.com/articles/principles-visual-design/); [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Documented token contrast audit (#103)

Calculated for documented opaque sRGB pairs, not observed runtime compliance: tertiary light/canvas 4.10:1; focus ring light/canvas 2.48:1; ring dark/panel 2.30:1; blue/amber/rose/green chips 4.19/3.61/3.54/4.34:1; violet/slate 6.41/7.35:1. Normal text AA 4.5:1, large text 3:1; non-text contrast 3:1 when applicable. Inspect real colors, adjacency, size, states and exceptions. Do not replace WCAG 2.2 with draft WCAG 3/APCA. Do not change historic tokens without validated revision.

## Transition evidence contract

Record component, from, event, guard, to, side effect, visual feedback, focus, announcement, motion technique, duration/easing (only if verified), cancellation/reversal, fallback, evidence source, test and status. Example (proposed, not observed): unanswered → selected → submitting → correct/incorrect/error; error can retry; cancellation and stale responses must be handled. Semantic result independent from animation. For each transition gather original source and before/during/after evidence when licensed, never infer motion from still images.

## Research backlog

[#103 color](https://github.com/ianmaciel7/exams-app-archive/issues/103), [#104 foundations](https://github.com/ianmaciel7/exams-app-archive/issues/104), [#105 states/transitions](https://github.com/ianmaciel7/exams-app-archive/issues/105), [#102 coverage](https://github.com/ianmaciel7/exams-app-archive/issues/102), [#94 benchmark integrity](https://github.com/ianmaciel7/exams-app-archive/issues/94). Expand primary literature and current 2026 sources; no claim of full extraction or implementation. No restricted media copied.
