# Admin Curation Retention And History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement retained failed admin curation jobs, admin curation history APIs/UI, and large newline-delimited arXiv intake while preserving bounded execution.

**Architecture:** Extend the existing `community_curation_jobs` model instead of creating a second task system. Keep admin orchestration in `paper_service`, persist new retention metadata in MySQL/repository layers, expose thin admin APIs from `papers.py`, and add one dedicated admin history page in the existing React shell.

**Tech Stack:** FastAPI, MySQL migrations, repository/service split in Python, React 18 + Vite + Vitest, i18next locale JSON, npm build + PowerShell deploy.

---

### Task 1: Add schema coverage for retained admin curation metadata

**Files:**
- Create: `backend/migrations_mysql/20260419_0006_admin_curation_retention_fields.sql`
- Modify: `backend/tests/unit/test_mysql_community_admin_curation_migrations_sql.py`

- [ ] **Step 1: Write the failing migration test**

```python
def test_mysql_admin_curation_retention_migration_exists_and_declares_required_columns() -> None:
    assert RETENTION_MIGRATION.exists()
    sql = _normalized_sql(RETENTION_MIGRATION)
    assert "alter table community_curation_jobs" in sql
    assert "terminal_task_status varchar(32) null" in sql
    assert "failed_artifact_path text null" in sql
    assert "artifact_storage_backend varchar(32) null" in sql
    assert "published_paper_id varchar(64) null" in sql
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/unit/test_mysql_community_admin_curation_migrations_sql.py -q`
Expected: FAIL because the new migration file and assertions do not exist yet.

- [ ] **Step 3: Add the migration file and wire the test constant**

```sql
alter table community_curation_jobs
  add column terminal_task_status varchar(32) null after status,
  add column failed_artifact_path text null after error,
  add column artifact_storage_backend varchar(32) null after failed_artifact_path,
  add column published_paper_id varchar(64) null after paper_id;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/unit/test_mysql_community_admin_curation_migrations_sql.py -q`
Expected: PASS

### Task 2: Extend repository and API contracts for admin curation history

**Files:**
- Modify: `backend/app/repositories/community_paper_repository.py`
- Modify: `backend/app/api/routes/papers.py`
- Modify: `backend/tests/unit/test_community_admin_curation_api.py`

- [ ] **Step 1: Write failing API tests for history list and delete**

```python
def test_admin_can_list_curation_jobs(monkeypatch) -> None:
    ...
    response = asyncio.run(_call())
    assert response.status_code == 200
    assert response.json()["items"][0]["job_id"] == "job-1"

def test_admin_can_delete_failed_curation_job(monkeypatch) -> None:
    ...
    response = asyncio.run(_call())
    assert response.status_code == 200
    assert response.json()["job_id"] == "job-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/unit/test_community_admin_curation_api.py -q`
Expected: FAIL because the new routes and response models do not exist yet.

- [ ] **Step 3: Add repository list/search helpers and route models**

```python
class AdminCurationJobHistoryItemResponse(BaseModel):
    job_id: str
    batch_id: str
    paper_id: Optional[str] = None
    published_paper_id: Optional[str] = None
    task_id: Optional[str] = None
    source_type: str
    arxiv_id: Optional[str] = None
    status: str
    terminal_task_status: Optional[str] = None
    error: Optional[str] = None
    failed_artifact_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/unit/test_community_admin_curation_api.py -q`
Expected: PASS

### Task 3: Preserve failed admin curation evidence and implement hard-delete flows

**Files:**
- Modify: `backend/app/services/paper_service.py`
- Modify: `backend/tests/unit/test_admin_curation_lifecycle.py`
- Modify: `backend/tests/unit/test_task_artifact_storage.py`

- [ ] **Step 1: Write failing lifecycle tests for retention**

```python
def test_cleanup_failed_admin_curation_artifacts_retains_translation_row_and_records_failed_artifact_path(...):
    ...
    assert repository.deleted_translation_tasks == []
    assert repository.job["failed_artifact_path"] == "failed_tasks/task-existing"
    assert repository.job["artifact_storage_backend"] == "object_storage"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/unit/test_admin_curation_lifecycle.py -q`
