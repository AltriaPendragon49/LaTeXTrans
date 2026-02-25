# web-api Delta

## ADDED Requirements

### Requirement: Compilation Failure Status Semantics
The API layer SHALL expose compilation-stage failures as explicit terminal task status `failed_compilation` with actionable summaries.

#### Scenario: Coordinator reports compilation failure
- **WHEN** translation orchestration returns compile failure (`status=failed_compilation` or missing compiled PDF)
- **THEN** `/translate` background workflow MUST set task status to `failed_compilation`
- **AND** MUST store readable compile summary in task `error` and `message` fields.

#### Scenario: Orchestrator returns non-existent PDF path
- **WHEN** orchestration returns a non-empty `pdf_path` but the file does not exist on disk
- **THEN** API workflow MUST treat the task as `failed_compilation` (not generic runtime failure)
- **AND** error summary MUST include the missing path for diagnostics.

#### Scenario: Compilation completes with warnings
- **WHEN** orchestration reports `completed_with_warnings`
- **THEN** task status MUST be `completed_with_warnings`
- **AND** warning details MUST be surfaced to clients.

### Requirement: Translated PDF Resolution Safety
Download/preview endpoints SHALL resolve translated PDFs deterministically and MUST avoid selecting copied source PDFs.

#### Scenario: Resolve by task log first
- **WHEN** `task_log.json` contains `compilation_completed` or `compilation_completed_with_warnings` entries with `pdf_path`
- **THEN** resolver MUST prioritize those paths if they exist under the task output root.

#### Scenario: Safe fallback without deep recursion
- **WHEN** no valid task-log PDF path is available
- **THEN** resolver MAY use strict naming-convention fallback only
- **AND** MUST NOT use unrestricted deep recursive PDF search.

#### Scenario: Nested source PDF exists but translated PDF missing
- **WHEN** output tree contains copied source PDF in nested source subdirectory
- **AND** translated PDF is absent
- **THEN** resolver MUST return no translated PDF instead of returning the nested source PDF.

### Requirement: Terminal State Propagation for Streaming and Polling
Task status streaming and polling SHALL treat compilation-specific terminal states consistently.

#### Scenario: SSE terminal status includes compilation outcomes
- **WHEN** task status becomes `completed_with_warnings` or `failed_compilation`
- **THEN** SSE stream MUST emit terminal complete event and close.

#### Scenario: Frontend polling stops on compilation failure
- **WHEN** polling receives `failed_compilation`
- **THEN** client MUST stop polling and render failure UI without "View Result" actions.

### Requirement: Progress UI Feedback for Rate Limits
The task management system SHALL support atomic progress message updates without altering percentage values to accommodate rate-limiting feedback.

#### Scenario: Atomic message-only update
- **WHEN** a progress update is received with `percentage=-1`
- **THEN** the system MUST update only the task's `message` field
- **AND** MUST preserve the last known `progress` and `stage`.

#### Scenario: Deadlock-free task updates
- **WHEN** processing an atomic message update
- **THEN** the system MUST NOT perform re-entrant locking on the task state
- **AND** MUST ensure UI components (like amber-pulse bars) receive the data promptly.

#### Scenario: Rate-limited visual feedback
- **WHEN** a task message contains "rate limited"
- **THEN** frontend components MUST render the progress bar and status text with amber pulsing visual cues
- **AND** MUST display a global warning banner if the task is in the active processing view.

[Checklist: Delta validation]
- [x] -1 percentage logic implemented in TaskManager
- [x] TaskManager deadlock fixed
- [x] Frontend amber-pulse styles applied to TaskList/Processing
- [x] Rate limit warning text includes performance suggestion
