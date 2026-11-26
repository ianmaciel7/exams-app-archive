# Data visualization and evidence coverage — 2026-11-26

Dated product documentation and historical promotional stills. Counts are catalog records, not a percentage of product coverage. No authenticated runtime tests performed.

## Data model comparison

| Surface | Data model | Interaction boundary | Source |
|---|---|---|---|
| ChatGPT Visualize | Snapshot generally; Site separate | Input control state varies; no live sync guarantee | [Official](https://learn.chatgpt.com/docs/visualizations) |
| Claude Data | Per-chart query; refresh on open when due | Direct content editing and reviewed query changes; live-share access separate | [Official](https://support.claude.com/en/articles/17454700-get-started-with-claude-data) |
| Grok Bot Pages | Stored page; Bot updates same object | Reader filters and toggles do not persist | [Official](https://docs.x.ai/grok-bot/files-and-results) |
| Gemini Canvas app | Generated app code and optional data storage | App data can persist; public sharing can expose shared state | [Official](https://support.google.com/gemini/answer/16419134?hl=en-gi) |
| Gemini Notebook data table | Generated source synthesis; export creates a separate snapshot | Customization prompt shapes schema; exported sheet is not live linked | [Official](https://support.google.com/gemininotebook/answer/16206563?hl=en-CA) |
| Google Sheets canvas (adjacent product) | Interactive views over one spreadsheet tab | Kanban movement/date changes can update backing sheet; gallery, calendar and dashboard examples | [Official](https://support.google.com/docs/answer/17035851?hl=en-GI) |

Related reference: Sheets canvas supports generated kanban, gallery, calendar and dashboard views over one tab; data updates in a semester planner example can flow in both directions; access matches the spreadsheet. This is not the Gemini app Canvas. [Help](https://support.google.com/docs/answer/17035851?hl=en-GI) · [Semester planner example](https://blog.google/products-and-platforms/products/workspace/gemini-google-workspace-back-to-school/). Test move/update, source writeback, conflicts, filters, shared access and single-tab constraint.

## Product observations

- **Generated visualization recovery and replacement (ChatGPT Space):** The Visualize guide distinguishes controls such as adjustable inputs, pause/restart and step navigation from the generated result itself. Follow-up can replace the visualization; blank output recovery includes one reload, retry or simplifying the dataset. A durable hosted application is a Site. Acceptance (not executed): Verify control semantics, keyboard, state reset, failure fallback and replacement identity; no claim of uniform controls. [Official source](https://learn.chatgpt.com/docs/visualizations).

- **Chart query lineage and data freshness (Claude):** A chart can expose its underlying query and last refresh time; title, caption and chart are directly editable. This is an inspectable metric provenance pattern rather than an assurance that a query is correct. Acceptance (not executed): Verify query access, data definition, units, last refresh, editor controls and unauthorized access. [Official source](https://support.claude.com/en/articles/17454700-get-started-with-claude-data).

- **Certified metric queries (Claude):** The beta query workflow has a certification toggle, additional context, Test and Publish; certification appears after a check. Non-certifying edits lose the badge; removing certification removes the badge from dependent dashboards. Acceptance (not executed): Test pending verification, failed query, publish authorization, uncertified edit and dependent badge revocation. [Official source](https://support.claude.com/en/articles/17454700-get-started-with-claude-data).

- **Read-only version preview and shared restore (Claude):** Dashboard version history includes direct edits; preview is read-only, restore creates its own history entry and changes the shared dashboard for readers. Acceptance (not executed): Test preview vs restore, edit authorization, concurrent viewers, invalid versions and recovery. [Official source](https://support.claude.com/en/articles/17454700-get-started-with-claude-data).

- **Scoped live data sharing (Claude):** By default viewers use their own connector access. Live sharing lets organization readers see results under the sharer's access, limited to dashboard queries; changing queries requires editor approval. This is separate from scheduled refresh, which the guide does not promise. Acceptance (not executed): Verify query scope, approval, revocation, stale saved results and scheduled-vs-on-open distinction. [Official source](https://support.claude.com/en/articles/17454700-get-started-with-claude-data).

- **Mind map branch disclosure and contextual chat (Gemini Notebook (formerly NotebookLM)):** Current Mind Maps help documents zoom, scroll, expand/collapse branches and node selection to ask a scoped chat question, along with full-view and download controls. The mobile app is not supported in this guide. Acceptance (not executed): Test keyboard node traversal, collapse state, zoom limits, chat focus, download restriction and mobile availability. [Official source](https://support.google.com/gemininotebook/answer/16212283).

- **Schema-directed data table generation (Gemini Notebook (formerly NotebookLM)):** Customization allows specifying language and desired rows/columns through a prompt. The generated table is source-grounded and can be exported; the examples are not fixed schema templates. Acceptance (not executed): Verify source selection, custom columns, citations, empty/missing data, long cells, export and accessibility. [Official source](https://support.google.com/gemininotebook/answer/16206563?hl=en-CA).

- **Focused chat view versus security boundary (Gemini Notebook (formerly NotebookLM)):** Chat View hides source/artifact surfaces for a focused experience, but does not revoke underlying notebook access. Public artifact links have different sign-in behavior from whole notebook links. Acceptance (not executed): Test hidden vs denied resources, direct links, role changes and sharing warning. [Official source](https://support.google.com/gemininotebook/answer/16206563?hl=en-CA).

- **Source Q&A versus experimental agentic chat (Gemini Notebook (formerly NotebookLM)):** The chat guide describes source-grounded answers and citation navigation, but separately lists experimental agentic capabilities with or without sources (research, code and file/chart outputs). Do not equate these modes or promise all answers are source-only. Acceptance (not executed): Test explicit source mode, external sources, tool action review and unsupported export; distinguish generated claims and citations. [Official source](https://support.google.com/gemininotebook/answer/16179559).

- **Initial automatic artifact generation (Gemini Notebook (formerly NotebookLM)):** The notebook creation guide says some first-source sessions can generate an initial report, study aid or media artifact automatically once, outside normal generation limits. Acceptance (not executed): Check user visibility, cancel/disable if available, unwanted output cleanup and quota; do not infer universal trigger. [Official source](https://support.google.com/gemininotebook/answer/16206563?hl=en-CA).

## Visual evidence

- [Customize Data Table dialog](https://storage.googleapis.com/gweb-uniblog-publish-prod/original_images/2_Customization.png) — Historical promotional screenshot, 1000 x 593 image. Header and close icon, language selector, labeled prompt area with examples, primary Generate button in footer. No loading/focus state shown. official historical promotional image visually inspected 2026-11-26; still only.
- [Generated Data Table with source column](https://storage.googleapis.com/gweb-uniblog-publish-prod/original_images/3_Output_example_1.png) — Historical promotional screenshot, 1000 x 631 image. Table title, source-count subtitle, header action icons, multi-column content with wrapped cells and row source references. Icon actions and sorting behavior not verified from pixels. official historical promotional image visually inspected 2026-11-26; still only.
[Publisher article, December 2025](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-data-tables/). No redistribution, exact viewport dimensions, motion or interaction measurement claimed.

## Coverage by product

| Product | Views | Outputs | Feature observations | Creation options | Documented flows | Contracts | Availability rows | Inspected stills | Visual leads |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ChatGPT Space | 14 | 8 | 17 | 30 | 3 | 0 | 3 | 7 | 0 |
| Claude | 6 | 8 | 24 | 7 | 2 | 1 | 6 | 1 | 2 |
| Grok Bot | 7 | 8 | 18 | 2 | 4 | 0 | 1 | 1 | 7 |
| Gemini | 7 | 13 | 10 | 6 | 3 | 0 | 2 | 0 | 8 |
| Gemini Notebook (formerly NotebookLM) | 7 | 11 | 32 | 5 | 2 | 2 | 3 | 2 | 6 |

Inspected stills include previously cataloged marketing examples and one GIF frame; not current runtime tests. Zero recorded rows does not mean a feature is absent. No verified motion timings.

## Remaining blockers

- Live authenticated interfaces not exposed by available browser tabs; read-only browser context cannot open/control them.
- No cross-account access or state mutation tests; no frame timing or current DOM/CSS measurement.
- Independent annotated holdout for retrieval not yet available.
