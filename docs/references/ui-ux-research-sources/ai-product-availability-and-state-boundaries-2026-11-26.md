# AI product availability, permissions and persistence — 2026-11-26

Companion to the [knowledge graph](../interface-pattern-library/ai-product-knowledge-graph.md). These are dated official documentation findings; no authenticated runtime testing. Unknown plan/platform details are not treated as unavailable.

## Availability matrix

| Product / capability | Plans or eligibility | Platform | Boundaries | Official source |
|---|---|---|---|---|
| ChatGPT Space — Space pages | Plus eligible rollout; Pro, Business, Enterprise; 18+ | Web/Desktop create/edit; iOS/Android edit, read/share/navigate | Organization sharing policy; residency exceptions Canada/UAE for managed workspaces | [guide](https://help.openai.com/en/articles/20001549-getting-started-with-space-in-chatgpt) |
| ChatGPT Space — Slides and Sheets | Slides rolling out to eligible Space users; Sheets coming soon | Exact editor platform availability not established here | Do not claim Sheets shipped | [guide](https://help.openai.com/en/articles/20001549-getting-started-with-space-in-chatgpt) |
| ChatGPT Space — Page sharing | Eligible Space users; admin policy | Platform-specific sharing options not exhaustively tested | View/edit; owner/creator can delete; embedded uploads follow page permissions; linked files keep own access | [guide](https://help.openai.com/en/articles/20001544-chatgpt-space-sharing-data-and-controls) |
| Claude — Artifacts / Docs / Slides / Design | Free, Pro, Max, Ultra, Team, Enterprise; file creation capability required | Web/Desktop create/edit/share; mobile design/deck/doc creation and editing; web/Desktop for sharing settings | Enterprise settings may override availability | [guide](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them) |
| Claude — Data template | Pro, Max, Ultra, Team, Enterprise | Template available web/Desktop; exact mobile editing unverified | Enterprise default on Nov 20 unless owner already set preference | [guide](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them) |
| Claude — Sheets and Whiteboards templates (beta) | Pro, Max, Ultra, Team, Enterprise | Web/Desktop; exact mobile behavior unverified | On by default for Team, off for Enterprise until enabled | [guide](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them) |
| Claude — Motion template (beta) | Team and Enterprise | Web/Desktop; exact mobile behavior unverified | Team default on; Enterprise default off | [guide](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them) |
| Claude — Artifact data storage | Pro, Max, Ultra, Team, Enterprise | Web/Desktop | Personal and shared storage; confirmation for shared storage; legacy publishing constraints differ | [guide](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them) |
| Claude — Artifact sharing | Public links and email invites on paid plans; email invite beta; organization-wide Team/Enterprise; groups Enterprise | Web/Desktop sharing settings; unavailable in mobile app | Org external-sharing policy; view/comment/edit; legacy sharing separate | [guide](https://support.claude.com/en/articles/9547008-share-artifacts) |
| Grok Bot — Pages | Gradual rollout; not available on Enterprise teams per guide | Desktop >=0.60.0; phone >=1.14.0 | Private default; audience options vary; only Bot edits; reader controls transient | [guide](https://docs.x.ai/grok-bot/files-and-results) |
| Gemini — Canvas documents and apps | Signed in; add Gemini features and document transformations 18+ | Computer guide; shared content opens on gemini.google.com, not mobile app | Autosave editing; private/shared generated app storage separate | [guide](https://support.google.com/gemini/answer/16047321?hl=en-12) |
| Gemini — Canvas persistent app data | App requires persistence; exact plan matrix not confirmed | Shared public links; private app user data and multi-user public database modes | Anyone with public link to multi-user app can view/edit associated shared data | [guide](https://support.google.com/gemini/answer/16419134?hl=en-gi) |
| Gemini Notebook (formerly NotebookLM) — Interactive Sites | 18+; global web rollout including Workspace; usage limits | Web; mobile coming soon at Nov 16 announcement | Notebook edit access needed to generate/delete; each user's inputs isolated; consumer owner/editor required for public site sharing | [guide](https://support.google.com/gemininotebook/answer/18945748) |
| Gemini Notebook (formerly NotebookLM) — Interactive Sites rollout | 18+ including Google Workspace subscribers | Web at launch; mobile later | Announcement is historical; confirm current access before assuming support | [guide](https://blog.google/innovation-and-ai/products/gemini-notebook/interactive-sites/?trk=public_post_comment-text) |
| Gemini Notebook (formerly NotebookLM) — Flashcards and Quizzes | Notebook edit access required for creation/deletion; plan-specific quotas not verified here | Platform support not exhaustively tested here | Saved progress, review/retake; CSV may be restricted for Play Books source content | [guide](https://support.google.com/gemininotebook/answer/16958963?hl=en) |

## Additional observations and verification criteria

### Embedded file permission vs reference (ChatGPT Space)
Uploaded files inherit page access; a link to a separately stored file does not itself grant access. Copied summaries on the page become visible to page readers.

[Official source](https://help.openai.com/en/articles/20001544-chatgpt-space-sharing-data-and-controls). **Acceptance test (not executed):** Check view/edit roles, embedded files, external access and revoke behavior.

### Personal vs shared artifact state (Claude)
Artifacts can store private per-user data or common shared data. First shared-storage use shows a confirmation. New artifacts can store before publishing; legacy artifacts require publication.

[Official source](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them). **Acceptance test (not executed):** Test two accounts, save/reload and visibility; distinguish current and legacy artifacts.

### Invitation expiry and revocation (Claude)
Pending email invitations expire in 30 days; accepted invitations do not expire automatically. Removing a person revokes access immediately. Organization settings and plan affect invitations.

[Official source](https://support.claude.com/en/articles/9547008-share-artifacts). **Acceptance test (not executed):** Test pending, expired, accepted, revoked and disabled external sharing.

### Artifact permission roles (Claude)
Viewer reads artifact/comments; commenter adds comments and downloads offered files; editor can change content. External commenters and editors have limitations; editors cannot delete artifact.

[Official source](https://support.claude.com/en/articles/9547008-share-artifacts). **Acceptance test (not executed):** Test each role and artifact type, including disabled comments and connectors.

### Library content facets and pinned items (Grok Bot)
Desktop Library filters All, Pages, Media, Links, Files, Apps and Pinned. Team Bot separates private-to-user and bot files; pin treatment differs.

[Official source](https://docs.x.ai/grok-bot/files-and-results). **Acceptance test (not executed):** Test filter results, pin/unpin and private/team visibility.

### Stable page address and rename (Grok Bot)
Rename commits with Enter or cancels with Escape; a public page address remains unchanged after renaming. Custom addresses are not supported per guide.

[Official source](https://docs.x.ai/grok-bot/files-and-results). **Acceptance test (not executed):** Test cancel, rename, stable link and access revoke.

### Sharing conflict and retry (Grok Bot)
Share menu explains unavailable audiences, failed access changes and concurrent access updates; failed saves offer Retry.

[Official source](https://docs.x.ai/grok-bot/files-and-results). **Acceptance test (not executed):** Exercise conflict, failed request, retry and inaccessible audience; no silent success.

### Copy shared Canvas content (Gemini)
A public shared Canvas result can be copied into a user's own editable Canvas; shared app data is a separate concept. Copy/edit shared content requires age 18+, and links open in web.

[Official source](https://support.google.com/gemini/answer/16047321?hl=en-12). **Acceptance test (not executed):** Test new object identity, original unchanged, shared data boundary and mobile limitation.

### Shared site with private inputs (Gemini Notebook (formerly NotebookLM))
Every user of a shared site, including owner, sees only their own saved inputs. Site viewers require access to the full notebook; public sharing requires consumer owner/editor.

[Official source](https://support.google.com/gemininotebook/answer/18945748). **Acceptance test (not executed):** Test two users, saved selections, notebook permissions and no cross-user input leakage.

### Site revocation and deletion (Gemini Notebook (formerly NotebookLM))
Turning off site sharing or deleting the site invalidates previously generated share links; sites can also be downloaded from Studio.

[Official source](https://support.google.com/gemininotebook/answer/18945748). **Acceptance test (not executed):** Test old links, role checks, export and deletion confirmation.

## Persistence boundary comparison

| Product | Content edits | Reader input |
|---|---|---|
| ChatGPT Space | Shared page editing with access controls | Generated visualization state depends on output type; exact per-block persistence unknown |
| Claude | Editable artifacts | Personal or shared storage supported for eligible artifacts |
| Grok Bot Pages | Bot changes page on request | Reader switches/filters are transient |
| Gemini Canvas | Autosaved document/app edits | Private per-user or shared app database possible |
| Gemini Notebook Sites | Notebook editors generate/delete site | Each user's own input persists independently; not visible to other site users |

Do not conflate artifact content, viewer state, saved personal data, shared data, source access and permission metadata.

## Verified visual evidence

[Claude Design official video thumbnail](https://www.anthropic.com/_next/image?q=75&url=https%3A%2F%2Fimg.youtube.com%2Fvi%2Ft_LBECIQQqs%2Fmaxresdefault.jpg&w=3840) — publisher-linked promotional video thumbnail visually inspected 2026-11-26; still only. Observed: Tweaks toggle enabled; Comment / Edit / Draw controls; Zoom 100% and expand icon; Share and Export buttons; Mobile device preview selected; Desktop and Tablet options; Dark mode toggle, theme swatches, typography sliders and section toggle. No runtime state or motion timing measured; sliders and options may be generated for the example; not a universal native inspector. [Announcement](https://www.anthropic.com/news/claude-design-anthropic-labs). Google Canvas direct image URLs were retried but the fetcher rejected the binary content type; these remain unverified visual leads.

## Correction

Artifact access can include view, comment or edit depending on role and type. Unpublishing a legacy artifact permanently deletes its stored data; do not generalize that rule to current artifacts. Previous records amended; no other product semantics changed.

## Remaining gaps

Full template inventory, per-feature availability beyond the rows above, exact responsive behavior, authenticated permission and persistence tests, video frame timings, comprehensive screenshot catalog, and independent retrieval evaluation remain open.
