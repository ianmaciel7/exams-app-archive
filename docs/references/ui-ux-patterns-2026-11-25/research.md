# Research synthesis

Date: 2026-11-25. Origin: ChatGPT Deep Research, editorially consolidated with official follow-up sources. See [references](references.md).

## Distinct layers
Separate object model, query/selection, presentation view, placement surface, interaction state and animation. A table is a presentation; a side panel is placement; a saved query is a data definition. The same item should not be duplicated in storage merely to display it differently.

## ChatGPT
OpenAI's public plugin UI guidelines (O1) describe embedded cards and carousels, expanded fullscreen experiences with conversational input, and picture-in-picture. Compact cards should communicate a focused outcome; carousels work for short visually differentiated choices; expanded surfaces support multi-step interaction. Use restrained hierarchy, system-compatible styling and accessible controls. Intelligent UI announcement (O2) documents conversational combinations of prose, graphics and interactive controls. Public developer libraries provide design resources, not proof of the internal ChatGPT implementation.

Conversation controls include composer, contextual message actions, attachment affordances and feedback. T1 is a third-party imitation, not authoritative product documentation; its visual details, action visibility and four-state controls are inspiration only. Do not assume private component names, exact tokens or timings. Official illustrations are linked in references.

## Claude
First-party help (A2) documents charts, diagrams and interactive visual explanations inside conversation. A1 distinguishes persistent artifacts, including code, documents, web experiences, dashboards, diagrams and interactive tools. A3 documents design/prototype creation and canvas editing; A4 documents collaborative whiteboards. This corrects the original report's incomplete treatment of Claude rich UI. Availability can vary by client and plan.
T2 and T3 demonstrate an editorial warm palette, serif text and restrained chrome; these are third-party examples, not official design tokens or proof of exact product behaviors. Do not infer lack of sharing, streaming, responsiveness or accessibility from a clone.

## Capacities
Object-centric workspaces decouple the content from list, table, gallery, wall, Kanban and other supported views. Collections are curated; queries dynamically select matching objects. Navigation includes previews, main and side-panel tabs, context-specific inspector and keyboard shortcuts. See capacities.md.

## Exams App recommendations (proposals)
Use a stable object ID and central data model. Store presentation preferences independently from queries. Start with table/list for question discovery, gallery for visual study assets, a split workspace for question and explanation, and accessible progress charts. Build richer surfaces only when task complexity warrants them. Keep contextual actions visible on focus/touch. Distinguish durable documents from ephemeral chat visuals. Add explicit empty, loading, error and retry states. Use existing archive tokens and motion evidence instead of inventing product fidelity.

## Known limitations
No live DOM/CSS audit, mobile recording or frame-by-frame capture was performed. Third-party screenshots and clones require independent validation. This archive is a curated derivative of the research report, not its complete verbatim text or a full product feature audit. Index rebuild and plugin synchronization are separate verification tasks.
