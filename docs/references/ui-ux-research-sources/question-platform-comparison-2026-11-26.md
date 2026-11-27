# Question platform evidence and proposed contracts (#95)

Scope: documented features, not current authenticated UI reproduction. D = documented; U = not established in reviewed evidence. Source links: [domain catalog](domain-research-2026-11-26.md).

| Capability | QConcursos | TEC Concursos | Crucial Exams | ExamTopics |
|---|---|---|---|---|
| Search and filters | D: board, topic, role, organization, year, personal history | D: notebook filters | D: certification objectives/domains | U: previous direct access blocked |
| Saved collections | D: saved filters and notebooks | D: notebooks, error notebooks | U: general saved-question sets | U |
| Response feedback | D: answer then result and study resources | D: teacher commentary, not universal coverage | D: Study Mode explanation | U |
| Simulation | D: custom count and duration, history, Elite variants | D: thematic blocks (provider tools documentation) | D: timed custom practice | U |
| Difficulty | D: difficulty filter | D: teacher/observed correctness classification | U: method | U |
| Mobile | U: specific states | D: provider claims responsive experience | D: provider claims synced progress | U |
| Pause/resume/expiry/error | U | U | U | U |
| Keyboard/AT, actual mobile layout | U | U | U | U |

TEC tools source: https://tecconcursos.zendesk.com/hc/pt-br/articles/48231250314523-Principais-ferramentas-do-Tec-Concursos (public text reviewed; no independent runtime verification). No restricted question content or screenshots retained.

## Proposed domain identity

- Competition (concurso): recruiting process; notice (edital): versioned official terms; organization (órgão): hiring entity; examining board (banca): organizer; position (cargo): role. Do not collapse these into one label. A competition can contain several assessments, positions and dates.
- Assessment/exam: versioned form and administration; certification: credential and exam blueprint; question/item: versioned prompt and scoring policy; discipline and topic: learning taxonomy; year: explicit year dimension (publication, administration or notice), not inferred from title.
- Saved query: live criteria; notebook: explicit membership; practice form: fixed selection and mode; attempt: responses, timings and lifecycle; result: grading policy revision and denominator. Preserve source metadata and aliases.

## Proposed original workflow and tests

Filter -> preview selection -> configure mode/count/time -> start immutable attempt -> select answer -> save draft -> next/previous/flag -> finish confirmation -> idempotent submission -> review result. Study mode may reveal feedback after individual submission; timed test policy may defer feedback. Test no results, invalid count, cancelled confirmation, unanswered/flagged states, persistence error and retry, reload, deadline expiry, accessible announcements, item annulment/version change and regrading without rewriting original response. These are proposed Exam App contracts, not observed third-party states. A timer policy must specify whether time continues while disconnected or paused and use a trusted deadline in production.

Remaining: actual authorized visual/state tests, plan/version availability, more Brazilian and international platforms, accessibility and mobile inspection, independent retrieval evaluation, plugin synchronization.

Executable original state reference: [Timed attempt state contract](timed-attempt-state-contract-2026-11-26.md). No third-party runtime claims.
