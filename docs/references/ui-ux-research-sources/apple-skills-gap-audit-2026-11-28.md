# Apple agent skills — coverage and gap audit (2026-11-28)

External research; original synthesis, not Apple guidance or an exhaustive certification. Companion to [source inventory](apple-agent-skills-plugins-2026-11-28.md) and [HIG craft](apple-hig-design-craft-2026-11-27.md).

## Scope and method

Inventoried 20 public GitHub repositories. Retrieved and examined 88 SKILL.md entrypoints (including overlapping Xcode generations and curated skills): 15 newer Xcode mirror, 7 older mirror, 2 Foundation Models Utilities, 4 Core AI, 12 independent HIG entries, 15 Zinoo category routers, 20 OpenAI iOS/macOS entries, and 13 selected entries from broader collections. Examined 10 targeted supporting references and five catalog READMEs. Not every nested reference or hundreds of catalog entries were read; no code, scripts or native Xcode export executed. Public sources read via GitHub; no private data copied.

Compared installed Especialista UI/UX 1.12.7 (35 skills, 99 files) and Exams Archive 0.8.26 (19 skills, 35 files). Inspected 16 and 6 relevant Markdown files respectively and searched all 90 and 33 Markdown/JSON files respectively for specific gap terminology. Compared selected public main-branch research documents and searched repository code for target terms. Search absence is not proof of universal absence. Shared knowledge may be routed to a canonical document instead of duplicated. Repository retrieval evaluator already has token budgets, latency and recall; this is distinct from conversational transcript management and agent tool-action evaluation.

## Transferable coverage

C = satisfactorily documented at reviewed abstraction; P = partial/operational depth gap; N = specialized procedure not located in inspected scope. Not a global Apple knowledge percentage or runtime certification.

| Area | UX specialist | Archive plugin (local) | Public archive |
|---|---|---|---|
| Hierarchy and composition | C | C | C |
| Material hierarchy / Liquid Glass | C | C | C |
| Color and typography | C | C | C |
| State and feedback | C | C | C |
| Motion and transitions | C | C | C |
| Article-specific HIG routing | P | P | P |
| Continuous adaptive resizing | P | P | P |
| Toolbar priorities / overflow | P | P | P |
| Window and panel lifecycle | P | P | P |
| Document autosave / undo / recovery | P | P | P |
| Multimodal input parity and gesture arbitration | P | P | P |
| Runtime accessibility evidence | P | P | P |
| Device/browser functional visual evidence | P | P | P |
| Comparable performance profiling | P | P | P |
| Privacy-bounded telemetry | P | N | P |
| Agent action and tool contracts | P | N | P |
| Agent action-specific evaluation | N | N | N |
| Conversation transcript lifecycle | N | N | N |

Shared scope: 5 C / 11 P / 2 N. Archive plugin local: 5 C / 9 P / 4 N. These are reviewer-defined categories, not a measurement of all available Apple knowledge.

## Prioritized proposed improvements (not implemented)

1. Adaptive workspace: component/container constraints, preserve selection and scroll during continuous resize; explicit toolbar priority and discoverable overflow, focus restore, no hidden essential command. Verify narrow-to-wide and reverse. Sources: [Xcode mirror](https://github.com/mariusfanu/xcode-skills), [HIGAgentSkills](https://github.com/justinwetch/HIGAgentSkills/blob/HEAD/distilled/toolbars.md), [OpenAI macOS patterns](https://github.com/openai/plugins/tree/main/plugins/build-macos-apps).
2. Documents and navigation: stable object identity and per-view state, save progress, cancellation, undo grouping, conflict/recovery, reopen and duplicate tabs; do not transplant native autosave/UndoManager API to web. Source: [document skill](https://github.com/mariusfanu/xcode-skills/tree/HEAD/plugins/xcode-skills/skills/building-document-based-swiftui-applications).
3. Multimodal input: distinguish focus and selection, gesture ownership, long press vs scroll vs drag, cancel/restore, keyboard/touch equivalents, avoid duplicate action. Sources: [gestures](https://github.com/mariusfanu/xcode-skills/tree/HEAD/plugins/xcode-skills/skills/macos-touch-gestures), [HIG focus](https://github.com/justinwetch/HIGAgentSkills/blob/HEAD/distilled/focus-and-selection.md).
4. Runtime evidence: identity (commit/build/environment), screenshot + semantic tree + actual interactions; capture before/after and failures; no screenshot-only compliance. Source: [device interaction](https://github.com/mariusfanu/xcode-skills/tree/HEAD/plugins/xcode-skills/skills/device-interaction), [OpenAI iOS workflows](https://github.com/openai/plugins/tree/main/plugins/build-ios-apps).
5. Comparable profiling: one task/trace, same workload/device/cache state, repeated measurements, raw results and causal limitations, verify output and cancellation. Use web-specific browser performance tooling rather than xctrace on web. Source: [runtime proof](https://github.com/coryparrry/apple-engineering-skills/tree/HEAD/skills/apple-runtime-performance-proof).
6. Privacy-safe telemetry: typed allowlist, low-cardinality events, no private content, bounded retention/export and actual event verification. Source: [privacy telemetry](https://github.com/coryparrry/apple-engineering-skills/tree/HEAD/skills/apple-privacy-telemetry).
7. Agent action contracts: stable public IDs, typed parameters, idempotence under retry, deterministic authority, permission and side-effect boundary; test cancellation and stale results. Sources: [App Intents](https://github.com/mariusfanu/xcode-skills/tree/HEAD/plugins/xcode-skills/skills/app-intents-specialist), [Foundation Models production](https://github.com/coryparrry/apple-engineering-skills/tree/HEAD/skills/apple-foundation-models-production).
8. Agent evaluations: representative versioned fixtures; intent choice, arguments, authorization, forbidden effects, output schema, fallback, cancellation, latency, repeatable safe evidence; separate retrieval evaluation from tool execution. Source: [evaluation](https://github.com/coryparrry/apple-engineering-skills/blob/HEAD/skills/apple-foundation-models-production/references/evaluation.md).
9. Transcript lifecycle: lazy skill loading, drop completed tool exchanges safely, bounded history, rolling window, summarization and preserve durable decisions, unresolved references and authorization boundaries; test context loss and token cost. Source: [Foundation Models Utilities](https://github.com/apple/foundation-models-utilities).
10. Source routing: foundational checks + platform + selected task article + bounded related expansion + live verification for version-sensitive rules. Distinguish primary Apple guidance, community interpretation and project choice. Sources: [HIGAgentSkills](https://github.com/justinwetch/HIGAgentSkills), [Zinoo routers](https://github.com/Zinoo00/apple-human-interface-guideline-skills), [davidcafor](https://github.com/davidcafor/apple-hig-skill).

## Exclusions and placement

Native compiler bounds safety, Xcode signing, SwiftPM packaging, Siri APIs, Core AI model conversion, platform gestures APIs and hardware profiling are not required web UI knowledge. Keep references available without importing platform-specific implementation into the UI/UX plugin. Adapt universal principles only. The UX plugin should own reusable design guidance; Archive should route to canonical sources, store public evidence and verify coverage, avoiding duplication. No application or plugin updates performed in this audit. Remaining: complete large catalog and nested-reference review and validate proposed workflows before publishing a plugin update.
