# Tasks: update-failed-task-quarantine

## 1. Failed Task Quarantine
- [x] 1.1 Add `failed_tasks_dir` setting and ensure directory creation.
- [x] 1.2 Add failed-terminal interception in `TaskManager.update_task()` for `failed` and `failed_compilation`.
- [x] 1.3 Add skip logic for cancelled and already intercepted tasks.
- [x] 1.4 Move only `outputs/{task_id}` to `data/failed_tasks` with conflict-safe naming.
- [x] 1.5 Delete `translation_tasks` row via Supabase admin client.
- [x] 1.6 Preserve terminal email notification flow.

## 2. Runtime Config Capture Root Fix
- [x] 2.1 Add `task_configs_dir` setting (`backend/data/task_configs`) and create directory on startup.
- [x] 2.2 Add `enable_task_config_capture` setting (`ENABLE_TASK_CONFIG_CAPTURE`, default true).
- [x] 2.3 Implement runtime service `backend/app/services/config_capture.py`.
- [x] 2.4 Ensure capture writes validator-compatible JSON snapshot with masked API keys.
- [x] 2.5 Ensure capture uses atomic write and fail-open behavior.
- [x] 2.6 Integrate runtime capture call in `backend/app/api/routes/translate.py`.
- [x] 2.7 Remove runtime dependency on `backend.tests.test_config_interceptor`.

## 3. Compatibility Tooling and Docs
- [x] 3.1 Update `backend/tests/apply_interceptor_patch.py` as compatibility helper:
  - no-op when runtime capture is already integrated
  - inject runtime capture block for older branches only
  - keep undo behavior
- [x] 3.2 Update `backend/tests/CONFIG_TESTING_GUIDE.md` to runtime workflow.
- [x] 3.3 Update usage examples in `backend/tests/config_validator.py` to `data/task_configs/config_*.json`.

## 4. Tests
- [x] 4.1 Add `backend/tests/test_task_manager_failed_task_quarantine.py` coverage.
- [x] 4.2 Add `backend/tests/test_config_capture_service.py` coverage:
  - writes file
  - masks API key
  - handles non-JSON additional info
  - returns `None` when disabled
  - fail-open on write error
- [x] 4.3 Update `backend/tests/test_translate_compilation_status_mapping.py`:
  - capture when enabled
  - skip when disabled
  - translation still completes when capture returns `None`
- [x] 4.4 Run regression tests:
  - `pytest -q backend/tests/test_translate_compilation_status_mapping.py`
  - `pytest -q backend/tests/test_task_sse_terminal_states.py`
  - `pytest -q backend/tests/test_task_manager_failed_task_quarantine.py`
  - `pytest -q backend/tests/test_config_capture_service.py`

## 5. OpenSpec Validation
- [x] 5.1 Update spec deltas for `translation-history`, `file-management`, and `web-api`.
- [x] 5.2 Run `openspec validate update-failed-task-quarantine --strict --no-interactive`.
