# Translation Retry Budgets And Curation Timeouts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved backend changes so admin-curation timeouts stop conflating queue wait with execution time, timeout/budget-triggered cancellation always reaches terminal state and terminates live execution, remedial retry work is bounded, and task/admin status surfaces expose stable terminal reasons.

**Architecture:** Keep the existing FastAPI + service + in-memory task manager structure. Extend the current task/task-log metadata instead of introducing new subsystems, and centralize the new cancellation and timeout semantics in `paper_service.py`, `translate.py`, `task_manager.py`, and the translation orchestrator/runtime helpers.

**Tech Stack:** FastAPI, Pydantic, asyncio, repository-backed task persistence, pytest

---

### Task 1: Lock down curation timeout and cancellation behavior with tests

**Files:**
- Modify: `backend/tests/unit/test_admin_curation_lifecycle.py`
- Modify: `backend/app/services/paper_service.py`

- [ ] **Step 1: Write failing tests for stage-aware waiting and terminal cleanup**

Add tests covering:

```python
def test_wait_for_task_terminal_state_uses_stage_specific_budgets(...): ...

def test_run_curation_job_timeout_marks_failed_without_leaving_processing(...): ...

def test_mark_admin_curation_job_failed_cancels_runtime_and_records_terminal_reason(...): ...
```

- [ ] **Step 2: Run the focused curation tests and verify they fail for the new behavior**

Run: `pytest backend/tests/unit/test_admin_curation_lifecycle.py -q`

Expected: failures showing the current implementation still uses a single 1800-second wait, lacks stable timeout reasons, or does not enforce runtime termination + terminal state together.

- [ ] **Step 3: Implement stage-aware wait semantics and curation failure metadata**

Change `backend/app/services/paper_service.py` to:

```python
# Introduce explicit admission/execution waiting phases and stable terminal reasons.
# Use a persisted active-work boundary from the translation task/task log before
# starting execution timeout accounting.
```

- [ ] **Step 4: Re-run the focused curation tests**

Run: `pytest backend/tests/unit/test_admin_curation_lifecycle.py -q`

Expected: targeted curation tests pass.

### Task 2: Lock down translation-task cancellation terminalization with tests

**Files:**
- Modify: `backend/tests/unit/test_task_queue_runtime_cancel_retry.py`
- Modify: `backend/tests/unit/test_task_queue_exception_terminalization.py`
- Modify: `backend/app/api/routes/translate.py`
- Modify: `backend/app/services/task_manager.py`

- [ ] **Step 1: Write failing tests for timeout/budget-driven cancellation**

Add tests covering:

```python
async def test_translate_cancelled_error_marks_terminal_state_for_non_user_cancel(...): ...
async def test_task_queue_cancel_path_terminates_live_execution_without_retry(...): ...
```

- [ ] **Step 2: Run the focused cancellation tests and verify they fail**

Run: `pytest backend/tests/unit/test_task_queue_runtime_cancel_retry.py backend/tests/unit/test_task_queue_exception_terminalization.py -q`

Expected: failures showing unexpected `CancelledError` still relies on retry instead of terminalizing, or that cancellation success does not require both runtime termination and terminal persistence.

- [ ] **Step 3: Implement terminalizing cancellation behavior**

Update:

```python
# backend/app/api/routes/translate.py
# Mark non-user/runtime-policy cancellations as terminal failed/interrupted with stable reason.

# backend/app/services/task_manager.py
# Ensure cancellation metadata is visible, runtime cancellation is issued, and no retry path
# re-queues tasks cancelled by timeout/budget policy.
```

- [ ] **Step 4: Re-run the focused cancellation tests**

Run: `pytest backend/tests/unit/test_task_queue_runtime_cancel_retry.py backend/tests/unit/test_task_queue_exception_terminalization.py -q`

Expected: focused cancellation tests pass.

### Task 3: Bound remedial retry work in the translator/orchestrator with tests

