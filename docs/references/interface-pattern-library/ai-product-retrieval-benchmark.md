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
