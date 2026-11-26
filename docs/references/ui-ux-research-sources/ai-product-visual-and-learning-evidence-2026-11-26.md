# Product visual references and learning flows — 2026-11-26

This delta prioritizes evidence relevant to adaptive workspace navigation, agent takeover, task feedback, study dashboards and source-grounded learning. Historical announcements are dated; no live UI inspection.

## Documented observations

### Roster-dependent sidebar — Grok Bot
A changelog entry documents a hidden/toggle sidebar for one Bot, a narrow rail for two to four, and full sidebar for five or more. These are roster-count rules, not viewport breakpoints.

[Source](https://x.ai/changelog/bot). Acceptance (not executed): Test counts 1, 2, 4, 5; resizing, manual override and keyboard access.

### Library preview and pinned sync — Grok Bot
Library row hover or keyboard focus reveals sender, date and Page visibility; pinned pages, links and files sync across devices per v0.75.2.

[Source](https://x.ai/changelog/bot). Acceptance (not executed): Test hover/focus parity, touch, pin sync and revoked access.

### Keyboard attachment reorder — Grok Bot
The v0.75.2 changelog documents both drag reordering and Alt with arrow keys for composer attachments.

[Source](https://x.ai/changelog/bot). Acceptance (not executed): Verify announced order, focus, drag parity and cancel.

### Three-level agent computer access — Grok Bot
The design article documents active title-bar status, pinned preview and full-screen takeover/handback. The article compares floating, side-by-side, modal and full-screen alternatives.

[Source](https://x.ai/news/designing-grok-bot). Acceptance (not executed): Test preview, manual takeover, return of control, connection failure and visible ownership.

### Reconnect card and suspended routine — Grok Bot
The changelog describes reconnect cards and a routine skipping scheduled runs until connector sign-in is restored. It also distinguishes unavailable history from a routine that never ran.

[Source](https://x.ai/changelog/bot). Acceptance (not executed): Verify sign-out, reconnect, skipped runs, history unavailable and safe resumption; no fake success.

### Typed chat cards and numeric tables — Grok Bot
The v0.75.2 changelog documents approval, question, file, link and table cards; approval summaries and sensitive-change flags; source citation chips; file type/name/size and decimal-aligned number columns.

[Source](https://x.ai/changelog/bot). Acceptance (not executed): Verify semantic labels, focus, safe action review, numeric alignment and narrow viewport.

### Diagnostic-to-practice learning loop — Gemini
At June 2026 launch, Study Notebooks used uploaded material and a diagnostic quiz to identify gaps, then tailored short lessons with follow-up quizzes.

[Source](https://blog.google/innovation-and-ai/products/gemini-app/gemini-study-notebooks/). Acceptance (not executed): Test diagnostic skip/retry, source grounding, lesson navigation and progress changes; do not claim learning efficacy.

### Skill-based progress dashboard — Gemini
The announcement describes objectives grouped by topic, Strengths / Focus areas / Not started status labels, automatic updates from quizzes, priority lesson recommendations and filters.

[Source](https://blog.google/innovation-and-ai/products/gemini-app/gemini-study-notebooks/). Acceptance (not executed): Check status change, incomplete quiz, filter reset and reason for priority; no inferred mastery scoring formula.

### Expandable three-region shell — Gemini Notebook (formerly NotebookLM)
The December 2024 redesign describes expanding the source viewer alongside notes and using chat while audio plays; this is historical documented behavior, not a 2026 pixel audit.

[Source](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-new-features-december-2024/). Acceptance (not executed): Verify current panel widths, collapse, focus, audio continuity and mobile reflow.

### Mind map node exploration — Gemini Notebook (formerly NotebookLM)
The 2025 announcement documents zooming into sections and selecting concepts to obtain summaries.

[Source](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-studying-help/). Acceptance (not executed): Test zoom, pan, keyboard node navigation, summary grounding and return focus.

### Source discovery and import review — Gemini Notebook (formerly NotebookLM)
The April 2025 launch describes a query, a ranked set of up to ten annotated source recommendations, then explicit import. This is a dated historical contract, not a current quota claim.

[Source](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-discover-sources/). Acceptance (not executed): Verify selection, relevance notes, import errors, duplicate and empty results.

### Explain with source citations — Gemini Notebook (formerly NotebookLM)
The September 2025 announcement connects quiz/flashcard explanations to citations in original learning material.

[Source](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-student-features/). Acceptance (not executed): Verify wrong-answer explanation, source anchor, unavailable source and clear distinction from generated reasoning.

### Textbook catalog as source type — Gemini Notebook (formerly NotebookLM)
The October 2026 announcement documents Add sources → Textbooks for available U.S./India provider titles and inline citations. Do not infer Brazilian catalog availability.

[Source](https://blog.google/innovation-and-ai/products/gemini-notebook/new-access-textbooks/). Acceptance (not executed): Verify catalog eligibility, import, citation, reading rights and unsupported geography.

## Visual references

| Media | Modality | Evidence status | Publisher |
|---|---|---|---|
| [Design-agent roster GIF](https://media.x.ai/cdn-cgi/image/fit%3Dscale-down%2Conerror%3Dredirect%2Cwidth%3D720%2Cheight%3D405%2Cf%3Dauto/v1/website/grok-bot-guides-designing-grok-bot-with-grok-bot-meet-the-team-b9959c98.gif) | gif | one rendered image inspected; animation frames/timing not inspected | [source](https://x.ai/bot/guides/designing-grok-bot-with-grok-bot) |
| [Production-character motion storyboard](https://media.x.ai/cdn-cgi/image/fit%3Dscale-down%2Conerror%3Dredirect%2Cwidth%3D720%2Cheight%3D183%2Cf%3Dauto/v1/website/grok-bot-guides-designing-grok-bot-with-grok-bot-motion-god-frames-f42d0711.png) | image | publisher link and caption verified; image fetch failed | [source](https://x.ai/bot/guides/designing-grok-bot-with-grok-bot) |
| [Starter bot cards in Figma](https://media.x.ai/cdn-cgi/image/fit%3Dscale-down%2Conerror%3Dredirect%2Cwidth%3D720%2Cheight%3D355%2Cf%3Dauto/v1/website/grok-bot-guides-designing-grok-bot-with-grok-bot-figma-starter-bots-f4b010c7.png) | image | publisher link and caption verified; image fetch failed | [source](https://x.ai/bot/guides/designing-grok-bot-with-grok-bot) |
| [Onboarding tool assets in Figma](https://media.x.ai/cdn-cgi/image/fit%3Dscale-down%2Conerror%3Dredirect%2Cwidth%3D720%2Cheight%3D390%2Cf%3Dauto/v1/website/grok-bot-guides-designing-grok-bot-with-grok-bot-figma-tools-2cfc9447.png) | image | publisher link and caption verified; image fetch failed | [source](https://x.ai/bot/guides/designing-grok-bot-with-grok-bot) |
| [NotebookLM three-panel redesign animation](https://storage.googleapis.com/gweb-uniblog-publish-prod/original_images/3_panel_ui_keyword_final_7_sources.gif) | gif | publisher link and alt text verified; GIF decoding unsupported | [source](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-new-features-december-2024/) |
| [Mobile source picker for flashcards and quizzes](https://storage.googleapis.com/gweb-uniblog-publish-prod/images/CreateFlashcardsQuizes_NotebookL.width-1200.format-webp.webp) | image | publisher link and alt text verified; binary fetch and download failed | [source](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-app-quizzes-flashcards/) |
| [Study notebook walkthrough](https://blog.google/innovation-and-ai/products/gemini-app/how-to-make-gemini-study-notebooks/) | embedded-video-page | official page retrieved; video playback and timestamps not verified | [source](https://blog.google/innovation-and-ai/products/gemini-app/how-to-make-gemini-study-notebooks/) |
| [Ambient agent prototype videos](https://x.ai/bot/guides/designing-grok-bot-with-grok-bot) | embedded-video-page | official captions retrieved; videos not played | [source](https://x.ai/bot/guides/designing-grok-bot-with-grok-bot) |

- **Design-agent roster GIF:** Four named role-specific agents in a two-by-two white panel, distinct red/blue/black avatars and green markers; demonstration image, not confirmed sidebar layout.
- **Production-character motion storyboard:** Publisher describes character entering, noticing window and bouncing into position. Not measured.
- **Starter bot cards in Figma:** Production design workflow, not a capture of shipped marketplace.
- **Onboarding tool assets in Figma:** Publisher describes populating onboarding with logos; not shipped UI evidence.
- **NotebookLM three-panel redesign animation:** Historical December 2024 Sources/Chat/Studio animation; do not infer current layout or timing.
- **Mobile source picker for flashcards and quizzes:** November 2025 mobile source selection reference; no pixel review.
- **Study notebook walkthrough:** Article embeds walkthrough of goal setting, practice and progress dashboard.
- **Ambient agent prototype videos:** Notch, corner hover and cursor companion experiments explicitly not shipped exactly as explored. Separate from product behavior.

One rendered frame was visible; no animation timelines, timestamps or exact UI measurements were verified. Existing Grok media manifest remains the source for previously archived independent examples. All new media are link-only; no binary copied.

## Documented flows

### Diagnostic quiz to skill dashboard
1. Add learning materials
2. Take diagnostic quiz
3. Receive targeted short lessons
4. Complete follow-up quizzes
5. Review updated topic status and recommended lesson

Unknown: exact scoring thresholds, failed quiz recovery, mobile layout, visual transitions. [Source](https://blog.google/innovation-and-ai/products/gemini-app/gemini-study-notebooks/).

### Agent computer preview and takeover
1. Observe computer activity indicator
2. Open pinned preview
3. Expand full-screen for takeover when help is needed
4. Return control to the agent

Unknown: exact takeover confirmation, connection recovery, focus management, transition timing. [Source](https://x.ai/news/designing-grok-bot).

## Scope and next checks

Treat adaptive learning dashboard states as a product reference, not a validated mastery metric or teaching outcome. Treat the Grok ambient prototypes as unshipped experiments. Confirm current UI, keyboard, state transitions, resize, storage and errors through authorized live inspection. No exact motion values inferred from a GIF frame.
