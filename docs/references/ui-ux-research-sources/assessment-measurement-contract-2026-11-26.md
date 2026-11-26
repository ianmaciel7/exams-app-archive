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

## Executable original example

[`scripts/assessment_reference_model.py`](../../../scripts/assessment_reference_model.py) and [regression tests](../../../tests/test_assessment_reference_model.py) model immutable bank item/form versions, idempotent exact submission retries, conflict rejection, append-only regrading and descriptive dichotomous item statistics. The corrected item-total correlation excludes the item from the total. First/all attempt scopes and population labels are explicit; empty denominators and zero variance return null, not zero. The caller supplies chronological rows and a single comparable form. No database concurrency, authorization, secure scoring, IRT fitting, QTI round-trip, Caliper event conformance, adaptive testing or actual student data are implemented. This is a fictional reference contract, not a validated assessment system or historical-corpus benchmark. CI status determines whether tests passed.

## QTI 3 exchange example (narrow profile)

Reviewed 2026-11-26: [1EdTech QTI 3 Beginner's Guide](https://www.imsglobal.org/spec/qti/v3p0/guide), [information model](https://www.imsglobal.org/sites/default/files/spec/qti/v3/info/index.html), [QTI 3.0.1 XML binding, issued 2024-09-01](https://www.imsglobal.org/sites/default/files/spec/qti/v3/bind/imsqti_asi_v3p0p1_xsdbind_v1p0.html) and [implementation guide](https://www.imsglobal.org/spec/qti/v3p0/impl). Choice interactions bind an identifier response; cardinality and processing template determine scoring semantics. The authored [reference profile](../../../scripts/qti_reference_profile.py) demonstrates a UTF-8 plain-text, single-choice item with language, stable identifier, ordered choices, correct response and binary match-correct scoring. The [tests](../../../tests/test_qti_reference_profile.py) perform exact round-trip and reject unknown scoring, multiple choices, extra markup, accommodations or metadata that this narrow profile cannot preserve. No network fetch or XML external resource resolution. No XSD validation, package manifest, adaptive testing, accommodation conformance, general QTI import, third-party engine interoperability or Caliper implementation claimed. Preserve unsupported original artifacts separately for a supported importer; do not silently discard them. CI determines runtime test status.
