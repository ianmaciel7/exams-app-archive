# AI-native product design and Beyond Chat — 2026-11-25

## Scope and terminology
AI-native products center AI capabilities; AI-first describes product priority, vertical AI describes specialization by industry/domain, task-specific AI describes a targeted activity, embedded AI describes integration into conventional workflows, and agentic UX describes autonomous execution under human supervision. These terms overlap; they are not mutually exclusive standards. General-purpose chat is one interaction model, not a required architecture.

## Evidence boundary
Original synthesis of prior public catalog and guide review; not a complete extraction of every example, not a market ranking, not user testing, not a claim of official taxonomy. 163 cross-indexed labels across 10 families; overlaps retained in existing catalogs. No third-party screenshots, videos or code copied. Revalidate exact source counts, redirects, versions and individual patterns before implementation. Sources are link-only. Distinguish observed pattern, recommendation, research guidance and normative accessibility requirements.

## Interaction lifecycle and decision criteria
Discover capabilities → instruct with editable context and parameters → observe real progress and results → refine with reversible controls → adapt with transparent, editable preferences. Use task, object, frequency, modality, risk, reversibility and autonomy to choose the surface. Beyond Chat DOPE: directability, observability, predictability, explainability. Keep human control throughout. A deterministic action should usually remain a direct control rather than a mandatory prompt.

## Architecture and layout

**Cross-indexed labels:** Embedded AI; Inline AI; Contextual Overlay; AI Sidebar; Split View; AI Workspace; Command Palette; AI Studio; Spatial Canvas; Node Workflow; AI Dashboard; Agent Control Center; Conversational UI; Search-first UI; Copilot Layout; AI Document Editor; Block-based Editor; Multi-pane Workspace; Comparison View; Generative Gallery; Wizard; Property Inspector; Agent Timeline; Multi-agent Workspace; Adaptive Interface; Multimodal Workspace; Ambient AI.

**Design rationale:** Choose surface by task, object, risk and input; prefer conventional direct controls for deterministic actions.

**Acceptance tests and limits:** Retain focus, scroll, context and keyboard access; responsive fallback for panels; compare time/errors with non-AI flow.

**Source references:** ai-layout-library, beyond-chat-examples, shape-of-ai.

## Discovery and input

**Cross-indexed labels:** Prompt Starters; Smart Empty State; Example Gallery; Templates; Smart Onboarding; Multimodal Input; Context Picker; @Mentions; Context Chips; Mode Selector; Parameter Controls; Prompt Enhancer; Natural Language Filters; Auto-fill.

**Design rationale:** Make capabilities and input scope discoverable; distinguish suggestions from selected context.

**Acceptance tests and limits:** Expose editable/removable context, clear permissions and accessible input labels; never silently add private sources.

**Source references:** aiverse-patterns, shape-of-ai, pair-guidebook.

## Editing and refinement

**Cross-indexed labels:** Select & Transform; Inline Editing; Ghost Text; Inline Suggestions; Selective Regeneration; Region Lock; Style Presets; Variations; Semantic Zoom; Progressive Disclosure; Diff View; Accept / Reject; Undo / Redo; Version History.

**Design rationale:** Make edits bounded, inspectable and recoverable; preserve unrelated content.

**Acceptance tests and limits:** Test partial selection, acceptance/rejection, undo, focus, failure and preservation of untouched regions.

**Source references:** shape-of-ai, aiverse-patterns, aiux-playground-patterns.

## Results and generative UI

**Cross-indexed labels:** Structured Output; Generative UI; Interactive Artifacts; Live Preview; Streaming; Parallel Alternatives; Smart Recommendations; AI Insights; Follow-up Actions; Reactive Blocks; Output Skeleton.

**Design rationale:** Render the useful object, not just prose; validate structured output and distinguish drafts from saved objects.

**Acceptance tests and limits:** Schema validation, source attribution, safe actions, keyboard navigation, cancel/retry, fallback to readable text.

**Source references:** beyond-chat-examples, aiverse-patterns, aiux-playground-patterns.

## Agentic UX

**Cross-indexed labels:** Intent Preview; Editable Plan; Approval Gates; Autonomy Control; Stage Tracker; Task Queue; Tool Visibility; Mid-run Steering; Action Audit; Checkpoints; Rollback; Agent Handoff; Parallel Execution; Completion Evidence; Escalation; Cancel / Pause; Cost Estimate; Scheduling.

**Design rationale:** Expose actual plan, scope, status, permissions, consequences and completion evidence; approval for consequential actions.

**Acceptance tests and limits:** Simulate failure, permission expansion, cancellation, timeout, retry and partial completion; do not fake progress or reasoning.

**Source references:** agentcat, beyond-chat-examples, hax-toolkit, pair-guidebook.

## AI design system

**Cross-indexed labels:** Prompt Input; Attachment Picker; Context Chip; AI Action Button; Contextual Menu; Parameter Slider; Model Selector; Autonomy Selector; Step Tracker; Progress Indicator; Streaming Indicator; Artifact; Result Card; Interactive Table; Diff Viewer; Revision Toolbar; Variation Selector; Approval Dialog; Stop Button; AI Label; Citation; Source Preview; Explanation Popover; Memory Editor; Context Indicator; Knowledge Source Picker; Rating; Correction Input; Report Action.

**Design rationale:** Extend existing semantic components instead of replacing them; AI labels should convey real provenance.

