# Documented product interaction flows — 2026-11-26

Twelve source-backed flows. These are paraphrased documentation sequences, not measured UI state machines. No hover, timing, pixel or keyboard behavior is inferred. Sources may describe rolling releases. 

## Inline content and revision (ChatGPT Space)
1. Open a page and invoke slash menu
2. Choose Generate and describe content
3. Review draft in place
4. Accept, request revision, or undo

Controls and boundaries: Selection-based toolbar, block handle, inline generator and review. Documented text; exact error/focus/animation not observed.

[Official guide](https://learn.chatgpt.com/docs/space/pages)

## Interactive visualization inside a page (ChatGPT Space)
1. Invoke Visualize with a request
2. Choose a starting point such as app, widget, screen or diagram
3. Review generated result and test controls
4. Request changes using adjacent chat

Controls and boundaries: Generated visualization is a different output from a native page block; persistence must be checked separately. Official guide; not a native template inventory.

[Official guide](https://learn.chatgpt.com/docs/space/pages)

## Child page versus reference (ChatGPT Space)
1. Open parent page
2. Choose Page to create a child, or Link to page to reference an existing page
3. Name new child or select target
4. Navigate the related content

Controls and boundaries: Child containment differs from reference; drag handle can move an entire heading section. Official guide; exact navigation history and deletion restoration untested.

[Official guide](https://learn.chatgpt.com/docs/space/pages)

## Collaborative whiteboard workflow (Claude)
1. Request a board or choose the Whiteboards tile
2. Arrange shapes, arrows and sections with collaborators
3. Optionally follow a teammate
4. Transform to a document/deck or export PNG

Controls and boundaries: Whiteboard beta; external invite policy; connected-app context not used on board per guide. Official help; association with generic canvas is contextual, not same editor.

[Official guide](https://support.claude.com/en/articles/18324319-get-started-with-claude-whiteboards)

## Collaborative spreadsheet workflow (Claude)
1. Start blank or describe a sheet
2. Edit cells with Claude and collaborators
3. Inspect outlined changed cells and formulas
4. Use version history or export XLSX

Controls and boundaries: Tabs, formulas, conditional formatting, dropdowns, checkboxes and charts; no connected-app live data at launch. Official help; visual selection and history behavior not tested.

[Official guide](https://support.claude.com/en/articles/18324300-get-started-with-claude-sheets)

## Page creation, reading and update (Grok Bot)
1. Ask Bot to create page
2. Open title card in chat
3. Use adjacent page-specific chat to request revision
4. Earlier card indicates updated version; reopen latest

Controls and boundaries: Desktop page dominates window; mobile closes back to chat. Reader filters/switches alter view only and do not save. Official help; no reader-write persistence.

[Official guide](https://docs.x.ai/grok-bot/files-and-results)

## Library discovery and pinning (Grok Bot)
1. Open Bot profile/details and Library
2. Browse date groups (five items at first) or use search
3. Show more or open item
4. Use overflow to pin/unpin; page owner can share

Controls and boundaries: Library excludes user uploads and Cloud Agent returned files per guide; desktop shortcut Cmd/Ctrl+K. Official help; actual visual grouping and pin order untested.

[Official guide](https://docs.x.ai/grok-bot/files-and-results)

## Page sharing and access failure (Grok Bot)
1. Open page sharing settings
2. Choose permitted audience
3. Copy link or narrow access
4. If access update fails, retry

Controls and boundaries: Private by default; public link allows reading and controls, but only Bot edits content; unavailable options explain why. Official help; no live access matrix tested.

[Official guide](https://docs.x.ai/grok-bot/files-and-results)

## Canvas application editing and debugging (Gemini)
1. Open app in Canvas
2. Switch to Code to edit or request a change
3. Inspect preview console and recent changes
4. Use Select & ask for scoped revision

Controls and boundaries: Edits auto-save; version controls documented for docs; preview errors and logs available. Official help; not inspected live.

[Official guide](https://support.google.com/gemini/answer/16047321?hl=en-12)

## Canvas sharing and app information review (Gemini)
1. Open Share & export
2. Choose Share
3. Review app information about shared data, AI features and session persistence
4. Copy public link if appropriate

Controls and boundaries: Anyone with public link may view/edit associated shared data; distinguish app data from document content. Official help; live security behavior not tested.

[Official guide](https://support.google.com/gemini/answer/16047321?hl=en-12)

## Flashcard generation and review loop (Gemini Notebook (formerly NotebookLM))
1. Select sources and Studio Flashcards or customization pencil
2. Choose difficulty/prompt; generation runs in background
3. Study with Explain, previous/next, known/missed controls
4. Review results; retry same, all, or missed cards

Controls and boundaries: Progress resumes; shuffle, delete card, restart, fullscreen and CSV where allowed. Edit access required to generate/delete study aid. Official help; correct/incorrect visual design and actual state persistence untested.

[Official guide](https://support.google.com/gemininotebook/answer/16958963?hl=en)

## Quiz generation and review loop (Gemini Notebook (formerly NotebookLM))
1. Choose Quiz in Studio, customize if needed
2. Wait while continuing other work
3. Answer and use Hint/Explain or navigate questions
4. Review or retake at end

Controls and boundaries: Fullscreen and previous/next; no claim of exact submit-button behavior or answer timing. Official help; feedback and score states need screenshots.

[Official guide](https://support.google.com/gemininotebook/answer/16958963?hl=en)

## Persistence comparison
Grok Bot Page controls are transient reader-side changes; revisions are requested from the Bot. Gemini Canvas can save app state across sessions; sharing may expose app data. Notebook study progress can resume. These are different state models and must not be merged into a single universal pattern. ChatGPT visualization state and Claude artifact-specific storage need per-output testing.
