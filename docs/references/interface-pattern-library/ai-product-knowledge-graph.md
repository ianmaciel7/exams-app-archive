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

## Creation options and object semantics — 2026-11-26

[Creation inventory](../ui-ux-research-sources/ai-product-creation-inventory-2026-11-26.md). 50 entries (not all native templates), 9 additional observations and one visually inspected official marketing image. Graph: 453 nodes, 814 edges. Search kind `creation-option`. Historical template leads and generated examples are explicitly classified. Live UI validation remains open.

## Data visualization and evidence coverage

[Comparative matrix, ten additional observations and per-product coverage](../ui-ux-research-sources/ai-product-dataviz-and-evidence-coverage-2026-11-26.md). Two original historical Notebook data-table stills inspected. Graph now 468 nodes, 852 relations. The adjacent Sheets canvas reference is explicitly outside the five-product benchmark. Unknown coverage remains unknown.

## Visual verification follow-up

[Four historical Claude Projects stills and eight failed media retrieval attempts](../ui-ux-research-sources/ai-product-visual-verification-2026-11-26.md). Graph: 472 nodes and 868 edges; 15 inspected stills and 23 leads, including a publisher page with four inspected children. No current UI or motion verification.

## Retrieval quality audit

[Five-product target-retrieval benchmark](ai-product-retrieval-benchmark.md): 22 frozen queries, no ranking changes in the initial baseline, independent relevance annotation still required. Report target recovery and missed IDs; do not treat passing unit tests as complete quality coverage.

## Runtime verification plan

[15 planned authorized test cases and independent-review protocol](ai-product-runtime-verification-plan.md) · [JSON](ai-product-runtime-verification-plan.json). All cases are not-run; no new evidence or completed coverage claimed.

## Adjacent generative UI research examples

[Research evidence and selected demo links](../ui-ux-research-sources/google-research-generative-ui-evidence-2026-11-26.md). One inspected original collage, five demo leads; not new native feature claims. Graph: 480 nodes, 889 edges.

## Direct provenance coverage — Grok Bot, 2026-11-26

