## Context

The current frontend already contains most of the necessary product capability, but it is expressed through an inconsistent shell:

- the homepage is community-first, but the overall navigation still feels like a compact tools dashboard
- translation, history, and settings are grouped through `ToolsHub` query-string panels instead of clear route ownership
- shared UI primitives and business components are split between reusable and page-specific responsibilities without stable boundaries
- translation workflow state still needs to live under a dedicated feature-owned store instead of a root-level catch-all surface
- the sidebar pattern is optimized for a utility app, not for a content-led reading platform

The approved governance work established path-based architecture rules and validated `PaperDetail` as the first pilot. The user has now approved a larger product decision: execute the rollout as a community-first, visually redesigned, full frontend migration without reducing feature coverage.

## Goals / Non-Goals

- Goals:
  - Make the product feel like a community reading platform first and a translation workspace second
  - Preserve feature coverage while allowing route reorganization, shell redesign, and UI-system replacement
  - Replace technical-folder ownership with `ui/`, `features/`, and `pages/<page>` boundaries across the app
  - Replace the sidebar with a persistent content-platform navigation that remains readable at first glance
  - Adopt a Uiverse-first sourcing workflow for generic UI primitives, then normalize those components inside `src/ui/`
  - Split state boundaries so community reading, translation workspace, and workspace settings no longer depend on one oversized store surface
  - Keep admin capabilities accessible in the main navigation for admins without leaking them to ordinary users

- Non-Goals:
  - No backend API contract redesign in this change
  - No intentional feature removal
  - No attempt to keep every old route as the primary canonical route
  - No commitment to preserve current visual styling, current sidebar pattern, or `ToolsHub` as a long-term surface

## Decisions

### Decision: The application shell becomes community-first

The new primary mental model is:

- `/` is the community homepage and first-class landing experience
- `/paper/:paperId` is the most important content route
- translation is a primary action, but not the primary shell identity
- user workspace utilities move into explicit workspace routes instead of one multi-panel tools page

Target route family:

```text
/
/paper/:paperId
/agent
/agent/:conversationId
/translate
/workspace/history
/workspace/settings
/workspace/glossary
/admin/curation
/admin/curation/tasks
```

Legacy entry points such as `/tools?panel=...`, `/history`, `/settings`, and `/glossary` may remain as redirects during migration, but they are no longer the target architecture.

### Decision: Anonymous users are browse/read only

Unauthenticated users may:

- browse the community homepage
- search papers
- open paper detail and read available content

Unauthenticated users may not:

- start translation
- access workspace history
- access workspace settings
- access glossary management
- use other persistent personal-workspace functions

This keeps the product discoverable while preserving a clear login boundary around translation and saved-workspace behavior.

### Decision: Admin entries live in the main navigation, but remain role-gated

Admin curation and admin task pages remain part of the main navigation model so administrators do not need a hidden parallel shell. However:

- admin entries render only when the current user has an admin role
- non-admin users never see those links
- admin capability remains visually integrated into the main shell rather than hidden behind a special backdoor route structure

### Decision: The sidebar is replaced by a persistent editorial navigation

The current hover-expand narrow rail is not appropriate for a community-first reading product. The new navigation must:

- show readable labels by default on desktop
- reserve stable horizontal space instead of overlapping or surprising the main canvas
- separate brand, primary navigation, admin navigation, and user/account actions
- feel like a research magazine or editorial product rather than a collapsible utility toolbar

The shell should still be responsive, but it should not depend on hover to become understandable.

### Decision: The visual language may be fully redesigned

The approved design direction is a "frontier magazine" look:

- stronger brand presence than the current shell
- editorial hierarchy on the homepage
- more intentional content pacing, typography, and cards
- modern but restrained motion

The goal is not arbitrary novelty. The goal is to make the homepage, reader, and workspace feel like one coherent research product.

### Decision: Uiverse-first component sourcing governs the new `ui/` layer

For reusable UI primitives:

1. Check Uiverse first
2. If a candidate matches the need, adapt it into the repository's `src/ui/` layer
3. Normalize tokens, colors, radius, spacing, motion, hover/focus states, and accessibility behavior there
4. Only create a net-new primitive when no suitable Uiverse starting point exists

This policy applies to components such as sidebar shells, buttons, cards, inputs, tabs, search surfaces, sheets, and other generic interaction patterns. Uiverse snippets are not to be pasted directly into feature pages; they must first be systematized into the app's own UI layer.

