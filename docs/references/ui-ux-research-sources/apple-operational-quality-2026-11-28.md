# Apple-derived operational quality — 2026-11-28

Original synthesis and operational enrichment of the [coverage audit](apple-skills-gap-audit-2026-11-28.md). All 13 identified improvement areas are documented; no runtime compliance or exhaustive corpus review claimed. The three shared skills own the detailed acceptance contracts. They are identical across the two published private plugin releases, as read back via Plugin Creator; public mirror is reviewed via PR. No active application changes.

- [adaptive-workspace-design](../../../plugins/exams-archive-native/skills/adaptive-workspace-design/SKILL.md)
- [runtime-ui-verification](../../../plugins/exams-archive-native/skills/runtime-ui-verification/SKILL.md)
- [agent-action-context-quality](../../../plugins/exams-archive-native/skills/agent-action-context-quality/SKILL.md)

## Index

The [structured catalog](apple-operational-quality-2026-11-28.json) explicitly records 13 operational enrichments, not 13 newly discovered universal concepts. Existing conceptual records retain their identities. The proposed public index projection includes source and record provenance and a dedicated test. Do not treat an unmerged PR or unrun CI as a deployed index.

- **HIG selective source routing / roteamento de conhecimento** — Select foundations, platform and task article; bounded related expansion; classify primary guidance vs interpretation. Acceptance: Trace each recommendation to source, version, platform or project choice; no ungrounded native-to-web rules.
- **Continuous adaptive resize / redimensionamento contínuo** — Container-local constraints, stable state, collapse order and focus recovery. Acceptance: Narrow-wide-narrow, zoom, long labels, splitter cancel; preserve selection, scroll and draft.
- **Toolbar priority and overflow / prioridade de comandos** — Explicit command groups and deterministic overflow with essential actions reachable. Acceptance: Test width thresholds, localization, keyboard/touch, anchor and focus return.
- **Window, tab and panel lifecycle / restauração do workspace** — Separate object identity, view instance and durable state; dispose on close. Acceptance: Test duplicate opening, reopen, restore, scope isolation, close active and history.
- **Document autosave, undo and recovery / recuperação de documentos** — Revision-guard saves, recoverable drafts, undo scope, conflict handling. Acceptance: Test edit during save, offline, retry, conflict and reload; no false saved state.
- **Multimodal gesture ownership / conflitos de gestos** — Define precedence of press, scroll, drag, pinch and selection; provide alternative inputs. Acceptance: Test pointercancel, nested scrolling, long press, keyboard reorder, no duplicate action.
- **Runtime accessibility evidence / acessibilidade real** — Automated and manual semantic, keyboard, assistive technology and composited contrast checks. Acceptance: Record tested AT/version, focus, reflow, reduced motion, failures and not-run checks.
- **Functional visual evidence / captura e comportamento** — Bind deployed revision, fixture, screenshot, semantic tree, interaction assertion and logs. Acceptance: Reproduce requested state and verify behavior; screenshot alone not proof.
- **Comparable performance profiling / medição de desempenho** — Repeat same workload and environment; preserve raw samples, distinguish hypotheses from measurement. Acceptance: Baseline vs candidate with correctness, cancellation, variance and explicit attribution.
- **Privacy-bounded telemetry / telemetria com privacidade** — Typed allowlist, low-cardinality metadata, bounded retention and authorized export. Acceptance: Assert no private payload, unknown fields or unintended network export.
- **Agent action contracts / ferramentas de IA** — Stable identifiers, typed schemas, deterministic authority, side effects and idempotency. Acceptance: Test duplicate request, cancellation, stale outputs, permissions, uncertain outcome reconciliation.
- **Agent action evaluation / avaliação de agentes** — Versioned fixtures test tool selection, arguments, forbidden effects, fallback and schema. Acceptance: Isolated fixtures with hidden labels, record denominator and failures; separate retrieval metrics.
- **Conversation transcript lifecycle / gerenciamento de contexto** — Selective skill loading, compact completed exchanges, preserve durable decisions and pending calls. Acceptance: Measure token/latency and context-loss regressions in long sessions; preserve authorization boundaries.
