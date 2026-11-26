# State and transition example: assessment confirmation

Original demonstration for #104/#105: [interactive HTML](state-transition-example-2026-11-26.html). It demonstrates a fictional question, not a historical product or actual backend. The semantics are independent of optional CSS animation.

| From | Event | Guard | To | Effect / accessibility |
|---|---|---|---|---|
| idle | choose | option exists | selected | selected radio; enable confirm |
| selected/error | confirm | selection exists | pending | freeze answer; announce progress; move focus to available cancel |
| pending | success | matching generation | correct/incorrect | show text result; reset available |
| pending | failure | matching generation | error | announce error; retain answer; enable retry |
| pending | cancel | in flight | selected | invalidate callback; restore confirm focus |
| any | reset | none | idle | cancel pending callback; clear selection; focus first option |

The generation guard rejects stale async completion; repeated submission cannot start another request while pending. Real backend idempotency and persistence would require additional implementation. Reduced motion removes the optional reveal without changing behavior. Native radio controls carry selection semantics. Actual focus behavior, screen readers, pointer/touch, browser forced colors and motion still need manual validation.

## Design decisions

- A single question is a focused task, so one column is appropriate; a full exam shell might require question navigation and a supporting review pane.
- A visible confirmation boundary distinguishes tentative selection from a scored response.
- Loading, failure, cancellation and retry are logical states, not animation variants.
- No fabricated progress percentage; status uses plain text instead of relying on red/green alone.
- Avoid forcing focus for unrelated changes; when a focused action becomes unavailable, move focus to a meaningful remaining control.

Sources: [ARIA APG](https://www.w3.org/WAI/ARIA/apg/), [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [CSS Transitions](https://www.w3.org/TR/css-transitions-1/). See the existing design foundations catalog for broader decision rules. This example is author-created and unvalidated in a live browser; it does not fulfill all acceptance criteria.

## Manual QA checklist (not run)

1. Choose via keyboard, then confirm and attempt a repeated submit.
2. Cancel before completion, wait, and verify selection remains without stale feedback.
3. Simulate failure, retry, and verify only the current response appears.
4. Reset while pending; verify old completion cannot change the idle state.
5. Check focus at each transition, live announcement, narrow layout, forced colors and reduced motion.
