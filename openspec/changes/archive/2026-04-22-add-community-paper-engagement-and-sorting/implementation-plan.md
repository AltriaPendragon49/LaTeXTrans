# Community Paper Engagement And Sorting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement authenticated community-paper favorites, likes, real view counting, and updated sorting with persistent backend/database state and matching frontend UX.

**Architecture:** Extend the existing FastAPI `papers` route + `paper_service` + `community_paper_repository` stack instead of introducing new backend layers. Persist new engagement entities in MySQL, keep aggregate counters on `papers`, and wire the React community feed/detail shell to backend-driven viewer state with a shared favorite picker and favorites routes.

**Tech Stack:** FastAPI, repository/service pattern, MySQL migrations, pytest, React 19, React Router, Vitest, i18next.

---

### Task 1: Add backend schema coverage and failing SQL/tests

**Files:**
- Create: `backend/migrations_mysql/20260421_0008_community_paper_engagement.sql`
- Modify: `backend/tests/unit/test_mysql_local_auth_baseline_migration_sql.py`
- Create: `backend/tests/unit/test_mysql_community_paper_engagement_migration_sql.py`

- [ ] **Step 1: Write failing migration tests for favorites folders, folder membership, and daily views**

```python
def test_engagement_migration_creates_favorite_folders_table():
    sql = Path("backend/migrations_mysql/20260421_0008_community_paper_engagement.sql").read_text(encoding="utf-8")
    assert "create table if not exists favorite_folders" in sql.lower()
    assert "unique key uq_favorite_folders_user_name" in sql.lower()


def test_engagement_migration_creates_daily_view_dedupe_table():
    sql = Path("backend/migrations_mysql/20260421_0008_community_paper_engagement.sql").read_text(encoding="utf-8")
    assert "create table if not exists paper_daily_views" in sql.lower()
    assert "unique key uq_paper_daily_views_dedupe" in sql.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/test_mysql_community_paper_engagement_migration_sql.py -q`
Expected: FAIL because the new migration file does not exist yet.

- [ ] **Step 3: Write the migration with required tables and indexes**

```sql
create table if not exists favorite_folders (...);
create table if not exists favorite_folder_papers (...);
create table if not exists paper_daily_views (...);
```

- [ ] **Step 4: Run migration tests to verify they pass**

Run: `pytest backend/tests/unit/test_mysql_community_paper_engagement_migration_sql.py backend/tests/unit/test_mysql_local_auth_baseline_migration_sql.py -q`
Expected: PASS

### Task 2: Add repository/service failing tests for likes, favorites, views, and sort rules

**Files:**
- Modify: `backend/tests/unit/test_papers_view_tracking.py`
- Modify: `backend/tests/unit/test_papers_list_detail_contract.py`
- Create: `backend/tests/unit/test_papers_engagement_api.py`
- Modify: `backend/app/repositories/community_paper_repository.py`
- Modify: `backend/app/services/paper_service.py`

- [ ] **Step 1: Write failing backend tests for new behavior**

```python
def test_record_view_counts_once_per_user_per_day(monkeypatch):
    ...

def test_list_papers_supports_views_and_likes_sort(monkeypatch):
    ...

def test_detail_viewer_state_reports_favorite_folder_count(monkeypatch):
    ...

def test_toggle_like_requires_login():
    ...
```

- [ ] **Step 2: Run targeted backend tests to verify they fail for the intended missing behavior**

Run: `pytest backend/tests/unit/test_papers_view_tracking.py backend/tests/unit/test_papers_list_detail_contract.py backend/tests/unit/test_papers_engagement_api.py -q`
Expected: FAIL with missing repository/service behavior or missing routes.

- [ ] **Step 3: Implement minimal repository and service support**

```python
class CommunityPaperRepository:
    def list_favorite_folders(...): ...
    def sync_paper_favorite_folders(...): ...
    def toggle_paper_like(...): ...
    def record_daily_view(...): ...
```

- [ ] **Step 4: Re-run targeted backend tests until green**

Run: `pytest backend/tests/unit/test_papers_view_tracking.py backend/tests/unit/test_papers_list_detail_contract.py backend/tests/unit/test_papers_engagement_api.py -q`
Expected: PASS

### Task 3: Add API routes and contract coverage for favorites workspace and interactions

**Files:**
- Modify: `backend/app/api/routes/papers.py`
- Modify: `backend/tests/unit/test_papers_engagement_api.py`
- Modify: `frontend/src/types/community.ts`
- Modify: `frontend/src/lib/community-api.ts`

- [ ] **Step 1: Extend API tests with expected request/response contracts**

```python
def test_list_favorite_folders_contract(client): ...
def test_put_paper_favorite_folders_contract(client): ...
def test_post_like_contract(client): ...
def test_post_view_accepts_anon_principal_header(client): ...
```

