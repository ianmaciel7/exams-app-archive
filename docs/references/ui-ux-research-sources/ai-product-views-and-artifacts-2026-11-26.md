# AI product views, artifacts and interactive workspaces

2026-11-26. Companion to [ChatGPT Space benchmark](chatgpt-space-views-and-composable-pages-2026-11-26.md). Public official sources only; no authenticated inspection, no copied media, no private data. Names are product labels or analyst categories, not a unified official taxonomy. Plan/platform/rollout constraints apply. NotebookLM renamed Gemini Notebook on 2026-07-16.

## Claude

### Views and entry points
- Projects
- Artifacts tab
- Side-by-side chat and artifact
- Design canvas
- Installed apps
- Inline connected app

### Creatable outputs (not all are native templates)
- Docs
- Slides
- Design
- Data
- Motion (beta)
- Sheets (beta)
- Whiteboards (beta)
- Interactive tools and dashboards

### Patterns and validation
- **claude-artifact-lifecycle** — Reusable artifact separate from conversation; create, edit, revisit, share; legacy artifacts before 2026-09-16 are distinct. Acceptance: Test reopening, editing, share permissions, plan restrictions. [Source](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them).
- **claude-fine-grained-design** — Direct text edits, element comments and generated adjustment controls for spacing/colors/layout; design system context; handoff bundle. Acceptance: Verify scope of edits, controls via keyboard, review and export. [Source](https://www.anthropic.com/news/claude-design-anthropic-labs).
- **claude-project-context** — Project-level knowledge and instructions organize related conversations; not equivalent to artifact. Acceptance: Test project boundaries and file access. [Source](https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects).
- **claude-installable-artifact** — Desktop installation gives app a separate entry point. Acceptance: Test installation availability, reopening, permissions, uninstall. [Source](https://support.claude.com/en/articles/18516354-install-an-artifact-as-an-app?frmapp=yes).
- **claude-interactive-connectors** — Connected service UI can appear inside chat; distinguish provider actions from generated app. Acceptance: Review tools and permission before actions. [Source](https://support.claude.com/en/articles/13454812-use-interactive-connectors-in-claude).

### Official visual leads
- [Design prototypes and refinement](https://www.anthropic.com/news/claude-design-anthropic-labs) — publisher page with visual examples or documentation; inspect original media separately.
- [Project context and artifacts](https://www.anthropic.com/news/projects) — publisher page with visual examples or documentation; inspect original media separately.

### Sources
- [Artifacts guide](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them) — official source retrieved in research
- [Design help](https://support.claude.com/en/articles/14604416-get-started-with-claude-design) — official source retrieved in research
- [Design launch and visual demos](https://www.anthropic.com/news/claude-design-anthropic-labs) — official source retrieved in research
- [Projects guide](https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects) — official source retrieved in research
- [Projects visual examples](https://www.anthropic.com/news/projects) — official source retrieved in research
- [Install artifact as app](https://support.claude.com/en/articles/18516354-install-an-artifact-as-an-app?frmapp=yes) — official source retrieved in research
- [Interactive connectors](https://support.claude.com/en/articles/13454812-use-interactive-connectors-in-claude) — official source retrieved in research
- [Release notes](https://support.claude.com/en/articles/12138966-release-notes?tab=tab-crm) — official source retrieved in research

## Grok Bot

### Views and entry points
- Chat
- Details
- Library
- Computer
- Pages
- Marketplace
- Routines

### Creatable outputs (not all are native templates)
- Files
- Pages
- Dashboards
- Comparison tables
- Launch/project trackers
- Charts
- Filters and switches
- Routine-generated updates

### Patterns and validation
- **grok-bot-persistent-agent** — Agent has durable identity, job and working context; chat is one entry point. Acceptance: Test agent selection and context boundaries. [Source](https://docs.x.ai/grok-bot/bots).
- **grok-bot-avatar-states** — Idle, Thinking, Working, Waiting, Blocked, Done; motion communicates state, distinguish identity from progress. Acceptance: Provide readable text state and reduced motion; measure timing only from recordings. [Source](https://x.ai/news/designing-grok-bot).
- **grok-bot-execution-visibility** — Show meaningful task execution rather than undifferentiated loading dots. Acceptance: Test blocked/approval/error and actual progress without fake percentages. [Source](https://x.ai/news/designing-grok-bot).
- **grok-bot-pages** — Pages reside in Bot Library; open via chat card; primary page beside smaller chat panel; controls and sharing; gradual rollout, Enterprise excluded per guide. Acceptance: Verify plan, permission, state persistence, loading and export. [Source](https://docs.x.ai/grok-bot/files-and-results).
- **grok-bot-recurring** — Routines run on schedule; can update pages; distinguish saved routine from generated tracker. Acceptance: Verify cadence, run status, review and failure. [Source](https://docs.x.ai/grok-bot/overview).

### Official visual leads
- [Avatar motion and execution states](https://x.ai/news/designing-grok-bot) — publisher page with visual examples or documentation; inspect original media separately.
- [Team and agent UI](https://x.ai/news/grok-bot-1-0?trk=article-ssr-frontend-pulse_little-text-block) — publisher page with visual examples or documentation; inspect original media separately.
- [Page examples and library behavior](https://docs.x.ai/grok-bot/files-and-results) — publisher page with visual examples or documentation; inspect original media separately.

### Sources
- [Designing Grok Bot](https://x.ai/news/designing-grok-bot) — official source retrieved in research
- [Grok Bot overview](https://docs.x.ai/grok-bot/overview) — official source retrieved in research
- [Files and results / Pages](https://docs.x.ai/grok-bot/files-and-results) — official source retrieved in research
- [Get started](https://docs.x.ai/grok-bot/get-started) — official source retrieved in research
- [Create and manage Bots](https://docs.x.ai/grok-bot/bots) — official source retrieved in research
- [Mobile guide](https://docs.x.ai/grok-bot/mobile) — official source retrieved in research
- [Grok Bot 1.0 announcement](https://x.ai/news/grok-bot-1-0?trk=article-ssr-frontend-pulse_little-text-block) — official source retrieved in research
- [Changelog](https://x.ai/changelog/bot) — official source retrieved in research
- [Design marketplace](https://x.ai/bot/marketplace/design) — official source retrieved in research
- [Use cases](https://docs.x.ai/grok-bot/use-cases) — official source retrieved in research

## Gemini

### Views and entry points
- Canvas
- Visual Layout
- Dynamic View
- Gems
- Study Notebooks
- Guided Learning
- Immersive Explorations

### Creatable outputs (not all are native templates)
- Documents
- HTML/React app previews
- 3D visualizations
- Games
- Quizzes
- Flashcards
- Task lists
- Sales trackers
- Pricing calculators
- Slides
- Infographics
- Web pages
- Audio Overview

### Patterns and validation
- **gemini-canvas-edit** — Chat beside editable canvas; Select & ask for scoped edits; previous/next versions; export. Acceptance: Test selection precision, version changes, autosave, keyboard and export. [Source](https://support.google.com/gemini/answer/16047321?hl=en-12).
- **gemini-adaptive-generative-ui** — Visual Layout and Dynamic View were introduced as generative-interface experiments; do not assume universal availability. Acceptance: Test semantic fallback and responsive layout. [Source](https://blog.google/products-and-platforms/products/gemini/gemini-3-gemini-app/).
- **gemini-simulation** — Interactive 3D models and charts for learning. Acceptance: Provide labels, units, keyboard controls and static fallback. [Source](https://blog.google/innovation-and-ai/products/gemini-app/3d-models-charts/).
- **gemini-document-transform** — Create quiz, infographic, web page, audio or slides from a document. Acceptance: Check source traceability and distinguish generated results from original content. [Source](https://support.google.com/gemini/answer/16047321?hl=en-12).
- **gemini-study-space** — Study notebooks synchronize sources across Gemini and Gemini Notebook. Acceptance: Test source selection and cross-app identity. [Source](https://blog.google/innovation-and-ai/products/gemini-app/gemini-study-notebooks/).

### Official visual leads
- [3D game, quiz, dashboard and document examples](https://blog.google/innovation-and-ai/products/gemini-app/gemini-canvas-tasks/) — publisher page with visual examples or documentation; inspect original media separately.
- [Interactive simulations and models](https://blog.google/innovation-and-ai/products/gemini-app/3d-models-charts/) — publisher page with visual examples or documentation; inspect original media separately.
- [Visual Layout and Dynamic View demos](https://blog.google/products-and-platforms/products/gemini/gemini-3-gemini-app/) — publisher page with visual examples or documentation; inspect original media separately.

### Sources
- [Canvas help](https://support.google.com/gemini/answer/16047321?hl=en-12) — official source retrieved in research
- [Canvas examples 2026-11-23](https://blog.google/innovation-and-ai/products/gemini-app/gemini-canvas-tasks/) — official source retrieved in research
- [Visual layout and Dynamic View announcement](https://blog.google/products-and-platforms/products/gemini/gemini-3-gemini-app/) — official source retrieved in research
- [3D models and interactive charts](https://blog.google/innovation-and-ai/products/gemini-app/3d-models-charts/) — official source retrieved in research
- [Immersive explorations](https://blog.google/innovation-and-ai/products/gemini-app/immersive-explorations-student-hub/?trk=article-ssr-frontend-pulse_little-text-block) — official source retrieved in research
- [Study notebooks](https://blog.google/innovation-and-ai/products/gemini-app/gemini-study-notebooks/) — official source retrieved in research
- [Sketch to app](https://blog.google/innovation-and-ai/products/gemini-app/turn-drawings-into-apps-gemini/) — official source retrieved in research
- [Gems mini-apps help (search excerpt; direct fetch redirected)](https://support.google.com/gemini/answer/16802014?hl=en) — search excerpt; direct fetch failed
- [Interactive images](https://blog.google/products-and-platforms/products/education/gemini-interactive-images/) — official source retrieved in research

## Gemini Notebook (formerly NotebookLM)

### Views and entry points
- Notebook collection
- Sources
- Chat
- Studio
- Artifact viewer
- Full-screen study view
- Interactive site

### Creatable outputs (not all are native templates)
- Audio Overview
- Video Overview
- Mind Map
- Reports
- Data Tables
- Flashcards
- Quizzes
- Slide Decks
- Infographics
- Notes
- Interactive Sites

### Patterns and validation
- **gemini-notebook-three-region-shell** — Separate evidence sources, interaction and generated outputs; select sources and label categories. Acceptance: Test independent selection, focus and reflow. [Source](https://support.google.com/gemininotebook/answer/16206563?hl=en-CA).
- **gemini-notebook-source-grounding** — Sources can be selected for chat or outputs; changes/deletion do not automatically update already generated outputs. Acceptance: Show provenance, generation date and stale outputs. [Source](https://support.google.com/gemininotebook/answer/16215270?co=GENIE.Platform%3DDESKTOP&hl=en).
- **gemini-notebook-study-loop** — Difficulty, number, explain, previous/next, Got it/Missed it, review/retake, missed-only, shuffle, resume, full screen, restart and CSV when permitted. Acceptance: Test answer feedback, progress resume and missed-only filtering. [Source](https://support.google.com/gemininotebook/answer/16958963?hl=en).
- **gemini-notebook-question-formats** — Short answer, multi-select and fill-in-the-blank in addition to quizzes; Learning Overview combines summaries and studio outputs. Acceptance: Test multiple answer validation, accessibility and source-based explanation. [Source](https://blog.google/innovation-and-ai/products/gemini-notebook/three-tips-study-gemini-notebook/?trk=article-ssr-frontend-pulse_little-text-block).
- **gemini-notebook-async-output** — Studio generation runs while user continues working; completion can notify and mark unread. Acceptance: Test generation pending, unread persistence, failure and notification preferences. [Source](https://support.google.com/gemininotebook/answer/16206563?hl=en-CA).
- **gemini-notebook-review-before-render** — Optional Review toggle for slide outlines or video producer notes; refine before Proceed. Acceptance: Test editable plan, confirmation, cancellation and skip review. [Source](https://blog.google/innovation-and-ai/products/gemini-notebook/co-create-slides-videos/?trk=article-ssr-frontend-pulse_little-text-block).
- **gemini-notebook-interactive-site-state** — Sites built from sources can save checkbox/field selections; web rollout 18+; mobile coming soon at announcement. Acceptance: Test persisted input and sharing separately; no assumption of collaborative state. [Source](https://support.google.com/gemininotebook/answer/18945748).
- **gemini-notebook-mobile-constraints** — Mobile support differs; notes, mind maps, reports and data table generation restricted per guide. Acceptance: Test platform-specific capability availability. [Source](https://support.google.com/gemininotebook/answer/16296687?co=GENIE.Platform%3DAndroid&hl=en).

### Official visual leads
- [Studio output gallery and video overview](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-video-overviews-studio-upgrades/) — publisher page with visual examples or documentation; inspect original media separately.
- [Mobile flashcard and quiz examples](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-app-quizzes-flashcards/) — publisher page with visual examples or documentation; inspect original media separately.
- [Slide/video review walkthroughs](https://blog.google/innovation-and-ai/products/gemini-notebook/co-create-slides-videos/?trk=article-ssr-frontend-pulse_little-text-block) — publisher page with visual examples or documentation; inspect original media separately.
- [Interactive site examples](https://blog.google/innovation-and-ai/products/gemini-notebook/interactive-sites/?trk=public_post_comment-text) — publisher page with visual examples or documentation; inspect original media separately.

### Sources
- [Rename announcement 2026-07-16](https://blog.google/innovation-and-ai/products/gemini-notebook/notebooklm-gemini-notebook/) — official source retrieved in research
- [Help center](https://support.google.com/gemininotebook/) — official source retrieved in research
- [Create notebook and Studio outputs](https://support.google.com/gemininotebook/answer/16206563?hl=en-CA) — official source retrieved in research
- [Flashcards and quizzes](https://support.google.com/gemininotebook/answer/16958963?hl=en) — official source retrieved in research
- [Mind maps](https://support.google.com/gemininotebook/answer/16212283) — official source retrieved in research
- [Add or discover sources](https://support.google.com/gemininotebook/answer/16215270?co=GENIE.Platform%3DDESKTOP&hl=en) — official source retrieved in research
- [Notes](https://support.google.com/gemininotebook/answer/16262519?hl=en) — official source retrieved in research
- [Chat](https://support.google.com/gemininotebook/answer/16179559) — official source retrieved in research
- [Interactive sites help](https://support.google.com/gemininotebook/answer/18945748) — official source retrieved in research
- [Interactive sites launch 2026-11-16](https://blog.google/innovation-and-ai/products/gemini-notebook/interactive-sites/?trk=public_post_comment-text) — official source retrieved in research
- [Learning Overview and expanded quiz types](https://blog.google/innovation-and-ai/products/gemini-notebook/three-tips-study-gemini-notebook/?trk=article-ssr-frontend-pulse_little-text-block) — official source retrieved in research
- [Slide and video review flow](https://blog.google/innovation-and-ai/products/gemini-notebook/co-create-slides-videos/?trk=article-ssr-frontend-pulse_little-text-block) — official source retrieved in research
- [Studio upgrade (historical)](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-video-overviews-studio-upgrades/) — official source retrieved in research
- [Mobile quiz visual examples (historical)](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-app-quizzes-flashcards/) — official source retrieved in research
- [Mobile limitations](https://support.google.com/gemininotebook/answer/16296687?co=GENIE.Platform%3DAndroid&hl=en) — official source retrieved in research

## Direct image links from Gemini Canvas official article
- [3D visualizer](https://storage.googleapis.com/gweb-uniblog-publish-prod/images/Gemini_Canvas_3D_planet_generato.width-1200.format-webp.webp) — official page image link and alt text retrieved; direct fetch unsupported content type; visual pixels not verified.
- [Physics quiz](https://storage.googleapis.com/gweb-uniblog-publish-prod/images/03_for_students_1_personalize_le.width-1200.format-webp.webp) — official page image link and alt text retrieved; direct fetch unsupported content type; visual pixels not verified.
- [Role and permission dashboard](https://storage.googleapis.com/gweb-uniblog-publish-prod/images/07_for_work_2_optimize_operation.width-1200.format-webp.webp) — official page image link and alt text retrieved; direct fetch unsupported content type; visual pixels not verified.
- [Speaker notes](https://storage.googleapis.com/gweb-uniblog-publish-prod/images/06_for_work_1_accelerate_impact_.width-1200.format-webp.webp) — official page image link and alt text retrieved; direct fetch unsupported content type; visual pixels not verified.

## Comparison and design implications (hypotheses)
- ChatGPT Space: composable content, hierarchical pages and object views.
- Claude: reusable typed artifacts, canvas refinement and design-system handoff.
- Grok Bot: durable agents, visible work state, routines and page/library integration.
- Gemini: adaptive generative interfaces and interactive canvas tools.
- Gemini Notebook: source-grounded study workspace, artifact production and mastery feedback.
- Exams App candidates: study spaces, exam objects, source reader, conventional question answering, review missed questions, progress tracking, optional contextual AI, and scoped artifact generation. Keep deterministic actions available without AI. Separate persistent state, generated snapshots, source version, and scheduled jobs. Do not adopt merely because a competitor supports it.

## Gaps
No pixel-verified direct image assets this batch; original media URLs and publisher pages cataloged. Inspect authenticated UI for exact layout, states, motion, mobile breakpoints, accessibility, permissions, storage, and current template availability; do not infer from promotional images. Gems mini-apps direct help fetch redirected and was not verified in full. No claim of complete product inventory.
