# ChatGPT Space, views and composable pages — product benchmark

Review: 2026-11-26. Scope: public official OpenAI documentation and product images; no authenticated UI or source inspection. Space replaces Library for eligible accounts; Projects remain distinct. Rollout varies by plan/device. Slides rollout and Sheets coming soon per Help Center; marketing descriptions are not availability guarantees.

## Information architecture and views

Workspace/account → personal or shared space → folders/pages → subpages → blocks/references. Projects separately organize chats/files/instructions. This is a conceptual model, not a claim about backend schema. Views are not all presentation modes: some are filters, collections or navigation destinations.

| View | Role |
|---|---|
| All | collection |
| Your items | ownership filter |
| Shared with you | access filter; indirect shared-space items may be excluded |
| Pages | type view; open parent for children |
| Images | type view |
| Your creations | origin filter |
| Uploads | origin filter |
| Suggested | discovery |
| Recents | recent activity |
| Sites | sidebar entry |
| Google Drive | external source entry |
| Space | scoped collection |
| Parent page | hierarchy |
| Search | results with optional type filters |

## App shell and editing

Navigation sidebar (New page, All, Pages, Sites, Images, Google Drive in official guide), main page, conversation alongside page, selection toolbar, comments and sharing. Slash menu: Generate, Visualize, Page, Image, File, Agent Instructions, heading 1–3, bulleted/numbered lists, Task, Checklist, Quote, Code, Table, Divider, Link to page, Prompt, Highlight, references to Files/Pages/Chats (inventory from prior research; availability may vary). Use @ for mentions; distinguish linking an existing object from creating a child. Block handles and drag/reorder: verify exact states in authenticated UI. Table width: Normal/Flexible/Full width; Fit menu readability/equal distribution when available; copy link/Markdown, insert below and delete. Selection AI, inline agent, comment-based AI and side conversation have different scopes. Review edits and sharing changes. Keep Updated not available at launch; configure and verify scheduled task separately.

## Pattern inventory and acceptance checks

### Separate organizational contexts
Group related objects without conflating a shared content space and a conversation project.
- Acceptance check (derived): Test membership, access and movement independently.
- Source: https://help.openai.com/en/articles/20001549-getting-started-with-space-in-chatgpt

### Object collections and facets
Separate ownership, access, object type, origin and activity from hierarchy.
- Acceptance check (derived): Test shared-space indirect access, empty results, filters and permissions.
- Source: https://help.openai.com/en/articles/20001549-getting-started-with-space-in-chatgpt

### Composable page / block editor
Use searchable slash menu for content, references and interactive tools; create nested page or link existing page.
- Acceptance check (derived): Test keyboard, touch, focus, insert/reorder, deletion and reference identity.
- Source: https://learn.chatgpt.com/docs/space/pages

### Per-block table width and fit
Normal, Flexible, Full width and readability/equal columns. Do not infer exact sizes.
- Acceptance check (derived): Test narrow viewport, overflow, fit and screen reader headers.
- Source: https://learn.chatgpt.com/docs/space/pages

### Contextual AI and scoped edits
Side chat for broad work; selected text, inline mentions and comments for scoped work. Review proposals before acceptance.
- Acceptance check (derived): Test scope, undo/review, permission, cancellation, errors, keyboard.
- Source: https://learn.chatgpt.com/docs/space/agents

### Verified recurring updates
Distinguish a generated tracker from actual scheduled execution; verify saved task and run. Keep Updated unavailable at launch per guide.
- Acceptance check (derived): Test task enablement, next run, freshness, source and failure.
- Source: https://learn.chatgpt.com/docs/space/agents

### Intelligent UI / generated interface
Choose text, cards, forms, charts or interactive output based on need; state persistence varies by experience and chat.
- Acceptance check (derived): Test fallback text, state reload, control semantics, contrast and reduced motion.
- Source: https://help.openai.com/en/articles/20001598-intelligent-ui-in-chatgpt

