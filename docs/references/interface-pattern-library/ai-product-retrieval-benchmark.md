# AI product retrieval benchmark — 2026-11-26

A separate public target-retrieval suite against the existing production federated search, frozen before the first ranking run. Baseline corpus/ranker commit: `b1f7826a2daec4e4e5f82fd3fbd0c5e287980ecc`. No ranker or synonym modifications made as part of suite creation.

- 20 positive questions (four per product: ChatGPT Space, Claude, Grok Bot, Gemini, Gemini Notebook), plus two unrelated negatives. Portuguese and English, with targets for product behavior, visual evidence, flows, availability and interaction contracts.
- [Queries](../../../tests/evaluation/ai-product-queries.json), [target IDs](../../../tests/evaluation/ai-product-labels.json), [workflow](../../../.github/workflows/ai-product-retrieval-benchmark.yml).
- Actual production runner receives query text and ID only. The workflow moves label files before retrieval; scoring happens separately against the recorded capture. Scope is public only. Score and inputs are hash-checked; the report includes per-product results and missed target IDs.
- Targets were annotated by the same research assistant using existing catalog records; they are not a comprehensive relevance assessment. Interpret recall as recovery of named target records, labeled-hit fraction as a diagnostic rather than true precision, and MRR relative to the targets. No independent human holdout is claimed.
- First run is a diagnostic baseline, not a pass/fail quality threshold. Do not tune ranking on these queries and later call them held out. Freeze a different independently annotated set before making a production-quality claim.
- This benchmark does not measure citation correctness, app UI or runtime behavior, answer synthesis, external agents or private archives.

## Remaining work

Independent reviewers must define relevant and irrelevant results, assess equivalent evidence records and judge answer/source grounding without seeing the original rankings first. Product UI verification requires authorized interactive sessions and measurement of actual states. No fabricated measurements.

## Measured baseline and regression classification

The first run on commit `865f5fb3b8e50aed59cfbe3aa3aea469a9e7dbbd` completed successfully: [run 45835682380](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45835682380), [capture artifact](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45835682380/artifacts/15125046781), [baseline metrics](../../../tests/evaluation/ai-product-baseline-2026-11-26.json).

| Metric | Baseline |
|---|---:|
| Mean target recall@20 | 95% |
| Mean labeled-hit fraction@20 | 47.5% |
| MRR | 0.875 |
| p95 | 3.768 s |
| Negative abstention | 2/2 |

The only missed expected record was the Gemini skill-progress dashboard (gemini-01). A plausible cause is missing bilingual vocabulary for state, progress and studies in public lexical ranking. Added domain-neutral term equivalences and a synthetic cross-domain test; no query IDs, gold labels or product-specific rules in the ranker. The original query and target files remain unchanged. Improvement is unconfirmed until the next real run. Because the benchmark informed this change, all subsequent scores are development-regression metrics, not independent validation. An independently annotated set and real UI tests remain required.

## Regression run and budget experiment

[Run 45836462489](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45836462489) retained the same 95% target recall, 0.875 MRR and 2/2 negative abstention; p95 was 5.216 s. The captured Gemini query returned three related records but not the target. The bilingual change did not improve the measured retrieval. No causal latency regression is established from two CI runs. [Measured run](../../../tests/evaluation/ai-product-regression-2026-11-26.json).

The workflow now repeats identical queries at 2,000 and 8,000 token budgets against the same snapshot, with all label files removed before either capture. Captures retain actual budget omissions, gaps and candidate counts. Comparison reports missing, recovered and lost target IDs, estimated token use and negative abstention. The ranker is unchanged in this experiment. Do not enlarge production budgets by default or claim improvement until measured. Independent annotation and live UI verification remain open.

## Measured budget sensitivity and reranking experiment

[Run 45837182187](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45837182187) confirmed 95% mean target recall at both 2,000 and 8,000 tokens. The labeled-hit fraction fell from 47.5% to 11.62%; this is not exhaustive precision. The Gemini target was explicitly omitted for budget in both captures, despite being a candidate. The query retained 3 and 13 results respectively, using estimated 1,977 and 7,812 tokens. [Budget measurements](../../../tests/evaluation/ai-product-budget-measured-2026-11-26.json).

