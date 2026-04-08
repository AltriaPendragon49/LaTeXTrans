## MODIFIED Requirements

### Requirement: User Task Isolation
The system SHALL ensure that authenticated users can access only their own persisted translation tasks through application-layer ownership checks backed by the local database.

#### Scenario: Query the current user's task list
- **WHEN** an authenticated user requests `GET /api/history`
- **THEN** the system SHALL return only rows owned by the current local user id
- **AND** the results SHALL remain sorted by `created_at` descending.

#### Scenario: Query another user's task
- **WHEN** an authenticated user requests a task that is not owned by the current local user id
- **THEN** the system SHALL return the existing access-denied or not-found behavior for that endpoint
- **AND** it SHALL not depend on Supabase RLS to hide the row.

### Requirement: Task Deletion
The system SHALL delete persisted task metadata from the local database while continuing to clean only `outputs` and `terms` directories and preserving shared `uploads` directories as reusable cache.

#### Scenario: Delete a completed task from history
- **WHEN** an authenticated user confirms deletion for one of their history tasks
- **THEN** the system SHALL delete the task's persisted row from the local database
- **AND** it SHALL delete local `outputs/{task_id}/` and `terms/{task_id}/` directories
- **AND** it SHALL NOT delete shared uploads directories
- **AND** the frontend SHALL continue to show a success notification.

### Requirement: Deferred Task Persistence
The system SHALL delay authenticated task persistence until translation start and SHALL persist those rows into the local database instead of Supabase.

#### Scenario: Upload does not create a persisted row yet
- **WHEN** a user uploads source files before starting translation
- **THEN** the system SHALL create only the in-memory task state
- **AND** it SHALL NOT create a persisted translation-task row yet.

#### Scenario: Authenticated translation persists on first translation start
- **WHEN** an authenticated user starts translation for a task that has not been persisted yet
- **THEN** the system SHALL create the persisted task row in the local database
- **AND** that row SHALL include the full task metadata needed for history and later recovery.

#### Scenario: Guest translation remains non-persistent
- **WHEN** a guest user starts translation without a local authenticated identity
- **THEN** the system SHALL skip authenticated-history persistence
- **AND** the task SHALL remain guest-only runtime state.

### Requirement: Non-Terminal Task Status Reconciliation
The system MUST reconcile non-terminal task rows against local task logs and SHOULD asynchronously repair the local database record when a terminal status can be inferred.

#### Scenario: Reconcile status from local log
- **WHEN** a user requests task history and a persisted task is still marked `pending`, `processing`, or `queued`
- **AND** a local `task_log.json` contains a terminal event for that task
- **THEN** the API response MUST return the inferred terminal status and 100% progress
- **AND** the system SHOULD asynchronously update the local database row to match the inferred status.
