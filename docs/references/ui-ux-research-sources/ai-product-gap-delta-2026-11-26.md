# AI product gap research — 2026-11-26

Official search excerpts, no live tests. Acceptance checks are proposed.

## Hierarchical deletion (chatgpt-space)
Deleting a page sends descendants to Trash, including descendants owned by others.

[Official source](https://help.openai.com/en/articles/20001549-getting-started-with-space-in-chatgpt). Acceptance: Test warning, child ownership, restoration scope and irreversible deletion.

## Dashboard refresh and connector access (claude)
Dashboards refresh on open when due; live sharing can use the sharer's connector access, subject to admin policy.

[Official source](https://support.claude.com/en/articles/17454700-get-started-with-claude-data). Acceptance: Check stale/fresh/error, last refreshed, data provenance and revoked access.

## Responsive version history (claude)
Claude Docs history overlays text when the artifact panel is too narrow; guide notes a keyboard navigation limitation.

[Official source](https://support.claude.com/en/articles/16923645-get-started-with-claude-docs). Acceptance: Test overlay/side-by-side widths, focus and version restore.

## Artifact sharing and storage lifecycle (claude)
Artifact access can include view, comment or edit depending on role and type. Unpublishing a legacy artifact permanently deletes its stored data; do not generalize that rule to current artifacts.

[Official source](https://support.claude.com/en/articles/9547008-share-artifacts). Acceptance: Test permission matrix, warning and irreversible removal.

## Approval gate (grok-bot)
Bot shows an approval card and waits; approvals for work started without the user can expire after about 30 minutes.

[Official source](https://docs.x.ai/grok-bot/troubleshooting). Acceptance: Test pending, approve, deny, expiry, notification and retry.

## Event-triggered routine (grok-bot)
Slack triggers can start routines as well as schedules; trigger and app access are distinct.

[Official source](https://docs.x.ai/grok-bot/skills-routines-and-automations). Acceptance: Test setup, trigger, pause, failed run and approval boundary.

## Persistent Canvas app data (gemini)
Canvas creates a Firestore instance when persistence is required; shared-user data can be visible via a public shared link.

[Official source](https://support.google.com/gemini/answer/16419134?hl=en-gi). Acceptance: Test private/shared data, reload, public-link warning and failure.

## Note to source (gemini-notebook)
Convert notes to sources for Q&A, generated artifacts and citations; mobile note editing is unsupported per guide.

[Official source](https://support.google.com/gemininotebook/answer/16262519?hl=en). Acceptance: Test conversion, duplication, deletion, source selection and mobile.

## Source citation navigation (gemini-notebook)
Selecting a citation navigates to quoted source context; saving chat as note retains inline citations.

[Official source](https://support.google.com/gemininotebook/answer/16179559). Acceptance: Test exact anchor, unavailable source, keyboard and return.

[Knowledge graph and backlog](../interface-pattern-library/ai-product-knowledge-graph.md)

Correction source: [Claude artifacts guide](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them). The legacy unpublish rule is not a current-artifact rule.
