# 项目文档汇总: update-mobile-responsive-shell-and-workspaces

> 说明：
> 1. 已忽略汇总文件自身 `all_docs_combined.md` 及包含 `backup/test` 等关键词的文件。
> 2. 为避免 Markdown 语法冲突，源码使用了 4 个反引号进行代码块包裹。

## 1. 文档文件结构

```text
📦 update-mobile-responsive-shell-and-workspaces
├── design.md
├── proposal.md
├── specs
│   ├── community-paper-discovery-ui
│   │   └── spec.md
│   ├── community-public-read-experience
│   │   └── spec.md
│   └── web-ui
│       └── spec.md
└── tasks.md
```

---

## 2. 详细文档内容

### 📄 design.md

````markdown
## Context
The current shell uses a sidebar-first desktop layout that remains visible on narrow screens. Community feed controls, paper detail actions, workflow workbenches, and admin history views all inherit that desktop assumption, which leads to cramped content width and overlapping interaction zones on mobile.

This change needs one consistent responsive model across the whole frontend rather than a series of isolated page patches. The user specifically approved:
- a 4-item mobile bottom navigation
- full-page mobile coverage including admin routes
- mobile default single-column translated reading

## Goals
- Provide one shared mobile shell pattern that applies across the frontend.
- Preserve desktop capability while making narrow-screen routes usable and conflict-free.
- Default paper reading and preview to translated single-column mode on mobile.
- Define responsive behavior by page family so implementation stays consistent.

## Non-Goals
- Re-architect desktop information architecture beyond the responsive shell boundary.
- Add new product capabilities unrelated to responsive behavior.
- Deliver full translated-PDF interaction parity on mobile beyond safe readable fallback behavior already allowed by existing specs.

## Decisions
- Decision: Use a mobile bottom navigation with exactly four primary destinations.
  - Rationale: It removes the narrow-screen left-rail width penalty and keeps first-level navigation in a thumb-reachable zone.
- Decision: Keep desktop sidebar behavior for larger viewports.
  - Rationale: Desktop information density and existing workflows benefit from the current rail model.
- Decision: Treat page responsiveness as page-family templates rather than per-page exceptions.
  - Rationale: This reduces drift and helps all current and future routes follow the same mobile rules.
- Decision: Default narrow-screen paper detail and preview to translated single-column presentation.
  - Rationale: The user explicitly approved translated-first single-column reading for mobile.
- Decision: Move secondary controls and support panes into explicit tabs, drawers, or collapsible regions on mobile.
  - Rationale: Persistent dual panes and dense action rows are the primary source of button conflict and cramped layouts.

## Page-family patterns
### Public browse pages
- Routes: `/`, `/tools`, `/favorites`, `/profile`, `/login`
- Mobile pattern: single-column scroll, compact top bar, bottom navigation, stacked search/filter/action areas

### Reading and preview pages
- Routes: `/paper/:paperId`, `/preview`
- Mobile pattern: single-column translated-first reader by default
- Secondary content: source view, insights, similar content, terminology, and auxiliary metadata move into explicit tabs, drawers, or collapsible sections

### Workflow pages
- Routes: `/translate`, `/processing`
- Mobile pattern: stacked workbench with primary task progression first, advanced configuration and logs below or behind expansion controls
- Primary action rule: start/continue/download controls stay visually obvious and thumb-reachable

### Workspace and admin pages
- Routes: `/workspace/history`, `/workspace/settings`, `/workspace/glossary`, `/admin/curation`, `/admin/curation/tasks`, `/agent`
- Mobile pattern: card lists, stacked forms, expandable details, drawer-style secondary navigation where needed
- Data-density rule: desktop tables and side rails degrade to cards and explicit expansion instead of horizontal squeeze

## Risks / Trade-offs
- Different navigation models between desktop and mobile increase layout branching.
  - Mitigation: centralize shell logic and page-family rules instead of scattering one-off breakpoints.
- Admin pages may need larger structural changes than public pages.
  - Mitigation: treat admin history and conversation as first-class members of the responsive rollout, not follow-up cleanup.
- Existing tests are likely desktop-oriented.
  - Mitigation: add route-level responsive expectations for the shared shell and representative pages in each family.

