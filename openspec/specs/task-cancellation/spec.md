# task-cancellation Specification

## Purpose
TBD - created by archiving change isolate-token-queues. Update Purpose after archive.
## Requirements
### Requirement: Absolute Execution Termination
Direct forceful thread execution termination (`asyncio.Task.cancel()`) MUST occur explicitly whenever a processing queue item translation is completely canceled or expunged by authoritative commands, halting the process inherently instead of allowing phantom runtime token deductions post-termination relying merely on status flags.

#### Scenario: Compilation cancellation tears down subprocess tree
- **WHEN** cancellation occurs while compilation subprocess is running
- **THEN** runtime cancellation handling MUST terminate process-group/tree for the compile PID
- **AND** MUST await subprocess completion before releasing compile slot/state.

#### Scenario: Cancellation cleanup clears runtime compile metadata
- **WHEN** cancellation or timeout cleanup finishes
- **THEN** in-memory runtime fields `compile_pid`, `compile_engine`, `compile_started_at` MUST be cleared.

### Requirement: Purge Task Configurations During Deletion
File system remnants capturing detailed historical configuration states (namely JSON log traces) MUST be actively scrubbed alongside broader output directories whenever a complete task record obliteration directive performs locally.

#### Scenario: Executing full deletion of task remnants
- **Given** a successfully completed translation task possessing generated configuration diagnostic files under `backend/data/task_configs/`.
- **When** a `delete_task_full` command executes against this specific task ID.
- **Then** the file system deletes the JSON configuration snapshots securely without orphaned residues.
- **And** legacy configuration captures generated earlier inclusive of sequences inside `backend/data/task_configs/{taskId}.json` suffer permanent local removal seamlessly alongside task outputs.

### Requirement: Task status APIs expose stable terminal reasons
The backend task-status API surfaces SHALL expose stable machine-readable terminal reasons for failed or interrupted translation tasks without forcing operators to parse free-form log text.

#### Scenario: Translation task status includes terminal reason
- **WHEN** `GET /api/task/{task_id}` returns a translation task in a terminal failure or interrupted state caused by remedial-budget exhaustion, timeout, cancellation, or fatal upstream-provider error
- **THEN** the response MUST include a stable machine-readable `terminal_reason` field
- **AND** the existing human-readable `message` or `error` text MAY remain supplemental.

#### Scenario: Active task status does not fake terminal reason
- **WHEN** `GET /api/task/{task_id}` returns a task that is still non-terminal
- **THEN** the response MUST NOT claim a terminal reason for the task
- **AND** intermediate progress messaging MUST remain compatible with existing clients.

### Requirement: Admin curation status APIs expose timeout domain and terminal reasons
The backend admin-curation status surfaces SHALL expose machine-readable failure reasons that distinguish admission-stage timeout, execution-stage timeout, retry-budget exhaustion, and fatal upstream-provider failure.

#### Scenario: Admin curation status distinguishes timeout domains
- **WHEN** an admin client reads curation-job status after a timeout failure
- **THEN** the returned payload MUST expose a stable machine-readable reason that distinguishes `admission_timeout` from `execution_timeout`
- **AND** operators MUST NOT need to infer the timeout domain from elapsed wall-clock text alone.

#### Scenario: Admin curation status surfaces translation terminal reason
- **WHEN** the underlying translation task ends because of remedial-budget exhaustion or fatal upstream-provider failure
- **THEN** the curation status payload MUST expose the corresponding stable machine-readable terminal reason for that job
- **AND** the admin UI MUST be able to render the failure class without parsing backend logs.