### Interactive visualization vs persistent app
Visualization is generally snapshot; sites are a distinct option. Show data context, labels, accessibility and simpler fallback on failure.
- Acceptance check (derived): Test keyboard, data table, units, blank/loading/error and export.
- Source: https://learn.chatgpt.com/docs/visualizations

### Unified content search
Search existing objects by type, with permission boundaries; Ctrl/Cmd+K. Not web search.
- Acceptance check (derived): Test keyboard, archived vs deleted/locked, access and filter reset.
- Source: https://help.openai.com/en/articles/10056348-finding-your-chats-projects-and-files-in-chatgpt

### Customizable mobile navigation
Home and Explore separate frequent work from discovery; pin/unpin/replace shortcuts.
- Acceptance check (derived): Test touch, focus, available destinations, full tab bar and responsive behavior.
- Source: https://help.openai.com/en/articles/20001723-using-the-new-experience-in-the-chatgpt-mobile-app

### Contextual collaboration
Shared page editing, comments anchored to content, review attribution and sharing controls when offered.
- Acceptance check (derived): Test permissions and simultaneous edits; do not infer implementation.
- Source: https://learn.chatgpt.com/docs/space/collaboration

## Official visual evidence

All six images were opened and visually inspected on 2026-11-26. Original publisher-hosted links, no copied bytes. Marketing examples do not prove native templates, persistence, animation timing or actual behavior. Data in screenshots is illustrative.

