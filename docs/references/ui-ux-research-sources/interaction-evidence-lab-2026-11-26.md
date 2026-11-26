# Interaction evidence lab

Original demo using fictional data. [Open HTML](interaction-evidence-lab-2026-11-26.html). [Transition matrix JSON](interaction-evidence-lab-2026-11-26.json).

## Contracts and limits

- Search: request identity plus AbortController, retain results during refresh, separate cancelled/error/empty, retry without stale overwrite. [MDN AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController). The fake local transport uses timers; no real network/offline or API behavior is claimed.
- Tabs: focus can differ from selected panel until manual activation. Modal: native dialog and focus restoration. [APG Tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) and [APG Modal Dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/). Real assistive technology not tested.
- Reader: original ASCII quote and prefix/suffix; ambiguity, missing quote or changed context remain unresolved. [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/). Not full JSON-LD conformance, PDF coordinates, Unicode offset normalization, OCR or persistence.
- Dashboard: native filter and tabular alternative, explicit denominator, missing accuracy distinct from zero. [Vega-Lite selection guidance](https://vega.github.io/vega-lite/docs/selection.html). Demo uses no external chart library and models discrete filters, not interval brushing. No learning efficacy claim.
- Motion: state and focus updates independent of visual effects; instant fallback and reduced-motion stylesheet. No claim of measured animation performance.

Browser reproduction: `python tests/smoke_interaction_evidence_lab.py /tmp/interaction-evidence`. Desktop and mobile Chromium, captured states with fictional content. CI status is authoritative; no test passed until actual run completed.
