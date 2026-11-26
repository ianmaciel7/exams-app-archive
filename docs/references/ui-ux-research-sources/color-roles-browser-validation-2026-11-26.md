# Color roles and rendered validation — 2026-11-26

Scope: original generated demonstration of the archive token contract, not a screenshot or compliance claim about the active application.

| Decision | Use | Avoid | Test |
|---|---|---|---|
| Primitive/reference colors | Maintain stable values and tonal scales | Direct component use without semantic roles | Inspect gamut and resolve aliases |
| Semantic role | Separate surfaces, primary/secondary/tertiary text, focus, statuses, and identity | Reusing category color as a success signal | Verify text/indicator contrast and text labels |
| Component state | Map hover, press, selection, disabled, invalid and focus separately | Distinguishing states by hue alone; disabling semantic feedback | Keyboard, pointer and screen-reader state |
| Transparency | Composite against the actual surface before evaluating contrast | Testing the alpha color independently of its backdrop | Test browser-computed opaque result on each permitted surface |
| Chart encoding | Categorical for groups, sequential for magnitude, diverging around meaningful midpoint | Artificial ordering of categorical colors; rainbow by default | Legend, non-color alternative and data table |
| Dark and forced colors | Preserve semantic meaning and focus using system colors where appropriate | Inverting arbitrary colors or overriding system palette | Real browser forced-colors and keyboard tests |
| Aesthetic direction | Neutral, expressive or mixed according to context and brand | Universal 60/30/10 rule or claims that hue determines emotion | Compare task performance and preferences; record evidence |

The thresholds for ordinary text and required non-text indicators are from [WCAG 2.2 Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) and [Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html); [Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) requires a non-color cue where color conveys information. Applicability, exceptions and actual adjacency still matter. CSS color mixing follows [CSS Color 5](https://www.w3.org/TR/css-color-5/), not a blanket browser support guarantee. The initial broader references remain in the design-foundations catalog.

## Reproduce

- `python scripts/check_token_contrast.py`: canonical opaque pairs, linear sRGB computation without rounding for acceptance.
- `python scripts/render_token_demo.py /tmp/color-demo.html`: standalone reference page generated from actual token spec; no external assets.
- `python tests/smoke_token_colors.py /tmp/token-evidence`: Chromium light/dark, actual computed color conversion, composited overlay, focus ring, identity chips, deliberate mutation, forced-colors keyboard selection and mobile reflow. CI archives the HTML, screenshots and JSON report, including individual ratios.

Browser colors use 8-bit sRGB samples; source-token checks retain unquantized calculations. A passed fixture is not an accessibility audit of the whole app. P3 hardware, gradients/images, color-vision simulation, manual assistive-technology testing and other browser engines remain separate requirements. The chart palette examples and product-level state coverage still need separate empirical testing.