Artifact 15127632547 contained 58 returned hits, all with a record or blob hash, but 4 hit occurrences (3 distinct Grok graph nodes) lacked direct source URLs. The graph projector intentionally requires explicit source edges. An audit found 0/41 view nodes and 0/48 output nodes with direct source edges. Verified the official [Files and results](https://docs.x.ai/grok-bot/files-and-results) and [Skills and routines](https://docs.x.ai/grok-bot/skills-routines-and-automations) documentation, updated 2026-11-19, and added 14 feature-specific source edges across 13 nodes. Direct coverage is now 5/41 views and 8/48 outputs; do not infer unsupported associations for the remainder. Generated examples are not native templates; reader controls are transient, Bot edits persist, and routines can create/update pages. Routines appear on desktop Details and the phone profile. No authenticated UI verification or ranking change. The exact current benchmark must be measured separately because catalog provenance changed.

## Direct provenance coverage — Gemini Notebook, 2026-11-26

Added 19 feature-specific source edges using existing canonical Google Help and launch source nodes. Direct coverage: 11/41 views and 19/48 outputs across the five products. Six Notebook views and eleven Notebook outputs have direct documentation; notebook collection remains unlinked pending an explicit collection-view source. 480 nodes and 922 edges; all endpoints resolve. Study progress and individual site inputs are documented as persistent; shared-site users cannot see others' inputs. Exports to Docs/Sheets are detached from the original notebook and its sharing permissions. Interactive reports are distinct from document reports; the latter are not a universal interactive editor. Full-screen flashcard/quiz controls do not establish every artifact viewer's layout. Official text checked, no authenticated runtime, screenshots, ranking changes or independent benchmark claims.

## Direct provenance coverage — ChatGPT Space, Claude and Gemini, 2026-11-26

Added 55 source edges, 2 centrally registered official help sources; 482 nodes and 977 edges, all endpoints resolve. Overall direct coverage 35/41 views and 48/48 outputs. Coverage counts any direct feature-specific source, including explicitly classified historical announcements and generated examples; it does not certify UI or template availability.

| Product | Views | Outputs | Remaining unlinked IDs |
|---|---:|---:|---|
| chatgpt-space | 12/14 | 8/8 | `view:chatgpt-space:sites`, `view:chatgpt-space:google-drive` |
| claude | 5/6 | 8/8 | `view:claude:installed-apps` |
| gemini | 7/7 | 13/13 | None |
| grok-bot | 5/7 | 8/8 | `view:grok-bot:computer`, `view:grok-bot:marketplace` |
| gemini-notebook | 6/7 | 11/11 | `view:gemini-notebook:notebook-collection` |

OpenAI Help documents ownership filters, nested pages and search; Space marketing illustrations establish generated examples, not native templates. Claude Artifacts Help distinguishes seven native templates from arbitrary tools and dashboards, and interactive connector views from artifact views. Gemini Canvas Help documents code/preview and creation outputs; the November 23 blog gives generated use cases; older launches do not certify current rollout. React-specific internals, exact installed-app navigation, Space Sites/Google Drive view labels and remaining unlinked items require explicit evidence. No screenshots, runtime testing or ranking changes in this pass.

## Remaining six entry points — scope-qualified provenance, 2026-11-26

Added 7 direct source edges and 2 central sources. All 41 recorded views/entry-point labels and 48 recorded outputs now have source links. **Two Space labels remain scope-unverified**: Sites is documented as an adjacent ChatGPT sidebar destination; Google Drive browsing is documented in Library and connected-file context in Space. Neither is certified as an internal Space filter. Claude Installed Apps is a desktop File > Apps entry, not a web artifact collection. Grok Computer is illustrated in the official overview, and Marketplace discovery is documented; exact layout untested. Gemini Notebook home supports removal of recent shared notebooks, public search and featured discovery, subject to account eligibility. 484 nodes, 984 edges, 612 central sources; no unresolved endpoints or central source IDs. 41/41 source-linked labels is not 41/41 runtime-confirmed views. No authenticated tests, media download, index rebuild or ranking changes in this pass.

## Recovery and learning flow evidence — 2026-11-26

Three additional official sources, one documented recovery contract, three documented flows and one uninspected image lead. [Grok computer and apps](https://docs.x.ai/grok-bot/computer-and-apps) documents account-level shared computer, per-Bot screens (not separate security boundaries), preview and takeover, reconnect, update/recover/reset retention and least-destructive escalation. [September Gemini Notebook launch](https://blog.google/innovation-and-ai/products/gemini-notebook/new-study-tools-september-2026/) describes post-study feedback, editing questions and additional quiz formats; launch eligibility not current verification. [June Gemini education announcement](https://blog.google/products-and-platforms/products/education/iste-students-2026/) describes adaptive lessons and topic-level exam feedback, with a Brazil ENEM announcement not verified as released. The Gemini Notebook hero media could not be fetched; caption-only lead, no visual inspection. 492 nodes, 998 edges, 615 sources. Existing runtime test plan remains not-run; no ranker changes, new independent reviewer, or UI accessibility claims.

## Focus, access and study-session contracts — 2026-11-26

Four additional official text-derived contracts (not runtime observations): progressive artifact panel escape and focus return, comment-mode focus, direct versus inherited access revocation, and flashcard session resumption/review scope. Existing sources reused: [Claude keyboard guide](https://support.claude.com/en/articles/17457950-use-artifacts-with-a-keyboard-or-screen-reader), [Space collaboration](https://learn.chatgpt.com/docs/space/collaboration), [Notebook study aids](https://support.google.com/gemininotebook/answer/16958963?hl=en). Unknowns include exact focus after deletion, permission conflicts and latency, empty missed-card subset and motion. Claude legacy and standalone artifacts have different panel navigation; no universal keyboard guarantee. The [Space pages guide](https://learn.chatgpt.com/docs/space/pages) explicitly illustrates Sites and Google Drive sidebar labels; this refines the earlier scope caveat without asserting internal filters or current account availability. No new source IDs. 496 nodes, 1008 edges, zero dangling or duplicate edge keys. Runtime and independent review remain pending.

### Derived implementation checks (proposed, not product facts)

| Contract | Exam App acceptance checks |
|---|---|
| Panel focus return | Opening a question inspector moves focus to a logical control. Escape closes its innermost popup before the inspector; focus returns to its opener or a stable fallback. Test keyboard and assistive technology. |
| Comment mode | Distinguish target selection, draft, submitted and error states; preserve draft when possible, restore focus on cancel and enforce role authorization server-side. |
| Inherited access | Explain effective permission and source of grant; remove direct and inherited grants separately; verify actual access with synthetic role fixtures; linked sources require independent checks. |
| Study progress | Store learner-session state separately from deck content; resume by stable IDs, support missed-only review, define empty-subset behavior, and test reload and deck changes. |

These are design/test candidates, not an implementation change or a measured reproduction of the benchmark products.
