# Historical file and component explorer

The public site has a dedicated Files view (`site/files.html`) with a Git tree, exact revision pinning, path filter, React/story filter, code viewer, image viewer, and an isolated HTML preview.

## Sources
- The two explicitly allowed public Exams repositories are queried only when the user selects a revision or file. Unauthenticated GitHub REST requests may hit rate limits; no token is requested. Source is read by immutable commit and blob SHA.
- For a deleted repository or private Notes revision, restore a bundle locally using the extraction guide and import the checkout folder. The selected files stay in the browser. No private paths are sent to GitHub.
- Git tree results are branch snapshots; unlike a historical path index they do not mix deleted files from different revisions.

## React rendering
A TSX/JSX file is source, not an executable web page. Use the original pinned revision, its lockfile, CSS, providers and existing stories. Notes old-5 has Ladle stories under src/app/_components/workspace/; see docs/ladle.md in that revision. Inspect package scripts and dependencies before installing or running any historical code. Use a disposable checkout with no credentials, no production configuration, and no access to private services. Build the original story or an explicit fixture for the component. Where possible, bundle the result as a self-contained HTML document with inline compiled JS/CSS and data-URL assets. Import the reviewed HTML into the Files viewer. Static preview disables scripts; the optional live preview allows inline scripts only inside a sandboxed, opaque-origin iframe with a restrictive CSP. Do not use the live mode for unknown or unreviewed builds. Sandbox is not a complete OS/network isolation guarantee (e.g. frame navigation).

The site does not transpile arbitrary React code, fetch dependencies from CDN, or execute old source automatically. Multi-file Next.js applications and stories requiring servers need an isolated local build. Actual visual fidelity must be checked against historical screenshots with exact source and revision. The next milestone is a reviewed, reproducible build catalog for React stories with per-component dependencies, fixtures and screenshot QA.

## First reviewed React render

The deployment workflow builds the original public `exams-app-old@b86b70c304e574022416e8e2ecdc3816f1b386f1:src/app/loading.tsx` from a pinned byte-identical source (`5850f0972153976a33e3e42e0891f9f23ac8bad8`). The build refuses a different Git blob. It uses React DOM Server, TypeScript and equivalent CSS utilities, with a different pinned React runtime from the historical lockfile. It is an SSR preview, not a full historical app or a pixel-verified reproduction. The generated preview is deployed as `preview-loading.html` by GitHub Actions only.

## Interactive React + screenshot catalog

The reviewed ErrorBoundary is the exact public source from exams-app-old at commit b86b70c304e574022416e8e2ecdc3816f1b386f1, blob 936e638aa231a2533e866c12e4d97a429c524d6c. Its original retry button calls a fixture callback (counter). A theme control is provided by the fixture. The build uses pinned React/esbuild dependencies, equivalent CSS and no network access. It is not a pixel-verified historical environment.

Install optional tooling locally:

```sh
npm install --prefix ~/.cache/exams-app-archive/component-previews/preview-deps --no-save --ignore-scripts react@19.1.1 react-dom@19.1.1 esbuild@0.25.5
python -m pip install 'playwright>=1.49,<2'
python -m playwright install chromium
```

CLI (same commands in both plugin mirrors):

```sh
python plugins/exams-archive/scripts/archive_query.py components list
python plugins/exams-archive/scripts/archive_query.py components render error-boundary
python plugins/exams-archive/scripts/archive_query.py components capture error-boundary --state retry --theme dark --width 390 --height 844
python plugins/exams-archive/scripts/archive_query.py components screenshots --component error-boundary
python plugins/exams-archive/scripts/archive_query.py components export SCREENSHOT_ID --output component.png
```

MCP stdio tools: components_list, component_render, component_capture, component_screenshots, component_screenshot_image. The final tool returns PNG bytes as an MCP image. The local SQLite catalog stores PNG BLOB, full commit, source path/blob, build SHA-256, state, theme, viewport, timestamp and PNG SHA-256. The database is not published by Pages. CLI and MCP operate on the same local cache; no daemon, no second historical index, no arbitrary historical code execution. Component coverage is currently one interactive reviewed source; expand the allowlist through explicit source/dependency review and fixture QA.
