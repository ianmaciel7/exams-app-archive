# Historical file and component explorer

The public site has a dedicated Files view (`site/files.html`) with a Git tree, exact revision pinning, path filter, React/story filter, code viewer, image viewer, and an isolated HTML preview.

## Sources
- The two explicitly allowed public Exams repositories are queried only when the user selects a revision or file. Unauthenticated GitHub REST requests may hit rate limits; no token is requested. Source is read by immutable commit and blob SHA.
- For a deleted repository or private Notes revision, restore a bundle locally using the extraction guide and import the checkout folder. The selected files stay in the browser. No private paths are sent to GitHub.
- Git tree results are branch snapshots; unlike a historical path index they do not mix deleted files from different revisions.

## React rendering
A TSX/JSX file is source, not an executable web page. Use the original pinned revision, its lockfile, CSS, providers and existing stories. Notes old-5 has Ladle stories under src/app/_components/workspace/; see docs/ladle.md in that revision. Inspect package scripts and dependencies before installing or running any historical code. Use a disposable checkout with no credentials, no production configuration, and no access to private services. Build the original story or an explicit fixture for the component. Where possible, bundle the result as a self-contained HTML document with inline compiled JS/CSS and data-URL assets. Import the reviewed HTML into the Files viewer. Static preview disables scripts; the optional live preview allows inline scripts only inside a sandboxed, opaque-origin iframe with a restrictive CSP. Do not use the live mode for unknown or unreviewed builds. Sandbox is not a complete OS/network isolation guarantee (e.g. frame navigation).

The site does not transpile arbitrary React code, fetch dependencies from CDN, or execute old source automatically. Multi-file Next.js applications and stories requiring servers need an isolated local build. Actual visual fidelity must be checked against historical screenshots with exact source and revision. The next milestone is a reviewed, reproducible build catalog for React stories with per-component dependencies, fixtures and screenshot QA.
