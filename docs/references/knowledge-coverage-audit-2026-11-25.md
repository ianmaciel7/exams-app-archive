# Knowledge coverage audit — 2026-11-25

Status: initial public-source research intake, not a completed domain audit or proof of indexing. All source evidence is public. Historical encrypted bundles were not opened in this audit. Do not infer absence from a single catalog. The canonical implementation backlog is #95–#102, with benchmark integrity #94 as a cross-cutting dependency.

## Observed inventory

At snapshot `9cd43924f43796b0dbadf8c3d0e68c89ac5e7093`, the main interface pattern catalog contains 423 unique source URLs, 47 patterns, and 30 source IDs directly referenced by those patterns; 393 lack that direct relation (other catalogs may contain links), and 79 lack a status field. The main visual evidence manifest contains 49 records, of which 23 are archived blobs and 26 are link-only. The concept catalog contains 38 records. See [sources](interface-pattern-library/sources.json), [patterns](interface-pattern-library/patterns.json), [visual manifest](visual-evidence-library/manifest.json), and [ingestion audit](../../reports/SEMANTIC-INGESTION-AUDIT.md). Do not conflate differing catalog counts or use these numbers as recall metrics.

## Research intake and issue mapping

| Domain | Verified source or source evidence consulted | Extraction focus | Issue |
|---|---|---|---|
| Question platforms | [QConcursos filters](https://suporte.qconcursos.com/pt-BR/articles/12118570-como-usar-os-filtros-de-questoes), [question workflow](https://suporte.qconcursos.com/pt-BR/articles/11649035-como-resolver-questoes-na-central-de-preparacao), [question notebook](https://suporte.qconcursos.com/pt-BR/articles/11655308-como-criar-um-caderno-de-questoes), [TEC filters](https://tecconcursos.zendesk.com/hc/pt-br/articles/48593690506267--Tutorial-Como-utilizar-os-filtros-do-Tec-Concursos), [TEC error notebook](https://tecconcursos.zendesk.com/hc/pt-br/articles/48591881334939--Tutorial-Como-fazer-um-caderno-de-erros-no-Tec-Concursos), [Crucial Exams](https://crucialexams.com/) | Filters, saved sets, assessment attempts, error review, focus, timer and feedback; deeper UI state audit pending. | [#95](https://github.com/ianmaciel7/exams-app-archive/issues/95) |
| Learning science | [Dunlosky et al. 2013](https://pubmed.ncbi.nlm.nih.gov/26173288/), [APS review summary](https://www.psychologicalscience.org/publications/journals/pspi/learning-techniques.html), [Anki FSRS FAQ](https://faqs.ankiweb.net/what-spaced-repetition-algorithm) | Practice testing and distributed practice have strong review-level support; FSRS is an adaptive scheduling implementation, not proof of individual retention. Extract study scope and limitations. | [#96](https://github.com/ianmaciel7/exams-app-archive/issues/96) |
| Assessment | [QTI](https://www.1edtech.org/standards/qti), [Caliper](https://www.1edtech.org/standards/caliper), [Moodle 5.3 Quiz](https://docs.moodle.org/503/en/Quiz_activity), [H5P](https://h5p.org/content-types-and-applications), [INEP guide located](https://download.inep.gov.br/publicacoes/institucionais/avaliacoes_e_exames_da_educacao_basica/entenda_a_sua_nota_do_enem_guia_do_participante.pdf) | Portable tests/items, activity events, item types, attempts, feedback, scoring and psychometric limitations. INEP PDF requires page-level extraction and verification. | [#97](https://github.com/ianmaciel7/exams-app-archive/issues/97) |
| PKM | [Obsidian Graph](https://obsidian.md/help/plugins/graph), [Tana Supertags](https://outliner.tana.inc/learn/features/supertags), [RemNote Help](https://help.remnote.com/en/) | Graph filters, typed nodes and fields, notes/flashcards and links; compare Capacities and other workspace tools. | [#98](https://github.com/ianmaciel7/exams-app-archive/issues/98) |
| Readers | [Zotero PDF Reader](https://www.zotero.org/support/pdf_reader), [annotation storage](https://www.zotero.org/support/kb/annotations_in_database), [PDF.js](https://mozilla.github.io/pdf.js/), [Hypothesis](https://web.hypothes.is/help/overview-of-the-hypothesis-system/), [W3C Web Annotation](https://www.w3.org/TR/annotation-model/) | Annotation anchoring, persistent data, PDF rendering, resource segments and interoperability. | [#99](https://github.com/ianmaciel7/exams-app-archive/issues/99) |
| Design systems | [React Aria](https://react-aria.adobe.com/), [DTCG](https://www.designtokens.org/), [GOV.BR accessibility](https://www.gov.br/ds/acessibilidade) | Accessible behavior, token exchange, Brazilian accessibility guidance, component states and contracts. | [#100](https://github.com/ianmaciel7/exams-app-archive/issues/100) |
| Data visualization | [Vega-Lite examples](https://vega.github.io/vega-lite/examples/) | Brushing, selection, linked views, pan/zoom and coordinated charts/tables; accessibility and valid metric interpretation. | [#101](https://github.com/ianmaciel7/exams-app-archive/issues/101) |
| Coverage/governance | Internal catalogs and ingestion audit linked above | Source lifecycle, canonical IDs, provenance, freshness, license, deduplication, concept links, contradiction handling, coverage tests. | [#102](https://github.com/ianmaciel7/exams-app-archive/issues/102) |

## Candidate references (not fully inspected in this intake)

- Question platforms: ExamTopics (direct HTTP 403; no restricted exam content), Estratégia Questões, Gran Questões, official exam providers.
- Learning: FSRS implementation, Anki manual, Roediger/Karpicke, Cepeda et al., Sweller; validate original publications and applicability.
- Assessment: AERA/APA/NCME testing standards, ETS, xAPI, LTI, Canvas LMS, OECD/PISA, INEP official data.
- PKM: Capacities (existing partial evidence), Heptabase, Logseq, Anytype, Notion, Linear, VS Code.
- Reader: Readwise Reader (existing partial evidence).
- Design systems: Base UI, Ariakit, Open UI, Spectrum, Fluent, Primer, USWDS, WCAG/APG, WebAIM, axe-core, eMAG; existing Radix/shadcn/Storybook.
- Data visualization: Observable Plot, D3, ECharts, TanStack Table, AG Grid, Tufte, Munzner, Cleveland/McGill, Shneiderman.
- Information retrieval/governance: Software Heritage, Context7, PROV-O, Dublin Core, DataCite, FAIR, Anthropic Contextual Retrieval, BEIR, MTEB, Docling.

Issues contain exact candidate URLs when available, extraction tasks and acceptance checks. A candidate is not a verified source claim. No source media was copied. Do not publish proprietary question content, private data, or restricted media.

## Permanent coverage and acceptance policy

Prioritize depth and evidence over source count. Every domain must report source verification and limitations, concepts, evidence type, applicable behavior/state, accessibility, anti-patterns, example/test, origin/version and links to relevant ADRs/components. Store structured data and Markdown in canonical catalogs after deduplication; validate real CLI/MCP retrieval and source provenance. Measure source coverage separately from retrieval quality and agent response quality; comply with #94. Preserve immutable backups, public/private scope and the [shared UX contract](shared-ux-knowledge/README.md). Publish a real coverage report before claiming completeness. This intake is not yet indexed or synchronized to installed plugins; #95–#102 track implementation.
