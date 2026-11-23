# Exams Archive — Codex plugin

Portable, skill-only plugin. No MCP service and no inference-based indexing. Reads the authenticated private release locally.

## Install and use

1. Clone the private repository (a GitHub credential with read access is required).
2. Authenticate with `gh auth login`.
3. In Codex desktop, add the repo marketplace (in `.agents/plugins/marketplace.json`) or run `codex plugin marketplace add ./` from the repository root, then install **Exams Archive**. You may also use `codex plugin marketplace add ianmaciel7/exams-app-archive` if your GitHub authentication can read the private repository.
4. Instruct Codex: **Use Exams Archive to find old graph screenshots**.
5. Or run directly from this plugin folder: `python scripts/archive_query.py sync`, then `python scripts/archive_query.py search "grafo"`.

`sync` checks the private release asset SHA-256 against the private report before installing the SQLite file. `export-pages` generates local **private** JSON for the browser portal, never a site artifact.

The snapshot is historical. Its FTS queries cover paths and commit subjects, not full file content. See `docs/EXTRACTION-GUIDE.md` at the archive repository root for bundle-based recovery.

Do not publish the generated JSON or share the SQLite file. GitHub Pages is a PUBLIC shell with a LOCAL importer only.