### Decision: The `ui/` layer owns both primitives and approved composition shells

To keep future page work inside a stable design system, `src/ui/` is no longer limited to atom-only primitives. It may also host reusable composition shells when all of the following are true:

- the component has no page-specific business semantics
- the component exists to enforce layout, spacing, interaction, or visual-system consistency
- the component can be reused across multiple surfaces without knowing domain data contracts

This means the approved `ui/` inventory now includes:

- primitives: `Button`, `Card`, `Input`, `Textarea`, `Pill`
- governed controls: `SegmentedControl`, `ToggleSwitch`, `Switch`
- navigation shell: `SidebarShell`, `SidebarNavItem`, `SidebarUtilityPanel`
- composition shells: `EditorialTabs`, `UploadCard`, `UploadDropSurface`, `SectionHeading`, `StatePanel`, `PageIntro`, `FilterToolbar`, `NoticeBanner`
- feedback and loading shells: `LoadingState`
- section shells: `SectionCard`

Governance rules for future work:

- new generic controls must be added under `src/ui/` before page usage
- page files may style layout, but may not invent parallel button, card, tabs, or upload patterns when a `ui/` equivalent exists
- feature and page modules may wrap `ui/` components with domain semantics, but may not fork the base visual contract
- Uiverse remains the first source to audit for generic interaction patterns, but only normalized, tokenized versions may enter `src/ui/`
- semantic status feedback must reuse the governed shell status tokens (`--shell-info/*`, `--shell-success/*`, `--shell-warning/*`, `--shell-danger/*`) through shared primitives such as `NoticeBanner`, `StatusBadge`, `WorkflowStepper`, `StatePanel`, `Card`, and `Button`
- the legacy primitive sidebar runtime has been removed; `src/ui/sidebar-shell/*` is now the only active sidebar/navigation system and all locale/a11y ownership follows that shell
- PaperX semantic status colors now have first-class `--px-shell-*` definitions (`info`, `success`, `warning`, `danger`, strong border, contrast text), while `--shell-*` remains only as a compatibility alias layer for reader/prose and remaining transitional surfaces

Current Uiverse-backed direction inside the system:

- action buttons use an adapted rounded editorial CTA pattern
- cards use a layered magazine-panel treatment adapted into `Card`
- segmented navigation/tabs use an adapted soft-pill switcher pattern in `EditorialTabs`
- upload surfaces use an adapted drag-and-drop spotlight card in `UploadCard`
- generic drag-and-drop intake zones use a lighter governed `UploadDropSurface` shell so feature flows can reuse the same upload affordance without duplicating page-local dropzone markup
- empty, error, login-required, and permission-gated views use a normalized state card shell in `StatePanel`
- route-level title, description, and top action zones use a normalized intro/header shell in `PageIntro`
- settings and preference forms use a normalized section wrapper in `SectionCard`
- list sorting and feed framing use an adapted segmented utility strip in `FilterToolbar`
- inline warnings, success confirmations, and neutral editorial guidance use a normalized banner shell in `NoticeBanner`
- loading spinners and route/panel loading placeholders use a normalized shell in `LoadingState`
- auth, workspace, and processing surfaces reuse `NoticeBanner` for danger, warning, info, success, and neutral feedback instead of route-local alert variants
- sidebar account and auth utility blocks use `SidebarUtilityPanel` so the shell does not grow sidebar-local card variants
- metadata pills and sidebar treatment follow the same Uiverse-first normalization rule even when adjusted heavily for PaperX tokens
- workspace history, workspace settings, login, app boot, and profile loading states converge on `LoadingState` instead of route-local spinner shells
- community detail similar-link actions and low-level primitives such as `Checkbox` and `Tooltip` now consume PaperX shell tokens instead of legacy `text-primary` / `bg-primary` utility vocabulary
- shared destructive/info/success state components such as `Button`, `Card`, `NoticeBanner`, `StatusBadge`, `StatePanel`, `WorkflowStepper`, and `Badge` now read from PaperX semantic tokens rather than defining status colors ad hoc inside each component
- shared confirmation flows now rely on governed `AlertDialog` action variants (`default`, `outline`, `destructive`) instead of page-local destructive button recipes inside dialog footers
- admin curation submission and admin task history now normalize around `FormFieldShell`, `RecordRow`, and `DataTable` so admin surfaces do not keep bespoke filter/list compositions
- processing summary, timeline, and live-log framing now normalize around `PanelShell` tones plus governed `Pill` / `StatusBadge` primitives instead of feature-local shadow recipes

