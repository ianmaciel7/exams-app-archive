# Context-oriented retrieval (Context7-inspired)

## Agent contract

1. Resolve a concept before querying its content. If the input names distinct concepts, resolve each and query separately unless their relationship is the subject.
2. Pass the returned canonical ID and exact catalog snapshot to the context command. A revision mismatch is explicit; no silent fallback or historical substitution.
3. Ask a specific question. Use product filters when the question refers to a named product. Retrieve source-authored excerpts and media pointers, not whole catalogs.
4. Check missing modalities, omitted results, candidate labels and provenance. Fetch the original record when necessary. Do not infer historical implementation from external research.
5. Historical retrieval remains authenticated and separately scoped. A historical contract must pin repo/ref/commit, index release and checksum; no public queries containing private details.

```sh
python scripts/archive_context.py resolve "barra lateral"
python scripts/archive_context.py context ui.navigation.sidebar "personalized sidebar examples" --snapshot <returned-sha256>
python scripts/archive_context.py context ui.interaction.reorder "sortable list" --product dnd-kit --max-bytes 5000
```

The result is compact JSON with an exact UTF-8 output budget (not an estimated token count), contextual breadcrumbs, typed snippets, sources, content fingerprints, availability, declared licenses, and explicit gaps. It ranks title and selected catalog fields, gives priority to curated membership, and interleaves evidence types. Identical visual blobs are grouped with all occurrences, subject to the response budget. It is a public-only projection and not an embedding service or LLM-generated synthesis. The snapshot is a content fingerprint of the loaded catalog, not an upstream product version; prior snapshots must be restored from their original Git revision.

## Research and transfer

- [Context7 library indexing](https://context7.com/docs/adding-libraries): explicit source inclusion, canonical library resolution, versioned retrieval; [Context7 skill](https://github.com/upstash/context7/blob/master/skills/find-docs/SKILL.md): focused queries, code and informational snippets; [freshness](https://context7.com/docs/library-updates): refresh policy. Adaptation: curated catalogs and canonical concept IDs, pinned inputs, focused retrieval, provenance and eventual incremental refresh. Unlike current-doc retrieval, preserve all historical revisions.
- [Sourcegraph context](https://sourcegraph.com/docs/cody/core-concepts/context): lexical and structural code search; reuse historical symbol and evidence graph engines rather than indexing a second copy.
- [GraphRAG](https://microsoft.github.io/graphrag/): group summaries and global/local retrieval; use taxonomy overviews and bounded evidence neighborhoods, not mandatory LLM summaries.
- [Anthropic Contextual Retrieval](https://www.anthropic.com/research/contextual-retrieval): enrich chunks before ranking; here use deterministic concept/catalog/title breadcrumbs and selected fields. Benchmark richer contextual BM25 or optional embeddings on real missed queries before replacing FTS5.

## Remaining work (#77)

Unify the public and authenticated historical adapters using a scope-aware common interface, with immutable version references, a freshness manifest, incremental content-hash invalidation, semantic chunking (code symbols, document sections, motion sequences), precise citations, concept summaries with supporting evidence and real gold-set evaluations. Expose through existing CLI/MCP and each installed plugin only after regression and access tests. Do not send historical data to Context7 or other third parties. Do not claim installed plugin synchronization from a repository commit.
