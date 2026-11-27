# Unified public research index

This explicit, offline FTS5 projection indexes the general and workspace pattern catalogs, official source registers, the new visual library and Grok Bot media manifest. Source IDs resolve against the corresponding catalog. Each result contains its catalog path, SHA-256, original record and links. No private sources or bundles are read. Records are namespaced; a repeated pattern from separate sources is not silently merged.

```bash
python scripts/research_index.py --coverage
python scripts/research_index.py 'side panel' --kind pattern
python scripts/research_index.py 'vídeo' --kind visual
python scripts/research_index.py 'shared layout' --db .cache/public-research.sqlite
```

Rebuilds from source on every invocation; persisted databases are derived and should stay out of Git. Lexical search with limited PT/EN alias expansion is not semantic/vector search. No claim of historical context-pack or multi-agent runtime integration; those remain tracked in #45, #64, #65 and #70. Tests exercise ingestion, source resolution and queries. This is a first public research projection, not a replacement for the authenticated historical index.

## Incremental reconciliation, filters and provenance

```bash
python scripts/research_index.py --audit
python scripts/research_index.py --graph
python scripts/research_index.py sortable --product dnd-kit --availability archived-blob-verified
```

A persisted database now reconciles added, changed and removed records. The public CLI filters by product, source URL, availability, confidence and date range before ranking/limit. The optional local MCP adapter exposes research_search and research_audit. The graph contains only explicit catalog-to-source URL citations; it does not imply equivalence, historical decisions, verified links or actual UI behavior. Audit counts distinguish modality, declared availability and unknown product, with query hit counts rather than invented recall. These are partial deliveries for #64, #65, #67, #72, #74 and #75; no private corpus is ingested and no agent runtime is asserted.

## ClickUp product research

The explicitly approved ClickUp pattern projection links the shared source register and retains original batch pointers, review status and proposed QA. It is a set of product-specific observations rather than a universal pattern taxonomy or verified live UI.

```bash
python scripts/research_index.py sidebar --product ClickUp --kind pattern
python scripts/research_index.py "filter draft" --product ClickUp --kind pattern
python scripts/research_index.py ClickUp --product ClickUp --kind source
```

## Operational index membership

Use `python scripts/research_index.py --coverage --db .cache/public-research.sqlite` to build/reconcile the current explicitly approved public projection and report exact membership counts by catalog. Create the database parent directory first if needed. Use `python scripts/research_index.py --verify-index --db .cache/public-research.sqlite` to check an existing database in read-only mode without rebuilding, returning nonzero for drift. Missing, stale, duplicate and unexpected FTS/metadata entries are reported; the next build repairs them. Empty denominators are unknown, not 100%. This measures stored row membership only, not semantic retrieval accuracy, source completeness, media inspection or private historical coverage.
