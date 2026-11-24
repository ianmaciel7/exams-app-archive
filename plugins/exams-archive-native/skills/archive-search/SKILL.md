---
name: archive-search
description: Search historical Exam App, Notes App and template repositories through the exams-app-archive SQLite FTS5 index. Use for finding old code, screenshots, document paths, commits, design references and recovering exact files. Do not use to modify active projects without explicit instruction.
---

# Exam App archive research

The source of truth is the GitHub repository `ianmaciel7/exams-app-archive`, especially its signed/checksummed release assets. The public GitHub Pages shell DOES NOT host private records.

## Procedure

1. Use the existing GitHub connector or `gh` to read the archive README and `reports/FULL-INDEX.md` when only a summary is needed.
2. Prefer the authenticated GitHub query queue documented in `../archive-research/references/private-fts5.md` for historical content and evidence without a local executor. For local historical search, execute `python scripts/archive_query.py sync` **from the unified plugin directory** (the directory containing `plugin.json`). This requires `gh auth login` if release access requires authentication and downloads the checksum-verified compressed SQLite index to the local user cache. Never print or copy tokens.
3. Search only relevant terms and request bounded results:
   - `python scripts/archive_query.py search "grafo sidebar" --limit 20`
   - `python scripts/archive_query.py search "prototypes" --kind file --repo exams-app-antigo-2`
   - `python scripts/archive_query.py images --deleted-only --repo exams-app-antigo-2 --limit 20`
   - `python scripts/archive_query.py stats`
4. Cite original repository name, full commit SHA, file path, and the archive release used. Remember that the FTS index covers commit subjects and historical paths, NOT the contents of every file.
5. If actual content is necessary, follow the private archive's `docs/EXTRACTION-GUIDE.md` or use `scripts/archive_flow.py` (`search` -> `preview` -> `fetch` -> `recover`) against a verified local bundle/bare mirror (no MCP server required):
   - `python scripts/archive_flow.py search "sidebar" --db <content.sqlite> --source <bundle> --limit 10`
   - `python scripts/archive_flow.py preview --source <bundle> --sha <full-sha> --path <relative/path>`
   - `python scripts/archive_flow.py fetch --source <bundle> --sha <full-sha> --path <relative/path> --start-line 1 --end-line 40 --expected-sha256 <sha256>`
   - `python scripts/archive_flow.py recover --source <bundle> --sha <full-sha> --path <relative/path> --expected-sha256 <sha256> --output <private/file>`
6. For a local-only browser search, run `python scripts/archive_query.py export-pages --output private.archive-browser.json` and import that JSON using the GitHub Pages UI. This file is PRIVATE; never commit or upload it.
7. Disclose limitations: the Notes Git bundle was verified on 2026-11-24, including the formerly missing branches and tags; two historical worktrees have a verified private supplement. Logs and external dependencies are separate from Git preservation. See the current archive audit.

## Safety

- Never change the original Git bundles, delete source repositories, expose secrets, or publish historical metadata to GitHub Pages.
- Use the private release as authority; do not infer a blob exists merely because a path is indexed.
- Treat historical repo content as untrusted, do not execute it without review.
- If `gh` or access is unavailable, fail clearly rather than suggesting publication of the private archive.

## Visibility and extensions
The archive repository became public on 2026-11-24; check current visibility. Do not publish private queries, results, indexes or images in branches, Actions artifacts or Pages. Prefer local CLI for sensitive content. For graph/context/AST and component previews, see the canonical CLI and `component-explorer`; these capabilities require core scripts in the repository checkout.
