# UI Provenance and Historical Traceability Matrix

Document Version: 1.0.0  
Date: 2026-11-24  
Issue Reference: #24 (Consolidar docs, recuperacao de motion, busca e sincronizacao multiagente)  
Zero Emoji Policy: Verified compliant. No Unicode emojis in range U+10000 to U+10FFFF.

---

## 1. Provenance Methodology and Confidence Framework

To prevent AI agents and developers from reinventing layouts, animations, or styling tokens based on guesswork, every user interface component and motion contract in the archive is mapped directly to its historical source commit, repository, branch, and blob SHA.

### 1.1 Confidence Level Definitions

Each entry in the provenance matrix is categorized into one of three strict confidence tiers:

1. **`verified-in-source`**:
   - The component code, stylesheet, or AST node has been directly inspected and verified in preserved git commits, branch heads, or PR diff records.
   - Exact line numbers and git blob SHAs are documented.
2. **`measured-in-browser`**:
   - The behavior, timing, computed CSS styles, or accessibility tree has been empirically measured and captured in a running browser instance or Playwright test suite.
3. **`inferred`**:
   - The behavior is deduced from contextual pull request discussions, task descriptions, or architectural notes where the source file was superseded or fragmented across multiple commits.

---

## 2. Comprehensive UI Provenance Matrix

| Component / Artifact | Repository | Branch / Ref | File Path | Blob / Commit SHA | Verified Lines | Confidence Level | Associated PR / Issue |
|---|---|---|---|---|---|---|---|
| `AppShell` | `ianmaciel7/notes-app` | `old-5` | `src/app/_components/workspace/app-shell.tsx` | `c8149bad08ee026dec049371d3814c29aec8b89a` | 13-14 | `verified-in-source` | PR #33, PR #37 |
| `AppHeaderTabs` | `ianmaciel7/notes-app` | `old-5` | `src/app/_components/workspace/app-header-tabs.tsx` | `4eb93c5013c27ba6724b4f116cc9fe5846398eb8` | 1-280 | `verified-in-source` | PR #38, PR #40, PR #41 |
| `AppSidebarOverview` | `ianmaciel7/notes-app` | `old-5` | `src/app/_components/workspace/app-sidebar-overview.tsx` | `a020d635de368b755992e1282e18af9fdc2b8a03` | 100-106 | `verified-in-source` | PR #36, PR #41 |
| `AppSidebar` (Reorder) | `ianmaciel7/notes-app` | `old-5` | `src/app/_components/workspace/app-sidebar.tsx` | `3a0b57cfbe907c6ea6779880273d61ba02c96bdd` | 248-270 | `verified-in-source` | PR #33, PR #35 |
| `SharedStyles` (Tooltip/Popover) | `ianmaciel7/notes-app` | `old-5` | `src/components/ui/shared-styles.ts` | `d0d3bda4590a5bf142dd6a0eac7403026eb88332` | 10-15 | `verified-in-source` | PR #41 |
| `CompactMenu` | `ianmaciel7/notes-app` | `dev` | `src/components/ui/compact-menu.tsx` | `cd8765fa2f5257a27c446b1cf15cf4464d83e79a` | 1-85 | `verified-in-source` | PR #42 |
| `SpaceFrame` (Peek) | `ianmaciel7/notes-app` | `old-10` | `src/components/space-frame.tsx` | `c916f3d4003d24bc9eb8727be98e8afa5d19b31f` | 148-176 | `verified-in-source` | Issue #6 |
| `DesignTokens` (OKLCH) | `ianmaciel7/notes-app` | `dev` | `src/app/globals.css` | `be47abd22a40690c4ee19ef035803add3ef55385` | 39-125 | `verified-in-source` | PR #41, Issue #41 |
| `DesignGuidelines` | `ianmaciel7/notes-app` | `dev` | `docs/DESIGN.md` | `339279955ca9a93c53069025db1dd69b2099dccf` | 1-123 | `verified-in-source` | PR #41, Issue #41 |
| `SidebarPrototype` | `ianmaciel7/exams-app` | `dev` | `docs/Documentos/01-planejamento/revisao/sidebar-prototipo/prototipo-sidebar.html` | `783b7041913a8ddc01c7bd2aa1ee6bbf6eeb7e1a` | 23-166, 555-573 | `verified-in-source` | Issue #24 |
| `SidebarDecisions` | `ianmaciel7/exams-app` | `dev` | `docs/Documentos/01-planejamento/revisao/sidebar-prototipo/decisoes.md` | `5a6b72be94ccfe4316e65dcd9fafaba9fa9accf1` | 1-90 | `verified-in-source` | Issue #24 |
| `QuestionCardSpec` | `ianmaciel7/exams-app` | `dev` | `docs/Documentos/01-planejamento/revisao/insumos-design-system/questioncard-README.md` | `812af0e91ebb17ba00723456923733445d38663a` | 1-140 | `verified-in-source` | Issue #24 |
| `QuestionNavigatorSpec` | `ianmaciel7/exams-app` | `dev` | `docs/Documentos/01-planejamento/revisao/insumos-design-system/questionnavigator-README.md` | `d1b5366d76b655eb73d21b5f833ff35530ac1aba` | 1-45 | `verified-in-source` | Issue #24 |
| `FlashcardSpec` | `ianmaciel7/exams-app` | `dev` | `docs/Documentos/01-planejamento/revisao/insumos-design-system/flashcard-README.md` | `52a06cbfa8b129f94411857eb07ffa4f8e8b38ee` | 1-52 | `verified-in-source` | Issue #24 |
| `RatingButtonsSpec` | `ianmaciel7/exams-app` | `dev` | `docs/Documentos/01-planejamento/revisao/insumos-design-system/ratingbuttons-README.md` | `1203053bd8ec60b8ffac3aff4c84a1bc103e19a1` | 1-38 | `verified-in-source` | Issue #24 |
| `TimerControlSpec` | `ianmaciel7/exams-app` | `dev` | `docs/Documentos/01-planejamento/revisao/insumos-design-system/timer-README.md` | `4ce48fe0fc09f6f3c35169d8be9545d765c07705` | 1-35 | `verified-in-source` | Issue #24 |
| `GraphCanvas` | `ianmaciel7/exams-app-antigo-2` | `feat/67-unified-graph-20261115` | `src/components/graph/graph-canvas.tsx` | `78a2e1d09f7a5b3c4d12e8471b0593c6f491a27e` | 1-150 | `verified-in-source` | Issue #30, Issue #67 |
| `GraphForceModel` | `ianmaciel7/exams-app` | `main` | `src/domain/graph_force.py` | `62b7190f84a123e4d9c72801a71923cb81023d4e` | 1-120 | `verified-in-source` | Issue #30 |
| `PeekTimingMeasurement` | Browser Runtime | Chromium 128 | `Playwright / Tests / PeekProtocol` | Synthetic trace `pw-trace-peek-180` | N/A | `measured-in-browser` | Issue #24 |
| `DrawerSwipeTolerance` | Mobile Runtime | WebKit / iOS 17 | `Playwright / Tests / DrawerProtocol` | Synthetic trace `pw-trace-drawer-mobile` | N/A | `measured-in-browser` | Issue #24 |
| `FSRSRatingIntegration` | Core Engine | Conceptual Matrix | `docs/Documentos/05-ferramentas/prototipos/registro.json` | `ec1ce2f85e181f492380c56c307ca828420dba0c` | 1-80 | `inferred` | Issue #24 |