## Validation approach
- Verify shared shell behavior on narrow screens, including safe-area spacing and bottom-nav persistence.
- Verify paper detail and preview default to translated single-column mobile reading.
- Verify workflow pages keep primary actions reachable without action overlap.
- Verify history/admin pages switch from table compression to card/expansion behavior.

## Open Questions
- None remaining for this proposal. The user approved the navigation model, admin inclusion, responsive route-family approach, and translated-first mobile reading default.
````

---

### 📄 proposal.md

````markdown
# Change: Mobile-responsive shell and workspace patterns

## Why
The current frontend shell and several major pages are still primarily desktop-first. On narrow viewports this causes navigation chrome to consume reading width, action buttons to compete for the same horizontal space, and dual-pane or table-oriented pages to become cramped or conflicting.

## What Changes
- Add a mobile shared-shell contract with a top action bar, a fixed 4-item bottom navigation, and safe-area-aware page spacing.
- Define responsive page-family patterns for public browse pages, reading/preview pages, workflow pages, workspace pages, and admin pages.
- Make narrow-screen paper reading and preview default to single-column translated-first presentation, with secondary controls and support panels moved into explicit tabs, drawers, or collapsible sections.
- Require high-density workspace and admin pages to degrade from desktop table or dual-pane layouts into card, expansion, and stacked action patterns on mobile.

## Impact
- Affected specs: `web-ui`, `community-paper-discovery-ui`, `community-public-read-experience`
- Affected code: shared shell and sidebar components, community feed/detail pages, preview and workflow workbenches, workspace pages, admin pages, responsive tests
````

---

### 📄 specs\community-paper-discovery-ui\spec.md

````markdown
## ADDED Requirements
### Requirement: Community discovery controls remain conflict-free on mobile
The community discovery surface SHALL provide a narrow-screen layout that preserves browse capability without relying on the desktop sidebar or cramped control rows.

#### Scenario: Mobile homepage uses single-column discovery framing
- **WHEN** a user opens the community homepage on a narrow/mobile viewport
- **THEN** the page SHALL render its hero, search, sort, and feed content in a single-column flow
- **AND** the browse controls SHALL not overlap, clip, or compete for the same horizontal space

#### Scenario: Mobile discovery shell uses shared bottom navigation
- **WHEN** the community discovery routes render on a narrow/mobile viewport
- **THEN** navigation to first-level destinations SHALL use the shared four-item bottom navigation
- **AND** the previous left-rail shell SHALL not consume persistent reading width on those screens
````

---

### 📄 specs\community-public-read-experience\spec.md

````markdown
## ADDED Requirements
### Requirement: Narrow-screen reading defaults to translated single-column mode
The public paper-reading experience SHALL default narrow/mobile viewports to a translated-first single-column reading presentation whenever translated reading assets are available.

#### Scenario: Mobile paper detail opens with translated reading available
- **WHEN** a user opens a paper detail page on a narrow/mobile viewport
- **AND** translated reading content is available
- **THEN** the reader SHALL default to a single-column translated presentation
- **AND** the UI SHALL not default to a side-by-side bilingual or dual-pane reading layout

#### Scenario: Mobile paper detail falls back when translated reading is unavailable
- **WHEN** a user opens a paper detail page on a narrow/mobile viewport
- **AND** translated reading content is not available
- **THEN** the page SHALL fall back to the best available readable source mode
- **AND** it SHALL keep the single-column mobile reading structure

### Requirement: Narrow-screen reading support uses explicit secondary surfaces
The public paper-reading experience SHALL move mobile secondary reading-support content into explicit toggles instead of keeping desktop-persistent support panes visible beside the reader.

#### Scenario: Mobile paper detail exposes support content
- **WHEN** a user needs insights, similar papers, paper metadata, or other reading-support content on a narrow/mobile viewport
- **THEN** the page SHALL expose that support content through explicit tabs, drawers, sheets, or collapsible regions
- **AND** those secondary surfaces SHALL not crowd the default single-column reader

