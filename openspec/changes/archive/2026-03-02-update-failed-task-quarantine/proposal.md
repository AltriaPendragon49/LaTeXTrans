# Change: update-failed-task-quarantine

## Why
Failed translation tasks remained in persistent history and mixed with successful user records, which made user history noisy and made debugging slower.

In addition, config capture was implemented as a test-only interceptor import from `backend.tests`, which created a runtime hard dependency and prevented stable config snapshot collection in normal backend runs.

## What Changes
- Add failed-task interception in `TaskManager.update_task()` for terminal statuses:
  - `failed`
  - `failed_compilation`
- On failed terminal status:
  - move only `data/outputs/{task_id}` to `data/failed_tasks/{task_id}`
  - use conflict-safe timestamp suffix when destination exists
  - delete corresponding `translation_tasks` row from Supabase
- Preserve in-memory task state for active status inspection while service is alive.
- Skip quarantine/delete behavior for user-cancelled tasks.

- Rebuild config capture as runtime functionality (no `backend.tests` dependency):
  - add runtime service `backend/app/services/config_capture.py`
  - add settings:
    - `task_configs_dir` (`backend/data/task_configs`)
    - `enable_task_config_capture` (`ENABLE_TASK_CONFIG_CAPTURE`, default `true`)
  - integrate capture call directly in `translate.py`
  - keep capture fail-open (never break translation on capture failure)
  - store validator-compatible JSON snapshots with masked API keys only

- Keep `backend/tests/apply_interceptor_patch.py` as a compatibility helper:
  - no-op when runtime capture is already integrated
  - inject runtime capture block only for older branches
  - keep undo behavior

- Update testing guide and validator examples to use `data/task_configs/config_*.json`.

## Impact
- Affected specs:
  - `translation-history`
  - `file-management`
  - `web-api`
- Affected code:
  - `backend/app/core/config.py`
  - `backend/app/services/task_manager.py`
  - `backend/app/services/config_capture.py`
  - `backend/app/api/routes/translate.py`
  - `backend/tests/apply_interceptor_patch.py`
  - `backend/tests/CONFIG_TESTING_GUIDE.md`
  - `backend/tests/config_validator.py`
  - `backend/tests/test_task_manager_failed_task_quarantine.py`
  - `backend/tests/test_translate_compilation_status_mapping.py`
  - `backend/tests/test_config_capture_service.py`
- Behavioral outcomes:
  - failed tasks are automatically removed from persistent history records
  - failed output artifacts are retained under `backend/data/failed_tasks`
  - config snapshots are captured to `backend/data/task_configs` during runtime translation when enabled
  - translation no longer depends on `backend.tests.*` modules
