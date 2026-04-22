# Admin Repeat arXiv Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make repeated admin arXiv curation hard-delete all prior traces before creating a fresh curation job and fresh `paper_id`.

**Architecture:** Extend the existing admin curation service instead of adding a new workflow. Keep duplicate detection and reset orchestration in `paper_service`, add one repository query for matching curation jobs, and prove the behavior with focused lifecycle tests before touching production code.

**Tech Stack:** Python, FastAPI service layer, repository SQL helpers, pytest

---

### Task 1: Add failing lifecycle tests for duplicate admin arXiv reset

**Files:**
- Modify: `backend/tests/unit/test_admin_curation_lifecycle.py`
- Test: `backend/tests/unit/test_admin_curation_lifecycle.py`

- [ ] **Step 1: Write the failing test**

```python
def test_submit_admin_arxiv_curation_batch_resets_existing_completed_arxiv_history(monkeypatch): ...

def test_submit_admin_arxiv_curation_batch_resets_existing_failed_arxiv_history(monkeypatch): ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/unit/test_admin_curation_lifecycle.py -k "resets_existing_" -q`
Expected: FAIL because the submission path still reuses the existing `paper_id` and never performs the reset.

- [ ] **Step 3: Write minimal implementation**

```python
async def _reset_existing_admin_arxiv_curation(...):
    ...

async def submit_admin_arxiv_curation_batch(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/unit/test_admin_curation_lifecycle.py -k "resets_existing_" -q`
Expected: PASS

### Task 2: Add repository support for duplicate-job lookup

**Files:**
- Modify: `backend/app/repositories/community_paper_repository.py`
- Test: `backend/tests/unit/test_admin_curation_lifecycle.py`

- [ ] **Step 1: Write the failing test**

```python
def test_reset_helper_queries_jobs_by_arxiv_id_in_created_order(monkeypatch): ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/unit/test_admin_curation_lifecycle.py -k "queries_jobs_by_arxiv_id" -q`
Expected: FAIL because the repository does not yet expose the query.

- [ ] **Step 3: Write minimal implementation**

```python
def list_curation_jobs_for_arxiv_id(self, arxiv_id: str) -> list[dict[str, Any]]:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/unit/test_admin_curation_lifecycle.py -k "queries_jobs_by_arxiv_id" -q`
Expected: PASS

### Task 3: Keep backend index and focused verification aligned

**Files:**
- Modify: `backend/file.md`
- Modify: `openspec/changes/update-admin-curation-repeat-arxiv-reset/tasks.md`

- [ ] **Step 1: Update backend responsibility notes**

```text
backend/app/services/paper_service.py: 管理员 arXiv 重复入库现已在提交前执行旧记录全流程硬删除与运行取消，再创建新的 curation job 与 paper_id。
backend/app/repositories/community_paper_repository.py: 增加按 arxiv_id 枚举 curation jobs 的查询，供重复入库预删除编排使用。
```

- [ ] **Step 2: Run focused verification**

Run: `python -m pytest backend/tests/unit/test_admin_curation_lifecycle.py -q`
Expected: PASS

- [ ] **Step 3: Validate OpenSpec**

Run: `openspec validate update-admin-curation-repeat-arxiv-reset --strict --no-interactive`
Expected: Validation passes with no errors.
