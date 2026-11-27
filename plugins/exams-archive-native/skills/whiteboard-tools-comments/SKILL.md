---
name: whiteboard-tools-comments
description: Use when creating, reviewing or editing Open Artifact whiteboards, sketches, wireframes, prototypes, sticky notes, native drawing tools, anchored comments, or collaborative design review. Select native tools by semantic role and validate stage responsibilities and runtime capabilities.
---

# Whiteboard tools and anchored design review

Source basis (2026-11-26): installed Open Artifact whiteboard skill, including Element format, Comments, History and Sharing; historical v0.16.3 schema https://github.com/JimLiu/open-artifact/blob/v0.16.3/packages/whiteboard-core/src/schema.ts . Toolbar order/names from a screenshot are interpretations until tooltips/runtime are verified. For real project boards read the applicable whiteboard skill, AGENTS.md and docs/boards/whiteboard-guidelines.md; confirm dev before and after Exam App work.

## Native tool selection

| Tool | Use | Avoid |
|---|---|---|
| Select | Select, move, resize or edit existing elements when supported | Accidental modifications while navigating |
| Pan | Move viewport without changing data | Treating navigation as an edit |
| Text | Essential interface labels, headings and readable content | Replacing native notes or comment threads |
| Section / Frame | Group genuinely related screens, alternatives or regions | Decorative framing or premature formal Sketch hierarchy |
| Sticky note | Visible persistent hypotheses, decisions, rationale and concise design annotations outside the interface | Treating notes as review threads or as application UI |
| Draw / Pen | Editable freehand strokes and semantic geometry for hand-drawn sketches | Raster substitutes when editability is required |
| Shape | Semantic blocks, structural regions and diagrams at suitable fidelity | Polished production shapes in exploratory sketches |
| Image | Authentic references/screenshots with provenance, or requested visual assets | Substituting a screenshot for editable native elements |
| Comment | Anchored question, issue, proposal or review discussion | Fake comments, duplicates or permanent requirements hidden in a thread |

Names, shortcuts and schema vary by version: inspect installed runtime, tooltips, available commands and permissions; do not invent APIs. The installed Open Artifact skill currently says agent-created visible stickies are rounded yellow shape elements and not human-only note elements; project v0.16.3 historically accepted native type: note. Verify the actual version and permission before choosing representation; do not silently override the current host contract. Preserve user-authored notes. Comments are separate from board elements; never replace a thread with a shape or text. In the installed Open Artifact skill, comments may anchor to an item, point or region; standalone uses comments.json and `open-artifact comments <root> [--all] --json`, `comment-reply`, `comment-resolve [--reopen]`; hosted uses ArtifactComments only if available. Do not fabricate a create-comment API: if creation is unsupported, provide the proposed text and anchor for manual placement, and state the limitation. Never spoof authorship or manufacture feedback.

## Stage-specific responsibility

- Sketch: questions about hypotheses, broad composition, hierarchy and alternative approaches. Use sparse notes only for essential intent; no detailed production specs, exhaustive review markers, or polished overlays. Keep comments outside the depicted app, anchored to the smallest meaningful target.
- Low fidelity: structural grouping, navigation, information architecture and missing states.
- Mid fidelity: component semantics, expected behavior, states and transitions; flag unresolved decisions.
- High fidelity: visual consistency, accessibility, responsive layout, motion and design tokens as applicable.
- Interactive prototype: reproducible interaction defects, expected vs actual behavior, environment and flow.
- Usability testing: observations supported by actual sessions; separate finding, hypothesis and recommendation; never fabricate participant feedback.

## Comment lifecycle and quality gates

1. Read existing threads, including resolved when relevant, and board state; deduplicate by target and issue. Preserve IDs, original authors, chronology, existing threads and unrelated elements.
2. Use an actual item, point or region anchor. One issue per thread; concise observation, question or suggested change, with stage and evidence when relevant. Mark proposal vs confirmed decision. Keep issue trackers and durable documentation as source of truth for approved decisions; link instead of duplicating.
3. Reply in the same thread when supported. Resolve only after the underlying change or decision is verified; leave unresolved issues open with reason. Reopen if the regression recurs. If an anchor disappears, retain provenance and re-anchor only using supported functionality; report any orphaned thread.
4. Verify persistence after reload, correct anchor/target and visibility, thread reply/resolution, no unauthorized writes, no duplicate comments, no changed unrelated geometry; confirm export/archive behavior (a PNG is not proof that threads persist). Verify open/closed threads and theme/zoom when relevant. Distinguish observed behavior, source documentation and proposed tests. Don't claim a screenshot proves interaction.
5. In Exams App, keep English project-authored content; preserve the owning stage and its approved scope. Record verified decisions in appropriate release docs and links; comments supplement, never replace notes or the source of truth. Do not create comments merely to satisfy a quota. Use native API/CLI only when available and report missing capability.

## Complementary plugin
Use Especialista em UI/UX for general principles and design methods; Exams Archive owns reproducible historical evidence and current source checks. Follow sync-bridge and shared-ux-knowledge for changes.
