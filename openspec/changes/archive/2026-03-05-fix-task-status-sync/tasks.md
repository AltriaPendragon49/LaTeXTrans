# Tasks: Fix Task Status Sync and Notification Failures

1. [x] **Update Failed Task Interception**
   - **Target**: `backend/app/services/task_manager.py` (specifically `_intercept_failed_task`)
   - **Action**: Remove the call to `_delete_failed_task_from_supabase`.
   - **Validation**: Ensure that when a task fails (e.g., via structure guard check), its `STATUS` remains in the DB as `failed`, `failed_compilation`, or `structure_invalid` and is subsequently returned by the `history.py` endpoint.

2. [x] **Ensure Email Preference Recovery**
   - **Target**: `backend/app/services/task_manager.py` (specifically `_recover_from_supabase`)
   - **Action**: Extract `db_task.get("email_notification", False)` or from the JSON payload and embed it into the restored `advanced_config` dictionary.
   - **Validation**: Verify that resuming a task from the DB correctly retains the `email_notification: true` flag.

3. [x] **Extend Frontend Task History UI**
   - **Target**: `frontend/src/` (History components and SSE logic)
   - **Action**: Map `structure_invalid` and `failed_compilation` into terminal "Failed" states so the UI correctly displays the error instead of defaulting to a generic "Waiting" or "Processing" badge. 
   - **Validation**: Verify visual badging on the History page for tasks populated with these fail states.

4. [x] **Address Flusher Race Condition for Terminated Tasks**
   - **Target**: `backend/app/services/task_manager.py`
   - **Action**: Validate if there's a race condition where a completed task doesn't flush. Currently, if `_flusher` drops writes when the container is shutting down, it fails. Provide a shutdown flush mechanism if missing.
   - **Validation**: TDD tests on `SupabaseFlusher` confirming terminal states are successfully pushed.

5. [x] **Lazy Task-Log Status Reconciliation**
   - **Target**: `backend/app/api/routes/history.py`
   - **Action**: Implement a mechanism in the history API to inspect local `task_log.json` for non-terminal tasks and correct their status in Supabase if a terminal event is found.
   - **Validation**: Verify that tasks stuck in "Pending" but actually finished are corrected and displayed as "Completed" on the history page.
