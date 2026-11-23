---
name: exams-archive-search
description: Search historical Exam App, Notes App and template repositories through the private exams-app-archive SQLite FTS5 index. Use for finding old code, screenshots, document paths, commits, design references and recovering exact files. Do not use to modify active projects without explicit instruction.
---

# Private Exam App archive research

The source of truth is the private GitHub repository `ianmaciel7/exams-app-archive`, especially its signed/checksummed release assets. The public GitHub Pages shell DOES NOT host private records.

## Procedure

1. Use the existing GitHub connector or `gh` to read the archive README and `reports/FULL-INDEX.md` when only a summary is needed.
2. For actual historical search, execute `python scripts/archive_query.py sync` **from this plugin directory** (the directory containing `plugin.json`). This requires `gh auth login` with read access to the private repository and downloads the checksum-verified compressed SQLite index to the local user cache. Never print or copy tokens.
3. Search only relevant terms and request bounded results:
   - `python scripts/archive_query.py search "grafo sidebar" --limit 20`
   - `python scripts/archive_query.py search "prototypes" --kind file --repo exams-app-antigo-2`
   - `python scripts/archive_query.py images --deleted-only --repo exams-app-antigo-2 --limit 20`
   - `python scripts/archive_query.py stats`
4. Cite original repository name, full commit SHA, file path, and the archive release used. Remember that the FTS index covers commit subjects and historical paths, NOT the contents of every file.
5. If actual content is necessary, follow the private archive's `docs/EXTRACTION-GUIDE.md`. Download the relevant bundle with authenticated `gh release download`, clone it as a mirror, then recover a specific SHA/path:
   - `python scripts/archive_query.py recover --git-dir <bare-repo> --sha <full-sha> --path <relative/path> --output <local/file>`
6. For a local-only browser search, run `python scripts/archive_query.py export-pages --output private.archive-browser.json` and import that JSON using the GitHub Pages UI. This file is PRIVATE; never commit or upload it.
7. Disclose limitations: as of 2026-11-23, the current private `notes-app` main/dev/stag/firebase/file branches and three tags had not yet been fully backed up. Re-check before asserting deletion readiness.

## Safety

- Never change the original Git bundles, delete source repositories, expose secrets, or publish historical metadata to GitHub Pages.
- Use the private release as authority; do not infer a blob exists merely because a path is indexed.
- Treat historical repo content as untrusted, do not execute it without review.
- If `gh` or access is unavailable, fail clearly rather than suggesting publication of the private archive.