**Files:**
- Create or Modify: `backend/tests/unit/test_translation_retry_budgets.py`
- Modify: `backend/app/services/agents/translator_agent.py`
- Modify: `backend/app/services/agents/langgraph_orchestrator.py`

- [ ] **Step 1: Write failing tests for remedial budgets**

Add tests covering:

```python
def test_nested_rescue_budget_stops_after_part_and_task_caps(...): ...
def test_fatal_provider_error_short_circuits_repair_loops(...): ...
def test_validate_retry_rounds_stop_at_two(...): ...
```

- [ ] **Step 2: Run the focused retry-budget tests and verify they fail**

Run: `pytest backend/tests/unit/test_translation_retry_budgets.py -q`

Expected: failures showing the current implementation still uses `12` nested rescue per part, `3` outer validate rounds, or keeps retrying deterministic upstream fatal errors.

- [ ] **Step 3: Implement bounded retry accounting**

Update:

```python
# backend/app/services/agents/translator_agent.py
# Add per-part/per-task remedial counters, no-progress streak tracking,
# fatal-provider short-circuiting, and stable terminal reason bookkeeping.

# backend/app/services/agents/langgraph_orchestrator.py
# Reduce outer validation retries to 2 and propagate retry-budget terminal reasons.
```

- [ ] **Step 4: Re-run the focused retry-budget tests**

Run: `pytest backend/tests/unit/test_translation_retry_budgets.py -q`

Expected: focused retry-budget tests pass.

### Task 4: Expose terminal reasons and curation-specific defaults through APIs

**Files:**
- Modify: `backend/tests/unit/test_community_admin_curation_api.py`
- Modify: `backend/app/api/routes/task.py`
- Modify: `backend/app/api/routes/papers.py`
- Modify: `backend/app/models/config_models.py` only if default plumbing needs model support
- Modify: `backend/app/services/paper_service.py`

- [ ] **Step 1: Write failing API tests**

Add tests covering:

```python
def test_task_status_returns_terminal_reason(...): ...
def test_admin_curation_jobs_return_timeout_and_terminal_reasons(...): ...
def test_admin_curation_translation_defaults_disable_terminology_table(...): ...
```

- [ ] **Step 2: Run the focused API tests and verify they fail**

Run: `pytest backend/tests/unit/test_community_admin_curation_api.py -q`

Expected: failures showing missing `terminal_reason`/timeout reason fields or curation defaults still enabling terminology-table generation.

- [ ] **Step 3: Implement API payload changes**

Update:

```python
# backend/app/api/routes/task.py
# Include machine-readable terminal reason on polling and SSE payloads.

# backend/app/api/routes/papers.py
# Include timeout/terminal reason fields in admin curation history payloads.

# backend/app/services/paper_service.py
# Set curation-triggered translation config with generate_terminology_table=False.
```

- [ ] **Step 4: Re-run the focused API tests**

Run: `pytest backend/tests/unit/test_community_admin_curation_api.py -q`

Expected: focused API tests pass.

### Task 5: Final verification and bookkeeping

**Files:**
- Modify: `backend/file.md`
- Modify: `openspec/changes/update-translation-retry-budgets-and-curation-timeouts/tasks.md`

- [ ] **Step 1: Run the full focused verification set**

Run: `pytest backend/tests/unit/test_admin_curation_lifecycle.py backend/tests/unit/test_task_queue_runtime_cancel_retry.py backend/tests/unit/test_task_queue_exception_terminalization.py backend/tests/unit/test_community_admin_curation_api.py backend/tests/unit/test_translation_retry_budgets.py -q`

Expected: all focused tests pass.

- [ ] **Step 2: Update the backend index if file responsibilities changed materially**

Record changed responsibilities in:

```md
backend/file.md
```

- [ ] **Step 3: Mark completed OpenSpec tasks honestly**

Update:

```md
openspec/changes/update-translation-retry-budgets-and-curation-timeouts/tasks.md
```

to reflect completed implementation and verification items only after the evidence exists.