**Acceptance tests and limits:** Document anatomy, states, keyboard, screen-reader names, focus, validation and design tokens. No decorative AI icon alone as disclosure.

**Source references:** carbon-ai, intelliface, hax-toolkit.

## Motion and states

**Cross-indexed labels:** Streaming Reveal; Skeleton Loading; Progress Transition; Morphing; Expand / Collapse; Panel Transition; Inline Insertion; Diff Highlight; Completion Feedback; Error Recovery; Drag and Drop; Hover Disclosure; Focus Transition; Reduced Motion.

**Design rationale:** Use motion to communicate real state changes and preserve spatial continuity, not simulate activity.

**Acceptance tests and limits:** Respect reduced motion; provide non-motion and non-hover alternatives; measure progress only when available; stable geometry.

**Source references:** pair-guidebook, hax-toolkit.

## Trust and human control

**Cross-indexed labels:** Capability Disclosure; Limitation Disclosure; Context Transparency; Explainability; Provenance; Calibrated Uncertainty; Permission Scope; Feedback; Memory Review; Error Recovery; Human Override.

**Design rationale:** Communicate capabilities before use, relevance during use, correction when wrong and adaptation over time.

**Acceptance tests and limits:** Check sources and uncertainty, accessible dismissal/correction, inspect/edit memory, revocable permissions and safe manual fallback.

**Source references:** pair-guidebook, hax-toolkit, carbon-ai.

## Visual and responsive design

**Cross-indexed labels:** Typography; Semantic Color; Iconography; Spacing; Borders; Elevation; Optional Gradients; Resizable Panels; State Differentiation; Responsive Adaptation; Accessibility; Consistency.

**Design rationale:** No mandatory AI aesthetic; optimize hierarchy, density, contrast and conventional affordances.

**Acceptance tests and limits:** Check contrast, zoom, reflow, keyboard, touch, screen reader, state differentiation; no color-only meaning.

**Source references:** carbon-ai, intelliface, saasui-ai, mobbin.

## Antipatterns

**Cross-indexed labels:** Chat-first for Everything; AI Washing; Prompt-only Controls; Black-box Automation; Fake Progress; Forced AI; Hidden Context; Unrecoverable Actions; Uncalibrated Confidence; Excessive Anthropomorphism; AI Decoration; Infinite Suggestions; Inconsistent Interactions.

**Design rationale:** Avoid unnecessary AI, opaque automation and irreversible actions; do not mistake decoration for utility.

**Acceptance tests and limits:** Compare conventional alternative, test dismissal, correction, transparent scope, actual status, and recovery.

**Source references:** hax-toolkit, pair-guidebook, beyond-chat-examples.

## Product references and application hypotheses
NotebookLM (knowledge workspace), Gamma (document/presentation), Motion (planning), ElevenLabs (audio studio), Runway (video studio), Flora (spatial canvas), Lovable (builder), Cursor (code editor). These are reference candidates, not validated teardowns. For education: use embedded contextual actions for questions, PDF selection transformations, flashcard generation, structured simulations, performance insights, natural language filters and optional agentic planning with approval. Preserve manual question-solving; defer optional AI beyond MVP until benefit is validated. No product decision or code change is implied.

## Sources
- [The Shape of AI](https://www.shapeof.ai/) — editorial-pattern-catalog; Interaction families; inspect individual patterns before implementation.
- [AI UX Playground](https://www.aiuxplayground.com/patterns) — editorial-pattern-catalog; Product examples and interaction patterns; access varies.
- [Aiverse](https://aiverse.design/patterns) — editorial-pattern-catalog; Five-phase lifecycle: discovering, instructing, observing, refining, adapting.
- [AI Layout Library](https://ai.designdhaval.com/) — editorial-layout-catalog; Layout alternatives; names below are an original synthesis, not a copy.
- [Beyond Chat](https://www.beyondchat.design/examples/) — editorial-pattern-catalog; Non-chat interfaces; directability, observability, predictability, explainability.
- [AI Design Guide](https://www.aidesign.guide/agentic-ux-patterns) — editorial-pattern-catalog; Agent interactions; examples are not universal evidence.
- [Intelliface](https://www.intelliface.in/) — editorial-pattern-catalog; AI UI examples and components.
- [Google People + AI Guidebook](https://pair.withgoogle.com/guidebook-v2/) — primary-design-guidance; User needs, mental models, trust, feedback, graceful failure and control.
- [Microsoft HAX Toolkit](https://www.microsoft.com/en-us/haxtoolkit/) — primary-research-guidance; 18 guidelines organized around initial, ongoing, erroneous and long-term interaction.
- [IBM Carbon for AI](https://www.carbondesignsystem.com/building-blocks/foundations/carbon-for-ai) — primary-design-system; AI identification and explainability; check component status.
- [SaaSUI AI App UI Design](https://www.saasui.design/ai-app-ui-design) — visual-gallery; Product screenshots; link only.
- [Mobbin](https://mobbin.com/) — visual-gallery; Product screens and flows; access and rights vary.
- [SAP Design System](https://www.sap.com/design-system/) — primary-design-system; Enterprise patterns; specific AI guidance not exhaustively inspected.
- [Atlassian Design System](https://atlassian.design/) — primary-design-system; Productivity components; specific AI guidance not exhaustively inspected.
