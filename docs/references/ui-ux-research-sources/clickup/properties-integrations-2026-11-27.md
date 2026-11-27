# ClickUp — property schema, business rules and integrations (batch 7)

Reviewed 2026-11-27. Baseline `b204b802189fc685f3c41637ef2f2969d178c408`. 46 additional unique source records; 23 field types; 12 interaction/business rule contracts. Opened articles and search excerpts have separate statuses in the source register. No live ClickUp workspace was accessed.

## Property types

Source: [Custom Field types](https://help.clickup.com/hc/en-us/articles/6303499162647-Custom-Field-types). Classification below is analytical; field names reflect vendor taxonomy.

| Type | Class | Behavior |
|---|---|---|
| Button | action | Starts configured automation manually. |
| Checkbox | boolean | True/false value. |
| Date | date-time | Date and optional time. |
| Dropdown | single-option | Configured options; shared across all field locations; 500 maximum. |
| Email | contact | Email address. |
| Files | attachment | Local or connected storage. |
| Formula | computed | Expression over supported fields. |
| Labels | multi-option | Up to 500 options; multiple selection. |
| Location | geographic | Formatted address. |
| Money | numeric | Amount and configured currency. |
| Number | numeric | Formatted number. |
| People | reference | People and optionally teams; configurable visibility and cardinality. |
| Phone | contact | Country code and number. |
| Progress (Auto) | computed | Subtasks, checklist items and assigned comments; nested subtasks excluded from rollup. |
| Progress (Manual) | numeric | Configurable range and manual completion. |
| Rating | ordinal | Configurable emoji and 1–5 scale. |
| Relationships | reference | Links to tasks. |
| Rollup | derived-reference | Reads selected related-task properties. |
| Signature | input | Typed or drawn signature; no identity verification claim. |
| Text | text | Single line; 2,048 characters. |
| Text area (Long Text) | rich-text | Rich text; 50,000 characters. |
| Voting | aggregate | Votes; configurable voter visibility. |
| Website | url | Website link. |

## Business rules and interaction contracts

### clickup-required-vs-transition

Creation-required fields apply at task creation; status changes need a separate automation. Owners/admins configure; Business and above.

Proposed QA: Test task and subtask creation, API bypass (unknown), status change with empty property, automation failure and clear error.

Sources: [clickup-field-required](https://help.clickup.com/hc/en-us/articles/30407234676887-Make-Custom-Fields-required).

### clickup-field-access

Default role access, edit schema+value, set value, view only, private. Named exceptions override baseline; creator retention. Restricted fields can be absent from other viewers' saved queries; saving without access may remove such criteria. Form exposure differs.

Proposed QA: Test read/write/metadata permissions independently, query-save loss, form exposure, formula dependency and privilege revocation.

Sources: [clickup-field-permissions](https://help.clickup.com/hc/en-us/articles/26025804975895-Custom-Field-permissions).

### clickup-formula-column

Simple and advanced expression editors; one expression applies to the column. TODAY() disallows certain query, automation and aggregation uses. Results hidden if any input is inaccessible. Formula cannot span multiple locations.

Proposed QA: Test null and zero, division by zero, access changes, time zones, circular references (unknown), migration and stale results.

Sources: [clickup-formula-create](https://help.clickup.com/hc/en-us/articles/30494683858071-Create-a-Formula-Field).

### clickup-relation-scope

Relationship selector may allow all workspace tasks or tasks from a named List. Optional rollup projects related data.

Proposed QA: Test allowed targets, duplicate IDs, deleted/moved target, permission changes and empty relation.

Sources: [clickup-relationship-create](https://help.clickup.com/hc/en-us/articles/14276813483031-Create-Relationship-Custom-Fields).

### clickup-goal-metrics

Targets may be numbers, binary completion, money or task completion. Goal percentage changes when target progress changes; task shows goal badge.

Proposed QA: Define target weights explicitly before implementing; test reversed ranges, currency, linked completion and missing target.

Sources: [clickup-goal-create](https://help.clickup.com/hc/en-us/articles/6325733579671-Create-a-Goal).

### clickup-dependency-shift

Configured rescheduling moves dependents by date change; requires blocking due date and blocked start date. Working-day rule and closed-task option apply. Gantt path limits changes to visible tasks and dependencies.

Proposed QA: Test cycles (not documented), chains, working days/holidays, partial dates, closed status, hidden rows, permission and preview of cascading effects.

Sources: [clickup-dependencies-reschedule](https://help.clickup.com/hc/en-us/articles/6304547785367-Rescheduling-dependencies).

### clickup-sprint-measures

Sprint has timeline, status and effort; missing-estimate warning. Reporting separates scope changes, burndown, burnup, velocity, cumulative flow, cycle and lead time.

Proposed QA: Test scope changes, effort units, date window, completed work, chart drilldown and distinction from study accuracy.

Sources: [clickup-sprint-report](https://help.clickup.com/hc/en-us/articles/6310087298327-Monitor-and-report-on-your-sprints), [clickup-sprint-intro](https://help.clickup.com/hc/en-us/articles/6303974210071-Intro-to-Sprints).

### clickup-connection-scope

Personal connections scoped to user; workspace connection lets workspace users search shared indexed data. Role and app availability differ.

Proposed QA: Consent scope, index lifecycle, disconnect, revoked credentials, source ACL, cross-user leakage and reauthorization.

Sources: [clickup-integration-connect](https://help.clickup.com/hc/en-us/articles/31096074478359-Connect-an-app), [clickup-connected-search](https://help.clickup.com/hc/en-us/articles/14642390285463-Connected-Search).

### clickup-external-file-preview

External links can have preview/embed or plain URL; Drive can create and attach external docs; login-required embeds have desktop/mobile restrictions.

Proposed QA: Test unavailable auth, link permission, deleted source, preview fallback, read/write scope and platform limitations.

Sources: [clickup-integration-drive](https://help.clickup.com/hc/en-us/articles/14841781940759-Google-Drive-integration), [clickup-integration-figma](https://help.clickup.com/hc/en-us/articles/13648563810711-Figma-integration).

### clickup-repository-link

Connect repositories to Spaces; tasks can reference commits, branches and PRs; creation and sync depend on permissions.

Proposed QA: Test repository admin setup, disconnected repos, duplicate events, cross-repo references and source-of-truth ownership.

Sources: [clickup-integration-github](https://help.clickup.com/hc/en-us/articles/6305771568791-GitHub-integration).

### clickup-calendar-sync

Personal calendar connection; Google Calendar offers event sync both directions through Planner. Do not infer task sync equivalence.

Proposed QA: Test timezone, recurring events, private events, conflict resolution (unknown), deleted event and revocation.

Sources: [clickup-integration-google-calendar](https://help.clickup.com/hc/en-us/articles/6336507264663-Google-Calendar-integration), [clickup-integration-outlook-calendar](https://help.clickup.com/hc/en-us/articles/30618267005975-Outlook-Calendar-integration).

### clickup-integration-automation

Configured trigger, optional conditions, and actions connect external services; supported app list varies.

Proposed QA: Test retries, loop prevention, dedupe, secrets, permission, audit, pending and partial failure.

Sources: [clickup-integration-automations](https://help.clickup.com/hc/en-us/articles/6312091699735-Set-up-integration-Automations).

## Integration connection scopes

Personal: Box, Dropbox, Facebook, Figma, GitHub, GitLab, Google Calendar, Google Drive, Gmail, Instagram, Jira, Microsoft OneDrive, Microsoft SharePoint, Microsoft Teams, Notion, Outlook Mail, Salesforce, Zoom, Ziflow, Certain external MCP servers.

Workspace: Box, Confluence, Dropbox, GitHub, GitLab, Google Drive, Jira, Microsoft OneDrive, Microsoft SharePoint, Microsoft Teams, Notion, Slack, Certain external MCP servers.

Documented integration automation apps: Bugsnag, Calendly, Email, GitHub, Google Calendar, Google Drive, Gmail, HubSpot, Slack, Twilio, Outlook Mail.

[Connection scope](https://help.clickup.com/hc/en-us/articles/31096074478359-Connect-an-app); [automation setup](https://help.clickup.com/hc/en-us/articles/6312091699735-Set-up-integration-Automations); [integration directory page 1](https://help.clickup.com/hc/en-us/sections/5228895204247-Integrations), [page 2](https://help.clickup.com/hc/en-us/sections/5228895204247-Integrations?page=2). Directory pages traversed; linked articles not all opened. Do not equate a connection with a particular API action or entitlement.

## Remaining gaps

- Detailed type-by-type field UI and API payload validation
- Individual integration article bodies, complete app/plan/role matrix and authentication scopes
- Full article inventory, visual/runtime evidence, actual motion, CSS and accessibility
- Cross-index reusable patterns into canonical interface catalog

[Structured batch](properties-integrations-2026-11-27.json). No app or plugin changes.
