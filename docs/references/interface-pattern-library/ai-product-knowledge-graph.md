# AI product knowledge graph

2026-11-26. Cross-index of ChatGPT Space, Claude, Grok Bot, Gemini and Gemini Notebook. Product observations are not universal principles. [JSON graph](ai-product-knowledge-graph.json), [gap delta](../ui-ux-research-sources/ai-product-gap-delta-2026-11-26.md), [source register](sources.json), [patterns](patterns.json).

## Counts

- products: 5
- sourceAliases: 72
- addedCentral: 70
- addedLocal: 9
- previousObservations: 34
- newObservations: 9
- addedPatterns: 43
- centralPatterns: 90
- centralSources: 573
- nodes: 294
- edges: 388
- views: 41
- outputs: 48
- evidence: 22
- candidates: 56

## Retrieval

Product → feature observation → official source; product → output → comparison concept or visual example. Task list, dashboard, quiz, flashcards and other concepts are analyst groupings. Component/state candidates are explicitly unverified and must not be presented as shipped features. Add observed interaction/transition nodes only with specific evidence. Source aliases retain historical IDs; tracking parameters deduplicated while locale/functional parameters retained. No historical record deleted.

## Backlog

| ID | Priority | Gap | Status | Acceptance |
|---|---|---|---|---|
| GAP-01 | P0 | Feature inventory and availability | open | Capability matrix; native feature vs generated example |
| GAP-02 | P0 | Templates and editors | open | Template cards, creation, per-editor controls and export |
| GAP-03 | P0 | States and transitions | open | Trigger, before/after, focus, interruption and recovery |
| GAP-04 | P0 | End-to-end flows | open | Create/edit/share/reopen/delete; question and flashcard review |
| GAP-05 | P0 | Visual evidence | open | Publisher URL, exact frame, date, viewport, rights, evidence-to-feature relation |
| GAP-06 | P0 | Central catalog integration | resolved | Register every benchmark source alias and observation |
| GAP-07 | P0 | Relationship graph | partial | Stable typed nodes, edges and source references; expand evidence and live state relations |
| GAP-08 | P0 | Persistence and permissions | partial | Save/reload/sharing/roles/deletion/version/conflict matrix |
| GAP-09 | P1 | Data visualization and generated UI | open | Chart controls, tooltips, drill-down, keyboard, data fallback |
| GAP-10 | P1 | App shell and responsiveness | open | Measure widths, resizing, collapse, overflow and reflow |
| GAP-11 | P1 | Motion and microinteractions | open | Record state changes and reduced motion; measure timing |
| GAP-12 | P1 | Tokens and typography | open | Measure actual styles and contrast; no inferred CSS |
| GAP-13 | P1 | Accessibility and keyboard | open | Actual focus, keyboard and assistive technology tests |
| GAP-14 | P1 | Plan and platform availability | open | Record feature, plan, platform and release date |
| GAP-15 | P1 | Errors and recovery | open | Failed save, offline, permission, retry and cancellation |

## Ingestion contract

Every benchmark must resolve source IDs centrally, preserve stable observation IDs and link product, feature, view, output and evidence as supported. Record date, platform, plan, rights, evidence type and exact source. Unknown is not absent. Capture before/after, trigger, input, focus, motion, error and recovery for actual interactions. Validate IDs/edges/sources and evidence status before merging. No FTS rebuild, no plugin release claimed.

## Documented flows and public retrieval — 2026-11-26

- [Twelve documented flows](../ui-ux-research-sources/ai-product-documented-flows-2026-11-26.md), with source-specific persistence boundaries and explicit untested behavior.
- Graph now has 308 nodes and 426 edges; prior counts above are historical snapshots.
- Public research FTS projects recorded views, outputs, visual references and documented flows. Candidate component/state nodes are excluded from search evidence. Existing pattern records are retained; graph feature observations remain centrally indexed without a third duplicate projection. CI and deployment are separate validation gates.

## Availability and state boundaries

[15-row matrix and 10 additional product observations](../ui-ux-research-sources/ai-product-availability-and-state-boundaries-2026-11-26.md). Graph now 319 nodes and 461 edges. Claude Design promotional thumbnail visually inspected; no motion inference.

## Editor contracts and transitions — 2026-11-26

- [16 observations and three documented sequences](../ui-ux-research-sources/ai-product-editor-contracts-2026-11-26.md)
- Graph: 348 nodes, 528 edges. Official text-derived contracts are explicitly distinct from runtime observations. No visual or motion measurement claim.

## Searchable contracts and availability

15 dated availability rows and three documented transition contracts are now projected into public FTS and the research website. Graph: 363 nodes, 558 edges. Candidates remain excluded. CI must validate retrieval; the projection is not a runtime observation.

## Visual and learning evidence — 2026-11-26

[13 observations, eight media links and two flows](../ui-ux-research-sources/ai-product-visual-and-learning-evidence-2026-11-26.md). One rendered GIF frame inspected; remaining links are uninspected leads. Graph: 393 nodes, 634 edges. No video timing or runtime claims.
