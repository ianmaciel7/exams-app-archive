# Evidence-based issue remediation — 2026-11-26

Scope: public archive only. No private data, active app or historical bundle changes. Baseline: 451e1d712017dc75d2ed7489f563949fb8f7527d.

| Issue | Current delivery | Still required before closure |
|---|---|---|
| #94 | Public production runner separated from scoring; legacy report warnings; tests for label rejection and actual ranking metrics. | Independently annotated holdout, real corpus and agents, mutation/CI evidence, actual citation and privacy gates. |
| #95–#101 | Twenty-six source-backed [structured records](ui-ux-research-sources/domain-research-2026-11-26.json) added to canonical research index across all seven issues. | Domain research, structured ingestion, original demos, verified retrieval and evidence. |
| #102 | Automated exact source URL coverage and missing status/relations diagnostics in existing research index audit. | Automated cross-domain coverage, status reconciliation, source and evidence verification. |
| #103 | Corrected canonical opaque token pairs; automated contrast check and regression test. | Browser states, forced colors, composite surfaces, rendered examples and retrieval validation. |
| #104–#105 | Existing [decision and transition synthesis](ui-ux-research-sources/design-foundations-and-state-transitions-2026-11-25.md) plus [original question transition demo and matrix](ui-ux-research-sources/state-transition-example-2026-11-26.md). | New independent research, transition demos, state coverage and tested retrieval. |
| #106 | Historical image retrieval labels metadata honestly: filename-derived, no visual inspection, no verified states, unverified branch freshness; authorized local blob locator. | Targeted byte recovery implemented with immutable commit/path/blob verification and a local Git regression test. Actual historical image inspection and labelled multilingual evaluation remain required. |

Do not close issues based on this table or on synthetic unit tests. A separate production evaluation is required. For the public-only retrieval runner, provide independently curated query-only JSON (id/query), capture results using `python scripts/production_retrieval_eval.py run queries.json capture.json`, then separately score using `python scripts/production_retrieval_eval.py score capture.json labels.json score.json`. Labels map query IDs to relevant production hit IDs. Do not publish private queries or labels. Public CI executes an 11-query author-curated development sample; independent holdout and actual external agent testing are not claimed.


## Follow-up validation

Plugin Creator readback: Exams Archive v0.8.4, all 25 canonical text files identical to the branch snapshot 8a19538cb48f9ffca71375dfe3cbba607b511f5b. Multiagent plugin validation and archive plugin tests passed at 0d9c1d7b6e238101f461ce0b5739125b7d4fb050. Browser workspace smoke and component preview passed at that commit; the newly added assessment smoke exposed a reset defect (named form control shadowed reset method), fixed in the follow-up. Await CI before claiming the assessment smoke passed. The public evaluation is a development sample, not independent or comprehensive.

## Production ranking baseline and follow-up

The public 11-query development run at 942ef46bb51f56ce06312439cb9463cf05fae7f7 measured recall@20 0.60 (6/10), mean precision@20 0.1818 against incomplete labels, MRR 0.4833, one false positive for the negative case, p50 1.065s/p95 1.836s. This is not independent holdout evidence. Follow-up replaces per-fragment FTS fallback with field-weighted query-concept matching over real records, filters incidental metadata and avoids default code routing on unclassified queries. Re-run the same development sample transparently and use new independent queries for generalization. No claim of improvement until measured.

The ranking revision 35981dc3c504f01a40a18e0df367f77bfc958f4f measured recall 0.80, precision 0.4833, MRR 0.75, abstention on one negative case 1.0, p50 1.691s and p95 3.410s in the same development sample (CI run 45825480465). Caching pure lexical normalization is proposed to address the latency regression; new measurement required. Eight additional sources were reviewed, including two learning research abstracts; product and media inspections remain unperformed.
