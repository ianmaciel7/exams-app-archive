# Learning evaluation contract (#96)

Original proposed evaluation, not an experiment that has been run. Sources and caveats live in [domain research](domain-research-2026-11-26.md). Use original or licensed equivalent items, not restricted exam material.

| Outcome | Definition | Required denominator / limits |
|---|---|---|
| Immediate practice accuracy | Correct first responses during practice | Scored first responses; report missing and repeated responses separately |
| Delayed retention | Recall after prespecified interval without answer reveal | Eligible delayed-test items and participants; report attrition and elapsed time |
| Transfer | Unseen items requiring application to new contexts | Separate near and far transfer, exclude exposed items |
| Workload | Actual active review time and due backlog | Report time distribution, skipped and overdue items |
| Calibration | Agreement of predicted recall probability with observed delayed outcomes | Versioned scheduler predictions, chronological held-out reviews, sample size; undefined when no data |

## Design and state contracts

Recall before reveal; preserve original attempt, explanation version, review grade, timestamp, scheduler version and due date. Distinguish new, learning, due, overdue, relearning, suspended, skipped and completed. Do not erase review history on preference changes. Offer pause and accessible feedback, preserve backlog even when a daily limit hides cards, and show workload separately from retention target. A schedule change is not evidence of better learning.

## Proposed evaluation protocol

Predefine population, primary endpoint, time horizon, comparable original items, allocation, sample size and attrition handling. Compare matched exposure and time; use independent delayed items, record baseline knowledge and report uncertainty. Randomize participants or appropriately counterbalance item groups; avoid spillover and account for repeated observations. Keep evaluation items and labels outside the scheduler. No claim of efficacy from completion counts, streaks, immediate accuracy or synthetic simulations. Do not label a fixed interval heuristic as FSRS; pin a real scheduler version and validate held-out calibration if implementing it. Review cognitive load and metacognition with additional primary research before assigning evidence grades.

References: [Dunlosky et al. 2013](https://pubmed.ncbi.nlm.nih.gov/26173288/), [Anki Deck Options](https://docs.ankiweb.net/manual/deck-options), [Brunmair & Richter 2019](https://pubmed.ncbi.nlm.nih.gov/31556629/), [Wisniewski et al. 2020](https://pubmed.ncbi.nlm.nih.gov/32038429/), [Butler 2010](https://pubmed.ncbi.nlm.nih.gov/20804289/). Public abstracts and Anki documentation reviewed; no full systematic review or human study performed.
