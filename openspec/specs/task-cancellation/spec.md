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

