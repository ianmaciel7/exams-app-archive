# Concept-organized knowledge

The archive keeps immutable historical sources and derived indexes separate. This first implementation is a topic-oriented projection over the existing **public research catalog**, not a second database or an authenticated historical index.

## Use

```sh
python scripts/concept_packs.py "barra lateral"
python scripts/concept_packs.py "painel lateral"
python scripts/concept_packs.py "reorder" --limit 8
python scripts/concept_packs.py --audit
python -m unittest discover -s tests -p test_concept_packs.py
```

The versioned taxonomy in `config/knowledge-concepts.json` uses stable IDs, bilingual labels, aliases, broader concepts and explicitly curated memberships, inspired by [SKOS](https://www.w3.org/TR/skos-primer/). Lexical candidates are separately labeled and never asserted as equivalent. Concept groups combine multiple catalogs while maintaining evidence type, source, date, original record hash, availability and license. Identical visual blobs are grouped without dropping occurrences. Results allocate evidence across modalities, report truncation and missing types, and list unclassified records for review. Querying an ambiguous or unknown term must not silently invent knowledge. Source-only records remain retrievable through research_index.py.

## Next integration gates

- Reuse the historical glossary, context linker, evidence graph and authenticated content index. Map concept IDs explicitly, not by filename alone. Keep private source material and query logs in the authenticated channel; never publish private context packs.
- Adopt a common versioned envelope for historical and research evidence: scope, entity ID, relationship, exact source pointer, source revision, validity interval, evidence class, derivation version, and confidence. Do not treat proposals, inferred relationships and original implementation as interchangeable.
- Add hierarchical topic overviews with citations, followed by bounded entity-local retrieval; inspired by [GraphRAG](https://microsoft.github.io/graphrag/) without requiring a hosted model or another database.
- Preserve conflicts and superseded versions. Deduplicate by exact content identity only; similar evidence is related, not identical.
- Evaluate real queries (sidebar versus side panel, tab pin versus pinned object, motion, deleted files, screenshots, architecture decisions) against expected source IDs and required evidence types; report recall, precision, missed evidence, cost and latency. Run across all clients before claiming synchronized behavior.
- Add multimedia segmentation and provenance when licensed and available; do not assert visual understanding from a filename.
- Keep public/private access gates, independent encrypted restore testing, and versioned plugin publishing. No changes to backup bundles or credentials are part of this projection.

## Scope

This module does not change existing FTS5 behavior, execute archived code, use embeddings, summarize private records, or guarantee complete historical coverage. The taxonomy is intentionally small and auditable. Expand it via review of the unassigned report; do not force every record into a group.

Each occurrence exposes compact, source-authored catalog statements and original media pointers where present. The result is evidence navigation rather than an AI-generated synthesis. Multiple independently named concepts are returned separately, even when one phrase is longer.
