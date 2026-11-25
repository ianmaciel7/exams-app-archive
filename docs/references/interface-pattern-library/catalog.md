# Interface pattern library — expanded research

Research date: 2026-11-25. General-purpose UI/UX, independent of any product. This is an additive library, not a universal taxonomy or a ranking of adoption in 2026. Includes long-established patterns and recent platform capabilities. Each guardrail is an applied design recommendation, not a claim of measured benefit.

## visual

| Pattern | Classification | Purpose | Guardrail | Sources |
|---|---|---|---|---|
| Liquid Glass | Platform visual language | A translucent, dynamic functional layer separates controls from content. | Use sparingly for toolbars or navigation; provide opaque fallback and test contrast. | [apple](https://developer.apple.com/design/human-interface-guidelines/materials) |
| Material 3 Expressive | Platform design language | Shape, scale, color, containment and motion reinforce hierarchy. | Use meaningful emphasis, not arbitrary saturated colors. | [material](https://design.google/library/expressive-material-design-google-research), [wear](https://developer.android.com/design/ui/wear/guides/get-started/design-language) |
| Progressive blur | Visual technique | Gradually reduce detail behind a control or edge rather than blur every surface. | Test readable content and contrast; opaque fallback. | [waves](https://www.wavespace.agency/blog/ui-design-trends), [apple](https://developer.apple.com/design/human-interface-guidelines/materials) |
| Content-first / calm UI | Design principle | Reduce permanent chrome and show secondary actions on demand. | Keep frequent actions discoverable; do not hide critical status. | [noise](https://developer.chrome.com/docs/modern-web-guidance/guides/user-experience/content-first-noise-reduction), [envato](https://elements.envato.com/learn/ux-ui-design-trends) |
| Variable typography | Visual technique | Adjust type axes or styles for hierarchy and expressive emphasis. | Maintain readability, zoom and predictable layout. | [wear](https://developer.android.com/design/ui/wear/guides/get-started/design-language), [material](https://design.google/library/expressive-material-design-google-research) |
| Semantic tokens and modes | Design system architecture | Map design intent to tokens that change across themes or contexts. | Avoid per-component hardcoded values; test contrast per mode. | [tokens](https://www.figma.com/resource-library/design-tokens/), [figmodes](https://help.figma.com/hc/en-us/articles/15343816063383-Modes-for-variables) |

## navigation

| Pattern | Classification | Purpose | Guardrail | Sources |
|---|---|---|---|---|
| Anchored popover | Interaction pattern | A transient nonmodal surface opens adjacent to its invoker. | Use fallback positioning and appropriate keyboard/focus semantics. | [popover](https://developer.chrome.com/docs/modern-web-guidance/guides/ui-atoms/viewport-aware-dropdowns), [modern](https://developer.chrome.com/docs/modern-web-guidance/guides) |
| Responsive overflow toolbar | Interaction pattern | Move secondary commands into an overflow control as space shrinks. | Preserve accessible command names and shortcuts; don't hide primary tasks. | [modern](https://developer.chrome.com/docs/modern-web-guidance/guides), [noise](https://developer.chrome.com/docs/modern-web-guidance/guides/user-experience/content-first-noise-reduction) |
| Origin-aware transitions | Motion/navigation pattern | Open from a visible source to communicate where the destination came from. | Do not delay navigation or use motion as the sole cue. | [natural](https://developer.chrome.com/docs/modern-web-guidance/guides/user-experience/natural-interactions), [motion](https://motion.dev/docs/react-layout-animations) |
| Contextual hint / hover card | Interaction pattern | Expose explanatory preview linked to an object without leaving the page. | Also support focus or explicit activation; dismiss without trapping input. | [modern](https://developer.chrome.com/docs/modern-web-guidance/guides), [apg](https://www.w3.org/WAI/ARIA/apg/example-index/) |
| State-preserving reparenting | Implementation capability | Move a component between surfaces while preserving interaction state when supported. | Check browser support; test focused inputs, scroll and media. | [modern](https://developer.chrome.com/docs/modern-web-guidance/guides) |
| Gesture-enabled bottom sheet | Interaction pattern | A surface slides up from the bottom; optionally drag to resize or dismiss. | Provide explicit close, focus management and keyboard operation. | [sheet](https://motion.dev/examples/react-sheet-modal), [apg](https://www.w3.org/WAI/ARIA/apg/example-index/) |

## editing

| Pattern | Classification | Purpose | Guardrail | Sources |
|---|---|---|---|---|
| Inline editing | Interaction pattern | Switch a displayed value to an editor in the same place. | Save/cancel and validation; preserve focus and handle conflicts. | [inline](https://atlassian.design/guidelines/product/patterns/inline-edit) |
| Expandable row | Interaction pattern | Reveal related details directly below an item. | Use explicit expand control and accessible expanded state. | [table](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines) |
| Contextual batch actions | Interaction pattern | Reveal relevant actions when one or more items are selected. | Show selection count and clear selection; confirm risky operations. | [table](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines) |
| Instant filtering | Interaction pattern | Apply each filter immediately while the user explores. | Keep results stable and announce change without overwhelming screen readers. | [filters](https://www.carbondesignsystem.com/building-blocks/core/patterns/filtering) |
| Apply-to-filter | Interaction pattern | Stage filter choices and apply them together. | Show unsaved changes and active filters; provide reset. | [filters](https://www.carbondesignsystem.com/building-blocks/core/patterns/filtering) |
| Editable combobox | Widget pattern | Text entry and selectable suggestions share one control. | Follow APG focus and keyboard contract; don't use arbitrary menu roles. | [apg](https://www.w3.org/WAI/ARIA/apg/example-index/) |
| Treegrid | Widget pattern | Tabular properties combined with expandable hierarchy. | Use only when hierarchy and columns are both essential; test keyboard traversal. | [apg](https://www.w3.org/WAI/ARIA/apg/example-index/) |
| Actionable empty state | Interaction pattern | Differentiate no items, no matches and unavailable data. | Offer relevant recovery, reset or creation action; no fake data. | [empty](https://atlassian.design/content/designing-messages/empty-state/), [carbon](https://www.carbondesignsystem.com/building-blocks/core/patterns/overview) |
| Skeleton loading | Feedback pattern | Reserve expected content geometry while data loads. | Use busy/status semantics and timeout; static alternative. | [table](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines) |

## motion

| Pattern | Classification | Purpose | Guardrail | Sources |
|---|---|---|---|---|
| Shared-element transition | Motion pattern | Preserve object identity across layouts with coordinated geometry. | Use stable identity; preserve focus independently of visual snapshots. | [motion](https://motion.dev/docs/react-layout-animations), [chrome](https://developer.chrome.com/blog/new-in-web-ui-io26) |
| Element-scoped view transition | Implementation capability | Limit snapshot transitions to a region instead of the entire page. | Use fallback; browser support is not universally verified. | [chrome](https://developer.chrome.com/blog/new-in-web-ui-io26) |
| Physics-based spring | Motion technique | Motion responds to stiffness, damping and interruption. | Avoid excess oscillation; match semantic urgency and reduced-motion settings. | [motion](https://motion.dev/docs/react-layout-animations), [motionex](https://motion.dev/Examples) |
| Shape morphing | Motion technique | Interpolate compatible geometry to communicate transformation. | Maintain recognizable identity; avoid motion-only status signals. | [wear](https://developer.android.com/design/ui/wear/guides/get-started/design-language), [grok](https://x.ai/news/designing-grok-bot) |
| Scroll-linked animation | Motion technique | Animation progress follows scroll or visibility rather than elapsed time. | No essential content hidden by animation; reduced motion and support fallback. | [scroll](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations), [chrome](https://developer.chrome.com/blog/new-in-web-ui-io26) |
| Scroll-triggered animation | Motion technique | A visibility/scroll threshold triggers a time-based sequence. | Distinguish from scroll-linked motion; check implementation support. | [chrome](https://developer.chrome.com/blog/new-in-web-ui-io26) |
| Staggered reveal | Motion technique | Offset the entrance of related elements to establish sequence. | Keep total delay small; avoid delaying access to controls. | [sheet](https://motion.dev/examples/react-sheet-modal), [motionex](https://motion.dev/Examples) |
| Gesture-driven motion | Motion technique | Coordinate drag movement and spring return or settle. | Add keyboard and non-drag pointer alternative; support cancel. | [sheet](https://motion.dev/examples/react-sheet-modal), [natural](https://developer.chrome.com/docs/modern-web-guidance/guides/user-experience/natural-interactions) |
| Discrete entry/exit transitions | Implementation capability | Animate entering and leaving top-layer or display states with suitable CSS. | Check @starting-style and transition-behavior support and fallback. | [chrome](https://developer.chrome.com/blog/new-in-web-ui-io26), [modern](https://developer.chrome.com/docs/modern-web-guidance/guides) |
| Stateful animated mascot | Feedback pattern | Avatar communicates lifecycle through expression, pose and text. | Don't infer completion from animation; pause and reduced motion. | [grok](https://x.ai/news/designing-grok-bot) |

## ai

| Pattern | Classification | Purpose | Guardrail | Sources |
|---|---|---|---|---|
| Agent entry point | Interaction pattern | Expose an agent in the context of a task, capability or workspace. | Clearly communicate scope and limitations. | [ms](https://learn.microsoft.com/en-us/agents/design-guidelines/overview), [pair](https://pair.withgoogle.com/guidebook-v2/patterns) |
| Human approval gate | Interaction pattern | Pause before a consequential action and show an understandable request. | Show scope and consequence; allow reject or edit; never treat silence as consent. | [msapproval](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/agent-design-canvas-framework), [agentcat](https://www.aidesign.guide/agentic-ux-patterns) |
| Progressive AI explanation | Interaction pattern | Provide concise explanation and deeper evidence on demand. | Separate verified sources from model estimates; don't fabricate rationale. | [pair](https://pair.withgoogle.com/guidebook-v2/patterns), [paircases](https://pair.withgoogle.com/guidebook-v2/case-studies) |
| Calibrated uncertainty display | Interaction pattern | Communicate limitations or uncertainty when it helps the user decide. | Avoid arbitrary percentages or unwarranted precision. | [pair](https://pair.withgoogle.com/guidebook-v2/patterns) |
| AI feedback and correction | Interaction pattern | Users can correct, reject or refine an output. | Explain what feedback affects; make correction actionable. | [pair](https://pair.withgoogle.com/guidebook-v2/patterns) |
| Graceful AI failure / handoff | Interaction pattern | Return control when automation cannot complete the task. | Show what failed and what remains; preserve user work. | [paircases](https://pair.withgoogle.com/guidebook-v2/case-studies), [ms](https://learn.microsoft.com/en-us/agents/design-guidelines/overview) |
| Declarative generative UI | Architecture pattern | Agent emits structured UI intent for a trusted host component catalog. | Validate schema; restrict actions and keep host permissions authoritative. | [a2ui](https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/) |
| Scoped agent permissions | Interaction pattern | Grant access to a specific action or resource instead of unrestricted authority. | Make duration and revocation clear; reapprove scope changes. | [msapproval](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/agent-design-canvas-framework), [agentcat](https://www.aidesign.guide/agentic-ux-patterns) |
| Streaming response and activity | Feedback pattern | Show incremental results and meaningful activity as work progresses. | Don't invent internal thought or progress; support interruption and recovery. | [ms](https://learn.microsoft.com/en-us/agents/design-guidelines/overview), [agentcat](https://www.aidesign.guide/agentic-ux-patterns) |

## data

| Pattern | Classification | Purpose | Guardrail | Sources |
|---|---|---|---|---|
| Brushing and linking | Data interaction pattern | Selecting a range or marks in one view highlights related items in another. | Make linked effects visible and reversible; provide non-drag alternatives. | [dash](https://dashboarddesignpatterns.github.io/patterns.html) |
| Cross-filtering | Data interaction pattern | Selection in one chart filters another representation. | Show active filters and reset; distinguish filtering from highlighting. | [dash](https://dashboarddesignpatterns.github.io/patterns.html), [filters](https://www.carbondesignsystem.com/building-blocks/core/patterns/filtering) |
| Details on demand | Data interaction pattern | Reveal exact values or record-level details when requested. | Support keyboard/touch and a structured data alternative. | [dash](https://dashboarddesignpatterns.github.io/patterns.html) |
| Overview + focus | Data interaction pattern | Show global context while enabling a focused subset or detail. | Preserve navigation back to overview and current context. | [dash](https://dashboarddesignpatterns.github.io/patterns.html) |
| Small multiples | Data composition pattern | Repeat the same chart design for comparable categories. | Use comparable scales and labels; avoid excessive panels. | [dash](https://dashboarddesignpatterns.github.io/patterns.html) |
| Multi-page dashboard | Data composition pattern | Partition questions into coordinated dashboard surfaces. | Avoid duplicating inconsistent filters and preserve contextual state. | [dash](https://dashboarddesignpatterns.github.io/patterns.html) |
| Dashboard density management | Data composition principle | Choose information amount and grouping for the user's decision. | Avoid sacrificing important context for empty space; test task time. | [dash](https://dashboarddesignpatterns.github.io/patterns.html), [noise](https://developer.chrome.com/docs/modern-web-guidance/guides/user-experience/content-first-noise-reduction) |