The public candidate ranker already uses bilingual query groups; the previous second-stage BM25 used separately expanded terms and provenance path/domain text. The new public reranking experiment uses the same bilingual concepts, one contribution per group, and title/snippet/product rather than provenance paths. Authenticated ranking, default budget, labels and existing gates remain unchanged. A synthetic test verifies cross-language scoring. No improvement claim until a measured run. CI also now triggers on the workflow permissions inventory, which was previously outside its path filters. Prior test failure was missing inventory documentation, not a permission expansion.

## Measured reranking outcome

[Run 45838090219](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45838090219) completed: default 95% mean target recall, expanded 100%; MRR 0.875/0.8875; negative abstention 2/2 for both. Labeled-hit fraction 47.5%/11.98% (not exhaustive precision). [Full measurements](../../../tests/evaluation/ai-product-reranking-measured-2026-11-26.json). All four general CI jobs passed in run 45838089930. Default budget preserved; compact payload/relevance evaluation remains follow-up. This is development regression, not independent certification.

## Compact context experiment (opt-in)

The repeated occurrence fields in public retrieval hits can consume budget without adding information. The experiment introduces `compact_occurrences=True` for public retrieval only. It preserves source URLs, snippets, IDs, scores, provenance, distinct occurrences, and all differing values. Equal occurrence fields are inherited from primary provenance via a versioned presence mask; `expand_public_hit` restores the full original record, including missing-versus-empty semantics. Default response, authenticated retrieval, ranking and 2,000-token budget remain unchanged.

The workflow captures both full and compact representations with identical 2,000-token budgets before reading labels, plus the existing expanded-budget comparison. Synthetic tests check exact round-trip, smaller estimated payload, preserved identities and scope isolation. The token estimator is character-count based, with reserved envelope accounting; it is not a guarantee of actual LLM tokens or full response length. Do not adopt compact encoding in existing clients before compatibility and benchmark verification. Results pending.

## Measured compact encoding and selection-policy experiment

[Run 45839109901](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45839109901) retained 95% named-target recall at 2,000 tokens for both full and compact representations; MRR 0.875, 2/2 negative abstention. The labeled-hit fraction was 47.5% versus 44.17%. The compact format did not recover the remaining target. [Measurements](../../../tests/evaluation/ai-product-compact-measured-2026-11-26.json).

Inspection of the expanded capture shows the Gemini target had the third-highest fused score among returned hits (0.04840551) but appeared fifth after evidence-type interleaving. The three highest-scored returned hits would require 1,510 estimated tokens in full representation, against a 1,500 result-token allowance. This is evidence of an ordering/budget interaction, not a reason to hardcode Gemini. The new opt-in experiment preserves the top three fused-ranked results before interleaving remaining evidence types, combined with compact encoding at the same 2,000 budget. Existing selection, authenticated scope, labels and gates unchanged by default. Prefix length is an experimental design choice informed by this development suite, not independently optimized. Do not promote without regression and independent evaluation; report any losses in diversity or target recovery. No production adoption or success claimed.

## Development tuning conclusion

[Run 45840281190](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45840281190) succeeded; [measurements and artifact pin](../../../tests/evaluation/ai-product-relevance-first-measured-2026-11-26.json). Same 2,000 estimated token budget, same 22 queries (20 positive, 2 negative, 25 named target IDs):

| Configuration | Mean target recall | Labeled-hit fraction | MRR | Negative abstention |
|---|---:|---:|---:|---:|
| Full, default selection | 95% | 47.50% | 0.875 | 2/2 |
| Compact, default selection | 95% | 44.17% | 0.875 | 2/2 |
| Compact, relevance-first | 100% | 43.33% | 0.8917 | 2/2 |

The last configuration recovered every named target, with 100% target recall for each product and no misses. Four CI jobs passed in [45840281188](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45840281188). Lower labeled-hit fraction is a trade-off; relevance annotations are incomplete, so neither precision gains nor precision losses are established. Latency was similar in this run, not a controlled performance experiment. Engine token estimates exclude some envelope overhead; do not claim exact model token use.

**Decision:** stop tuning on this development set. Preserve defaults and opt-in flags. Before changing defaults, require independent reviewer judgments, a separately frozen query set, per-query relevance/diversity and provenance checks, plus client compatibility. The [review intake](ai-product-independent-review-intake.md) is an unexecuted protocol, not independent evidence. Live product inspection remains separately blocked by session access.