#### Scenario: Mobile preview route opens on a narrow screen
- **WHEN** a user opens the preview route on a narrow/mobile viewport
- **THEN** the preview SHALL default to a single-document translated reading view
- **AND** alternate source or comparison views SHALL remain available through explicit user switching rather than simultaneous side-by-side rendering
````

---

### 📄 specs\web-ui\spec.md

````markdown
## ADDED Requirements
### Requirement: Shared shell provides a mobile bottom-navigation layout
The frontend shared shell SHALL provide an explicit narrow-screen navigation model instead of compressing the desktop sidebar into the mobile viewport.

#### Scenario: Narrow screen enters the shared shell
- **WHEN** a user opens a shared-shell route on a narrow/mobile viewport
- **THEN** the UI SHALL replace the desktop sidebar-first layout with a mobile shell that uses a top action region and a fixed bottom navigation
- **AND** that bottom navigation SHALL expose exactly four primary destinations
- **AND** the page content SHALL reserve safe-area-aware space so bottom navigation does not overlap interactive content

#### Scenario: Desktop shell remains unchanged in principle
- **WHEN** a user opens a shared-shell route on a desktop-width viewport
- **THEN** the UI SHALL continue using the desktop navigation model
- **AND** the mobile bottom-navigation pattern SHALL not displace the desktop reading and workspace layout

### Requirement: Route families use explicit mobile degradation patterns
The frontend SHALL apply consistent responsive layout rules across public, workflow, workspace, and admin route families instead of squeezing desktop compositions onto narrow screens.

#### Scenario: Public browse routes render on narrow screens
- **WHEN** a user opens public browse routes such as `/`, `/tools`, `/favorites`, `/profile`, or `/login` on a narrow/mobile viewport
- **THEN** those pages SHALL render as single-column mobile-safe compositions
- **AND** search, filters, and primary actions SHALL stack or wrap without overlapping

#### Scenario: Workflow and workspace routes render on narrow screens
- **WHEN** a user opens workflow or workspace routes such as `/translate`, `/processing`, `/workspace/history`, `/workspace/settings`, or `/workspace/glossary` on a narrow/mobile viewport
- **THEN** the UI SHALL prioritize the primary task or record content in a stacked layout
- **AND** secondary controls, logs, or configuration panels SHALL move into collapsible, tabbed, or subsequent stacked sections rather than stay in competing side-by-side regions

#### Scenario: Admin routes render on narrow screens
- **WHEN** an admin user opens `/admin/curation`, `/admin/curation/tasks`, or `/agent` on a narrow/mobile viewport
- **THEN** the UI SHALL preserve route capability with mobile-safe stacked layouts
- **AND** desktop tables, rails, or multi-column controls SHALL degrade into cards, expansions, drawers, or stacked action groups instead of remaining horizontally compressed
````

---

### 📄 tasks.md

````markdown
## 1. Shared shell and navigation
- [ ] 1.1 Replace the narrow-screen left rail with a mobile shared shell that uses a top action region, fixed 4-item bottom navigation, and safe-area-aware spacing.
- [ ] 1.2 Preserve the current desktop navigation model while defining explicit responsive breakpoints and shared page padding rules.

## 2. Public browse and reading pages
- [ ] 2.1 Update the community homepage, tools hub, favorites entry flow, profile, and login surfaces to use mobile-safe single-column layouts with conflict-free search and action placement.
- [ ] 2.2 Update paper detail and preview so narrow screens default to translated single-column reading, with secondary panels and actions exposed through explicit toggles, tabs, or drawers.

## 3. Workflow, workspace, and admin pages
- [ ] 3.1 Convert translation and processing pages to mobile-first stacked workbench layouts with thumb-reachable primary actions.
- [ ] 3.2 Convert history, settings, glossary, admin curation, admin task history, and conversation pages from desktop table or rail assumptions into stacked card, collapsible, or drawer-based mobile layouts.

## 4. Verification
- [ ] 4.1 Add or update responsive tests that cover shared-shell navigation, mobile paper-detail defaults, workflow action placement, and admin/workspace degradation patterns.
- [ ] 4.2 Manually verify representative narrow-screen routes for interaction conflicts, safe-area spacing, and translated-first mobile reading behavior.
````

---

