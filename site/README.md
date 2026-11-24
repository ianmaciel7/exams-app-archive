# Exams Archive Pages

Public static shell for the archive. The GitHub repository is public. Only `site/index.html`, `site/style.css`, `site/app.js`, `site/.nojekyll`, and `site/llms.txt` may be deployed or used. The explorer imports locally selected JSON with `File.text()`: it does not fetch, upload, transmit, persist, or log the data.

## Setup & Platform Availability

1. **GitHub Pages availability**: On GitHub Free accounts, GitHub Pages is restricted to public repositories (calling Pages enablement on private repos returns HTTP 422: `Your current plan does not support GitHub Pages for this repository`). For a private repository a paid plan is required. This public repository can use GitHub Free, configured in **Settings → Pages → Source: GitHub Actions**. Note: if enabled, a Pages site is **publicly visible**, despite a private repository.
2. **Offline & Local Execution (No Paid Service Required)**:
   The static shell in `site/` works completely offline without any internet connection or cloud service:
   ```bash
   # Option A: Local lightweight HTTP server
   python3 -m http.server 8080 --directory site

   # Option B: Direct file opening
   # Open site/index.html directly in Chrome, Firefox, Safari or Edge
   ```
3. Run the `Archive Pages` workflow or push the site on `main`. Its upload artifact includes ONLY the allowlisted static files, never the private index, docs, releases, or bundles. If GitHub Pages is unavailable due to account plan restrictions, the workflow verifies and validates the static shell safely without failing.
4. Authenticate locally with `gh auth login`. From `plugins/exams-archive`, run:
   ```bash
   python scripts/archive_query.py sync
   python scripts/archive_query.py export-pages --output private.archive-browser.json
   ```
5. On the Pages website or local offline explorer (`http://localhost:8080` or `file://...`), select the generated JSON file. Search stays 100% in the browser and disappears on refresh. The JSON contains potentially sensitive paths; do not publish or commit it.

The site is a LOCAL index viewer, not a searchable public mirror. There are no secrets and no API endpoints in the deployed artifact.

## Security & Privacy Verification

- **Allowlist gate**: Only `site/index.html`, `site/style.css`, `site/app.js`, `site/.nojekyll`, and `site/llms.txt` are included.
- **Strict Content Security Policy (CSP)**: `default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'`.
- **Zero Network Calls**: No outgoing telemetry, analytics, cookies, local storage, or server communication.
- **Zero-Emoji Policy**: Pure monochromatic SVG and text UI without Unicode emojis.

## Limitations

Searches cover file paths, commit messages and image records; not full source text. Exact recovery requires the corresponding private Git bundle and full SHA.

## Agent and graph interfaces

The public catalog works without an import. Import a graph export (`nodes` + `edges` or `links`) to explore typed relationships locally. See [Agent access](../docs/AGENT-ACCESS.md) for CLI and MCP. The site also serves `llms.txt`. The packaging allowlist includes this curated text file; no historical JSON is published.
