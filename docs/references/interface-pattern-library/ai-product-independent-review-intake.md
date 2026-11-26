# Independent review intake — AI product retrieval

Status: **awaiting independent reviewer**. The assistant that designed the previous suite and modified ranking cannot serve as its independent evaluator. Do not reuse prior labels or infer correct answers from existing retrieval order. This document freezes the procedure, not a populated holdout set. No results or certification are claimed.

## Assignment

1. An independent reviewer writes a fresh set of at least 25 answerable questions (at least five per product), and five clearly unrelated/unsupported negative questions. Mix Portuguese and English; include object identity, state persistence, access, failure recovery, exact UI evidence, and cross-product disambiguation. Include questions where a source URL is useful and where a visual lead is insufficient. Use fictional examples, public sources only, no private content.
2. Freeze the query JSON and pin corpus/ranker revision before any runs. Preserve the author's identity or pseudonymous reviewer identifier, timestamp, and hashes separately. The assistant does not author the final held-out questions or relevance labels.
3. Independent reviewer records the intended answer and acceptable evidence identifiers from original sources without seeing retrieval scores. Include alternative equally valid sources and distinguish historical screenshots, documented behavior and measured runtime findings. Record uncertain judgments explicitly. A second reviewer resolves disagreements when possible.
4. Run the unchanged default and experimental configuration against the same snapshot, identical queries, 2,000 estimated tokens and result limit. Pool unique hits from both plus independently identified records, remove ranking scores/configuration and shuffle deterministically. Keep the ID map out of the ranker. The reviewer assigns grades 0 (irrelevant), 1 (partially relevant), 2 (directly relevant), or null (unjudged), and provenance status. Record pool coverage and answerability; do not count unjudged as confirmed irrelevant.
5. Freeze judgments, then score once. Compare mean target recall, per-query losses, MRR, judged precision/nDCG with explicit denominator, negative abstention, diversity by requested evidence type, and exact provenance round-trip. Assess actual answers against primary sources separately. Report latency across repeated comparable runs if needed.

## Suggested acceptance decision, to approve before reviewing

- No previously recovered named target lost on the development regression suite; all existing public regression gates and scope-isolation checks pass.
- Independently judged recall improves or stays equal, with no material deterioration in judged precision, answer grounding or negative abstention. Report per-query and per-product trade-offs; no universal quality threshold inferred from this small sample.
- Provenance, source links, original IDs and distinct occurrences reconstruct exactly. Existing clients retain compatible full representation or explicitly opt in to the compact encoding. No private retrieval path change.
- Reviewer signs off on any diversity or relevance trade-off; document disagreements and limitations. Do not alter ranker, budget or acceptance rules after seeing holdout results. A changed candidate requires a new independent validation set.

## Submission schema (blank)

- reviewer_id, role, independent_of_tuning (boolean), frozen_at, corpus_commit, ranker_commit, queries_sha256
- queries: [{id, query, product, information_need, answerability, primary_source_urls, acceptable_evidence_ids}]
- judgments: [{query_id, record_id, grade, provenance_status, rationale, reviewer_id}]
- adjudications: [{query_id, record_id, reviewer_ids, resolved_grade, rationale}]
- judgments_sha256, signoff, unresolved_limitations

No reviewer data or private credentials should be published without authorization. If no independent reviewer or permitted session is available, retain pending status rather than manufacturing labels. See issue #114 and the separate runtime verification plan.