Current system component inventory for future page work:

- action primitives: `Button`
- form primitives: `Input`, `Textarea`, `LanguageSelector`
- state/toggle primitives: `ToggleSwitch`, `Switch`, `SegmentedControl`, `ThemeToggle`
- content primitives: `Card`, `Pill`
- search and query primitives: `SearchBar`
- data presentation primitives: `DataTable`
- shell/navigation primitives: `SidebarShell`, `SidebarNavItem`, `SidebarUtilityPanel`
- reusable composition shells: `EditorialTabs`, `UploadCard`, `SectionHeading`, `StatePanel`, `PageIntro`, `FilterToolbar`, `NoticeBanner`
- reusable loading shells: `LoadingState`
- reusable upload shells: `UploadDropSurface`
- reusable disclosure shells: `DisclosureCard`
- semantic state primitives: `StatusBadge`, `WorkflowStepper`
- reusable section shells: `SectionCard`
- reusable surface shells: `PanelShell`
- reusable message shells: `ChatBubble`
- reusable info tiles: `InfoTile`
- reusable form shells: `FormFieldShell`
- reusable composer shells: `ComposerShell`
- reusable record/list row shells: `RecordRow`
- low-level radix-backed primitives under `src/ui/primitives/`: `AlertDialog`, `Badge`, `Checkbox`, `Collapsible`, `Label`, `Progress`, `Resizable`, `ScrollArea`, `Select`, `Sheet`, `Skeleton`, `Tabs`, `Tooltip`, `Toaster`, and supporting primitives
- runtime ownership now lives under `src/ui/`, `src/layout/`, `src/features/*`, and `src/pages/*/components`; the legacy generic runtime `src/components/` directory has been removed, and related tests now live beside their owned modules
- the streaming community-agent experience now belongs to `src/features/community-conversation/`; `/agent` route files are reduced to route wrappers and no longer own the conversation controller, stream runtime, or UI subcomponents
- the glossary workspace placeholder also now follows the same pattern as history/settings, with `src/features/user-workspace/components/GlossaryWorkspace.tsx` owning the surface while the route file stays a thin entry wrapper
- the translation processing monitor now also follows the same rule, with `src/features/translation-workflow/components/ProcessingWorkspace.tsx` and `ProcessingLogViewer.tsx` owning the workbench while `/processing` stays a thin route entry
- the paper detail reader now follows the same ownership rule, with `src/features/community-paper/components/PaperDetailScreen.tsx` owning detail loading, reader-mode orchestration, and translation/download actions while `/paper/:paperId` remains a route wrapper only
- the login experience now follows the same ownership rule, with `src/features/auth-shell/components/LoginWorkspace.tsx` owning credential validation, sign-in flow, and account-support actions while `/login` remains a route entry wrapper only
- the profile experience now follows the same ownership rule, with `src/features/user-workspace/components/ProfileWorkspace.tsx` owning authenticated account presentation and sign-out actions while `/profile` remains a route entry wrapper only

Uiverse audit and adoption record for the current system layer:

