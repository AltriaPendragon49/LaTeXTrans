## RENAMED Requirements

- FROM: `### Requirement: Throttled Supabase Synchronization`
- TO: `### Requirement: Throttled Persistent-State Synchronization`

## MODIFIED Requirements

### Requirement: State Layer Separation
The system state MUST remain split into Runtime (`TaskRuntimeState`) and Persistent (local database) layers after Supabase removal.

#### Scenario: Compile runtime metadata remains in runtime layer
- **WHEN** compilation starts or ends
- **THEN** `compile_pid`, `compile_engine`, and `compile_started_at` MUST remain runtime-only state
- **AND** those fields MUST NOT be persisted into terminal history rows in the local database.

### Requirement: Throttled Persistent-State Synchronization
The system SHALL throttle persistent-state writes to the local database while keeping async task or status paths non-blocking.

#### Scenario: Async DB wrapper strategy mode
- **WHEN** async route or service paths issue database operations
- **THEN** execution SHALL use the configured async-safe database wrapper strategy
- **AND** the default mode SHALL remain safe for threaded offload and local development stability.

### Requirement: API Read Strategy
`/api/task/{task_id}` MUST prefer runtime task state before falling back to persisted local database state.

#### Scenario: Frontend polls task progress
- **WHEN** the frontend or another client requests `/api/task/{task_id}`
- **THEN** the backend SHALL first check runtime state for that task id
- **AND** only if runtime state is unavailable MAY it fall back to persisted local database state.

#### Scenario: Runtime state remains the real-time source
- **WHEN** the frontend consumes SSE or polling for live task updates
- **THEN** the real-time source SHALL remain `TaskRuntimeState`
- **AND** the system SHALL NOT reintroduce database change streams as the primary real-time source.

### Requirement: Task State Recovery
System MUST remember user preferences even when tasks are recovered from the local database after a restart.

#### Scenario: Recover task from local persistence retains email preference
- **WHEN** the backend restarts and recovers an active task from the local `translation_tasks` store
- **THEN** it MUST correctly deserialize the `email_notification` flag
- **AND** it MUST restore that value into in-memory task configuration so terminal notifications still work.

### Requirement: Task Status Synchronization
Final task statuses MUST flush immediately to the local persistent store.

#### Scenario: Terminal-state flush bypasses normal throttle
- **WHEN** a task reaches a terminal state such as `completed` or `failed`
- **THEN** the persistent-state flusher MUST dispatch the write immediately to the local database
- **AND** later non-persistence exceptions in the same update flow SHALL NOT suppress that terminal-state write.
