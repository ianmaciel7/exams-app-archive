# Agent entry point

Read README.md and docs/CONCEPT-KNOWLEDGE.md before organizing archive knowledge. Use scripts/concept_packs.py for topic-oriented public research and scripts/research_index.py for exact public records. Historical evidence must be recovered using the authenticated documented archive path, never copied into public exports. Keep original files immutable, preserve SHA/path/source and distinguish historical facts, external references, proposals and inferences. Report missing evidence instead of inventing it. Do not execute legacy code or expose private material. Follow docs/PLUGIN-SYNC.md when changing installed plugin behavior.

For focused public research use the two-step `python scripts/archive_context.py resolve` then `context` with canonical ID and returned snapshot. See docs/CONTEXT-RETRIEVAL.md. Never replace a requested historical version with current external research.
