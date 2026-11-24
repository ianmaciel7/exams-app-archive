# Dynamic archive architecture

## Decisions

- Git and bundles are the durable source; the public site consumes a generated metadata manifest, not a manually edited list.
- Public-source policy: only explicitly approved repositories whose current visibility is public; do not publish the private archive index, private Notes history, screenshots or secrets.
- Refs are discovered automatically; tree enumeration and immutable SHA provenance; duplicate file versions deduplicated by repo/path/blob. Current catalog does not include every deleted historical commit.
- Existing SQLite/FTS5 stays canonical for authenticated historical lookup. A future public full-text projection may use Pagefind chunked search or SQLite WASM with HTTP-range compatibility proof. Do not expose the canonical private database.
- Graphify deterministic AST extraction plus optional semantic extraction, incremental by content hash; preserve edge confidence and source. Sigma.js/Graphology for large interactive graphs. Current public graph remains structural, not semantic.
- Ladle/Storybook static builds and story metadata; Playwright capture with fixtures, viewport, theme, source/build hashes. Only reviewed builds execute. Local SQLite screenshot catalog stays private by default.
- CLI and MCP should read the same versioned dataset and report indexed versus uninspected coverage. No database per client.

## References

- https://github.com/Graphify-Labs/graphify
- https://www.sigmajs.org/concepts/rendering/
- https://pagefind.app/
- https://github.com/phiresky/sql.js-httpvfs
- https://ladle.dev/docs/meta/
- https://ladle.dev/docs/visual-snapshots/
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

## Acceptance

1. New public file or branch appears after regeneration without edits to site code.
2. Searching and file tree use the same generated manifest. No silent fallback to a fixed sample.
3. Private repo or truncated tree fails closed; failed build does not replace deployed catalog.
4. Graph semantic extraction and component build coverage tracked separately; no false claims of complete coverage.
5. Regression tests validate new refs, path filtering, private rejection, and browser search. Deployment success must be confirmed separately.
