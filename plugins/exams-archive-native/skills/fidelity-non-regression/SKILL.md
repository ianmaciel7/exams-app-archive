---
name: fidelity-non-regression
description: Use when advancing, creating, reviewing or auditing Sketch, Low-Fidelity, Mid-Fidelity, High-Fidelity, Mockup or Prototype stages. Prevent loss of previously approved content, controls, states, responsive layouts and behavior using traceable coverage and actual capture review.
---

# Fidelity non-regression gate

Fidelity is not coverage. A new stage may use fewer representative screens, but must not silently remove previously approved requirements. Read the immutable approved baseline, inventory, flows and decisions before generating a new artifact.

1. Derive a coverage ledger: stable requirement/state ID, predecessor SHA/evidence, current screen/component specimen and element IDs, status represented/missing/deferred, reason and review evidence. Use explicit owner approval for changed product behavior. A justified later-stage deferral must identify its target and source; an absent applicable visual state is missing, not deferred.
2. Complete representative screens: actual content and alternatives, all necessary actions, navigation, pagination, feedback and continuity. Distinguish intentional scroll viewport clipping from missing source. Reuse shared source for repeated components and overlay underlay. Cover applicable loading, empty, error, retry, pending, selected, correct/incorrect/locked, hover/focus/pressed/disabled, long content, narrow/phone and localized states using complete screens or focused component studies.
3. Inspect actual native captures at useful zoom in both relevant themes and device widths; compare against the immutable predecessor. A green build, valid element count, link to prior board or smaller scenario count does not establish visual coverage.
4. Record missing coverage and proactively notify the owner before presenting the artifact as ready. Allow explicitly labeled work in progress; block approval and progression until applicable gaps and visual review are resolved. Do not duplicate every historical artboard or implement out-of-stage functionality just to meet a count.
5. For Exam App verify dev at start/end, preserve approved boards, consult AGENTS.md and canonical release coverage ledger, and validate CI separately from human visual review.

Case 2026-11-27: approved Mid-Fidelity (21 states) to High-Fidelity (four initial specimens) at exams-app commit 2cc13ec. Published images exposed incomplete question alternatives/actions, missing pagination, lifecycle/feedback/control specimens, long-text and responsive detail, and inconsistent drawer underlay. Record the regression rather than call a green CI approval. The rule is a project quality convention, not a claim of universal UX law. Canonical record: https://github.com/ianmaciel7/exams-app-archive/blob/main/docs/references/ui-ux-research-sources/ux-design-activities-2026-11-25.md