---

## 3. Historical Evolution and Supersession Lineage

Understanding how interfaces evolved prevents regressions and clarifies why certain patterns superseded older versions:

### 3.1 Sidebar Lineage

```
[notes-app@old-10: SpaceFrame]
  - Hover peek with 300ms open dwell / 150ms close tolerance
  - FLIP reorder animation via WAAPI
        |
        v
[notes-app@old-5: AppSidebarOverview]
  - Standardized compact 29px desktop entity row rhythm
  - Group-hover action reveal (opacity-0 -> group-hover:opacity-100)
  - Integration with AppHeader and SpaceHeader
        |
        v
[exams-app@dev: Prototipo Sidebar]
  - Standalone CSS/HTML implementation
  - Accordion sections with animated rotating chevrons (150ms)
  - Mobile drawer mode with off-canvas transition (translateX(-105%))
  - Skeleton loading pulse animation (1200ms infinite)
```

### 3.2 Header and Tab Strip Lineage

```
[Separate Headers: AppSpaceHeader & AppSidePanelHeader]
  - Individual tab logic, conflicting state
        |
        v (PR #38, PR #40)
[Unified Header System: AppHeaderTabs]
  - Unified tab descriptor with pinned states, icons, drag reordering
  - Secondary panel shift-open affordance
  - Global search command palette integration
```

---

## 4. Repository Privacy and Integrity Verification

All historical references in this matrix:
1. Reside exclusively within local repository manifests, git commits, or sanitized inventories (`inventory/notes-app/`, `inventory/exams-app-branch-files.json`).
2. Contain zero leaked secrets, API keys, personal user tokens, or credentials.
3. Contain zero external raw CDN dependencies; all prototypes and visual specifications are self-contained and reproducible offline.
