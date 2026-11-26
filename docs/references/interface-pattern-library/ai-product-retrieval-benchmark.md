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

## Artifact compatibility and budget-accounting audit

Downloaded artifact 15127632547 and verified its SHA-256. All four captures share the same snapshot and query set. Decoded compact occurrences using the v1 inheritance mask, then compared by query and hit ID to the full expanded capture. 55/55 compact hits and 57/58 relevance-first hits matched the corresponding full record exactly. The remaining hit was not present in the expanded capture, so its independent full-record equivalence is unverified. The combined 113 records occupied 209,518 canonical JSON UTF-8 bytes vs 242,160 after decoding (13.48% smaller). [Audit data](../../../tests/evaluation/ai-product-compact-compatibility-audit-2026-11-26.json). This is artifact-level compatibility, not a test of every consumer.

**Budget correction:** the reported budget caps the metadata reserve, not the actual full serialized envelope. For relevance-first, max reported total was 1,999, while the uncapped sum of envelope_tokens and results_tokens had median 2,276, maximum 2,458, and exceeded 2,000 for 20 of 22 queries. For Gemini-01, the reported 1,807 consists of 500 reserved metadata + 1,307 results; uncapped envelope 959 + results 1,307 = 2,266. These estimates omit final response overhead and use characters/4 rather than a model tokenizer. Accordingly, 100% recall is measured at a **configured allocation budget of 2,000**, not a strict full-model-context ceiling of 2,000. Do not promote the experiment on the basis of an end-to-end token-limit claim. A follow-up should measure the actual consumer payload and define a separate compact context projection vs complete audit ledger before changing any limit or interface. No ranking change.

## Optional bounded consumer projection

The `scripts/public_context_payload.py` adapter separates the model-facing JSON from the complete retrieval audit. It retains complete selected snippets, source URLs, original IDs, occurrence aliases, provenance status and pointers; excludes scores, duplicated fields and verbose audit metadata from the model-facing object. The full audit stays separate and is linked by SHA-256. The projection is intentionally lossy as a wire format; it is not the audit itself. Oversize entries are skipped whole with omission counts. No ranker, default response or private retrieval change. The exact canonical serialized context (including envelope, separators and omission fields) is checked against the configured character-based estimate and optional UTF-8 byte limit; tokenizer counts, other prompt messages and transport overhead are outside this contract.

Example local CLI (new audit file required; no overwrite):

```sh
python scripts/public_context_payload.py "study progress" --budget-tokens 2000 --audit-output audit.json --compact-occurrences --relevance-first > context.json
```

Only `context.json` is the bounded model-facing object. Keep `audit.json` out of the model prompt and use it for source verification. The CLI does not store an audit service or change MCP clients. The benchmark now records the complete expanded-occurrence audit and projection of its relevance-first arm before labels are read; the post-capture comparator checks digest, exact projection, budget and named-target recall including occurrence aliases. All measurements remain development regressions. No new independent judgments or production adoption. Results pending.
