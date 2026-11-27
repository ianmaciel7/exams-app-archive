# Brand identity and color systems — 2026-11-27

Scope: original synthesis of public search excerpts, publisher tables of contents/abstracts and official documentation. Not full books, not a product audit. Complements existing design-foundations and color-roles-browser-validation guides. No copyrighted plates copied.

## Brand strategy and identity (brand-strategy-identity)

Define audience, problem, competitive alternatives, positioning, promise, personality and brand architecture; use research and brief before visual explorations. Separate brand voice, logo, typography, imagery, color and motion; build usage rules for product, marketing and print. Compare 2–3 directions against same brief, not arbitrary hue associations. Test recognition, differentiation and task performance; obtain owner approval.

Sources: [wheeler](https://www.wiley.com/en-sg/designing-brand-identity-a-comprehensive-guide-to-the-world-of-brands-and-branding-6th-edition-p-9781119984818), [ibm-color](https://www.ibm.com/design/language/color/). **Limit:** Method synthesis; no universal number of alternatives.

## Color theory and harmony (color-harmony)

Hue, lightness/value, chroma and saturation are distinct; tint/shade/tone are traditional mixing concepts, not exact CSS operations. Explore monochromatic, analogous, complementary, split-complementary, triadic, tetradic and square harmonies as hypotheses. Wheel angles depend on chosen color model. Vary hierarchy and surface area; compare identical foreground colors on differing surrounds (simultaneous contrast).

Sources: [adobe-harmony](https://www.adobe.com/uk/creativecloud/design/discover/color-palette.html), [albers](https://yalebooks.yale.edu/book/9780300179354/interaction-of-color/). **Limit:** Educational methods, not accessibility guarantees or causal laws.

## Color perception and psychology (color-psychology)

Color can influence affect, cognition and behavior; context, culture, task, prior learning and stimulus properties moderate effects. Do not claim blue always means trust or red always means danger. Test matched alternatives with representative users, neutral wording, counterbalanced order, controlled contrast and recorded uncertainty.

Sources: [elliot-maier](https://pubmed.ncbi.nlm.nih.gov/23808916/), [albers](https://yalebooks.yale.edu/book/9780300179354/interaction-of-color/). **Limit:** Review abstract explicitly notes limits to generalization; no full-paper audit.

## Color science and reproduction (color-science)

RGB is additive; CMYK device/print-dependent subtractive process. HSL/HSV are useful selection models, not perceptually uniform. CIE XYZ/Lab/LCH and Oklab/OKLCH describe color differently; OKLCH L is perceptual lightness, C chroma, H hue, not WCAG luminance. sRGB and Display P3 have different gamuts. Specify target space, white point/profile where relevant, gamut-map and verify output; for print use actual ICC profiles and proof, not universal RGB-to-CMYK conversion. CSS Color 4/5 maturity and browser support are separate.

Sources: [css4-2026](https://www.w3.org/TR/2026/CRD-css-color-4-20261029/), [css5-2026](https://www.w3.org/TR/2026/WD-css-color-5-20261116/), [icc](https://www.color.org/icc_specs2/), [icc-cie](https://registry.color.org/colorimetry-data/). **Limit:** Draft specifications are not guarantees of browser behavior.

## Color system engineering (color-system-engineering)

Choose seed, neutrals and distinct semantic families; derive ramps with target gamut, role contrast and usable chroma. Map primitive → semantic → component/state tokens; retain on-color pairs. Brand logo may differ from action accent. Material tonal palettes, Radix 12-step role scales and IBM 12 grades are distinct conventions, not interchangeable. Use semantic roles for surface/text/border/action/status/selection/focus/data; specify default/hover/pressed/disabled/selected/invalid and theme mappings. Check alpha against actual backdrop, gradients at worst case, and forced colors.

Sources: [material-tonal](https://github.com/material-foundation/material-color-utilities/blob/main/concepts/dynamic_color_scheme.md), [radix-scale](https://github.com/radix-ui/website/blob/main/data/colors/docs/palette-composition/understanding-the-scale.mdx), [ibm-color](https://www.ibm.com/design/language/color/), [carbon-color](https://www.carbondesignsystem.com/building-blocks/foundations/color/overview), [css4-2026](https://www.w3.org/TR/2026/CRD-css-color-4-20261029/). **Limit:** No mandatory ramp count or 60/30/10 ratio.

## Accessibility and evaluation (color-accessibility-evaluation)

WCAG 2.2 AA normal text 4.5:1; large text 3:1; applicable non-text cues 3:1 against adjacent colors. Evaluate exceptions and exact pairs without rounding up. Redundant labels/icons/patterns; test color-vision simulation, keyboard focus, forced colors, both themes, screenshots and assistive technology. Categorical/sequential/diverging encodings by data semantics. Contrast automation is necessary but not sufficient.

Sources: [wcag](https://www.w3.org/TR/WCAG22/), [wcag-nontext](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html), [carbon-color](https://www.carbondesignsystem.com/building-blocks/foundations/color/overview). **Limit:** APCA is not a WCAG 2.2 substitute; actual product audit still required.

## Governance and handoff (color-governance)

Record role, value, color space, allowed pairs, forbidden uses, theme overrides, contrast tests, owner and source. Review changes with versioned token diff, alias resolution, visual regression and migration plan; maintain brand guidelines separate from product tokens and cross-reference them. Tools: Adobe palette guidance for exploration; browser rendered fixtures and existing archive test suite for verification. Track unresolved issues and compare same tasks before/after.

Sources: [wheeler](https://www.wiley.com/en-sg/designing-brand-identity-a-comprehensive-guide-to-the-world-of-brands-and-branding-6th-edition-p-9781119984818), [carbon-color](https://www.carbondesignsystem.com/building-blocks/foundations/color/overview), [css4-2026](https://www.w3.org/TR/2026/CRD-css-color-4-20261029/), [wcag](https://www.w3.org/TR/WCAG22/). **Limit:** Proposed operational workflow; no claim that tests were run here.

## Source register

- wheeler: [Wiley — Designing Brand Identity, 6th ed.](https://www.wiley.com/en-sg/designing-brand-identity-a-comprehensive-guide-to-the-world-of-brands-and-branding-6th-edition-p-9781119984818) — publisher contents; book not read; reviewed 2026-11-27.
- albers: [Yale — Interaction of Color](https://yalebooks.yale.edu/book/9780300179354/interaction-of-color/) — publisher description; book not read; reviewed 2026-11-27.
- elliot-maier: [Elliot & Maier 2014, Annual Review of Psychology](https://pubmed.ncbi.nlm.nih.gov/23808916/) — peer-reviewed review abstract; reviewed 2026-11-27.
- adobe-harmony: [Adobe — Colour Palette Guide](https://www.adobe.com/uk/creativecloud/design/discover/color-palette.html) — educational guidance; reviewed 2026-11-27.
- css4-2026: [W3C CSS Color 4, 2026-10-29 CRD](https://www.w3.org/TR/2026/CRD-css-color-4-20261029/) — candidate recommendation draft; reviewed 2026-11-27.
- css5-2026: [W3C CSS Color 5, 2026-11-16](https://www.w3.org/TR/2026/WD-css-color-5-20261116/) — working draft; reviewed 2026-11-27.
- icc: [ICC specifications](https://www.color.org/icc_specs2/) — official profile specification summary; reviewed 2026-11-27.
- icc-cie: [ICC/CIE colorimetry data](https://registry.color.org/colorimetry-data/) — official data reference; reviewed 2026-11-27.
- material-tonal: [Material color utilities — dynamic color scheme](https://github.com/material-foundation/material-color-utilities/blob/main/concepts/dynamic_color_scheme.md) — official library documentation; reviewed 2026-11-27.
- radix-scale: [Radix Colors — Understanding the scale](https://github.com/radix-ui/website/blob/main/data/colors/docs/palette-composition/understanding-the-scale.mdx) — official library documentation; reviewed 2026-11-27.
- ibm-color: [IBM Design Language — Color](https://www.ibm.com/design/language/color/) — official brand guidance; reviewed 2026-11-27.
- carbon-color: [Carbon — Color](https://www.carbondesignsystem.com/building-blocks/foundations/color/overview) — official product guidance; reviewed 2026-11-27.
- wcag: [WCAG 2.2](https://www.w3.org/TR/WCAG22/) — normative recommendation, related excerpt reviewed; reviewed 2026-11-27.
- wcag-nontext: [W3C Understanding Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) — informative guidance; reviewed 2026-11-27.

## Related canonical knowledge

- [Design foundations](design-foundations-and-state-transitions-2026-11-25.md)
- [Rendered color validation](color-roles-browser-validation-2026-11-26.md)