- [ ] **Step 2: Run route contract tests to verify they fail**

Run: `pytest backend/tests/unit/test_papers_engagement_api.py -q`
Expected: FAIL on missing endpoints or response fields.

- [ ] **Step 3: Implement the thin route layer and type/client updates**

```python
@router.get("/favorite-folders")
async def list_favorite_folders(...): ...
```

```ts
export interface FavoriteFolder { ... }
export async function listFavoriteFolders() { ... }
```

- [ ] **Step 4: Re-run route contract tests**

Run: `pytest backend/tests/unit/test_papers_engagement_api.py -q`
Expected: PASS

### Task 4: Add frontend route/sidebar coverage for favorites workspace

**Files:**
- Modify: `frontend/src/layout/AppSidebar.tsx`
- Modify: `frontend/src/layout/AppSidebar.community-shell.test.tsx`
- Modify: `frontend/src/App.community-routing.test.tsx`
- Create: `frontend/src/pages/Favorites/index.tsx`
- Create: `frontend/src/pages/Favorites.test.tsx`

- [ ] **Step 1: Write failing frontend tests for authenticated favorites navigation**

```tsx
it("shows favorites in the sidebar only for authenticated users", () => { ... })
it("routes /favorites to the favorites workspace", () => { ... })
```

- [ ] **Step 2: Run frontend tests to verify they fail**

Run: `npm test -- AppSidebar.community-shell.test.tsx App.community-routing.test.tsx Favorites.test.tsx`
Expected: FAIL because the route and nav entry do not exist yet.

- [ ] **Step 3: Implement sidebar entry and favorites page shell**

```tsx
<SidebarNavItem to="/favorites" ... />
```

- [ ] **Step 4: Re-run the same frontend tests**

Run: `npm test -- AppSidebar.community-shell.test.tsx App.community-routing.test.tsx Favorites.test.tsx`
Expected: PASS

### Task 5: Add shared favorite picker and like UI with TDD

**Files:**
- Modify: `frontend/src/features/community-paper/components/PaperCard.tsx`
- Modify: `frontend/src/features/community-paper/components/PaperCard.test.tsx`
- Modify: `frontend/src/features/community-paper/components/PaperDetailHeader.tsx`
- Modify: `frontend/src/pages/PaperDetail.test.tsx`
- Create: `frontend/src/features/community-paper/components/FavoritePicker.tsx`
- Create: `frontend/src/features/community-paper/components/FavoritePicker.test.tsx`

- [ ] **Step 1: Write failing tests for picker behavior and highlighted favorite state**

```tsx
it("highlights the favorite button when the paper has at least one folder", () => { ... })
it("creates a folder, auto-selects it, and waits for confirm before saving paper assignment", async () => { ... })
it("optimistically toggles likes on feed cards", async () => { ... })
```

- [ ] **Step 2: Run focused frontend tests to verify they fail**

Run: `npm test -- PaperCard.test.tsx PaperDetail.test.tsx FavoritePicker.test.tsx`
Expected: FAIL because the picker and like controls are not implemented.

- [ ] **Step 3: Implement minimal UI and API wiring**

```tsx
<FavoritePicker paperId={paper.id} ... />
```

```tsx
<button aria-pressed={paper.viewer_state?.liked}>...</button>
```

- [ ] **Step 4: Re-run the focused frontend tests**

Run: `npm test -- PaperCard.test.tsx PaperDetail.test.tsx FavoritePicker.test.tsx`
Expected: PASS

### Task 6: Add i18n updates, backend file index updates, and final focused verification

**Files:**
- Modify: `frontend/src/i18n/task-copy.ts`
- Modify: locale resources already used by the community UI
- Modify: `backend/file.md`

- [ ] **Step 1: Add any new translation keys used by favorites, likes, and sort labels**

```ts
community: {
  favorites: { ... },
  feed: { sort: { latest: "...", views: "...", likes: "..." } }
}
```

- [ ] **Step 2: Run i18n validation**

Run: `npm run i18n:check`
Expected: PASS

- [ ] **Step 3: Update backend file index for any new migration or backend responsibility changes**

```md
- `backend/migrations_mysql/20260421_0008_community_paper_engagement.sql`: ...
```

- [ ] **Step 4: Run the focused final verification set**

Run: `pytest backend/tests/unit/test_mysql_community_paper_engagement_migration_sql.py backend/tests/unit/test_papers_view_tracking.py backend/tests/unit/test_papers_list_detail_contract.py backend/tests/unit/test_papers_engagement_api.py -q`
Expected: PASS

Run: `npm test -- AppSidebar.community-shell.test.tsx App.community-routing.test.tsx Favorites.test.tsx PaperCard.test.tsx PaperDetail.test.tsx FavoritePicker.test.tsx`
Expected: PASS

Run: `npm run i18n:check`
Expected: PASS
