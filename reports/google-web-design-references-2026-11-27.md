# Google web design references — 2026-11-27

Public web research; discovery only, not a screenshot or DOM audit. No private data or copied media. The visual descriptors below are qualitative study directions rather than measured design tokens.

| Public reference | Study direction |
|---|---|
| https://antigravity.google/ | Technical product identity |
| https://deepmind.google/ | Editorial hierarchy |
| https://labs.google/ | Experimental product discovery |
| https://design.google/ | Editorial design and typography |
| https://gemini.google/about/ | Neural Expressive |
| https://stitch.google.com/ | Design canvas and workspace |
| https://labs.google/fx/tools/flow | Creative workspace |
| https://store.google.com/ | Product presentation |
| https://aistudio.google.com/ | Technical workspace |
| https://m3.material.io/ | Material component guidance |
| https://fonts.google.com/ | Typography |
| https://ai.google/ | Institutional AI presentation |

## Documented evidence
- Google Design reports Fast Company's 2026 Design Company of the Year recognition: https://design.google/library/design-company-of-year-2026
- Google announced Neural Expressive at I/O 2026, including typography, dynamic color and motion: https://blog.google/innovation-and-ai/products/gemini-app/next-evolution-gemini-app/
- Stitch's AI-native design canvas announcement, 2026-03-18: https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-ai-ui-design/
- Google Store 2026 Webby recognition: https://winners.webbyawards.com/2026/websites-and-mobile-sites/features-design/best-user-interface/378591/google-store
- Google Sans Flex background: https://design.google/library/google-sans-flex-font

Next validation: capture dated screenshots from official sites, inspect computed tokens and interaction states, distinguish marketing pages from product interfaces. No exact palette, typography or geometry measurements were performed.

## Follow-up: validated design mechanisms and workspace patterns (2026-11-27)

| Source | Documented mechanism | Transferable recommendation and validation |
|---|---|---|
| [Material expressive research](https://design.google/library/expressive-material-design-google-research) | Google reports 46 studies, over 18,000 participants; key elements spotted up to four times faster in tested interfaces. Color, shape, size, motion and grouping direct attention. Unfamiliar playlist layout and label removal reduced usability. | Reserve stronger emphasis for task-critical controls. Compare fixation/task time, errors and accessibility against a conventional baseline. Do not generalize the reported improvement. |
| [M3 award](https://ux-design-awards.com/winners/2026-1-material-3-expressive) | 2026 Spring jury recognition; not independent proof of every implementation. | Separate award evidence, task fit and usability results. |
| [Google Sans Flex](https://design.google/library/google-sans-flex-font) | Six axes: weight, width, optical size, slant, grade, roundedness. Google Sans and Flex open-sourced in 2025. | Set typography by role and reading context; test long text, zoom and languages. Verify font license and axes before implementation. |
| [Neural Expressive](https://blog.google/innovation-and-ai/products/gemini-app/next-evolution-gemini-app/) | Announced May 19, 2026: dynamic visuals, motion, typography, haptics, continuity between text and voice, generative response formats. | Make state changes comprehensible, preserve reduced-motion and static fallbacks. Not a universal public token system. |
| [Stitch live design](https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-updates/) | May 19, 2026: canvas streams work, allows steering mid-iteration, exports to development. | Put work objects at center, support revision and visible progress, preserve manual control. |
| [AI Studio development](https://blog.google/innovation-and-ai/technology/developers-tools/google-io-2026-developer-highlights/) | Project context transfer to Antigravity. | Preserve context on tool handoff; verify editable output and recovery. |
| [Flow workspace](https://blog.google/innovation-and-ai/models-and-research/google-labs/flow-updates-february-2026/) | Feb 25, 2026: unified generation/editing/animation, searchable sortable filtered asset grid and collections. | Use task-appropriate views over canonical objects. Verify findability and bulk actions. |
| [Pomelli agent](https://blog.google/innovation-and-ai/models-and-research/google-labs/pomelli-agentic-capabilities/) | May 19, 2026: Business DNA informs on-brand outputs. | Capture brand identity and semantic constraints before generation, rather than selecting random trendy palettes. |
| [NotebookLM research](https://blog.google/innovation-and-ai/products/notebooklm/better-research-notebooklm/) | June 8, 2026: outputs grounded in sources accessible from Studio. | Preserve source linkage and distinguish source, generated object and user note. |
| [Gemini Notebook study tools](https://blog.google/innovation-and-ai/products/gemini-notebook/new-study-tools-september-2026/) | Sept 15, 2026: interactive learning overviews combine study formats. | Use task-specific study modes and preserve user progress. |
| [Interactive sites](https://blog.google/innovation-and-ai/products/gemini-notebook/interactive-sites/) | Nov 16, 2026: notebook sources can become interactive sites. | Separate artifact preview, source provenance, persistence, sharing and editing. |

## Visual evidence pointers
- Official Stitch canvas preview: https://labs.google/assets/images/tools/stitch-poster.webp (Google Labs; publication date not verified).
- Official Antigravity Agent Manager tutorial screenshot: https://codelabs.developers.google.com/static/getting-started-google-antigravity/img/d5ae91fc746e1bba_1440.png (tutorial, not verified current 2.0 interface).
- Official Stitch design-to-code tutorial screenshot: https://codelabs.developers.google.com/static/design-to-code-with-antigravity-stitch/img/ce283054cd30c7ab_2880.png (tutorial example; source last updated 2026-07-22).
- AI Studio tutorial screenshot: https://codelabs.developers.google.com/static/gemini-for-developers/img/48fadc9d3d5f9500.png (version/date not verified).
- M3 award component illustration: https://ux-design-awards.com/media/pages/winners/2026-1-material-3-expressive/500c7cadd7-1767723338/127_bild2.jpg (award showcase, not live UI).

## Design review protocol
Distinguish product workspace from marketing and editorial references. For each candidate record semantic color roles and contrast, type roles and reading measure, density, surface/edge/elevation, shape by component/state, spacing, icon labels, movement, focus, loading, empty/error states, mobile reflow and accessibility. Extract exact CSS only from verified versioned browser/DOM evidence. Avoid copying branding or treating awards as a mandate. Validate against representative tasks. This follow-up is documentary research and selected public visual pointers, not an exhaustive inventory, live capture, token extraction, implementation or user test.
