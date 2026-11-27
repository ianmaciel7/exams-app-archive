# ClickUp — reopened references and behavior contracts (batch 10)

Reviewed 2026-11-27, baseline `e66d23fa55fdcf55353b59ff7ff156c7598d52c4`. 30 previously incomplete references returned content: 29 article pages and one section directory. No new URL entries. Registry status before: {"verified":230,"search-result reviewed; direct fetch failed":4,"search-result reviewed; full article pending":80,"search-result reviewed; full section pending":3}; after: {"verified":260,"search-result reviewed; direct fetch failed":3,"search-result reviewed; full article pending":51,"search-result reviewed; full section pending":3}. No full product runtime or media test.

## Source review

- [view-customization](https://help.clickup.com/hc/en-us/articles/7255480884887-Customize-views-to-increase-productivity): Multiple sorting keys are prioritized in configured order; add the fields as visible columns before sorting.
- [template-customize](https://help.clickup.com/hc/en-us/articles/6326086730263-Customize-a-template): Template application can select a subset of settings. Updating the existing template overwrites it; distinguish applying from changing the source template.
- [checklist-templates](https://help.clickup.com/hc/en-us/articles/13455445264663-Create-checklist-templates): Role-specific create, apply, edit and removal permissions. Documented limits: 250 checklists per task, 500 items per checklist, item description 2,000 characters.
- [message-edit-delete](https://help.clickup.com/hc/en-us/articles/30092637130263-Edit-or-delete-messages): Edit sent message from context menu or hover toolbar; keyboard E shortcut when enabled. Edits 15 minutes or more after sending show an edited marker.
- [my-tasks](https://help.clickup.com/hc/en-us/articles/18944788880791-My-Tasks-page-formerly-Home): Personal canvas supports adding, reordering and removing cards; recent items can open from it.
- [personal-list-filter](https://help.clickup.com/hc/en-us/articles/31409908744727-Group-and-Filter-your-Personal-List): Personal List has direct group and filter controls plus equivalent settings through Customize.
- [individual-workspace](https://help.clickup.com/hc/en-us/articles/9563959684119-Set-up-your-individual-Workspace): Solo workspace layout available for one-person workspaces; same account can create a separate workspace; policy may require SSO or 2FA.
- [chrome-extension](https://help.clickup.com/hc/en-us/articles/6305599755671-Use-the-Chrome-extension): Chrome extension supports task creation, time tracking, bookmarking, notes and screen capture; setup includes permission review and workspace selection.
- [workload-style](https://help.clickup.com/hc/en-us/articles/30799933602327-Customize-your-Workload-view): Measure by points, tasks, time or percent of capacity; choose color dimension, show/hide weekends and include subtask rollups. Option to open on current selected date.
- [timeline-style](https://help.clickup.com/hc/en-us/articles/31440640517015-Customize-your-Timeline-view): Color by list, status, priority or dropdown value; configure weekends, week numbers, locations, parent names and title compression.
- [timeline-interactions](https://help.clickup.com/hc/en-us/articles/31440880547991-Add-and-manage-tasks-in-Timeline-view): Click canvas to add existing/new task; new task receives row/date defaults. Drag left/right end to change respective date; drag whole bar shifts both; move across groups changes group value.
- [button-field](https://help.clickup.com/hc/en-us/articles/30117356611735-Use-Button-Custom-Fields): Manual automation trigger on individual task; configurable label, icon, color and actions. Permission/plan boundaries apply.
- [design-review](https://help.clickup.com/hc/en-us/articles/6328033402007-Use-ClickUp-for-design-reviews): Review comments can be placed on images, PDF or video attachments; comment also appears in task activity, and can be assigned or resolved.
- [account-settings-index](https://help.clickup.com/hc/en-us/sections/17042819979543-Account-settings): Section lists account settings, storage, sleeping browser tabs, profiles, appearance, locale and high contrast. Section listing only.
- [core-features](https://help.clickup.com/hc/en-us/articles/6311563319063-Core-ClickUp-features): Overview links to hierarchy, user roles, customizable features and web/desktop/mobile entry points.
- [formula-intro](https://help.clickup.com/hc/en-us/articles/6308656424983-Intro-to-Formula-Fields): Numeric/date/time computations; TODAY-dependent formulas exclude sorting, filtering, grouping and calculation cards; input permissions constrain output and formula cannot span locations.
- [formula-advanced](https://help.clickup.com/hc/en-us/articles/15807110924567-Use-advanced-Formulas): Advanced formula editor can use Brain if enabled; text custom fields are not supported as inputs; generated expression results can vary.
- [formula-logic](https://help.clickup.com/hc/en-us/articles/20619000861207-Use-logic-functions-in-Formulas): Boolean AND, NOT, OR and XOR are documented; syntax errors require feedback.
- [formula-string](https://help.clickup.com/hc/en-us/articles/20619090939159-Use-string-functions-in-Formulas): Function table lists string functions but document explicitly says formula fields cannot manipulate strings and rejects text custom field inputs; treat as documentation ambiguity, test before implementation.
- [field-manage](https://help.clickup.com/hc/en-us/articles/6303670304919-Manage-Custom-Fields): Property manager supports sharing fields across locations, setting permissions, defaults, required and ordering options.
- [field-intro](https://help.clickup.com/hc/en-us/articles/6303536766231-Intro-to-Custom-Fields): Location-level field applies to descendants; task-type properties available regardless of location. Both can coexist.
- [field-move](https://help.clickup.com/hc/en-us/articles/14277098696599-Move-Custom-Fields): Moving upward exposes field to descendants; moving downward hides values outside scope without deleting them and re-expanding restores them. Files, Formula, Progress Auto, Relationship, Rollup and Tasks are excluded.
- [field-usage](https://help.clickup.com/hc/en-us/articles/10993484102167-Custom-Fields-uses): Quota counts value assignment, multiple labels count separately, creating field/options and linking tasks do not count. Existing data remains available on quota exhaustion.
- [goal-views](https://help.clickup.com/hc/en-us/articles/30807756167447-Use-views-for-goals-and-OKRs): Vendor recommends separate filtered/grouped list projections for goals and Gantt for dependencies and milestones; advice not measured usability.
- [goal-cards](https://help.clickup.com/hc/en-us/articles/6325664888727-Goals-cards): Grid cards show progress donut, target count, owner, last update; target count opens editing and card opens details.
- [dependencies-intro](https://help.clickup.com/hc/en-us/articles/6309155073303-Intro-to-Dependency-Relationships): Directed blocks and blocked-by relations remain visible after completion; Done counts as completion.
- [scheduling-intro](https://help.clickup.com/hc/en-us/articles/29661121592087-Intro-to-scheduling): Duration, non-working days and dependency rescheduling cooperate; two of start/due/duration determine the third.
- [task-duration](https://help.clickup.com/hc/en-us/articles/29571347936791-Use-task-duration-to-schedule-tasks): Working-day duration excludes non-working days; elapsed duration counts calendar days; duration editor within date modal.
- [milestones](https://help.clickup.com/hc/en-us/articles/6304458574615-Milestones): Milestone is a custom task type represented with diamond icon; type filter and Gantt representation supported.
- [clickapps](https://help.clickup.com/hc/en-us/articles/6304327753111-Intro-to-ClickApps): Owners/admins toggle modular features at workspace or supported Space scope; members can view but guests cannot manage.

## New behavior records

### Ordered multi-field sort

Sort uses ordered keys and requires the relevant fields to be columns.

Proposed QA: Test priority reorder, stable tie-breaks, hidden field changes, nulls and persistence.

Sources: [clickup-view-customization](https://help.clickup.com/hc/en-us/articles/7255480884887-Customize-views-to-increase-productivity).

### Template apply versus overwrite

Selective template settings are applied to destination; updating modifies the template itself. Checklist action permissions vary by role.

Proposed QA: Confirm affected source versus copy, preview selected settings, validate quotas and permissions.

Sources: [clickup-template-customize](https://help.clickup.com/hc/en-us/articles/6326086730263-Customize-a-template), [clickup-checklist-templates](https://help.clickup.com/hc/en-us/articles/13455445264663-Create-checklist-templates).

### Personal composable dashboard

Personal page contains reorderable removable cards, recent items and configurable personal list grouping/filtering.

Proposed QA: Test add/remove/reorder, keyboard, personalization persistence, empty state and cross-device context.

Sources: [clickup-my-tasks](https://help.clickup.com/hc/en-us/articles/18944788880791-My-Tasks-page-formerly-Home), [clickup-personal-list-filter](https://help.clickup.com/hc/en-us/articles/31409908744727-Group-and-Filter-your-Personal-List), [clickup-individual-workspace](https://help.clickup.com/hc/en-us/articles/9563959684119-Set-up-your-individual-Workspace).

### Message editing provenance

Edit from context menu or hover toolbar; after fifteen minutes, edited marker is shown.

Proposed QA: Test keyboard and focus, simultaneous edit, timestamp boundary, permissions and audit.

Sources: [clickup-message-edit-delete](https://help.clickup.com/hc/en-us/articles/30092637130263-Edit-or-delete-messages).

### Contextual browser capture

Browser extension captures work while browsing with workspace selection and permission review.

Proposed QA: Test source attribution, private content, denied permissions, offline behavior and duplicate capture.

Sources: [clickup-chrome-extension](https://help.clickup.com/hc/en-us/articles/6305599755671-Use-the-Chrome-extension).

### Workload metric and color encoding

Workload units and color dimensions are configurable independently. Layout options control temporal and hierarchical context.

Proposed QA: Test unit consistency, chart legend, contrast, hidden weekends, rollups and empty rows.

Sources: [clickup-workload-style](https://help.clickup.com/hc/en-us/articles/30799933602327-Customize-your-Workload-view), [clickup-timeline-style](https://help.clickup.com/hc/en-us/articles/31440640517015-Customize-your-Timeline-view).

### Timeline direct manipulation

Canvas placement creates with row/date defaults; drag endpoints edit one date, whole bar edits both, cross-row drag changes grouping.

Proposed QA: Test pointer and keyboard, cancel, permission, date boundaries, cross-group confirmation and rollback.

Sources: [clickup-timeline-interactions](https://help.clickup.com/hc/en-us/articles/31440880547991-Add-and-manage-tasks-in-Timeline-view).

### Configurable action property

Button property invokes task-specific automations; text, icon, color and actions configurable.

Proposed QA: Test pending, repeat click, scope, permissions, confirmation, errors and audit.

Sources: [clickup-button-field](https://help.clickup.com/hc/en-us/articles/30117356611735-Use-Button-Custom-Fields).

### Anchored review and activity mirror

Attachment comment also appears in task activity and supports assignment/resolution.

Proposed QA: Test stable comment identity, media version, anchor coordinate, permission and resolved state.

Sources: [clickup-design-review](https://help.clickup.com/hc/en-us/articles/6328033402007-Use-ClickUp-for-design-reviews).

### Property schema by type and location

Properties may inherit from location hierarchy or be attached to object type; both are visible in task schema.

Proposed QA: Test shared identity, duplicate names, move, inheritance and role gating.

Sources: [clickup-field-intro](https://help.clickup.com/hc/en-us/articles/6303536766231-Intro-to-Custom-Fields), [clickup-field-manage](https://help.clickup.com/hc/en-us/articles/6303670304919-Manage-Custom-Fields).

### Reversible property scope

Narrowing field scope hides out-of-scope values without deleting them; widening can restore them. Some field types cannot move.

Proposed QA: Test preservation, scope visibility and ACL enforcement, query behavior and warning before move.

Sources: [clickup-field-move](https://help.clickup.com/hc/en-us/articles/14277098696599-Move-Custom-Fields).

### Property assignment quota

Usage counts assigned values, not schema creation; each selected label counts. Data survives limit exhaustion.

Proposed QA: Test counting, retry idempotency, read access after exhaustion, clear limit messaging.

Sources: [clickup-field-usage](https://help.clickup.com/hc/en-us/articles/10993484102167-Custom-Fields-uses).

### Computed field input and expression constraints

Calculation inputs and permissions are constrained; TODAY() reduces query support. Vendor string-function article has contradictory wording; avoid asserting unsupported manipulation.

Proposed QA: Test null, invalid types, logic functions, private input, expression syntax and ambiguous string cases.

Sources: [clickup-formula-intro](https://help.clickup.com/hc/en-us/articles/6308656424983-Intro-to-Formula-Fields), [clickup-formula-advanced](https://help.clickup.com/hc/en-us/articles/15807110924567-Use-advanced-Formulas), [clickup-formula-logic](https://help.clickup.com/hc/en-us/articles/20619000861207-Use-logic-functions-in-Formulas), [clickup-formula-string](https://help.clickup.com/hc/en-us/articles/20619090939159-Use-string-functions-in-Formulas).

### Goal progress summary and drilldown

Goal card combines progress, target count, owner and freshness with target/detail entry points.

Proposed QA: Test metric denominator, zero targets, stale data, accessible donut alternative and edit permissions.

Sources: [clickup-goal-views](https://help.clickup.com/hc/en-us/articles/30807756167447-Use-views-for-goals-and-OKRs), [clickup-goal-cards](https://help.clickup.com/hc/en-us/articles/6325664888727-Goals-cards).

### Dependency relationship persistence

Blocker and waiting-on edges remain visible after Done or Closed.

Proposed QA: Test direction, cycle handling (not established), completion and edge visibility.

Sources: [clickup-dependencies-intro](https://help.clickup.com/hc/en-us/articles/6309155073303-Intro-to-Dependency-Relationships).

### Two-input scheduling

Any two of start date, due date and duration determine the third; workday vs calendar duration differs.

Proposed QA: Test holidays, timezone, date precision, edit precedence, invalid range and cascades.

Sources: [clickup-scheduling-intro](https://help.clickup.com/hc/en-us/articles/29661121592087-Intro-to-scheduling), [clickup-task-duration](https://help.clickup.com/hc/en-us/articles/29571347936791-Use-task-duration-to-schedule-tasks).

### Milestone as typed object

Milestone is a task type, not merely a decorative label; icon and filtering reflect type.

Proposed QA: Test type conversion, filtering, timeline representation and accessible label.

Sources: [clickup-milestones](https://help.clickup.com/hc/en-us/articles/6304458574615-Milestones).

### Scoped modular features

Admins/owners can enable features globally or per supported Space, while members have view-only access.

Proposed QA: Test inherited and overridden configurations, permission, disable-with-data and discoverability.

Sources: [clickup-clickapps](https://help.clickup.com/hc/en-us/articles/6304327753111-Intro-to-ClickApps).


## Index and CI

The explicit ClickUp projection now contains 110 observations, all source IDs resolve, and historical source status snapshots in the projection were refreshed. These are observations, not a deduplicated universal pattern count. Prior [CI](https://github.com/ianmaciel7/exams-app-archive/actions/runs/46019837420) passed the ClickUp projection test, but failed the overall suite (10 failures: plugin sync and regression monitor). Another [CI](https://github.com/ianmaciel7/exams-app-archive/actions/runs/46019992834) was in progress at inspection. No claim the unrelated failures are resolved. Do not weaken quality gates. A separate regression analysis is needed if they persist.

Remaining: 57 pending or failed source records, full article denominator, visual and motion evidence, actual CSS, accessibility and runtime. [Machine-readable review](review-behaviors-2026-11-27.json) · [Index](pattern-index.json).
