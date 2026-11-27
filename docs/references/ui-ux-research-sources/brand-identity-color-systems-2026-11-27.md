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

## Color-specific UX laws and perceptual effects — supplemental research

### Gestalt similarity, figure-ground and competing cues (color-gestalt-grouping)

Similar hues can group objects; figure-ground and proximity can reinforce or compete. Apply consistent color to equivalent roles and combine labels/shape/spacing; test whether users identify the groups correctly. **Limit:** Perceptual grouping is context-sensitive, not an exclusive color law.

Sources: [Wagemans et al. — A century of Gestalt psychology](https://pubmed.ncbi.nlm.nih.gov/22845751/); [Grouping by proximity or similarity?](https://pubmed.ncbi.nlm.nih.gov/9797920/). Search excerpts/abstracts reviewed 2026-11-27.

### Preattentive features, selective attention and Guided Search 6.0 (color-visual-search)

Hue can guide visual search; top-down goals, bottom-up salience, history, reward and scene context influence priority. Compare time to find and error rates with matched distractors; avoid competing accent colors. **Limit:** Guidance is not a guarantee of instantaneous detection; Guided Search 6.0 is a newer model, not a normative standard.

Sources: [Wolfe — Guided Search 6.0](https://doi.org/10.3758/s13423-020-01859-9); [Wolfe — Visual Search](https://doi.org/10.1146/annurev-vision-091718-015048). Search excerpts/abstracts reviewed 2026-11-27.

### Von Restorff isolation versus salience (color-isolation-memory)

Distinctiveness can improve memory in isolation paradigms; visual salience and memory are separate outcomes. Use a distinct meaningful accent sparingly, measure detection and recall separately. **Limit:** Does not establish conversion or task success.

Sources: [What explains the von Restorff effect?](https://www.sciencedirect.com/science/article/pii/S0749596X17300864); [Wolfe — Guided Search 6.0](https://doi.org/10.3758/s13423-020-01859-9). Search excerpts/abstracts reviewed 2026-11-27.

### Simultaneous color contrast and chromatic adaptation (color-context-adaptation)

Surround changes perceived color; temporal adaptation and contextual induction are distinct contributors. Compare the same token on actual surfaces, themes and ambient viewing conditions; validate separately from numerical WCAG contrast. **Limit:** Mechanisms and magnitude depend on conditions; do not infer a universal correction factor.

Sources: [Basic characteristics of simultaneous color contrast revisited](https://pubmed.ncbi.nlm.nih.gov/22983761/); [An empirical explanation of color contrast](https://pmc.ncbi.nlm.nih.gov/articles/PMC18850/). Search excerpts/abstracts reviewed 2026-11-27.

Weber, Weber–Fechner and Stevens are psychophysical models, not universal design-token spacing or contrast formulas. Existing Laws of UX catalog covers similarity, selective attention and Von Restorff; do not count these as new laws. Feature Integration Theory is a historical model; Guided Search 6.0 supplements earlier models. WCAG 2.2 remains distinct normative accessibility guidance.

## Advanced color perception and cognitive interference — 2026-11-27

### Stroop effect and semantic color interference (color-stroop-interference)

Conflicting word meaning and ink color can interfere with a color-naming task. In product design, avoid conflicting learned status colors and labels; use consistent text, icon and color for success/error. Compare congruent and conflicting alternatives with identical task, contrast and content; measure response time, errors and comprehension.

**Limit:** Experimental color-word effect is not proof of a universal red/green convention or a fixed UI performance penalty; localize and test. Color labels are a design extrapolation.

Sources: [Stroop — Studies of interference in serial verbal reactions](https://doi.org/10.1037/h0054651) — original study, abstract; [MacLeod — Half a century of research on the Stroop effect](https://pubmed.ncbi.nlm.nih.gov/2034749/) — review, abstract; [W3C — Understanding SC 1.4.1 Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color) — official informative guidance.

### Opponent processing and color vision (color-opponent-processing)

Trichromatic cone signals are processed by opponent neural mechanisms; historical red–green and blue–yellow appearance models are not identical to physiological channels. Distinguish opponent encoding from complementary wheel hues, and account for variation in color vision; pair status color with labels/icons and validate with representative users.

**Limit:** Historical Hering/Hurvich–Jameson links between neural opponency and unique hue appearance are challenged; do not treat them as settled or use them as palette-generation rules.

Sources: [Hurvich & Jameson — An opponent-process theory of color vision](https://pubmed.ncbi.nlm.nih.gov/13505974/) — historical study, bibliographic record; [Color appearance and the end of Hering’s Opponent-Colors Theory](https://pubmed.ncbi.nlm.nih.gov/37394292/) — critical review, abstract; [W3C — Understanding SC 1.4.1 Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color) — official informative guidance.

### Color constancy and viewing conditions (color-constancy)

Perceived surface color may remain relatively stable as illumination changes; constancy is imperfect and differs by scene, stimulus and observer. Distinguish it from chromatic adaptation, simultaneous contrast and display color management. For product QA compare identical tokens in actual themes and device/ambient conditions, with calibrated reference where fidelity matters.

**Limit:** Reflective-surface laboratory results do not directly establish color behavior on emissive displays; no claim of guaranteed constancy.

Sources: [Foster — Color constancy](https://pubmed.ncbi.nlm.nih.gov/20849875/) — review, abstract; [Witzel & Gegenfurtner — Color Perception: Objects, Constancy, and Categories](https://pubmed.ncbi.nlm.nih.gov/30004833/) — review, abstract.

### CIECAM16, CAM16, CAT16 and CAM16-UCS (color-appearance-ciecam16)

CIE 248:2022 CIECAM16 supersedes CIECAM02 report CIE 159:2004; uses viewing-condition-dependent transforms of XYZ to appearance correlates and a chromatic adaptation transform. CAM16 is the underlying appearance model, CAT16 the adaptation transform, CAM16-UCS a derived approximately uniform space. Useful for calibrated cross-media appearance matching and color-difference research. Record white point, adapting luminance, background and surround; validate implementation against published reference values before use.

**Limit:** Not a CSS-required space, mandatory design system algorithm or replacement for WCAG. Full CIE report not reviewed; do not implement equations from summary.

Sources: [CIE 248:2022 — CIECAM16](https://www.cie.co.at/publications/cie-2016-colour-appearance-model-colour-management-systems-ciecam16) — official report description, full paid report not read; [Li et al. — CAM16, CAT16, and CAM16-UCS](https://onlinelibrary.wiley.com/doi/full/10.1002/col.22131) — original article excerpt.

### Color discrimination, MacAdam ellipses and Delta E (color-discrimination-delta-e)

MacAdam's psychophysical experiments show that chromaticity discrimination varies across the color diagram under specified viewing conditions. Delta E measures color difference in a stated model: distinguish Euclidean CIELAB ΔE76, CIEDE2000 ΔE00 (ISO/CIE 11664-6:2022), OKLab distance and CAM16-UCS distance. Use one documented metric for brand tolerance or token drift and compare actual rendered adjacent state colors; test recognition without hue alone.

**Limit:** No universal ΔE=1 just-noticeable threshold or mandatory spacing between palette steps. ΔE is not WCAG contrast, and discriminability depends on area, context, observer, luminance and viewing conditions.

Sources: [MacAdam — Visual Sensitivities to Color Differences in Daylight](https://www.wip.osapublishing.org/josa/abstract.cfm?uri=josa-32-5-247) — original article abstract; [ISO/CIE 11664-6:2022 — CIEDE2000](https://www.iso.org/standard/82662.html) — official standard summary; full text not read; [Li et al. — CAM16, CAT16, and CAM16-UCS](https://onlinelibrary.wiley.com/doi/full/10.1002/col.22131) — original article excerpt; [W3C — Understanding SC 1.4.1 Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color) — official informative guidance.

### Feature Congestion, visual clutter and color competition (color-feature-congestion)

Rosenholtz et al. compare Feature Congestion, Subband Entropy and Edge Density; color variability contributes to clutter in their experiments. Reserve accent for meaningful priorities; separate category/status/selection encoding; use neutral secondary surfaces and redundant labels. Compare matched task screens with varied color complexity, measure search time, errors and missed states; preserve information and avoid hiding essential cues.

**Limit:** No universal maximum hue count, saturation threshold or guarantee of task performance. Feature Congestion is a research measure, not an accessibility criterion.

Sources: [Rosenholtz, Li & Nakano — Measuring visual clutter](https://pubmed.ncbi.nlm.nih.gov/18217832/) — original article abstract; [MIT Persci — Visual Clutter](https://persci.mit.edu/research/clutter/) — research project description.

Evidence scope: public abstracts, bibliographic records, article excerpts and official summaries; not a full standard or product audit. No new experiments conducted.
