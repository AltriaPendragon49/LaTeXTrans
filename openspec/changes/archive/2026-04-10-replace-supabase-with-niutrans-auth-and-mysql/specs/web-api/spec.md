## ADDED Requirements

### Requirement: Authentication API issues local sessions after NiuTrans verification
The backend SHALL expose authentication endpoints that verify credentials against the NiuTrans login API and then establish the current application's own authenticated session.

#### Scenario: Local login succeeds through upstream verification
- **WHEN** the client submits valid credentials to the current application's login endpoint
- **THEN** the backend SHALL verify those credentials through the NiuTrans login API
- **AND** it SHALL upsert the mapped local user record
- **AND** it SHALL return a local authenticated session or JWT for subsequent project API calls.

#### Scenario: Login response follows a stable auth contract
- **WHEN** the backend returns a successful login response
- **THEN** the payload SHALL include `access_token`, `token_type`, `expires_in`, and a normalized local `user` object
- **AND** clients SHALL NOT need to inspect raw upstream NiuTrans token fields to bootstrap the session.

#### Scenario: Session bootstrap returns the current local user
- **WHEN** the client calls `GET /api/auth/me` with a valid local token
- **THEN** the API SHALL return the normalized local authenticated user payload
- **AND** it SHALL be the canonical frontend bootstrap endpoint for restoring auth state.

#### Scenario: Local logout clears current application auth state
- **WHEN** the client requests logout through the current application's auth API
- **THEN** the backend and frontend SHALL clear the current application's local session state
- **AND** later protected API calls SHALL require a fresh local login.

#### Scenario: Auth failures use stable error codes
- **WHEN** login or session validation fails
- **THEN** the API SHALL return a machine-readable auth error code such as invalid credentials, invalid session, forbidden, or upstream unavailable
- **AND** the response SHALL still include a user-facing message.

## MODIFIED Requirements

### Requirement: Translation Progress Reporting
The system SHALL report granular progress updates during translation workflow stages, with optimized database I/O for local persistent operations.

#### Scenario: Async route DB calls do not pin event loop
- **WHEN** async API routes perform local database operations during task or persistence flows
- **THEN** blocking DB work SHALL execute through async-safe wrapper offload
- **AND** event-loop responsiveness for `/api/health` and task-status polling SHALL remain stable during compile load.

#### Scenario: Behavior-level event-loop health gate
- **WHEN** parser or validator phases run with simulated blocking work
- **THEN** automated tests SHALL verify scheduler or tick latency stays under the configured threshold
- **AND** concurrent task wall time SHALL indicate non-serialized behavior.

### Requirement: Persisted Task Recovery
The task manager MUST recover task configurations from the local file system and local database without depending on Supabase fallback behavior.

#### Scenario: Task missing from local database
- **WHEN** a task is not found in the local persistent store
- **THEN** the backend SHALL search the local file system using the configured `outputs_dir` and `uploads_dir`
- **AND** it SHALL retrieve metadata gracefully without requiring a Supabase fallback path.

### Requirement: Admin API supports manual stale task cleanup
The backend SHALL expose an administrative endpoint to manually trigger restart reconciliation for community-paper translation state across the local database and local filesystem.

#### Scenario: Admin triggers cleanup
- **WHEN** an authenticated local admin user calls `POST /api/admin/cleanup`
- **THEN** the API SHALL mark interrupted in-flight translation tasks as failed and clean related local artifacts
- **AND** it SHALL purge eligible non-success community-paper artifacts across the local database and disk
- **AND** it SHALL return a summary of the operations performed.

### Requirement: Backend automatically cleans up stale tasks on startup
The backend SHALL automatically reconcile community-paper translation state during startup so interrupted work is deterministically failed or cleaned across the local database and filesystem before traffic is served.

#### Scenario: Startup cleanup runs before serving traffic
- **WHEN** the backend process starts with stale queued, processing, or failed community-paper tasks still present
- **THEN** it SHALL mark active interrupted `translation_tasks` as failed and clean local task artifacts
- **AND** it SHALL purge eligible non-success community-paper records in the local database while keeping successful and public papers untouched
- **AND** later API traffic SHALL observe the cleaned state without requiring a manual cleanup call.

#### Scenario: Startup purge is explicitly disabled
- **WHEN** `ENABLE_STALE_PAPER_PURGE` is set to a disabled value
- **THEN** startup reconciliation SHALL skip non-success paper purge operations
- **AND** it SHALL continue to report cleanup execution status without deleting paper records.

### Requirement: Non-success community papers are deleted comprehensively
The backend SHALL remove purge-eligible non-success community papers from all related paper-facing local database tables and local task artifacts, not only from the primary `papers` row.

#### Scenario: Purge-eligible non-success paper has related moderation and reaction data
- **WHEN** a purge-eligible non-success community paper is purged during startup or admin cleanup
- **THEN** the backend SHALL delete related `comments`, `reports`, `moderation_actions`, `paper_assets`, `paper_likes`, `paper_favorites`, related `translation_tasks`, and the `papers` row from the local database
- **AND** it SHALL also delete the corresponding local task artifact directories and `community_papers/<paper_id>` folder.

#### Scenario: Public paper remains available after restart cleanup
- **WHEN** startup or admin cleanup runs
- **THEN** non-success papers that are currently public SHALL NOT be purged by default
- **AND** their reader assets and metadata SHALL remain queryable via normal paper APIs.

### Requirement: Community paper APIs retry transient database transport failures
Community paper service-layer API paths SHALL retry transient local database or driver-level transport failures before returning an error.

#### Scenario: Transient timeout recovers within retry budget
- **WHEN** a local database operation fails with transient transport or timeout exceptions
- **THEN** the API layer SHALL retry with bounded backoff
- **AND** it SHALL return success if a later retry succeeds within the configured retry budget.

#### Scenario: Transient timeout persists beyond retry budget
- **WHEN** retries are exhausted for transient transport or timeout exceptions
- **THEN** the API layer SHALL surface the final failure
- **AND** it SHALL not loop indefinitely.
