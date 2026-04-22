# Admin Curation History Filters And Bulk Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every admin history filter behave as intended and allow hard deletion of selected currently listed curation jobs in one action.

**Architecture:** Keep the existing repository-service-route split. Normalize status semantics at the API/service boundary, add a small batch-delete service path that reuses the single-delete workflow per job, and extend the existing React history page with checkbox selection plus a single batch action bar.

**Tech Stack:** FastAPI, repository/service pattern, React 18 + Vite + Vitest, i18next locale JSON.

---

### Task 1: Add backend regression tests for filter semantics and batch delete

**Files:**
- Modify: `backend/tests/unit/test_community_admin_curation_api.py`
- Modify: `backend/tests/unit/test_admin_curation_lifecycle.py`

- [ ] **Step 1: Write the failing API tests for `all`, grouped `processing`, and batch delete**

```python
def test_admin_list_curation_jobs_treats_all_status_as_unfiltered(monkeypatch) -> None: ...
def test_admin_list_curation_jobs_maps_processing_to_inflight_group(monkeypatch) -> None: ...
def test_admin_can_batch_delete_curation_jobs(monkeypatch) -> None: ...
```

- [ ] **Step 2: Run the focused backend API tests to confirm they fail**

Run: `python -m pytest backend/tests/unit/test_community_admin_curation_api.py -q`
Expected: FAIL because grouped processing and batch delete are not implemented yet.

- [ ] **Step 3: Add a lifecycle test for partial-success batch delete reporting**

```python
async def test_batch_delete_admin_curation_jobs_reports_successes_and_failures() -> None: ...
```

- [ ] **Step 4: Run the lifecycle test to confirm it fails**

Run: `python -m pytest backend/tests/unit/test_admin_curation_lifecycle.py -q`
Expected: FAIL because the batch delete service does not exist yet.

### Task 2: Implement backend filter normalization and batch delete API

**Files:**
- Modify: `backend/app/api/routes/papers.py`
- Modify: `backend/app/services/paper_service.py`
- Modify: `backend/app/repositories/community_paper_repository.py`

- [ ] **Step 1: Extend repository filtering for grouped inflight statuses**

```python
def list_curation_jobs(self, *, status_filter: Optional[str] = None, search: Optional[str] = None) -> list[dict[str, Any]]:
    if normalized_status == "processing":
        conditions.append(
            "(status = %s or status = %s or status = %s)" % (...)
        )
```

- [ ] **Step 2: Add service-layer batch delete orchestration that reuses per-job hard delete**

```python
async def batch_delete_admin_curation_jobs(*, job_ids: Sequence[str], current_user: Dict[str, Any]) -> Dict[str, Any]:
    ...
    for job_id in normalized_job_ids:
        try:
            deleted = await delete_admin_curation_job(job_id=job_id, current_user=current_user)
            successes.append(...)
        except HTTPException as exc:
            failures.append(...)
```

- [ ] **Step 3: Add route request/response models and the admin batch delete endpoint**

```python
class AdminBatchDeleteCurationJobsRequest(BaseModel):
    job_ids: List[str]

@router.post("/admin/curation/jobs/batch-delete", response_model=AdminBatchDeleteCurationJobsResponse)
async def batch_delete_admin_curation_jobs(...):
    ...
```

- [ ] **Step 4: Run the backend API and lifecycle tests**

Run: `python -m pytest backend/tests/unit/test_community_admin_curation_api.py backend/tests/unit/test_admin_curation_lifecycle.py -q`
Expected: PASS

### Task 3: Add frontend filter coverage and selected-result batch delete UX

**Files:**
- Modify: `frontend/src/pages/CommunityAdminCurationTasks.tsx`
- Modify: `frontend/src/lib/community-api.ts`
- Modify: `frontend/src/types/community.ts`
- Modify: `frontend/src/pages/CommunityAdminCurationTasks.test.tsx`
- Modify: `frontend/src/locales/en/common.json`
- Modify: `frontend/src/locales/zh/common.json`
- Modify: `frontend/src/locales/de/common.json`
- Modify: `frontend/src/locales/es/common.json`
- Modify: `frontend/src/locales/fr/common.json`
- Modify: `frontend/src/locales/ja/common.json`
- Modify: `frontend/src/locales/ko/common.json`
- Modify: `frontend/src/locales/ru/common.json`

- [ ] **Step 1: Write failing frontend tests for grouped processing, select-all, and batch delete**

```tsx
it("requests the grouped processing filter", async () => { ... })
it("selects all currently listed jobs and batch deletes them", async () => { ... })
```

- [ ] **Step 2: Run the focused frontend tests to confirm they fail**

Run: `cd frontend && npm run test -- pages/CommunityAdminCurationTasks.test.tsx --run`
Expected: FAIL because the page does not yet support selection or batch delete.

- [ ] **Step 3: Implement checkbox selection and the batch action bar with i18n keys**

```tsx
const [selectedJobIds, setSelectedJobIds] = useState<string[]>([])
...
<Button onClick={() => toggleSelectAllVisibleJobs()}>{t("community.admin.tasks.selectAllVisible")}</Button>
```

- [ ] **Step 4: Add batch delete API client and response typing**

```ts
export async function batchDeleteAdminCurationJobs(jobIds: string[]): Promise<AdminBatchDeleteCurationJobsResponse> { ... }
```

- [ ] **Step 5: Run frontend tests and i18n validation**

Run: `cd frontend && npm run test -- pages/CommunityAdminCurationTasks.test.tsx App.community-routing.test.tsx components/app-sidebar.community-shell.test.tsx --run`
Expected: PASS

Run: `cd frontend && npm run i18n:check`
Expected: PASS

### Task 4: Validate, deploy, and verify on the server

**Files:**
- Modify: `openspec/changes/update-admin-curation-history-filters-and-bulk-delete/tasks.md`

- [ ] **Step 1: Run full focused verification for this change**

Run: `python -m pytest backend/tests/unit/test_community_admin_curation_api.py backend/tests/unit/test_admin_curation_lifecycle.py backend/tests/unit/test_mysql_community_admin_curation_migrations_sql.py -q`
Expected: PASS

Run: `cd frontend && npm run test -- App.community-routing.test.tsx components/app-sidebar.community-shell.test.tsx pages/CommunityAdminCurationTasks.test.tsx --run`
Expected: PASS

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 2: Validate the OpenSpec change**

Run: `openspec validate update-admin-curation-history-filters-and-bulk-delete --strict --no-interactive`
Expected: PASS

- [ ] **Step 3: Deploy and verify**

Run: `cd frontend; npm run build; scripts\\deploy-frontend.ps1`
Expected: PASS

Run on server: pull latest code, restart backend, verify `/api/health`, verify the history `all` and `processing` filters, and run one real selected-result batch delete from existing retained history records.
Expected: filters return matching records and batch delete removes only the chosen selected jobs.
