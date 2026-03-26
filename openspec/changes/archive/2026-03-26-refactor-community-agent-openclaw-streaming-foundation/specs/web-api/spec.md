## MODIFIED Requirements
### Requirement: Community agent run API returns a natural assistant message
The community agent run API SHALL return the assistant’s natural-language reply as a first-class field while preserving run metadata such as citations, tool trace, provider state, and actions, and it SHALL support both blocking and async accepted execution modes.

#### Scenario: Conversational run completes successfully in blocking mode
- **WHEN** `POST /api/community-agent/runs` completes in blocking mode
- **THEN** the response SHALL include `message` containing the assistant’s natural-language reply
- **AND** it SHALL continue to include `citations`, `tool_trace`, `provider_state`, and `action`.

#### Scenario: Compatibility alias remains during migration
- **WHEN** existing consumers still read `summary`
- **THEN** the API SHALL keep `summary` aligned with `message` during the migration window
- **AND** the conversational UI SHALL prefer `message` when present.

#### Scenario: Async mode defers the final message to the stream and result endpoints
- **WHEN** `POST /api/community-agent/runs` is called in async mode
- **THEN** the accepted response MAY omit the final `message` body
- **AND** the final assistant reply SHALL be available through the stream and result endpoints.

## ADDED Requirements
### Requirement: Community agent runs support async accepted mode
The community agent run API SHALL support an async accepted mode so the client can start a run, subscribe to the live stream, and later retrieve the final snapshot by `run_id`.

#### Scenario: Async run is accepted
- **WHEN** the client submits a run in async mode
- **THEN** `POST /api/community-agent/runs` SHALL return an accepted payload with `run_id`, `status`, `stream_url`, and `result_url`
- **AND** the actual assistant content SHALL arrive over the stream endpoint.

### Requirement: Community agent exposes an authenticated live SSE stream
The community agent API SHALL expose an authenticated live SSE stream for a running agent session so the client can render assistant deltas, tool lifecycle updates, citations, actions, status, and completion in order.

#### Scenario: Client subscribes to a running agent stream
- **WHEN** the client opens the run event stream with valid authentication
- **THEN** the API SHALL stream ordered events for tokens, tool lifecycle, citations, actions, status, and completion
- **AND** it SHALL close the stream cleanly after completion or failure.

#### Scenario: Unauthorized stream request is rejected
- **WHEN** the client requests the stream without valid auth
- **THEN** the API SHALL reject the request with an auth failure
- **AND** it SHALL NOT leak run state.

### Requirement: Community agent stream events follow a stable schema
The community agent stream SHALL emit a stable event schema so clients can parse assistant deltas, tool transitions, and completion snapshots without depending on ad hoc payload shapes.

#### Scenario: Assistant text delta event
- **WHEN** the runtime emits a token chunk
- **THEN** the event SHALL contain a stable event type, run id, sequence number, and delta text payload.

#### Scenario: Completion event carries final run snapshot
- **WHEN** the run finishes
- **THEN** the stream SHALL emit a completion event containing final `message`, `citations`, `tool_trace`, `provider_state`, and `action`.

### Requirement: Admin API supports manual stale task cleanup
The backend SHALL expose an administrative endpoint to manually trigger restart reconciliation for community-paper translation state without requiring a server restart.

#### Scenario: Admin triggers cleanup
- **WHEN** an authenticated admin user calls `POST /api/admin/cleanup`
- **THEN** the API SHALL mark interrupted in-flight translation tasks as failed and clean related local artifacts
- **AND** it SHALL purge non-success community-paper artifacts (`not_started`, `queued`, `processing`, `failed`, `failed_compilation`, `structure_invalid`) across disk and Supabase
- **AND** it SHALL return a summary of the operations performed.

### Requirement: Backend automatically cleans up stale tasks on startup
The backend SHALL automatically reconcile community-paper translation state during startup so interrupted work is deterministically failed/cleaned and non-success artifacts are removed across the database and local filesystem before traffic is served.

#### Scenario: Startup cleanup runs before serving traffic
- **WHEN** the backend process starts with stale queued, processing, or failed community-paper tasks still present
- **THEN** it SHALL mark active interrupted `translation_tasks` as `failed` and clean local task artifacts
- **AND** it SHALL purge non-success community-paper records from all related local and Supabase storage while keeping successful papers untouched
- **AND** subsequent API traffic SHALL observe the cleaned state without requiring a manual restart or cleanup call.

### Requirement: Non-success community papers are deleted comprehensively
The backend SHALL remove non-success community papers from all related paper-facing Supabase tables and local task artifacts, not only from the primary `papers` row.

#### Scenario: Non-success paper has related moderation and reaction data
- **WHEN** a non-success community paper is purged during startup or admin cleanup
- **THEN** the backend SHALL delete related `comments`, `reports`, `moderation_actions`, `paper_assets`, `paper_likes`, `paper_favorites`, related `translation_tasks`, and the `papers` row
- **AND** it SHALL also delete the corresponding local task artifact directories and `community_papers/<paper_id>` folder.

#### Scenario: Successful paper remains available after restart cleanup
- **WHEN** startup or admin cleanup runs
- **THEN** papers already in successful/translated-ready state SHALL NOT be purged
- **AND** their reader assets and metadata SHALL remain queryable via normal paper APIs.

### Requirement: In-flight translation tasks fail cleanly after restart
The backend SHALL treat queued/pending/processing translation tasks as interrupted work on restart and convert them to a terminal failed state.

#### Scenario: Restart interrupts an active translation
- **WHEN** the backend restarts while a persisted translation task is in `queued`, `pending`, or `processing`
- **THEN** startup reconciliation SHALL mark the task `failed`, set restart-interruption diagnostics, and clean corresponding local artifacts
- **AND** related `papers` rows that still point to the interrupted task SHALL be updated away from active states.