- buttons and CTA rhythm were normalized from rounded call-to-action/button patterns on Uiverse, then retokenized for PaperX
- card surface treatment was adapted from a layered editorial card pattern, with the current baseline referencing `https://uiverse.io/vinodjangid07/bitter-eagle-34`
- tab treatment was selected from the `https://uiverse.io/tags/tabs` audit pool and normalized into `EditorialTabs`
- upload/dropzone treatment was selected from the `https://uiverse.io/tags/fileupload` audit pool and normalized into `UploadCard`
- lightweight dropzone treatment also reuses the `https://uiverse.io/tags/fileupload` audit pool, with the current governed implementation split into `UploadCard` and the slimmer `UploadDropSurface`
- filter and segmented control treatment was selected from the Uiverse tabs and search-surface audit pool, then normalized into `FilterToolbar`
- search and search-input treatment are now selected from the `https://uiverse.io/tags/search` audit pool and normalized into `SearchBar`
- notice and inline message treatment was selected from Uiverse alert/card vocabulary and normalized into `NoticeBanner`
- editorial sidebar navigation treatment follows the `https://uiverse.io/tags/sidebar` audit pool and is normalized into `SidebarShell` / `SidebarNavItem`
- sidebar utility framing follows the same sidebar audit direction and is normalized into `SidebarUtilityPanel`
- collapsible knowledge cards and expandable content rows now reuse a normalized `DisclosureCard` shell instead of page-local accordion card markup
- empty/state messaging shells inherit the same Uiverse-first card/button vocabulary rather than page-local one-off panels
- table and record-list framing are now selected from the `https://uiverse.io/tags/table` audit pool and normalized into `DataTable`
- glass/hero panel framing is now normalized into `PanelShell` so login, processing, and conversation side panels do not keep bespoke surface recipes
- conversation message treatment is now normalized into `ChatBubble` so assistant/user threads do not keep feature-local bubble recipes
- settings/history/value rows now normalize around `InfoTile` so workspace and translation configuration surfaces reuse one small-card contract
- settings and formatting field framing now normalize around `FormFieldShell` so select/input/toggle field wrappers do not diverge per workspace
- conversation prompt framing now normalizes into `ComposerShell` so prompt-entry surfaces do not keep feature-local form shells
- batch task rows and queued file rows now normalize around `RecordRow` so lightweight record lists share one governed presentation contract
- admin curation upload queues, batch status rows, and curation task history now reuse the same governed record/table vocabulary instead of separate admin-only list recipes
- processing summary states now reuse semantic `PanelShell` tones rather than bespoke success/error/accent surface classes

Selection rule used in this rollout:

- "Use all usable Uiverse components" is interpreted as auditing all high-value generic interaction categories relevant to PaperX, then importing only the variants that strengthen the house system
- candidates are only accepted when they can serve multiple surfaces after token normalization
- snippets are rejected if they introduce a parallel color system, inaccessible interaction, or page-specific semantics
- PaperX visual tokens now flow from `src/styles/tokens.css` as the single source of truth, while legacy `--shell-*` names are retained only as compatibility aliases for reader/prose surfaces still consuming the older variable names
- remaining translation/workspace surfaces are expected to converge on the PaperX shell token family (`--px-shell-*`) instead of mixing older semantic utility colors with governed `ui/` shells
- remaining page-level class overrides are acceptable only when they compose governed primitives and do not introduce a parallel button/card/form/dialog contract
- reusable mode switchers now use `src/ui/segmented-control/SegmentedControl.tsx` instead of page-local button groups, and page-level compositions like community conversation are expected to wrap this governed control rather than redraw local switchers
- shared libraries and API helpers no longer preload page modules directly; route preloading remains a route or feature concern, while `src/lib/` stays page-agnostic
- community feed data ownership now keeps its reusable query hook under `src/features/community-paper/hooks/useCommunityPapers.ts` instead of a root-level hook namespace
- brand assets now use the lightweight governed `frontend/paperx-mark.svg` mark for favicon and sidebar branding, replacing the previous large PNG runtime asset

### Decision: Architecture remains path-driven, but rollout now spans the whole app

The target structure remains:

```text
src/
  ui/
  styles/
  layout/
  hooks/
  utils/
  constants/
  features/
    community-paper/
    community-conversation/
    translation-workflow/
    auth-shell/
    user-workspace/
    admin-curation/
  pages/
    home/
    paper-detail/
    translate/
    workspace-history/
    workspace-settings/
    workspace-glossary/
    admin-curation/
    admin-curation-tasks/
```

The difference from the original governance phase is scope: this structure now becomes the rollout target for the full app rather than a future aspiration.

### Decision: `ToolsHub` is retired as an architectural center

`ToolsHub` currently acts like a page that hosts other pages. That blurs page boundaries and prevents route ownership from staying explicit.

The new model is:

