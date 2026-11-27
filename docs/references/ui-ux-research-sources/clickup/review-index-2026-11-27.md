# ClickUp — pending-source review and index integration (batch 9)

2026-11-27. Baseline `d57e027a2bbc623cd7aad2a8b423f697d8774d71`. 16 existing links attempted, 15 articles opened, one retrieval failed. No new URL records. Source registry before: {"verified":215,"search-result reviewed; full article pending":96,"search-result reviewed; direct fetch failed":3,"search-result reviewed; full section pending":3}; after: {"verified":230,"search-result reviewed; direct fetch failed":4,"search-result reviewed; full article pending":80,"search-result reviewed; full section pending":3}. These are catalog statuses, not independently confirmed vendor behavior.

## Reviewed articles

- [view-reorder](https://help.clickup.com/hc/en-us/articles/26004419744023-Group-and-reorder-views): Group by view type via location settings or overflow menu when full; horizontal drag reorder requires full edit permissions.
- [custom-fields-query](https://help.clickup.com/hc/en-us/articles/12665650881943-Search-sort-and-filter-tasks-by-Custom-Fields): Search covers eight textual field types only if visible as columns; search preferences apply to workspace views; hover value quick filter in List.
- [timeline-group](https://help.clickup.com/hc/en-us/articles/31440827150615-Group-tasks-in-Timeline-view): Second-level Assignee/List choices depend on primary group and location; collapse parent rows; List-level grouping does not add nested rows.
- [list-filter](https://help.clickup.com/hc/en-us/articles/6310206119575-Filter-and-search-tasks-in-List-view): Supported filters prefill new objects; single-value grouping hides nonmatching groups; separate subtasks mode makes them searchable.
- [dashboard-mixed-filters](https://help.clickup.com/hc/en-us/articles/16154237385495-Use-mixed-filters-in-Dashboards-and-cards): Dashboard/card filter scopes can coexist; nested AND/OR, apply, reset to last applied, clear group/all.
- [archive-task](https://help.clickup.com/hc/en-us/articles/6329610622487-Archive-a-task): Archive preserves task and attached files; archived tasks searchable via views and command bar; unarchive restores access to attachments.
- [done-status](https://help.clickup.com/hc/en-us/articles/6309517280919-Use-Done-statuses): Done remains visible, stops overdue reminders, clears waiting dependencies and counts toward goals.
- [task-activity](https://help.clickup.com/hc/en-us/articles/29723182607127-Task-activity-and-comments): Right icon rail separates Comments from full Activity; unread dot; assigned comments also appear in action items. Article has inconsistent migration wording.
- [activity-filter](https://help.clickup.com/hc/en-us/articles/6309921223191-Search-and-filter-task-activity): Filter history by actor and change type, including moves, properties, dependencies, sharing and Git events.
- [reply-comments](https://help.clickup.com/hc/en-us/articles/6308954445591-Reply-to-task-comments): Threads have unread counts, follower settings and scheduled replies; disabling threaded comments hides old threaded replies until re-enabled.
- [status-templates](https://help.clickup.com/hc/en-us/articles/6309533958935-Status-templates): Editing a shared template applies only locally; other locations retain previous statuses as Custom. Guests cannot edit or apply templates.
- [status-faq](https://help.clickup.com/hc/en-us/articles/6309465975063-Statuses-FAQ): Tasks in multiple Lists keep home List status schema; two statuses use checkmark icon, more use square; order configurable at schema and view levels.
- [task-creation](https://help.clickup.com/hc/en-us/articles/6309647350807-Create-a-task): Quick create from global toolbar/command bar, comments and Chat; access and details depend on surface.
- [docs-pin](https://help.clickup.com/hc/en-us/articles/7245958790807-Minimize-Docs-to-the-Tray): Personal Tray stores minimized Docs and tasks; click reopen, hover X remove. Do not assume same label in new layout.
- [template-library](https://help.clickup.com/hc/en-us/articles/6326023965591-Add-a-template-to-your-library): Community templates can be copied to workspace library, renamed and shared; original remains; available object types depend on entry and role.

Failed: [Customize views](https://help.clickup.com/hc/en-us/articles/7255480884887-Customize-views-to-increase-productivity) — direct fetch returned UnexpectedStatusCode.

## Search projection

92 product-specific research records derived from the family inventory, six earlier batch files and this review. Original paths, JSON pointers, source IDs, evidence labels and proposed QA retained. Records overlap semantically; count is indexed observations, not unique universal patterns. Search by product and pattern. FTS5 index uses an explicit catalog allowlist and existing shared source registry. Added regression tests; run CI before claiming runtime validation.

## Remaining gaps

- 87 existing references remain pending or failed.
- Runtime, CSS, motion, media playback, accessibility and complete Help Center enumeration remain incomplete.
- Review status does not certify accuracy of every earlier summary.

[Structured review](review-index-2026-11-27.json) · [Search projection](pattern-index.json).
