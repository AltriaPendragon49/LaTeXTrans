# Community-First Frontend Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the frontend into a community-first, editorial-style application shell with explicit workspace routes, a normalized `ui/` layer, and cleaner state boundaries without reducing feature coverage.

**Architecture:** The rollout keeps one isolated worktree and delivers one branch-level result, but execution is layered internally. First establish shell, routes, redirects, and UI tokens; then migrate community surfaces; then move translate/workspace/admin pages into explicit route ownership; finally reduce central store coupling and remove obsolete transitional structures.

**Tech Stack:** React 19, React Router, TypeScript, Vite, Vitest, Zustand, Tailwind CSS, i18next

---

### Task 1: Establish rollout baseline and route guard expectations

**Files:**
- Read: `frontend/src/App.tsx`
- Read: `frontend/src/layout.tsx`
- Read: `frontend/src/components/app-sidebar.tsx`
- Read: `frontend/src/contexts/AuthContext.tsx`
- Test: `frontend/src/App.community-routing.test.tsx`
- Test: `frontend/src/components/app-sidebar.community-shell.test.tsx`

- [x] **Step 1: Run the current routing and shell tests before route changes**

Run:

```bash
cd frontend
npm run test -- src/App.community-routing.test.tsx src/components/app-sidebar.community-shell.test.tsx
```

Expected: PASS for the current shell before route refactor starts.

- [x] **Step 2: Document the canonical route map for the rollout**

Write this route target list into the code comments or planning notes you use while implementing:

```text
/                         -> community homepage
/paper/:paperId           -> paper detail
/translate                -> translation workspace
/workspace/history        -> workspace history
/workspace/settings       -> workspace settings
/workspace/glossary       -> workspace glossary
/admin/curation           -> admin curation
/admin/curation/tasks     -> admin tasks
```

Expected: these routes become the only architecture source of truth during implementation.

### Task 2: Create shared shell tokens and persistent editorial navigation

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/ui/sidebar-shell/SidebarShell.tsx`
- Create: `frontend/src/ui/sidebar-shell/SidebarNavItem.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/layout.tsx`
- Modify: `frontend/src/components/app-sidebar.tsx`
- Test: `frontend/src/components/app-sidebar.community-shell.test.tsx`

- [x] **Step 1: Add shared design tokens for the new shell**

Create `frontend/src/styles/tokens.css` with CSS variables for the rollout shell:

```css
:root {
  --px-shell-bg: #f4efe6;
  --px-shell-surface: #f8f5ef;
  --px-shell-panel: #fffdf8;
  --px-shell-ink: #111111;
  --px-shell-muted: #5d584f;
  --px-shell-line: rgba(17, 17, 17, 0.08);
  --px-shell-accent: #b42318;
  --px-shell-accent-strong: #8f1d13;
  --px-shell-radius-xl: 24px;
  --px-shell-radius-2xl: 32px;
}

.dark {
  --px-shell-bg: #111111;
  --px-shell-surface: #181818;
  --px-shell-panel: #1f1f1f;
  --px-shell-ink: #f5f0e8;
  --px-shell-muted: #b7ae9f;
  --px-shell-line: rgba(245, 240, 232, 0.08);
  --px-shell-accent: #f04f37;
  --px-shell-accent-strong: #ff6a52;
}
```

- [x] **Step 2: Import the new token file into the global stylesheet**

Modify `frontend/src/index.css` so it imports the new token file near the existing global imports:

```css
@import "./styles/tokens.css";
```

Expected: new shell tokens are available app-wide.

- [x] **Step 3: Build a persistent sidebar shell primitive**

Create `frontend/src/ui/sidebar-shell/SidebarShell.tsx`:

```tsx
import type { ReactNode } from "react"

export function SidebarShell({
  brand,
  nav,
  utility,
}: {
  brand: ReactNode
  nav: ReactNode
  utility: ReactNode
}) {
  return (
    <aside className="sticky top-0 flex h-screen w-[272px] shrink-0 flex-col justify-between border-r border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] px-5 py-6">
      <div className="space-y-8">{brand}{nav}</div>
      <div>{utility}</div>
    </aside>
  )
}
```

- [x] **Step 4: Build a reusable navigation item primitive**

Create `frontend/src/ui/sidebar-shell/SidebarNavItem.tsx`:

```tsx
import type { ReactNode } from "react"
import { NavLink } from "react-router-dom"