### Task list
Prioritized checklist, sections and explanatory text.
[Official image](https://images.ctfassets.net/8su2tbn87fck/3DG9uFmP0vdJubLdCrPcs8/485f9dab24ece5c968b9cbf000d27a2b/chatgpt-space-todos-desktop-light.png?fm=webp&q=80&w=1340) · [Source page](https://chatgpt.com/features/space/)

### Data visualization
Sankey flows, categories, quantitative tooltip; sample data.
[Official image](https://images.ctfassets.net/8su2tbn87fck/6G6cC1s3Do82N8yZfMofXk/6652364afaf5d1dbfebf127243576879/chatgpt-space-data-desktop-light.png?fm=webp&q=80&w=1340) · [Source page](https://chatgpt.com/features/space/)

### Presentation
Split text and image slide.
[Official image](https://images.ctfassets.net/8su2tbn87fck/44xcuWcnbu4VdjgnJBciwX/e61163d8eb98a27aa4ef845a51636f4e/chatgpt-space-brand-pitch-desktop-light.png?fm=webp&q=80&w=1340) · [Source page](https://chatgpt.com/features/space/)

### Client portal
Navigation rail, document cards, task statuses and activity.
[Official image](https://images.ctfassets.net/8su2tbn87fck/0VCz9UfZ9PLozjGMdK1Xp/13b658fc92c55bbfa418dc82246b593e/chatgpt-space-sites-desktop-light.png?fm=webp&q=80&w=1340) · [Source page](https://chatgpt.com/features/space/)

### Project tracker
Burndown actual versus plan, progress bars, status legend, blockers.
[Official image](https://images.ctfassets.net/8su2tbn87fck/1XD9GxCSgSCal5pWFsR1P4/e27811173504cb6587e21c1e1bd8f50d/chatgpt-space-sprint-desktop-light.png?fm=webp&q=80&w=1340) · [Source page](https://chatgpt.com/features/space/)

### Interactive prototype
Embedded onboarding wireframe concept; not evidence of shipped motion.
[Official image](https://images.ctfassets.net/8su2tbn87fck/rV0a4g28Lvgu6fnTDdmlp/3c11073bb05593530b026539ebe98f5b/chatgpt-space-prototype-desktop-light.png?fm=webp&q=80&w=1340) · [Source page](https://chatgpt.com/features/space/)

## Creation possibilities, not a native template catalog

Task lists, checklists, plans, calendars, roadmaps, progress trackers, dashboards, charts, reports, notes, wireframes, prototypes, quizzes, games, calculators, simulations, diagrams, forms, educational exercises, sites and presentations. Four template names previously observed (Welcome Page, Daily To-do List, Project Dashboard, Project Tracker) require fresh UI verification; do not treat as complete inventory. Chart examples include Sankey and burndown; interactive chat may use side-by-side comparison, forms, buttons, maps or other generated content when appropriate. Distinguish generated components from native features and persistent data. Mobile Home/Explore and optional pinned shortcuts are rollout-dependent.

## Application hypotheses for Exams App (not approved decisions)

Spaces for exam/certification/study goals; objects for questions, exams, mock tests, notes and files. Separate object identity from views (list/table/gallery/dashboard/graph candidates). Contextual inspector and AI, linked objects, nested content, global search, modular study plan (task checklist + question progress chart). Choose visualization by task, not decoration; support keyboard, touch, visible focus, text/data equivalents, reduced motion and non-color-only states. Validate with actual workflows before adoption.

## Evidence gaps

No live authenticated inspection: empty/loading/error, hover/focus/active/disabled, exact DOM/CSS, dimensions, breakpoints, resizing/collapse, tokens, motion duration/easing, dark mode, state persistence and complete template list remain unverified. Capture original permitted screenshots or recordings per view and interaction; record date, platform, viewport, state, provenance and rights. No private user content or raw conversation included.

## Source register

- [ChatGPT Space product examples](https://chatgpt.com/features/space/) — verified; Six official examples, not a guarantee of native templates or live synchronization.
- [Getting started with Space](https://help.openai.com/en/articles/20001549-getting-started-with-space-in-chatgpt) — verified; Views, nesting, rollout and distinction from Projects.
- [Work with pages](https://learn.chatgpt.com/docs/space/pages) — verified; Block editor, menus, references, table widths.
- [Work with agents](https://learn.chatgpt.com/docs/space/agents) — verified; Selection, inline and comment AI, recurring work verification.
- [Collaborate in Space](https://learn.chatgpt.com/docs/space/collaboration) — verified; Official collaboration guide.
- [Visualizations](https://learn.chatgpt.com/docs/visualizations) — verified; Generated experiences, accessibility, errors, snapshot limitations.
- [Intelligent UI](https://help.openai.com/en/articles/20001598-intelligent-ui-in-chatgpt) — verified; Adaptive chat presentation and scoped state.
- [Global search](https://help.openai.com/en/articles/10056348-finding-your-chats-projects-and-files-in-chatgpt) — verified; Search filters, shortcuts and access.
- [New mobile experience](https://help.openai.com/en/articles/20001723-using-the-new-experience-in-the-chatgpt-mobile-app) — verified; Home, Explore and customizable tabs.
- [Space overview](https://learn.chatgpt.com/docs/space) — prior research; recheck; Overview
- [Space getting started](https://learn.chatgpt.com/docs/space/getting-started) — prior research; recheck; Getting started
- [Space sharing and controls](https://help.openai.com/en/articles/20001544-chatgpt-space-sharing-data-and-controls) — prior research; recheck; Access and data
- [Manage ChatGPT Space](https://learn.chatgpt.com/docs/enterprise/chatgpt-space) — prior research; recheck; Administration
- [Classic mobile](https://help.openai.com/en/articles/8142208-using-the-chatgpt-mobile-app-classic-experience) — prior research; recheck; Historical reference
- [Library](https://help.openai.com/en/articles/20001052-using-library-to-manage-files-in-chatgpt) — prior research; recheck; Historical reference
- [ChatGPT Slides](https://help.openai.com/en/articles/20001605-creating-and-collaborating-on-slides-in-chatgpt) — prior research; recheck; Specialized editor
- [DevDay 2026 recap](https://openai.com/index/devday-2026-recap/) — prior research; recheck; Announcement
- [ChatGPT release notes](https://help.openai.com/en/articles/6825453-chatgpt-release-notes) — prior research; recheck; Rollout chronology
- [Learn changelog](https://learn.chatgpt.com/docs/changelog) — prior research; recheck; Documentation history
- [ChatGPT Sites](https://learn.chatgpt.com/docs/sites) — prior research; recheck; Persistent sites
- [Official video candidate](https://www.youtube.com/watch?v=3_fayTbZrW8) — prior research; recheck publisher and content; Video lead; do not infer motion from stills
