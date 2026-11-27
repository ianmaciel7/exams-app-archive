# Shared UI/UX knowledge contract

Protocol v1.0, 2026-11-25. Collaboration through a canonical repository and available tools, not direct inter-plugin RPC or automatic synchronization.

## Roles
- Exams Archive owns historical evidence: source, commit, screenshots, prototype, behavior, ADR, implementation and reproducibility.
- Especialista em UI/UX owns general principles, research, design patterns, design methods, accessibility and acceptance tests.
- Both consume and contribute to workspace, navigation, interaction states, motion, visualization, AI-native UI, sketching, wireframes and design-system knowledge.

## Canonical discovery
- [Pattern library](../interface-pattern-library/README.md)
- [Research sources](../ui-ux-research-sources/README.md)
- [Archive source and skills](../../../plugins/exams-archive-native/README.md)
- Search archive indexes, graph, glossary, ADRs, screenshot catalog and component sources by concept and aliases. For project-current claims check the active repository/branch independently; never treat an archived revision as current.

## Bidirectional handoff
When either specialist is asked about a cross-domain topic, load this contract and relevant existing records, then consult the complementary evidence via connected GitHub, local archive CLI/MCP or installed skill if available. Do not require the user to mention both plugins. If unavailable, state what could not be verified and continue with the available sources. Do not recursively call the counterpart or pretend that installing a skill grants direct RPC or permissions.

Produce a single joined evidence packet: stable pattern/concept ID or existing alias; definition; problem/context; observed implementation with source path and SHA if known; external source URL and publication/version date; behavior/state/trigger; evidence type and confidence; accessibility; rationale and tradeoffs; acceptance tests; links to related patterns, components, screenshots, ADRs and unresolved gaps. Keep observed, documented, tested, normative and proposed claims separate. Never infer animation from still imagery or treat product behavior as a standard.

Example: Capacities sidebar peek → archive evidence (hover/pin behavior, captured source, versions) + UX specialist (progressive disclosure, focus, touch alternative, reduced motion, validation). Record one linked finding, not duplicate independent catalogs.

## Learning and sync
Deduplicate by existing stable IDs, aliases and normalized sources. Share general reusable discoveries and licensed references; never publish private queries, credentials, private plugin IDs, restricted media or user-specific data to the public archive. Keep historical source immutable; add dated annotations and links. Both plugins should read latest relevant canonical content when available, cache only compact routing rules, and report version/date when using a stale copy. Changes to the canonical archive follow authorized versioned writes and conflict checks; explicit sync requests follow the existing sync-ux-knowledge and sync-bridge skills. An instruction to consult knowledge is not authorization for unrelated writes, plugin installation or background execution.

## Acceptance checks
1. Either specialist alone can route a sidebar question to both evidence types without circular delegation.
2. A generic UX question does not require project-specific history unless relevant.
3. Contradictory evidence is labeled rather than overwritten; unavailable sources are not fabricated.
4. New reusable findings have one canonical record and links; repeated ingestion is idempotent.
5. Public/private separation, release guards and readback are maintained.
6. No automatic synchronization or native plugin-to-plugin calls are claimed without a separately verified integration.

## Design foundations and state transitions

Both plugins consult [decision guide](../ui-ux-research-sources/design-foundations-and-state-transitions-2026-11-25.md) and [cross-index](../ui-ux-research-sources/design-foundations-and-state-transitions-2026-11-25.json) for color selection, focus, layout, motion and state/transition decisions. Separate semantic state, event, guard, effect and visual animation; require source evidence, accessibility, interruption/reversal and real tests. #103–#105 remain research/validation backlog. No claim of automatic sync or historical implementation.

## UI sketch fidelity and stage responsibilities (2026-11-26)

Local design policy learned from sketch review; not a universal industry standard. Optimize fidelity for the decision being made, not for visual polish or AI implementation convenience.

- **Composition-only sketch:** explore masses, reading direction, approximate proportions and regions. Replace nonessential copy, repeated question titles and navigation labels with short strokes; represent icons with simple consistent drawn geometry. Use meaningful control silhouettes (radio circles, checkbox squares) where the interaction matters. No final typography, tokens, precise grid, mockup polish or decorative detail. A short label is allowed only if omitting it would make the hypothesis ambiguous; prefer an external anchored note for region explanations. Do not impose a universal ban on words or force irregularity.
- **Structural wireframe:** introduce semantic headings, representative labels, controls, hierarchy, states and layout constraints when needed to validate information architecture and task flow; use realistic text lengths where they affect layout. Reserve definitive styling and final copy for the appropriate later stage.
- **Mockup / prototype:** mockups define visual design and tokens; prototypes test relevant interactions, states and transitions. Neither is required merely to explore a sketch. Fidelity is multidimensional; visual simplicity must not conceal functional ambiguity.
- **Exam question-list example:** a narrow sidebar and vertically stacked question blocks can be explored with abstract navigation marks, short header strokes, enunciation lines and radio alternatives. Use actual labels only if validating navigation or question identity. ExamTopics historical evidence is not proof of its current UI; distinguish reference, adaptation and approved requirements.
- **Delivery/QA:** if the user asks for drawing rather than image generation, use supported native vector/pen primitives or an explicitly labeled procedural preview; do not claim unavailable native pen access. At normal viewing size check visual hierarchy, legibility, clear control meanings, minimal labels, consistent stroke family and no unnecessary precision. Do not convert a sketch into a screenshot-like mockup. Record the hypothesis and any unresolved semantic questions separately.
