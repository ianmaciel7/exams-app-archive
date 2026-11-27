# ClickUp — import, export, search, security and recovery (batch 8)

Reviewed 2026-11-27. Baseline `96cdcf8d41672d4f3be86844ccd64526d29d80bd`. 32 unique new source records. Twelve documented behavior contracts; no runtime tests. The existing source registry contained 285 ClickUp records, with 200 marked verified; this is registry metadata, not proof all links were independently checked again. Normalized URL duplicates: 0.

## Import compatibility

Source: [Importer field support](https://help.clickup.com/hc/en-us/articles/6310876671255-Fields-supported-by-the-Spreadsheets-importer).

- Supported property types: Checkbox, Date, Dropdown, Email, Labels, Money, Number, Phone, Progress (Manual), Rating, Text, Text area (Long text), Website.
- Unsupported as listed: Button, Files, Formula, Location, People, Progress (Auto), Relationships, Rollup, Signature, Task links, Voting.
- Task links is an importer-specific label; do not add to the previous general type count.

## Behavior contracts

### clickup-import-mapping

Choose file and destination, set date/delimiter, review suggested field mapping and invalid cell values before running. Mappings may reuse previous structural matches across users.

Proposed validation: Test locale, duplicate source IDs, hierarchy references, permission to create schema, and explicit disclosure of unmapped columns.

Sources: [clickup-spreadsheet-import](https://help.clickup.com/hc/en-us/articles/6310834724247-Use-the-Spreadsheets-Importer), [clickup-spreadsheet-prepare](https://help.clickup.com/hc/en-us/articles/6310821748759-Prepare-a-spreadsheet-for-import).

### clickup-import-job

Queue and running states can be canceled; result has completion or failure status and drill-down by entity, actor and operation ID.

Proposed validation: Test partial import, cancellation race, retry without duplicate entities, report authorization; rollback not established.

Sources: [clickup-import-history](https://help.clickup.com/hc/en-us/articles/6310875506839-Manage-imports).

### clickup-import-fidelity

Import maps cell values rather than workbook formatting. Computed, attachment and relational fields are unsupported; comments, image objects and rich presentation do not survive.

Proposed validation: Show preflight loss report; distinguish omitted property from empty value, and preserve raw source for reconciliation.

Sources: [clickup-import-fields](https://help.clickup.com/hc/en-us/articles/6310876671255-Fields-supported-by-the-Spreadsheets-importer).

### clickup-structured-doc-import

Docx, HTML and Markdown can be imported; HTML splitting is an option and HTML has a 10 MB cap. Protected destination and role capabilities constrain import.

Proposed validation: Test headings and nested pages, tables, unsupported embeds, file size, formatting and external references.

Sources: [clickup-import-docs](https://help.clickup.com/hc/en-us/articles/6325375296407-Import-Docs).

### clickup-export-projection

CSV exports are scoped to selected locations. Docs export selected or all pages into HTML, PDF or Markdown; embeds excluded and emailed download links expire after one hour.

Proposed validation: Test access, consistent snapshot, stable identifiers, attachment download and missing links; do not equate export to complete backup.

Sources: [clickup-export-tasks](https://help.clickup.com/hc/en-us/articles/6310551109527-Export-task-data), [clickup-export-overview](https://help.clickup.com/hc/en-us/articles/6310786693015-How-do-I-export-my-Workspace-s-data), [clickup-export-doc](https://help.clickup.com/hc/en-us/articles/6325383226391-Export-a-Doc).

### clickup-trash-lifecycle

Recoverable deleted items have 30-day window. Restore is individual. Deleted container contents are nested under container; some views, comments and individually deleted attachments cannot be recovered.

Proposed validation: Test delete versus archive, permission, container restore, multi-list identity, permanent delete warning and expiry.

Sources: [clickup-trash](https://help.clickup.com/hc/en-us/articles/6311742742423-Restore-items-from-the-Trash), [clickup-task-delete](https://help.clickup.com/hc/en-us/articles/6311358652951-Delete-a-task).

### clickup-disaster-recovery

Vendor reports automatic region-local encrypted backups for disaster recovery only, retained up to one year; item-level restore unavailable.

Proposed validation: Define separate self-service restore and disaster recovery policies; verify restore drill, RPO/RTO and export fidelity independently.

Sources: [clickup-backups](https://help.clickup.com/hc/en-us/articles/43941086639383-Backups-and-data-retention).

### clickup-search-command

Global search starts with recents, then relevance-ranked results. Pinned object/source filters, creator/assignee/location/status/type and archive controls; results expose open, new tab and copy-link actions, keyboard equivalents. AI can assist after no results.

Proposed validation: Test focus restoration, no results versus access denied, stale index, query history, source label and keyboard shortcuts.

Sources: [clickup-command](https://help.clickup.com/hc/en-us/articles/6533695640343-What-is-the-AI-Command-Bar), [clickup-search-filter](https://help.clickup.com/hc/en-us/articles/12609594406679-Sort-and-filter-AI-Command-Bar-results).

### clickup-link-boundary

Internal links require membership and object access; public links have different routes, and enterprise auth settings can require sign-in.

Proposed validation: Test public versus internal copy, revoke access, unauthenticated user, custom IDs, expired share and no permission leakage.

Sources: [clickup-link-types](https://help.clickup.com/hc/en-us/articles/41521317138455-What-s-the-difference-between-public-and-internal-links), [clickup-public-auth](https://help.clickup.com/hc/en-us/articles/33077853953943-Public-views-authentication).

### clickup-session-expiry

Session-duration policy can force all active users to sign out when changing from never-expire. Idle timeout offers continuation five minutes before expiry.

Proposed validation: Test confirmation, preservation of unsaved work, multi-tab activity, reauthentication and policy changes.

Sources: [clickup-session-management](https://help.clickup.com/hc/en-us/articles/6327732937751-Session-management).

### clickup-identity-controls

Optional or required SSO, policy-specific 2FA and administrator-assisted recovery; default policy differs from enforced policy.

Proposed validation: Test enrollment, lockout, recovery, revocation and cross-tenant scope; don't infer cryptographic assurance from UI.

Sources: [clickup-two-factor](https://help.clickup.com/hc/en-us/articles/6327741965591-Activate-and-manage-two-factor-authentication), [clickup-sso](https://help.clickup.com/hc/en-us/articles/6305043992343-Intro-to-single-sign-on-SSO), [clickup-security-defaults](https://help.clickup.com/hc/en-us/articles/21797055143575-Default-security-settings).

### clickup-retention-inheritance

Global chat retention can be overridden per conversation type; daily cleanup also removes child replies. Audit history has separate 60-day limit.

Proposed validation: Test inheritance, time-based deletion, admin permissions, audit trail and legal retention policy. Separate chat cleanup from backup lifecycle.

Sources: [clickup-chat-retention](https://help.clickup.com/hc/en-us/articles/30452538132759-Chat-data-retention), [clickup-audit-limits](https://help.clickup.com/hc/en-us/articles/25324213764119-Audit-Logs-feature-availability-and-limits), [clickup-audit](https://help.clickup.com/hc/en-us/articles/21929900448535-Workspace-audit-logs).

## Source registry reconciliation

Before: {"verified":200,"search-result reviewed; full article pending":80,"search-result reviewed; direct fetch failed":3,"search-result reviewed; full section pending":2}.

After: {"verified":215,"search-result reviewed; full article pending":96,"search-result reviewed; direct fetch failed":3,"search-result reviewed; full section pending":3}.

Status 'verified' denotes recorded article or directory retrieval, not a live UI test or independent verification of every vendor claim. Search previews remain explicitly partial. No coverage percentage against an unknown denominator.

## Remaining gaps

- Full article enumeration and review of pending sources
- Runtime and visual capture, motion measurements and design tokens
- Cross-index records into canonical searchable interface pattern catalog
- Verify API schema and migration behavior through authorized sandbox

[Structured batch](portability-security-2026-11-27.json). No private content, app code or proprietary media copied.
