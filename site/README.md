# Exams Archive Pages

Public **shell** for a private archive. Only `site/index.html`, `site/style.css`, `site/app.js`, and `site/.nojekyll` may be deployed. The public page imports locally selected JSON with `File.text()`: it does not fetch, upload, transmit, persist, or log the data.

## Setup

1. Configure **Settings → Pages → Build and deployment → Source: GitHub Actions** for the private repo. GitHub Pages availability for a private repository depends on the account plan. Note: a Pages site can still be **publicly visible**, despite a private repository.
2. Run the `Archive Pages` workflow or push the site on `main`. Its upload artifact includes ONLY the allowlisted static files, never the private index, docs, releases, or bundles.
3. Authenticate locally with `gh auth login`. From `plugins/exams-archive`, run:
   `python scripts/archive_query.py sync`
   `python scripts/archive_query.py export-pages --output private.archive-browser.json`
4. On the Pages website, select the generated JSON file. Search stays in the browser and disappears on refresh. The JSON contains potentially sensitive paths; do not publish it.

The site is a LOCAL index viewer, not a searchable public mirror. There are no secrets and no API endpoints in the deployed artifact.

## Limitations

Searches cover file paths, commit messages and image records; not full source text. Exact recovery requires the corresponding private Git bundle and full SHA. Some private Notes App branches remained pending at the last audit.
