# Evidence-based issue remediation — 2026-11-26

Scope: public archive only. No private data, active app or historical bundle changes. Baseline: 451e1d712017dc75d2ed7489f563949fb8f7527d.

| Issue | Current delivery | Still required before closure |
|---|---|---|
| #94 | Public production runner separated from scoring; legacy report warnings; tests for label rejection and actual ranking metrics. | Independently annotated holdout, real corpus and agents, mutation/CI evidence, actual citation and privacy gates. |
| #95–#101 | Ten source-backed [structured records](ui-ux-research-sources/domain-research-2026-11-26.json) added to canonical research index across all seven issues. | Domain research, structured ingestion, original demos, verified retrieval and evidence. |
| #102 | Automated exact source URL coverage and missing status/relations diagnostics in existing research index audit. | Automated cross-domain coverage, status reconciliation, source and evidence verification. |
| #103 | Corrected canonical opaque token pairs; automated contrast check and regression test. | Browser states, forced colors, composite surfaces, rendered examples and retrieval validation. |
| #104–#105 | Existing [decision and transition synthesis](ui-ux-research-sources/design-foundations-and-state-transitions-2026-11-25.md). | New independent research, transition demos, state coverage and tested retrieval. |
| #106 | Historical image retrieval labels metadata honestly: filename-derived, no visual inspection, no verified states, unverified branch freshness; authorized local blob locator. | Actual image inspection, pinned targeted byte recovery, labelled multilingual evaluation across domains. |

Do not close issues based on this table or on synthetic unit tests. A separate production evaluation is required. For the public-only retrieval runner, provide independently curated query-only JSON (id/query), capture results using `python scripts/production_retrieval_eval.py run queries.json capture.json`, then separately score using `python scripts/production_retrieval_eval.py score capture.json labels.json score.json`. Labels map query IDs to relevant production hit IDs. Do not publish private queries or labels. No independent gold set or actual agent test is claimed in this change.
