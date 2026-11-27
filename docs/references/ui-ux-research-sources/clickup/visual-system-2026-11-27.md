# ClickUp — visual system, interaction evidence and gallery discovery (batch 5)

Reviewed 2026-11-27. Baseline `0e02393d0795aa78bc1a1df42b5c62a77b738c91`. 26 new source records, 10 interaction analyses, four opened vendor screenshots and three linked GIFs whose retrieval failed. No actual product CSS or official internal design system established. No proprietary media copied.

## Evidence classes

- [Brand guidelines](https://clickup.com/brand?content_language=English): official identity gradients #FF02F0 → #FC6D2D; #6647F0 → #0091FF. Headlines use Plus Jakarta Sans, body Inter, captions Sometype Mono. Brand roles are not application tokens.
- [Uizze](https://uizze.com/design/clickup): public marketing site measurement dated 2026-10-27, reports #FFFFFF, #292D34, #838383, #646464, #000000, #7B68EE and heading 60 px, body 22 px, button radius 8 px. Not independent measurements by us, nor authenticated app values.
- UI Archive, Sitepeel, Refero Styles and Squint remain discovery candidates; direct fetch or full-page review incomplete. Do not merge their values into a canonical app theme.

## Interaction observations and proposed validation

### clickup-resizable-split-panel

Close/open via arrow and shortcut; drag divider; double-click resets default width; search filters while typing.

QA proposal: Record default/min/max widths at runtime, pointer capture, keyboard resize alternative, reset, collapsed/focus/touch.

[clickup-sidebar-search](https://help.clickup.com/hc/en-us/articles/32490367010839-Create-and-search-items-in-the-Home-and-Spaces-Sidebars). Evidence: official documentation; runtime-unverified.

### clickup-view-icon-override

View type icon can be overridden through searchable picker; persists for viewers, favorites and templates; clear restores default.

QA proposal: Test fallback, shared settings, icon-only accessible name and consistency across surfaces.

[clickup-view-icons](https://help.clickup.com/hc/en-us/articles/33624087758487-Use-custom-icons-for-your-views). Evidence: official documentation; runtime-unverified.

### clickup-reader-appearance

Sans/serif/mono, three sizes, default/full width, apply typography to all pages, optional header metadata, relationships dialog or accordion, sticky outline.

QA proposal: Separate per-page from document settings; test text zoom, persistence, reading width, mobile and semantic headings.

[clickup-doc-page-styles](https://help.clickup.com/hc/en-us/articles/6325167441175-Customize-Page-styles-in-Docs). Evidence: official documentation; runtime-unverified.

### clickup-reader-focus

Block focus dims other content while typing; page focus hides sidebars during typing.

QA proposal: Test keyboard, reading/typing transition, contrast of dimmed content, reduced motion and restoring panels.

[clickup-doc-page-styles](https://help.clickup.com/hc/en-us/articles/6325167441175-Customize-Page-styles-in-Docs). Evidence: official documentation; runtime-unverified.

### clickup-list-density

Wrap text, property icons, breadcrumb, parent names, hide tags, empty statuses, collapsed/expanded/flat subtasks and hide header.

QA proposal: Test keyboard discoverability, search/filter semantics, overflow, long titles, layout shift.

[clickup-list-customize](https://help.clickup.com/hc/en-us/articles/7255389296919-Customize-List-view). Evidence: official documentation; runtime-unverified.

### clickup-canvas-connection

Selection bounding box, resize/rotate, endpoint snapping, visible connectors, minimap, keyboard pan and move.

QA proposal: Test zoom coordinate mapping, endpoint drag, undo, keyboard, focus, touch and disconnected states.

[clickup-whiteboard-items](https://help.clickup.com/hc/en-us/articles/6326217118615-Add-items-to-a-Whiteboard). Evidence: official documentation; runtime-unverified.

### clickup-canvas-motion-preference

Whiteboard preferences include reduced motion enabled by default, alignment guides, edge scrolling and grid toggles. Scope is Whiteboard only.

QA proposal: Measure actual timing with recording; test OS reduced motion, interruption, scroll and non-motion feedback.

[clickup-whiteboard-items](https://help.clickup.com/hc/en-us/articles/6326217118615-Add-items-to-a-Whiteboard). Evidence: third-party description; image not inspected.

### clickup-system-command-palette

Desktop global command bar, configurable hotkey, local clipboard history (screenshot history Mac only), browser-to-app redirect preference.

QA proposal: Test launch, foreground focus restore, consent, cross-platform conflicts, privacy and offline failure.

[clickup-desktop](https://help.clickup.com/hc/en-us/articles/6311884486423-Use-the-ClickUp-desktop-app). Evidence: official documentation; runtime-unverified.

### clickup-undo-toast-reference

Third-party text description identifies status-change toast with undo and close.

QA proposal: Inspect screenshot and test undo availability, expiration, competing operations, accessible live region.

[clickup-nicelydone-components](https://nicelydone.club/examples/apps/clickup/components). Evidence: third-party description; image not inspected.

### clickup-empty-folder-reference

Third-party description identifies empty folder illustration, explanation and create-list CTA.

QA proposal: Test distinction between truly empty, filtered empty, permission failure and loading; CTA relevance.

[clickup-nicelydone-components](https://nicelydone.club/examples/apps/clickup/components). Evidence: third-party description; image not inspected.

## Media references

- [clickup-sidebar-resize](https://help.clickup.com/hc/article_attachments/36607098050455): Divider hover shows Close, Resize Drag and Reset Double-click; nested tree, icon rail, selected row and contextual plus/ellipsis. Status: opened.
- [clickup-view-custom-icon](https://help.clickup.com/hc/article_attachments/37480818868503): Selected List view has a globe icon, black underline; adjacent tabs include pinned icons and add-view affordance. Status: opened.
- [clickup-page-style-panel](https://help.clickup.com/hc/article_attachments/35207206612503): Segmented tiles for font style, size and width; tinted selected tile; header switches with labels and icons. Status: opened.
- [clickup-whiteboard-connection](https://help.clickup.com/hc/article_attachments/31273397360919): Two shapes connected by arrow, blue anchors, dashed guides, floating contextual toolbar. Status: opened.
- [clickup-list-column-resize-gif](https://help.clickup.com/hc/article_attachments/44225755104407): Official article labels GIF as column resizing; animation not reproduced. Status: unsupported-content-type.
- [clickup-whiteboard-create-gif](https://help.clickup.com/hc/article_attachments/39340374185111): Official article labels GIF showing whiteboard; animation not reproduced. Status: unsupported-content-type.
- [clickup-desktop-command-gif](https://help.clickup.com/hc/article_attachments/39020992302487): Article describes desktop AI Command Bar launched from another app; file fetch failed. Status: cache-miss.

## Third-party product galleries

Gummble reports 964 web screens and 207 flows with latest capture 2025-11-05. Uiland reports 218 mobile screens and 14 flows. Counts are gallery metadata, not downloaded/inspected evidence, not unique across galleries, and not evidence of current 2026 UI. Nicelydone product/component descriptions were retrieved. Mobbin screen links and individual mobile screens are candidates only. Do not bypass sign-in or copy gallery media. Preserve links and verify version and rights before use.

## Source delta

- [ClickUp brand guidelines](https://clickup.com/brand?content_language=English) — verified; Brand palette, typography, logo usage and product illustration categories; not authenticated UI tokens.
- [Uizze ClickUp design measurements](https://uizze.com/design/clickup) — verified; Public marketing site measured 2026-10-27; not official internal tokens.
- [UI Archive ClickUp](https://ui-archive.com/clickup.com) — search-result reviewed; direct fetch failed; Redirect loop; token categories listed in search only.
- [Sitepeel ClickUp design extraction](https://sitepeel.dev/design-md/clickup.com/) — search-result reviewed; direct fetch failed; Cache miss; do not use purported tokens as verified.
- [Refero Styles ClickUp](https://styles.refero.design/style/efcb73cb-b84a-4ae7-9a2b-e1116f79f130) — search-result reviewed; full article pending; Marketing site token candidate, not production workspace.
- [Use custom icons for your views](https://help.clickup.com/hc/en-us/articles/33624087758487-Use-custom-icons-for-your-views) — verified; Shared view icon, searchable picker and reset to type default.
- [Customize Page styles in Docs](https://help.clickup.com/hc/en-us/articles/6325167441175-Customize-Page-styles-in-Docs) — verified; Font family categories, sizes, page widths, focus mode, outline and relationship layouts.
- [Use the ClickUp desktop app](https://help.clickup.com/hc/en-us/articles/6311884486423-Use-the-ClickUp-desktop-app) — verified; System-wide command bar, clipboard history, deep linking and shortcut customization.
- [Customize your Workload view](https://help.clickup.com/hc/en-us/articles/30799933602327-Customize-your-Workload-view) — search-result reviewed; full article pending; Color by list, status, priority or dropdown property.
- [Customize your Timeline view](https://help.clickup.com/hc/en-us/articles/31440640517015-Customize-your-Timeline-view) — search-result reviewed; full article pending; Color by list, status, priority or dropdown property.
- [Add and manage tasks in Timeline view](https://help.clickup.com/hc/en-us/articles/31440880547991-Add-and-manage-tasks-in-Timeline-view) — search-result reviewed; full article pending; Drag date range endpoints, context-derived task defaults.
- [Use Button Custom Fields](https://help.clickup.com/hc/en-us/articles/30117356611735-Use-Button-Custom-Fields) — search-result reviewed; full article pending; Configurable icon/color and automation action.
- [Use ClickUp for design reviews](https://help.clickup.com/hc/en-us/articles/6328033402007-Use-ClickUp-for-design-reviews) — search-result reviewed; full article pending; Annotation of image, video and PDF.
- [Account settings](https://help.clickup.com/hc/en-us/sections/17042819979543-Account-settings) — search-result reviewed; full article pending; Theme, contrast and user settings.
- [Core ClickUp features](https://help.clickup.com/hc/en-us/articles/6311563319063-Core-ClickUp-features) — search-result reviewed; full article pending; Feature overview.
- [Gummble ClickUp web gallery](https://gummble.com/apps/clickup-web) — verified; Gallery reports 964 screens, 207 flows, three captured versions, latest capture 2025-11-05; only preview listing inspected.
- [Gummble ClickUp iOS gallery](https://gummble.com/apps/clickup-ios) — search-result reviewed; direct fetch failed; Cache miss; no iOS screen count asserted.
- [Nicelydone ClickUp examples](https://nicelydone.club/examples/apps/clickup) — verified; Product screens, onboarding, flows and component directory; text descriptions inspected.
- [Nicelydone ClickUp components](https://nicelydone.club/examples/apps/clickup/components) — verified; Descriptions of reversible notification toast and empty folder state; images not opened.
- [Uiland ClickUp mobile gallery](https://uiland.design/screens/clickup/screens/f317d0bb-e252-4c38-aa56-37cef23f0972) — verified; Directory reports 218 screens and 14 flows; sign-in required for most images.
- [Uiland ClickUp create screen](https://uiland.design/screens/clickup/screens/f317d0bb-e252-4c38-aa56-37cef23f0972/screen/d79f0e53-99f5-4017-a5fe-fbcfdb2abce2) — search-result reviewed; full article pending; Mobile creation screen candidate.
- [Uiland ClickUp goal and task](https://uiland.design/screens/clickup/screens/f317d0bb-e252-4c38-aa56-37cef23f0972/screen/d464f66f-0dbd-4ad2-ad52-1c04ce530028) — search-result reviewed; full article pending; Mobile goal/task screen candidate.
- [Uiland ClickUp bookmarks](https://uiland.design/screens/clickup/screens/f317d0bb-e252-4c38-aa56-37cef23f0972/screen/8bd80c6a-c7f0-4a18-8881-69f327df7ca7) — search-result reviewed; full article pending; Mobile bottom sheet candidate.
- [Mobbin ClickUp web screen A](https://mobbin.com/explore/screens/cb9d3f68-0824-457e-b951-cb42b20fdf7b) — search-result reviewed; full article pending; Screen candidate; no visual behavior claim.
- [Mobbin ClickUp web screen B](https://mobbin.com/explore/screens/7587be5b-57f1-49c3-b571-58b7859abb59) — search-result reviewed; full article pending; Screen candidate; no visual behavior claim.
- [Squint landing-page teardown](https://squint.page/sample-11/) — search-result reviewed; full article pending; Marketing page hierarchy analysis; not application CSS.

## Remaining gaps

- Authenticated app CSS and computed styles, actual icon paths, semantic color tokens, spacing scale, typography, breakpoints
- Motion GIF decoding and frame/timing measurements; three linked GIFs not inspected
- Full gallery screens and flows subject to access and rights
- Actual accessibility, contrast and focus order verification
- Official article-by-article enumeration remains incomplete

Machine-readable: [visual-system-2026-11-27.json](visual-system-2026-11-27.json).
