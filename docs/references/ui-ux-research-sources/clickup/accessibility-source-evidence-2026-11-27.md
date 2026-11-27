# ClickUp — accessibility and source evidence (batch 12)

Reviewed 2026-11-27, baseline `fb79a22dd928c2a87739bbb72f12a150a813c134`. 15 new source records, 8 research/QA records. Distinguish vendor statements, user feedback, W3C guidance, pinned source and runtime tests. No authenticated session or app modification.

## Official component source

The [FadingScroll repository](https://github.com/clickup/clickup_fading_scroll/) identifies its origin in the ClickUp mobile team. Pinned commit `d41d2af2cc1ab918fd6939e62a6730a6392c84df`. LICENSE is a placeholder; no source or images redistributed. The source implements independent edge fades based on remaining scroll extent, with default threshold 50 Flutter logical units, half-viewport cap and optional linear animation. The test source references eleven golden files across no-scroll, horizontal and vertical positions, at 500 × 400 logical units, DPR 1. The test's 1 ms scroll action is not a production animation duration. Neither demo nor test was executed.

- [lib/clickup_fading_scroll.dart](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/lib/clickup_fading_scroll.dart) — blob `9a9b4daf63034e2b18a32064cb4c5222628ab086`, text retrieved.
- [test/fading_scroll_test.dart](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/fading_scroll_test.dart) — blob `a763d3bee5a3c8d05579d2bee15ad4ef6c3c3156`, text retrieved.
- [LICENSE](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/LICENSE) — blob `ba75c69f7f2175380928fff6693b797e2373e603`, text retrieved.
- [README.md](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/README.md) — blob `3f00ba98ec7886256629b845f81ef1cb6617af00`, text retrieved.

### Golden test evidence pointers (not inspected images)

- [not_scrollable.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/not_scrollable.png) — blob `8240851ff475f00eac5711911c6ec008eb00ebbe`.
- [horizontal_01_start.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/horizontal_01_start.png) — blob `131d0a4d0ecc93b9bebe6fb45edb69bb6a6f9deb`.
- [horizontal_02_near_start.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/horizontal_02_near_start.png) — blob `d59c20c2dc90d7681519d3743d632c80db35da20`.
- [horizontal_03_middle.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/horizontal_03_middle.png) — blob `a4f9aa9f3892fc2c6effccb4cd9ca7884b08aa9e`.
- [horizontal_04_near_end.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/horizontal_04_near_end.png) — blob `4b8d61e243e1626afeb82cf226fc136d33969774`.
- [horizontal_05_end.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/horizontal_05_end.png) — blob `491e023ee6cca2145e3bfedd9fa64faedb28ede0`.
- [vertical_01_start.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/vertical_01_start.png) — blob `8aacb421e83e9d35ba6a5ec26d399eafdc43986e`.
- [vertical_02_near_start.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/vertical_02_near_start.png) — blob `eeed7fab092ae7e11e82f0bddb8f604fb2979a2f`.
- [vertical_03_middle.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/vertical_03_middle.png) — blob `4b6660b6e1c02553299248704a1ab1db3e79ef7e`.
- [vertical_04_near_end.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/vertical_04_near_end.png) — blob `fadd0e9c784fbfb0b9755154770cc5c099d1dc2a`.
- [vertical_05_end.png](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/vertical_05_end.png) — blob `bdc8b6fe067b5aae89085fe49f27419b360754ce`.

## Accessibility and component contracts

### Scroll overflow edge fading

Official Flutter source computes separate fades from hidden content before/after the viewport; supports horizontal and vertical axes. Default threshold 50 logical units, fade proportion capped at half the viewport. No fade when no content hidden on that edge. Optional animation duration; linear default curve, no animation when duration omitted.

Proposed validation: Test scroll positions, resizing, no overflow, high contrast, reduced motion, focus and visible scrollbar; don't assume web or production app uses these values.

Evidence: pinned source inspected; runtime not executed. Sources: [clickup-fading-scroll-code](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/lib/clickup_fading_scroll.dart), [clickup-fading-scroll-tests](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/test/fading_scroll_test.dart), [clickup-fading-scroll-license](https://github.com/clickup/clickup_fading_scroll/blob/d41d2af2cc1ab918fd6939e62a6730a6392c84df/LICENSE).

### Context-sensitive keyboard shortcuts

Global shortcuts configurable and initially disabled. Editor and task contexts have different bindings; navigation, closing and inbox commands documented. Docs support moving a block and converting selected text to a task or comment.

Proposed validation: Test input focus, shortcut conflicts, discoverability, platform mapping and ability to perform all actions without shortcut.

Evidence: official documentation; runtime unverified. Sources: [clickup-keyboard](https://help.clickup.com/hc/en-us/articles/6309030550167-Use-keyboard-shortcuts), [clickup-docs-keyboard](https://help.clickup.com/hc/en-us/articles/31672708905495-Keyboard-shortcuts-in-Docs).

### Persistent high-contrast disclosure indicator

Vendor documents a persistent background treatment for toggle-list chevrons in authenticated Docs; hover supplements visibility. Scope excludes public and several embedded surfaces.

Proposed validation: Test actual resting/hover/focus appearance, contrast, accessible expanded state and all excluded surfaces separately.

Evidence: official documentation; runtime unverified. Sources: [clickup-docs-keyboard](https://help.clickup.com/hc/en-us/articles/31672708905495-Keyboard-shortcuts-in-Docs), [clickup-high-contrast](https://help.clickup.com/hc/en-us/articles/6310793610391-Activate-High-Contrast-mode).

### Non-drag pointer and keyboard alternatives

External WCAG criterion requires a single-pointer alternative for nonessential drag functionality. Keyboard accessibility is separate. Proposed for sortable tabs, cards and panels, not a confirmed ClickUp feature.

Proposed validation: Test click/tap move menu, keyboard reorder, cancel, focus restoration and result announcement.

Evidence: external standard and proposed QA; no ClickUp conformance claim. Sources: [clickup-accessibility](https://clickup.com/accessibility), [clickup-wcag-dragging-reference](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html).

### Focus visibility with overlays

External minimum criterion requires focused controls not fully hidden by author content; sticky headers/footers and nonmodal overlays are relevant.

Proposed validation: Test sidebar popover, tab strip, sticky answer toolbar, toast and modal; verify focus indicator independently.

Evidence: external standard and proposed QA; no runtime observation. Sources: [clickup-wcag-focus-reference](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html), [clickup-accessibility](https://clickup.com/accessibility).

### Minimum pointer targets in dense workspace

External WCAG criterion specifies 24 by 24 CSS pixels or qualifying exceptions/spacing. Icon glyph size differs from clickable target.

Proposed validation: Measure hit areas rather than glyphs; verify close, more, checkbox, resize controls and mobile alternative.

Evidence: external standard; proposed QA. Sources: [clickup-wcag-target-reference](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).

### Reflow versus two-dimensional work surfaces

External WCAG criterion covers reflow at 320 CSS px width for vertical reading, with exceptions for content requiring two-dimensional layout.

Proposed validation: Test question reader, notes, sidebar controls and dialog at 320 CSS px, 400% zoom; isolate table/graph exceptions and maintain reachable controls.

Evidence: external standard; proposed QA. Sources: [clickup-wcag-reflow-reference](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html).

### Form accessibility risk and validation

Community reports describe inaccessible answer options, CAPTCHA and scrollbars; vendor acknowledges ongoing accessibility work. Reports not independently reproduced.

Proposed validation: Use native radio grouping, accessible names and error announcements, keyboard navigation, visible overflow, accessible alternatives to CAPTCHA and manual screen reader tests.

Evidence: community report; not independently reproduced. Sources: [clickup-form-accessibility-feedback](https://feedback.clickup.com/feature-requests/p/click-up-forms-no-fully-accessible), [clickup-scrollbar-feedback](https://feedback.clickup.com/feature-requests/p/make-vertical-scrollbar-visible-in-forms), [clickup-accessibility](https://clickup.com/accessibility).

## Retrieval limits

- clickup-sitepeel: cache miss on retry.
- clickup-ui-archive: redirect loop on retry.
- clickup-gummble-ios: cache miss on retry.
- clickup-fading-scroll-demo: cache miss.
- https://help.clickup.com/hc/en-us/sitemap.xml: not accessible via web tool.

- Actual VPAT content not retrieved; requires request to vendor
- Authenticated workspace DOM, CSS, accessibility tree and visual/motion capture
- Golden PNG bytes not retrieved or inspected; tests not executed
- Other gallery leads remain inaccessible; no bypass attempted
- Complete Help Center enumeration remains unestablished

Registry status: {"verified":322,"search-result reviewed; direct fetch failed":8,"direct fetch failed":1,"search-result reviewed; playback pending":1}. Includes W3C references explicitly scoped as external standards and one unavailable demo. The index contains 134 observations/QA records; they are not all independently verified product behavior. [Structured evidence](accessibility-source-evidence-2026-11-27.json).