export function SidebarNavItem({
  to,
  icon,
  label,
}: {
  to: string
  icon: ReactNode
  label: string
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition-colors ${
          isActive
            ? "bg-[color:var(--px-shell-accent)] text-white"
            : "text-[color:var(--px-shell-muted)] hover:bg-black/5 hover:text-[color:var(--px-shell-ink)] dark:hover:bg-white/5"
        }`
      }
    >
      <span className="shrink-0">{icon}</span>
      <span>{label}</span>
    </NavLink>
  )
}
```

- [x] **Step 5: Replace the hover-expand sidebar with the new persistent shell**

Refactor `frontend/src/components/app-sidebar.tsx` to use `SidebarShell` and `SidebarNavItem`, remove hover-width behavior, and keep:

- community home
- translate
- workspace history
- workspace settings
- workspace glossary
- admin curation
- admin tasks
- profile / sign-in area

Expected: labels are visible by default on desktop, and admin links remain role-gated.

- [x] **Step 6: Update the shell layout to reserve real space for navigation**

Refactor `frontend/src/layout.tsx` so it uses a two-column shell instead of `ml-20`:

```tsx
<div className="flex min-h-screen bg-[color:var(--px-shell-bg)] text-[color:var(--px-shell-ink)]">
  <AppSidebar />
  <main className="min-w-0 flex-1">
    <div className="min-h-screen overflow-auto">
      <Outlet />
    </div>
  </main>
  <Toaster />
</div>
```

- [x] **Step 7: Update shell tests for the new navigation map**

Adjust `frontend/src/components/app-sidebar.community-shell.test.tsx` to expect:

- `Community`
- `Translate`
- `History`
- `Settings`
- `Glossary`
- admin-only links when role is admin

Expected: PASS after the new nav is in place.

### Task 3: Introduce explicit canonical route pages and legacy redirects

**Files:**
- Create: `frontend/src/pages/home/index.tsx`
- Create: `frontend/src/pages/translate/index.tsx`
- Create: `frontend/src/pages/workspace-history/index.tsx`
- Create: `frontend/src/pages/workspace-settings/index.tsx`
- Create: `frontend/src/pages/workspace-glossary/index.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/CommunityFeed.tsx`
- Modify: `frontend/src/pages/ToolsHub.tsx`
- Test: `frontend/src/App.community-routing.test.tsx`

- [x] **Step 1: Add thin canonical route wrappers**

Create these files:

`frontend/src/pages/home/index.tsx`
```tsx
export { default } from "@/pages/CommunityFeed"
```

`frontend/src/pages/translate/index.tsx`
```tsx
export { default } from "@/pages/Dashboard"
```

`frontend/src/pages/workspace-history/index.tsx`
```tsx
export { default } from "@/pages/History"
```

`frontend/src/pages/workspace-settings/index.tsx`
```tsx
export { default } from "@/pages/TranslationSettings"
```

`frontend/src/pages/workspace-glossary/index.tsx`
```tsx
import { useTranslation } from "react-i18next"

export default function WorkspaceGlossaryPage() {
  const { t } = useTranslation()

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="rounded-[var(--px-shell-radius-2xl)] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-8">
        <h1 className="text-3xl font-semibold">{t("glossary.glossary_management")}</h1>
        <p className="mt-3 text-sm text-[color:var(--px-shell-muted)]">
          {t("glossary.managementComingSoon")}
        </p>
      </div>
    </div>
  )
}
```

- [x] **Step 2: Point the app router at canonical pages**

Update `frontend/src/App.tsx` lazy imports and routes to use:

```tsx
const HomePage = lazy(() => import("./pages/home"))
const TranslatePage = lazy(() => import("./pages/translate"))
const WorkspaceHistoryPage = lazy(() => import("./pages/workspace-history"))
const WorkspaceSettingsPage = lazy(() => import("./pages/workspace-settings"))
const WorkspaceGlossaryPage = lazy(() => import("./pages/workspace-glossary"))
```

And route structure:

```tsx
<Route index element={withSuspense(<HomePage />)} />
<Route path="translate" element={withSuspense(<TranslatePage />)} />
<Route path="workspace/history" element={withSuspense(<WorkspaceHistoryPage />)} />
<Route path="workspace/settings" element={withSuspense(<WorkspaceSettingsPage />)} />
<Route path="workspace/glossary" element={withSuspense(<WorkspaceGlossaryPage />)} />
<Route path="tools" element={<Navigate to="/translate" replace />} />
<Route path="history" element={<Navigate to="/workspace/history" replace />} />
<Route path="glossary" element={<Navigate to="/workspace/glossary" replace />} />
```

- [x] **Step 3: Demote ToolsHub to compatibility only**

Replace `frontend/src/pages/ToolsHub.tsx` with:

```tsx
import { Navigate, useSearchParams } from "react-router-dom"

export default function ToolsHubPage() {
  const [searchParams] = useSearchParams()
  const panel = searchParams.get("panel")

  if (panel === "history") return <Navigate to="/workspace/history" replace />
  if (panel === "settings") return <Navigate to="/workspace/settings" replace />
  if (panel === "glossary") return <Navigate to="/workspace/glossary" replace />
  return <Navigate to="/translate" replace />
}
```

- [x] **Step 4: Update routing tests for canonical routes**

Extend `frontend/src/App.community-routing.test.tsx` to assert:

- `/translate` renders translation page
- `/workspace/history` renders history page
- `/workspace/settings` renders settings page
- `/workspace/glossary` renders glossary page
- `/tools?panel=history` redirects to history page

- [x] **Step 5: Run route tests after route migration**

Run:

```bash
cd frontend
npm run test -- src/App.community-routing.test.tsx src/components/app-sidebar.community-shell.test.tsx
```

Expected: PASS with canonical route structure and compatibility redirects.

### Task 4: Enforce browse-only guest access and workspace auth gates

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/TranslationSettings.tsx`
- Test: `frontend/src/App.community-routing.test.tsx`

- [x] **Step 1: Add an authenticated workspace route guard**

In `frontend/src/App.tsx`, add:

```tsx
function AuthenticatedWorkspaceRoute({ children }: { children: ReactNode }) {
  const { user, loading, isAuthenticated } = useAuth()

  if (loading) return <RouteLoading />
  if (!isAuthenticated || !user) return <Navigate to="/login" replace />
  return <>{children}</>
}
```

- [x] **Step 2: Guard translate and workspace routes**

Wrap:

- `/translate`
- `/workspace/history`
- `/workspace/settings`
- `/workspace/glossary`

inside `AuthenticatedWorkspaceRoute`.

- [x] **Step 3: Keep homepage and paper detail public**

Do not wrap:

- `/`
- `/paper/:paperId`

Expected: guests can browse/read but not enter translation or workspace routes.

- [x] **Step 4: Add auth-boundary routing tests**

In `frontend/src/App.community-routing.test.tsx`, add cases for:

- unauthenticated `/translate` -> login
- unauthenticated `/workspace/history` -> login
- unauthenticated `/workspace/settings` -> login
- unauthenticated `/workspace/glossary` -> login
- unauthenticated `/paper/paper-1` -> still accessible

### Task 5: Migrate community feed into editorial home route composition

**Files:**
- Create: `frontend/src/pages/home/components/HomeHero.tsx`
- Create: `frontend/src/pages/home/components/HomeFeedSection.tsx`
- Modify: `frontend/src/pages/home/index.tsx`
- Modify: `frontend/src/pages/CommunityFeed.tsx`
- Modify: `frontend/src/components/community/PaperCard.tsx`
- Test: `frontend/src/pages/CommunityFeed.test.tsx`

- [x] **Step 1: Turn `pages/home/index.tsx` into the real homepage composition**

Replace the thin re-export with a route composition that imports `CommunityFeedPage` and wraps it with a new hero shell:

```tsx
import CommunityFeedPage from "@/pages/CommunityFeed"
import { HomeHero } from "./components/HomeHero"

export default function HomePage() {
  return (
    <div className="space-y-8 px-6 py-8 lg:px-10">
      <HomeHero />
      <CommunityFeedPage />
    </div>
  )
}
```

- [x] **Step 2: Add a magazine-like hero**

Create `frontend/src/pages/home/components/HomeHero.tsx` with:

- large editorial heading
- one-sentence product framing
- CTA buttons linking to `/translate` and the feed section
- visually stronger but functionally light hero

- [x] **Step 3: Strip duplicated page framing from `CommunityFeed.tsx`**

Reduce `CommunityFeedPage` so it behaves like a content section, not a full app page shell:

- remove outer page background assumptions
- keep search, sort tabs, cards, load more, admin delete
- let `HomeHero` own the top editorial framing

- [x] **Step 4: Run community feed tests**

Run:

```bash
cd frontend
npm run test -- src/pages/CommunityFeed.test.tsx
```

Expected: PASS with preserved community feed functionality.

### Task 6: Continue paper-detail integration and preserve prior pilot work

**Files:**
- Read: `frontend/src/pages/paper-detail/index.tsx`
- Modify: `frontend/src/pages/paper-detail/index.tsx`
- Modify: `frontend/src/pages/paper-detail/components/PaperDetailHeader.tsx`
- Modify: `frontend/src/features/community-paper/components/PaperDetailWorkspace.tsx`
- Test: `frontend/src/pages/PaperDetail.test.tsx`
- Test: `frontend/src/pages/PaperDetail.reader-first.test.tsx`

- [x] **Step 1: Align paper detail container styling to the new shell**

Refine the page shell classes in `frontend/src/pages/paper-detail/index.tsx` so they inherit the editorial shell tokens instead of the old dashboard shell assumptions.

- [x] **Step 2: Restyle the page header without reducing controls**

Update `PaperDetailHeader.tsx` so it keeps:

- back navigation
- all reading mode buttons
- translate / progress / download actions
- metadata strip

but aligns to the new shell typography and spacing.

- [x] **Step 3: Re-run paper-detail verification**

Run:

```bash
cd frontend
npm run test -- src/pages/PaperDetail.test.tsx src/pages/PaperDetail.reader-first.test.tsx src/components/community/PaperPreviewReader.test.tsx src/hooks/use-paper-detail.test.tsx
```

Expected: PASS after shell integration.

### Task 7: Begin translation-workflow and workspace boundary cleanup

**Files:**
- Create: `frontend/src/features/translation-workflow/`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/features/translation-workflow/store/useTranslationStore.ts`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/TranslationSettings.tsx`

- [x] **Step 1: Extract translation workflow ownership plan into code boundaries**

Create the feature directory and move or wrap:

- `AdvancedConfig`
- `BatchTranslation`
- `DropZone`
- `FormattingPanel`
- `LoginPrompt`

under `frontend/src/features/translation-workflow/` in stages, starting with thin re-exports if needed.

- [x] **Step 2: Stop growing the legacy root store surface**

Move translation-specific selectors and actions behind `features/translation-workflow/store/useTranslationStore.ts`; do not add new unrelated workspace logic to the translation workflow store.

- [x] **Step 3: Keep history and settings on their existing backend contracts**

Do not rewrite the backend API shape for history or settings. Limit changes to route ownership, page framing, and frontend state boundaries.

### Task 8: Final verification checkpoint for the first rollout wave

**Files:**
- Test: `frontend/src/App.community-routing.test.tsx`
- Test: `frontend/src/components/app-sidebar.community-shell.test.tsx`
- Test: `frontend/src/pages/CommunityFeed.test.tsx`
- Test: `frontend/src/pages/PaperDetail.test.tsx`
- Test: `frontend/src/pages/PaperDetail.reader-first.test.tsx`
- Test: `frontend/src/components/community/PaperPreviewReader.test.tsx`
- Test: `frontend/src/hooks/use-paper-detail.test.tsx`

- [x] **Step 1: Run the first-wave verification suite**

Run:

```bash
cd frontend
npm run test -- src/App.community-routing.test.tsx src/components/app-sidebar.community-shell.test.tsx src/pages/CommunityFeed.test.tsx src/pages/PaperDetail.test.tsx src/pages/PaperDetail.reader-first.test.tsx src/components/community/PaperPreviewReader.test.tsx src/hooks/use-paper-detail.test.tsx
```

Expected: PASS.

- [x] **Step 2: Run a production build**

Run:

```bash
cd frontend
npm run build
```

Expected: build succeeds; any pre-existing non-blocking env warnings should be documented but not confused with new regressions.

- [x] **Step 3: Update plan checkboxes honestly after verification**

Mark only the actually completed steps in this file.

Implementation note: because this is now a full rollout plan, later waves may extend this file rather than creating a second competing execution plan under the same change.
