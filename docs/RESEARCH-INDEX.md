# Unified public research index

This explicit, offline FTS5 projection indexes the general and workspace pattern catalogs, official source registers, the new visual library and Grok Bot media manifest. Source IDs resolve against the corresponding catalog. Each result contains its catalog path, SHA-256, original record and links. No private sources or bundles are read. Records are namespaced; a repeated pattern from separate sources is not silently merged.

```bash
python scripts/research_index.py --coverage
python scripts/research_index.py 'side panel' --kind pattern
python scripts/research_index.py 'vídeo' --kind visual
python scripts/research_index.py 'shared layout' --db .cache/public-research.sqlite
```

Rebuilds from source on every invocation; persisted databases are derived and should stay out of Git. Lexical search with limited PT/EN alias expansion is not semantic/vector search. No claim of historical context-pack or multi-agent runtime integration; those remain tracked in #45, #64, #65 and #70. Tests exercise ingestion, source resolution and queries. This is a first public research projection, not a replacement for the authenticated historical index.
