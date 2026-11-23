---
name: exams-archive-motion-research
description: Use when researching, creating or comparing UI animations, transitions, microinteractions, hover, sidebar peek, drawer, motion easing, timing, loading skeleton, drag and drop, gestures, focus and reduced-motion across historical Exams App and Notes App.
---

# UI motion and interaction retrieval — Exams Archive

## Core correction

The historical FTS5 index is lexical, not semantic: it indexes commit subjects, file paths and image metadata, **not full CSS/JS/TSX content**. A screenshot does not prove an animation. For motion questions, **do not rely on FTS5 or PNGs alone**.

## Source of truth

Read `ianmaciel7/exams-app-archive` at `main`, `docs/UI-MOTION-EVIDENCE.json` through the connected GitHub tool. This is a **curated 13-record motion catalog** with `aliases`, `concept`, `trigger`, `from`, `to`, `delay_ms`, `duration_ms`, `easing`, `properties`, `reduced_motion`, and source repo/ref/path/blob SHA/line range. It is not an embedding/vector index, not an exhaustive source-code index and not a runtime animation trace.

Classify user intent by **meaning**: `barra recolhida`, `peek`, `hover`, `reveal`, `fade`, `accordion`, `drawer`, `arrastar`, `reordenar`, `loading`, `tooltip`, `popover`, `scroll`, `focus`, `reduced motion` map to the catalog `aliases` and code signals. Return 3–8 relevant records, not a huge dump.

## Code-first pipeline

1. Read catalog, match intent semantically to candidate records, and choose *one* source branch for actual fidelity; do not merge animations from unrelated versions without labeling adaptation.
2. For every selected record call GitHub `fetch_file` on its `source.repository`, `ref`, `path` and source line range; verify `blob_sha` against live GitHub metadata. Expand line ranges to include handlers, CSS declarations, state and adjacent hooks. If SHA changes, flag drift; don't trust an outdated catalog blindly.
3. For uncataloged behaviors, follow `skills/ui-fidelity/references/visual-source-catalog.md` to the actual TSX/JS/CSS/HTML and tests/stories. Search source for `transition`, `duration-`, `ease-`, `animation`, `@keyframes`, `requestAnimationFrame`, `.animate`, `setTimeout`, `pointer`, `scroll`, `hover`, `focus-visible`, `data-open`, `data-closed`, `prefers-reduced-motion`, `motion-reduce`; read context, not isolated matches.
4. Report a **motion contract**: component, trigger, before/after states, delay vs duration (separate!), easing, animated property, keyboard/touch/focus behavior, reduced-motion response, source SHA/line and confidence. Unknown values stay `unknown` — do not infer timings from static screenshots.
5. For in-chat interactive previews use `skills/ui-fidelity/references/chat-preview-contract.md`; implement only verified transitions, timers, overlays, cleanup, escape/backdrop, focus return, reverse/interruption, mobile, reduced motion, loading timeout/error. Do not claim browser testing without actual execution.
6. For runtime validation, compare before/after **and intermediate** frames or a real GIF/video, inspect computed styles or Web Animations API and keyboard/touch behavior. Document source-only evidence vs real measurement.

## Verified examples from source (not runtime measurements)

- Notes `old-10`: peek opening is **300ms dwell delay**, closing **150ms dwell delay**; distinct from animation duration. `src/components/space-frame.tsx` SHA `c916f3d4003d24bc9eb8727be98e8afa5d19b31f`, lines 148–176.
- Notes `old-5`: reordering uses FLIP-style WAAPI `element.animate` translateY back to 0 in **200ms ease-out**, `app-sidebar.tsx` SHA `3a0b57cfbe907c6ea6779880273d61ba02c96bdd`, lines 248–270.
- Notes `old-5`: workspace shell declares width/height/transform/opacity **200ms ease-out**, reduced-motion disabled, `app-shell.tsx` SHA `c8149bad08ee026dec049371d3814c29aec8b89a`, lines 13–14.
- Notes `old-5`: shared popovers **150ms** open, **100ms** close; tooltip **180ms**, `src/components/ui/shared-styles.ts` SHA `d0d3bda4590a5bf142dd6a0eac7403026eb88332`, lines 10–15.
- Exams `dev` standalone: sidebar collapse **200ms**, caret **150ms**, skeleton pulse **1200ms**, mobile drawer **200ms**; `docs/Documentos/01-planejamento/revisao/sidebar-prototipo/prototipo-sidebar.html` SHA `783b7041913a8ddc01c7bd2aa1ee6bbf6eeb7e1a`.

## Safety and precision

Never treat code declarations as measured runtime performance; never mistake `delay_ms` for `duration_ms`. Metadata is in the private archive, not GitHub Pages. Do not publish private source assets, modify backups or claim this v0.5.0 feature creates semantic embeddings or automatically indexes all historical code. No changes to immutable archive index releases.

For terminology and QA see `references/motion-taxonomy.md`.
