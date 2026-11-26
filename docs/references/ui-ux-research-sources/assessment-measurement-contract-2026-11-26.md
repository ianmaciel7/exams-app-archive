# Assessment measurement contract

This is an original proposed domain model, not an implementation of Enem, QTI certification or a validated psychometric model.

| Entity | Identity and meaning | Invariant |
|---|---|---|
| Item | Stable bank ID plus immutable version | Corrections create a version or grading policy revision |
| Assessment | Edition, form, item-version references and grading policy | Publication freezes references |
| Attempt | Assessment/version, start/end, state, accommodations | Submission idempotent; attempt is not reusable filter |
| Response | Attempt + item-version, value and timestamps | Preserve original submitted response |
| Result | Response evaluation, score, grading-policy version | Regrade adds audit entry; original result retained |
| Rubric | Criteria, levels and applicable version | Not equivalent to multiple-choice answer key |
| Analytics | Population, inclusion criteria, time and denominator | Undefined metrics remain N/A |
| Calibrated item parameters | Model, calibration population, scale and uncertainty | Do not infer from a single user's accuracy |

## Fictional example

Eight correct of ten attempts is 80% observed accuracy. Item facility over five distinct first attempts with marks [1,1,0,0,1] is 60% for that sample. Neither establishes ability on the Enem scale, item discrimination, reliability or mastery. An item with no response variation cannot have a defined Pearson correlation with total score. Repeated attempts must be labeled separately.

## Decisions

- Classical test theory statistics and item response theory calibration answer different questions. Do not convert accuracy into an official score.
- QTI describes exchange structure; Caliper describes learning-activity events. Neither proves learning gains or validates a scoring model.
- Accessibility and fairness require assessment-specific review, not simply a standards logo.
- The public Inep process documentation, Moodle 5.3 report, 1EdTech version comparison and the joint Testing Standards publication index are linked in the canonical domain catalog. No full-book review or psychometric calibration performed.
