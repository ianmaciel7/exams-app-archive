# Domain research extracts — 2026-11-26

Public source-backed decisions; proposed tests have not been executed on a product. No private records or restricted assets. This is not exhaustive coverage.

## Question filtering and saved filters (#95)

Aliases: filtros de questões, QConcursos, banca, cargo, saved filters.

Decision: Combine exam attributes, keyword and exclusions; make the applied criteria visible and removable.

Limits: Do not confuse employer, examining board, position, exam year and discipline. Do not assume unseen filter states.

Acceptance: Given a saved filter, restore the same criteria; verify zero results and clearing a single criterion.

Source: [QConcursos help — question filters](https://suporte.qconcursos.com/pt-BR/articles/12118570-como-usar-os-filtros-de-questoes). Access checked 2026-11-26; link-only, media not inspected.

## Question notebook and saved sets (#95)

Aliases: caderno de questões, revisão, question collection.

Decision: Distinguish a selected question set from a live filter and a scored attempt.

Limits: The documentation describes creating notebooks; it is not proof of how all mobile or offline states work.

Acceptance: Check set membership, duplicates, empty set, and changes to source questions.

Source: [QConcursos help — question notebook](https://suporte.qconcursos.com/pt-BR/articles/11655308-como-criar-um-caderno-de-questoes). Access checked 2026-11-26; link-only, media not inspected.

## Retrieval and distributed practice (#96)

Aliases: prática de recuperação, repetição espaçada, practice testing, distributed practice.

Decision: Plan opportunities to recall information and distribute study across time, rather than only reread material.

Limits: Evidence for learning techniques is not validation of a particular app or scheduling algorithm; retention and transfer differ.

Acceptance: Compare delayed recall using equivalent items and record exposure, study time and attrition.

Source: [Dunlosky et al. (2013) — learning techniques review](https://pubmed.ncbi.nlm.nih.gov/26173288/). Access checked 2026-11-26; link-only, media not inspected.

## Assessment item and test interoperability (#97)

Aliases: QTI, questão, gabarito, tentativa, assessment.

Decision: Separate assessment item, test, response and result; use QTI for portable structured assessments where required.

Limits: Interoperability does not imply validity or calibrated difficulty. Do not apply IRT without calibration data.

Acceptance: Round-trip an original fictional item and check response identifiers, scoring and result versioning.

Source: [1EdTech — QTI](https://www.1edtech.org/standards/qti). Access checked 2026-11-26; link-only, media not inspected.

## Typed knowledge objects and relations (#98)

Aliases: PKM, objetos, Capacities, knowledge graph, backlinks.

Decision: Model reusable connected objects rather than forcing every record into a file hierarchy.

Limits: Documentation establishes the object-oriented concept, not all interaction states or historical app decisions.

Acceptance: Check stable identity, reference integrity, missing target and reversible type changes.

Source: [Capacities documentation](https://docs.capacities.io/). Access checked 2026-11-26; link-only, media not inspected.

## Typed nodes and fields (#98)

Aliases: Tana, supertag, propriedades, fields, nodes.

Decision: Use explicit type and field definitions for structured nodes; views can present the same data in different contexts.

Limits: Do not assume inheritance, sync or deletion semantics without feature-specific evidence.

Acceptance: Check required/optional fields, type changes and stale references in original examples.

Source: [Tana documentation — Supertags](https://outliner.tana.inc/learn/features/supertags). Access checked 2026-11-26; link-only, media not inspected.

## Annotation anchor resilience (#99)

Aliases: PDF, anotação, highlight, TextQuoteSelector, TextPositionSelector.

Decision: Separate annotation body, target and selector. Text quotes with context can help reanchor; positions are vulnerable to content edits.

Limits: Never silently reattach an ambiguous selection; avoid copying restricted text into exported annotations.

Acceptance: Test version change, repeated quotes, no match, changed offsets and explicit unresolved state.

Source: [W3C — Web Annotation Data Model](https://www.w3.org/TR/annotation-model/). Access checked 2026-11-26; link-only, media not inspected.

## Accessible component behavior contract (#100)

Aliases: componentes, design system, React Aria, keyboard, focus.

Decision: Define semantics, input behavior, keyboard, focus and states separately from visual tokens.

Limits: Library accessibility claims do not establish product-level conformance; verify actual composition.

Acceptance: Exercise keyboard, pointer and touch; test disabled, busy and invalid states and accessible names.

Source: [Adobe — React Aria](https://react-aria.adobe.com/). Access checked 2026-11-26; link-only, media not inspected.

## ARIA widget interaction patterns (#100)

Aliases: ARIA APG, roles, teclado, widget, acessibilidade.

Decision: Select the matching widget semantics and keyboard interaction contract; prefer native elements where appropriate.

Limits: APG is implementation guidance, not a substitute for WCAG conformance testing.

Acceptance: Validate accessible role/name/state, focus sequence and restoration, and screen-reader operation.

Source: [W3C — ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/). Access checked 2026-11-26; link-only, media not inspected.

## Data visualization palette semantics (#101)

Aliases: DataViz, gráfico, categorical, sequential, diverging, dashboard.

Decision: Choose categorical colors for unordered categories, sequential for magnitude, and diverging for a meaningful center.

Limits: Color must not be the only cue; distinguish missing values from zero and category from status.

Acceptance: Check legend/labels, contrast, textual alternative and meaningful ordering with original sample data.

Source: [IBM Carbon — Data visualization color palettes](https://www.carbondesignsystem.com/building-blocks/data-visualization/color-palettes). Access checked 2026-11-26; link-only, media not inspected.

## Additional verified public documentation

### Saved filters and exam attempts (#95)

Save and reopen search criteria independently of the scored attempt. The help article places save and reopen controls below filtering.

Limits: Do not assume that a saved filter freezes the set of items; distinguish query definition, notebook membership and attempt snapshot.

Acceptance: Change the source set and compare saved query results against immutable attempt membership.

Source: [QConcursos — saved filters](https://suporte.qconcursos.com/pt-BR/articles/11664140-como-salvar-e-acessar-seus-filtros). Link-only; product behavior and media not inspected.

### FSRS review scheduling (#96)

Deck settings include scheduling, desired retention, daily review limits and FSRS parameters. Higher retention targets trade review workload against expected forgetting.

Limits: A target retention is an algorithmic objective, not a guaranteed outcome. Preserve review history and model version.

Acceptance: Use fictional review histories, test schedule reproducibility and compare calibration on independent delayed recall.

Source: [Anki manual — deck options](https://docs.ankiweb.net/manual/deck-options). Link-only; product behavior and media not inspected.

### Learning activity event interoperability (#97)

Use shared event vocabularies and profiles to capture learning activity across providers.

Limits: Activity is not the same as measured learning outcome; avoid causal claims from clicks and time spent.

Acceptance: Validate event schema, duplicate delivery, timestamps and distinction between event and scored outcome.

Source: [1EdTech — Caliper Analytics](https://www.1edtech.org/standards/caliper). Link-only; product behavior and media not inspected.

### Object query versus collection (#98)

Queries can filter by object type, tags and linked objects. Model dynamic query results separately from explicit collections.

Limits: Do not infer every product state from the documentation; preserve object identity and permissions.

Acceptance: Compare a saved query before and after tag changes, and test inaccessible and deleted references.

Source: [Capacities — Queries](https://docs.capacities.io/reference/queries). Link-only; product behavior and media not inspected.

### Combobox popup focus (#100)

Combobox keyboard navigation and focus behavior depend on popup type; a dialog popup receives DOM focus.

Limits: Do not apply listbox focus semantics to a dialog. Native select may suffice.

Acceptance: Verify tab, arrows, Escape, selection, focus restoration and accessible state in a real browser.

Source: [W3C APG — combobox](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/). Link-only; product behavior and media not inspected.

### Static table versus interactive grid (#101)

An interactive grid has a managed keyboard navigation model; ordinary tabular data may use a semantic table.

Limits: Do not replace a static table with a grid role simply for visual styling. Editing controls can compete with arrow navigation.

Acceptance: Validate row/column announcements, keyboard movement, edit mode and accessible fallback.

Source: [W3C APG — grid](https://www.w3.org/WAI/ARIA/apg/patterns/grid/). Link-only; product behavior and media not inspected.

### Common region and visual hierarchy (#104)

A perceptible container groups related elements and can outweigh proximity. Choose containment when it clarifies relationships.

Limits: Do not surround all elements with cards or assume grouping guarantees task success.

Acceptance: Compare a list and grouped variant with real search tasks and comprehension measures.

Source: [NN/g — The Principle of Common Region](https://www.nngroup.com/articles/common-region/). Link-only; product behavior and media not inspected.

### View transition lifecycle and fallback (#105)

View transitions expose lifecycle and skip functionality for visual changes. Application state and focus must be resolved independently of animation.

Limits: Feature-detect, preserve an immediate fallback and avoid assuming support across all browsers or accessibility modes.

Acceptance: Test unsupported API, interrupted transitions, reduced motion and route changes without animation.

Source: [MDN — View Transition API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API). Link-only; product behavior and media not inspected.
