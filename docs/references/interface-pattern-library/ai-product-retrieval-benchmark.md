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
