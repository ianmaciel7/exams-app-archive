# Editor contracts and transition sequences — 2026-11-26

Official documentation research, not runtime inspection. Product-specific observations are not universal design principles. Native editors, generated app controls, output formats, and proposed acceptance checks remain distinct.

## Editor observations

### Editor region navigation — Claude
F6 and Shift+F6 move among top bar, canvas/slide and properties area; Tab and Escape handle the conversation/artifact boundary.

[Official source](https://support.claude.com/en/articles/17457950-use-artifacts-with-a-keyboard-or-screen-reader). Test (not executed): Test forward/backward navigation, focus restoration and nested edit mode.

### Hierarchical canvas focus — Claude
Enter/Return moves into selected artboards or nested groups; Tab navigates peers; Shift+Return moves up one level. Escape exits artboard then clears selection.

[Official source](https://support.claude.com/en/articles/14604416-get-started-with-claude-design). Test (not executed): Test parent/child navigation, keyboard text editing and visible selection.

### Selection toolbar conditional visibility — Claude
A floating selection toolbar is available when properties panel is closed; F6 can reach it and arrows navigate its controls. Escape returns to the canvas preserving selection.

[Official source](https://support.claude.com/en/articles/14604416-get-started-with-claude-design). Test (not executed): Test selection, inspector open/closed, arrow navigation and restored focus.

### Scope-specific editing channel — Claude
Comments target component changes; chat is used for broader structure; direct manipulation adjusts geometry and alignment.

[Official source](https://support.claude.com/en/articles/14604416-get-started-with-claude-design). Test (not executed): Compare selected element, comment and broader request; do not infer exact pixel behavior.

### Documented keyboard limitations — Claude
Placing new design text, shapes, notes or artboards requires pointer input per guide. Noninteractive generated web artifacts may be skipped by Tab and may not scroll with arrows.

[Official source](https://support.claude.com/en/articles/17457950-use-artifacts-with-a-keyboard-or-screen-reader). Test (not executed): Verify keyboard-only creation and scroll fallback; do not label entire editor accessible.

### Code-based motion artifact — Claude
Motion animates existing content as code rather than generating realistic footage. Edit timing or content through chat or editor; export MP4.

[Official source](https://support.claude.com/en/articles/17454997-get-started-with-claude-motion). Test (not executed): Verify local change scope, playback, export and timing; no runtime measurement.

### Design-system artifact and handoff — Claude
Design systems are reusable artifacts sourced from design references or code; documented /design-sync workflow can connect real components to design and implementation.

[Official source](https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design). Test (not executed): Verify source ownership, import, handoff and fidelity without assuming perfect parity.

### Direct document editing in chat — Gemini
Expand generated files to edit or select content for AI changes; PDF editing supported on web/mobile, other listed file formats web-only per announcement.

[Official source](https://blog.google/innovation-and-ai/products/gemini-app/edit-files-directly/). Test (not executed): Verify actual route and file type support; direct file editor is not necessarily Canvas.

### Staged slide deletion and restore — Gemini Notebook (formerly NotebookLM)
In revision mode, slides marked for removal are dimmed with a trash icon and can be restored before generating the revised deck.

[Official source](https://support.google.com/gemininotebook/answer/16757456?hl=en). Test (not executed): Test mark, restore, apply and cancel; capture actual states.

### Deck revision creates new output — Gemini Notebook (formerly NotebookLM)
Revisions generate a new slide deck and consume revision quota; thumbnails can be dragged to reorder in the revision preview.

[Official source](https://support.google.com/gemininotebook/answer/16757456?hl=en). Test (not executed): Check original unchanged, new identity, ordering, quota and recovery.

### Outline approval boundary — Gemini Notebook (formerly NotebookLM)
Optional outline review allows feedback before final slide rendering; Proceed ends refinement of that outline. Generation is nonblocking.

[Official source](https://support.google.com/gemininotebook/answer/16757456?hl=en). Test (not executed): Verify review, proceed, feedback limits, failure and ready notification.

### Producer-note approval and scheduling — Gemini Notebook (formerly NotebookLM)
Video generation can use optional producer-note review before rendering. Generate later schedules without producer notes; after Proceed that plan cannot be further refined.

[Official source](https://support.google.com/gemininotebook/answer/16454555?hl=en). Test (not executed): Test review vs schedule, render progress, error and cancellation if available.

### Interactive versus document report — Gemini Notebook (formerly NotebookLM)
Studio Reports offers interactive Learning Overview and document report generation as distinct options.

[Official source](https://support.google.com/gemininotebook/answer/18323649?hl=en). Test (not executed): Test template discovery, generation and persistent output behavior.

### Audio formats and background playback — Gemini Notebook (formerly NotebookLM)
Audio offers Deep Dive, Brief, Critique and Debate, plus language, length and focus options. Playback speed and background listening are documented.

[Official source](https://support.google.com/gemininotebook/answer/16212820). Test (not executed): Test speed, background playback, loading saved audio and source grounding.

### Infographic object actions — Gemini Notebook (formerly NotebookLM)
Generated infographics can be renamed, downloaded as PNG, shared or deleted from the artifact menu.

[Official source](https://support.google.com/gemininotebook/answer/16758265?hl=en). Test (not executed): Test menu visibility, download rights, sharing and deletion.

### Administrator page-sharing policy — Grok Bot
Team admins can configure team-wide, specific-teammate or disabled page sharing as feature rollout reaches their team.

[Official source](https://docs.x.ai/grok-bot/teams-and-enterprises). Test (not executed): Test disabled audience messaging and admin scope; not a live permission test.

## Documented state sequences

### notebook-deck-staged-revision
- existing deck → (Revise) → revision mode
- revision mode → (Delete slide) → pending deletion (dimmed + trash icon)
- pending deletion (dimmed + trash icon) → (Restore slide) → restored in draft
- revision mode → (Generate revised deck) → generate revised deck
- generate revised deck → (generation completes) → new deck
Unknown: failure, cancel, keyboard reorder, motion timing, exact appearance. [Source](https://support.google.com/gemininotebook/answer/16757456?hl=en).

### claude-design-nested-selection
- artboard title focused → (Space) → artboard selected
- artboard title focused → (Return) → layer navigation
- layer navigation → (Return on text layer) → text editing
- layer navigation → (Escape) → selection retained
- selection retained → (Escape) → selection cleared
Unknown: exact focus ring, animation, pointer parity, screen reader behavior in each browser. [Source](https://support.claude.com/en/articles/14604416-get-started-with-claude-design).

### notebook-video-review
- customization → (Enable review and generate now) → producer notes generating
- producer notes generating → (notes ready) → review ready
- review ready → (Review) → review and feedback
- review and feedback → (Proceed) → rendering
- rendering → (generation completes) → video ready
Unknown: exact progress UI, error, cancel, retry, motion. [Source](https://support.google.com/gemininotebook/answer/16454555?hl=en).

These sequences paraphrase explicit guide instructions, not screenshots or measured state machines. For slide revision, the dimmed pending-deletion appearance is explicitly described; no color value, duration or exact layout is claimed. Direct file editing is a separate feature from Canvas; the related surface is contextual only.

## Evidence gaps

The official Mind Maps help page timed out during this batch. No additional visual pixels or video timestamps were verified. Do not mark visual, accessibility or runtime coverage complete. The previous CI run 45830388216 passed all four jobs.
