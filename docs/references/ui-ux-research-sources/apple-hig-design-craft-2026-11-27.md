# Apple HIG, material hierarchy and interaction craft — 2026-11-27

## Scope and evidence

This is an original, focused design synthesis, not an official Apple skill or a complete ingestion of every HIG page. Primary documentary sources below were consulted on 2026-11-27; community repositories were reviewed for selected documented patterns. No native implementation, external script execution, user testing, pixel measurements, or verified browser test of an Apple implementation occurred. Do not claim native Liquid Glass or universal Apple-quality UI from these notes.

## Transferable decisions and checks

| Decision | Native reference | Web adaptation and acceptance test |
| --- | --- | --- |
| Content and controls have different jobs | Apple materials and WWDC25 design system | Reading surface remains opaque and quiet. Only a functional overlay may justify translucent material; evaluate composited text/non-text contrast, scroll underlay, opaque fallback and cost. |
| Hierarchy, harmony and adaptability | HIG principles, layout and typography | Establish semantic type and spacing roles; align content optically; reflow by available width; test wrapping, zoom and enlarged text. Preserve order, focus and task coverage. |
| Geometry relates to containment | WWDC25 shape/concentricity discussion | Deliberate nested corners only in rounded containment; do not impose one radius across controls, overlays and flush shell seams. Document shape and elevation tokens. |
| Fluidity is interaction behavior | WWDC25 material adaptivity and native control guidance; independent skill routing | Test interruptible/reversible transitions, cancellation, direct manipulation, state preservation, reduced motion and no delayed feedback. No universal spring/duration. |
| Feedback belongs near the action | Independent skill feedback gate; official HIG principles | Distinguish chosen, pending, evaluated/locked and technical error; inline status and actionable retry preserve context. Interrupt only when justified. |
| Native conventions are platform-specific | HIG layout, typography, adoption | Do not mandate Apple colors, point sizes, SF fonts or symbols on web. Use semantic HTML and applicable accessibility requirements, legal icon assets and verified theme tokens. |

## How to review a design system

Before exploration: retrieve product brief and revision, actual representative captures, approved layout/states and prior rejected directions. Require a material map, shape hierarchy, typographic roles, spacing/density scale, component/state aliases, motion and feedback matrix. For full-system alternatives, vary these foundations while keeping the same task/data; do not rename hue swaps as new systems. Review each actual render in both themes at independent readable sizes and mobile/desktop widths; separate token contrast from rendered measurements and runtime/assistive-technology tests. Never infer success from mockup screenshots. Reject invented features, excessive nested chrome, ornamental translucency and unrelated metrics. If a host cannot render a runnable demo, report the limitation and use verified captures instead.

For the current exam-reading task, a proposed application is a quiet opaque question surface, unobtrusive competition navigation, stable Answer/feedback area, and a functional mobile drawer. Preserve the approved product requirements and fidelity stage. This is a design hypothesis, not a selected identity or a change to the application.

## Source register

Official:
- https://developer.apple.com/design/human-interface-guidelines/design-principles/
- https://developer.apple.com/design/human-interface-guidelines/layout
- https://developer.apple.com/design/human-interface-guidelines/typography
- https://developer.apple.com/design/human-interface-guidelines/materials
- https://developer.apple.com/videos/play/wwdc2025/356/
- https://developer.apple.com/videos/play/wwdc2025/219/
- https://developer.apple.com/documentation/TechnologyOverviews/adopting-liquid-glass

Independent, supplementary:
- https://github.com/dickwu/apple-design-skill — repository overview: cross-platform review and targeted reference loading.
- https://github.com/efey1ldirim/apple-skill — selected SKILL.md and references/INDEX.md inspected: explicit color, typography, layout, materials and feedback gates; web adaptation and probe routing. Its exact native-like tokens, all-or-nothing lint rules and target values are not universal design standards.
- https://github.com/BDEfvox/apple-design-skill — repository overview: HIG and WWDC reference discovery; claims not independently validated end-to-end.

New shared skill: [apple-hig-design-craft](../../../plugins/exams-archive-native/skills/apple-hig-design-craft/SKILL.md). Reuse existing design foundations, design-system practice and anti-slop catalogs rather than duplicating them.