- translate becomes its own route page
- history becomes its own workspace route page
- settings becomes its own workspace route page
- glossary becomes its own workspace route page
- community agent conversation becomes a feature-owned workspace mounted by `/agent` route wrappers instead of a heavy page-owned controller
- complex translation workspace composition moves under `features/translation-workflow`, while the canonical `/translate` page owns route entry and legacy `Dashboard.tsx` remains only as a temporary compatibility export
- preview/comparison composition also belongs to `features/translation-workflow`, while `/preview` remains the route boundary that mounts the workbench
- processing/task monitoring composition also belongs to `features/translation-workflow`, while `/processing` remains the route boundary that mounts the workbench
- history and settings workspace composition belong to `features/user-workspace`, while `/workspace/history` and `/workspace/settings` remain the canonical route boundaries; legacy `/history`, `/settings`, and `/glossary` entry points now exist only as redirects, and global interface controls such as `LanguageSelector` and `ThemeToggle` live under `src/ui/` rather than page-owned paths
- translation-specific business controls such as advanced configuration, upload intake, batch orchestration, formatting panels, and terminology drawers belong to `features/translation-workflow`, not top-level `components/`
- auth-gated prompt shells such as `LoginPrompt` belong to `features/auth-shell`, while `src/ui/` continues to own only domain-agnostic primitives and composition shells
- community feed composition such as paper cards, feed states, and paper submission intake belongs to `features/community-paper`, while `CommunityFeed` remains the route boundary
- admin curation submission, polling, filtering, and batch-deletion behavior now belongs to `features/admin-curation`, while `/admin/curation` and `/admin/curation/tasks` remain route-entry wrappers only

Temporary redirects may remain, but page composition must no longer depend on panel-switching other page modules inside one host route.

### Decision: State is split by product boundary, not one central store

The current global store remains too large for a full rollout. During the implementation:

- translation workflow state moves behind `frontend/src/features/translation-workflow/store/useTranslationStore.ts` and is consumed through `useTranslationConfig` / `useTranslationTask`
- community reading state should be page- or feature-owned
- workspace settings and user preferences should be isolated from translation execution state

This change does not require one specific state library migration. It does require that no root-level universal store remains the ownership point for unrelated domains.

### Decision: Full rollout is executed in ordered layers inside the same worktree

The user wants one complete delivery, but the implementation should still be layered internally to reduce breakage:

1. shared tokens, `ui/`, and application shell
2. route reorganization and navigation
3. community homepage and paper detail
4. translate/workspace surfaces
5. admin surfaces
6. state-boundary cleanup and compatibility cleanup

This still produces one integrated branch-level deliverable, but avoids changing every axis blindly at the same moment.

### Decision: Shared shell polish is governed at the architecture layer, not page-by-page

The final refinement pass adds a few durable shell rules so future changes stay inside one system instead of drifting per page:

- the left navigation is explicitly collapsible with a stable button, and content width changes through the shared flex shell rather than hover-only sidebar behavior
- the top-left brand surface is logo-first only; the product name remains accessible via alt/aria metadata, but not duplicated as visible title text in the sidebar shell
- primary interaction affordances now inherit pointer and press-feedback behavior from shared base styles instead of each page deciding cursor/active treatment ad hoc
- rounded container treatment is intentionally reduced so heavy radii live on outer shells and true action controls, while dense content regions favor flatter internal segmentation
- the community homepage prioritizes above-the-fold density by shrinking hero/search height and rendering more papers in the initial desktop viewport
- paper detail prefers bilingual compare as the default reader mode whenever both source PDF and translated PDF are available, preserving single-mode switching as an explicit user action
- browser-based local frontend development falls back to `https://api.latextrans.online` when `VITE_API_BASE_URL` is unset, while explicit env configuration still remains the escape hatch for a local `9001` backend

## Risks / Trade-offs

- A full rollout creates more merge risk and more temporary duplication than incremental single-page migrations.
- Moving both shell and state boundaries in one program increases regression risk unless route-level verification stays strong.
- Uiverse-first sourcing can accelerate design quality, but only if snippets are normalized into a house UI system instead of copied ad hoc.
- Keeping admin features in the main nav improves discoverability for admins, but requires careful role-gating and navigation tests.

## Migration Plan

1. Upgrade the current OpenSpec change from governance-only to full rollout scope.
2. Keep the existing worktree/branch as the canonical implementation environment.
3. Preserve already completed `PaperDetail` pilot work where it matches the new structure.
4. Introduce the new shell, route model, and `ui/` foundations first.
5. Migrate homepage, reader, translate, workspace, and admin surfaces into the new route and feature layout.
6. Retain compatibility redirects and re-exports until the new structure is verified.
7. Remove transitional structures only after targeted tests and build verification pass.
8. After verification, delete obsolete compatibility exports so `src/ui/`, `src/features/*`, and `src/pages/*` remain the only active runtime ownership boundaries.

## Open Questions

- Which exact Uiverse components should be adopted for sidebar, search surface, tabs, and high-priority action buttons after token normalization?
- Which existing routes should remain as permanent aliases versus temporary redirects only?