Expected: FAIL because cleanup currently deletes translation rows and failed outputs.

- [ ] **Step 3: Change service behavior to retain failed rows/artifacts and add curation-job delete service**

```python
await _run_local_repo(
    lambda: repository.update_curation_job(
        job_id,
        {
            "status": "failed",
            "terminal_task_status": terminal_status,
            "failed_artifact_path": failed_artifact_path,
            "artifact_storage_backend": storage_backend,
            "updated_at": _utc_now_iso(),
        },
    )
)
```

- [ ] **Step 4: Run focused backend tests**

Run: `python -m pytest backend/tests/unit/test_admin_curation_lifecycle.py backend/tests/unit/test_task_artifact_storage.py -q`
Expected: PASS

### Task 4: Support newline-delimited intake and admin task history in the frontend

**Files:**
- Modify: `frontend/src/pages/CommunityAdminCuration.tsx`
- Create: `frontend/src/pages/CommunityAdminCurationTasks.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/app-sidebar.tsx`
- Modify: `frontend/src/lib/community-api.ts`
- Modify: `frontend/src/types/community.ts`
- Modify: `frontend/src/App.community-routing.test.tsx`
- Modify: `frontend/src/components/app-sidebar.community-shell.test.tsx`
- Modify: `frontend/src/locales/en/common.json`
- Modify: `frontend/src/locales/zh/common.json`
- Modify: `frontend/src/locales/de/common.json`
- Modify: `frontend/src/locales/es/common.json`
- Modify: `frontend/src/locales/fr/common.json`
- Modify: `frontend/src/locales/ja/common.json`
- Modify: `frontend/src/locales/ko/common.json`
- Modify: `frontend/src/locales/ru/common.json`

- [ ] **Step 1: Write failing routing/sidebar/UI tests**

```tsx
it("allows admin users to access /admin/curation/tasks", async () => {
  ...
  expect(await screen.findByText("Admin curation tasks page")).toBeInTheDocument()
})

it("shows the admin curation tasks link for admin users", async () => {
  ...
  expect(screen.getByRole("link", { name: /Admin tasks/i })).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm run test -- App.community-routing.test.tsx app-sidebar.community-shell.test.tsx --run`
Expected: FAIL because the new page, route, nav link, and copy do not exist yet.

- [ ] **Step 3: Implement newline parsing, history page, API types, and locale copy**

```ts
function parseArxivIds(rawValue: string): string[] {
  return Array.from(
    new Set(
      rawValue
        .split(/\r?\n/)
        .map((value) => value.trim())
        .filter(Boolean),
    ),
  )
}
```

- [ ] **Step 4: Run focused frontend tests**

Run: `cd frontend; npm run test -- App.community-routing.test.tsx app-sidebar.community-shell.test.tsx --run`
Expected: PASS

### Task 5: Run integrated verification, build, deploy, and commit

**Files:**
- Modify: `backend/file.md`
- Modify: `openspec/changes/update-admin-curation-task-retention-and-history/tasks.md`

- [ ] **Step 1: Update backend file index for any backend production file changes**

```md
- `backend/migrations_mysql/20260419_0006_admin_curation_retention_fields.sql`: MySQL migration adding retained admin curation metadata fields for failed artifact tracking and published-paper linkage.
```

- [ ] **Step 2: Run local verification**

Run: `python -m pytest backend/tests/unit/test_mysql_community_admin_curation_migrations_sql.py backend/tests/unit/test_admin_curation_lifecycle.py backend/tests/unit/test_community_admin_curation_api.py backend/tests/unit/test_task_artifact_storage.py -q`
Expected: PASS

Run: `cd frontend; npm run test -- App.community-routing.test.tsx app-sidebar.community-shell.test.tsx --run`
Expected: PASS

Run: `cd frontend; npm run build`
Expected: PASS

- [ ] **Step 3: Mark OpenSpec task checklist honestly**

```md
- [x] 1.1 ...
```

- [ ] **Step 4: Commit**

Run: `git add backend frontend openspec && git commit -m "feat: retain admin curation task history"`
Expected: commit created successfully.
