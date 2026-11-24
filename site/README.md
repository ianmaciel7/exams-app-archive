# Exams Archive Pages

Public static shell for the archive. The GitHub repository is public. Only `site/index.html`, `site/style.css`, `site/app.js`, `site/.nojekyll`, `site/llms.txt`, `site/files.html`, and `site/files.js` may be deployed or used. The explorer imports locally selected JSON with `File.text()`: it does not fetch, upload, transmit, persist, or log the data.

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

- **Allowlist gate**: Only `site/index.html`, `site/style.css`, `site/app.js`, `site/.nojekyll`, `site/llms.txt`, `site/files.html`, and `site/files.js` are included.
- **Strict Content Security Policy (CSP)**: `default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'`.
- **Local search**: no network calls, telemetry, cookies or storage. The separate Files view makes explicit unauthenticated reads to api.github.com for the two allowlisted public repositories. Local imports are not transmitted.
- **Zero-Emoji Policy**: Pure monochromatic SVG and text UI without Unicode emojis.

## Limitations

Searches cover file paths, commit messages and image records; not full source text. Exact recovery requires the corresponding private Git bundle and full SHA.

## Agent and graph interfaces

The public catalog works without an import. Import a graph export (`nodes` + `edges` or `links`) to explore typed relationships locally. See [Agent access](../docs/AGENT-ACCESS.md) for CLI and MCP. The site also serves `llms.txt`. The packaging allowlist includes this curated text file; no historical JSON is published.

## Files and components

Open [Files view](files.html) for historical public Git trees, source inspection and local HTML previews. See [Component explorer](../docs/COMPONENT-EXPLORER.md) for reviewed React build workflows.

## Graphify-inspired knowledge workspace

Graphify's HTML exporter motivated degree-scaled nodes, imported community colors, a group sidebar, confidence-styled edges and a node inspector. Reference: https://github.com/Graphify-Labs/graphify/blob/v8/graphify/exporters/html.py. The native SVG implementation has no CDN/runtime dependency; it bounds the visible view to 100 nodes and 800 relations, with group aggregation for larger datasets and 1–3 hop expansion. Graphify JSON supports nodes/links, community fields and relation confidence. Imported data remains local. The initial catalog is a bounded sample of **public** Git tree paths from two pinned old Exams repositories plus archive documentation; its edges are file containment, not a semantic Graphify extraction. Groups without imported community IDs are structural (repo/directory/type). No private dataset is packaged.

### Expanded public search catalog

The initial graph now uses eligible code, documents, and images from pinned public dev snapshots of exams-app, exams-app-old and exams-app-antigo-2. It is path/name search, not full-text search. The query parameter `?q=sidebar` pre-fills the search. Original-file links use the verified commit. Private historical records still require local import or authenticated recovery.

## Dynamic public catalog

The browser consumes generated `catalog.json` (schema v2), not hardcoded file paths. `scripts/build_public_catalog.py` enumerates all branches and tags in the explicit public-source policy, checks visibility at build time, resolves immutable trees, excludes sensitive path patterns and refuses truncated results. Duplicate content versions are grouped by repository/path/blob with ref aliases in the graph. GitHub Actions regenerates on site/config changes and twice daily. The same manifest drives the file explorer. It contains metadata only; private bundles, content search, semantic edges and reviewed component builds remain separate. Full historical deleted paths and private refs require authenticated access. For local testing generate the manifest with `gh` or import a historical JSON.

### Graph motion

Inspired by the official Graphify v8 HTML exporter (vis-network / ForceAtlas2, damping, bounded stabilization, hover and animated camera focus): https://github.com/Graphify-Labs/graphify/blob/v8/graphify/exporters/html.py. Exams Archive retains its local SVG renderer, using bounded requestAnimationFrame force iterations, previous visible positions, direct node dragging with incident edges, hover neighborhood emphasis and eased camera movement. The animation toggle and prefers-reduced-motion bypass motion. This is not the ForceAtlas2 solver itself; the visible subset remains bounded. CI tests settling, camera zoom, node dragging and reduced motion controls.
