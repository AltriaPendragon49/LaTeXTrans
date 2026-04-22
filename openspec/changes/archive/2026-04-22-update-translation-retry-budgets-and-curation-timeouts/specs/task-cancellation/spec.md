## ADDED Requirements

### Requirement: Cancellation and timeout cleanup produce terminal persisted state
Cancellation, timeout, and budget-exhaustion cleanup SHALL reconcile runtime execution with persisted task state so abandoned translation runs cannot remain marked as active.

#### Scenario: Running translation is cancelled by administrative timeout handling
- **WHEN** timeout or administrative cleanup cancels a translation that has already entered active runtime execution
- **THEN** the persisted translation task MUST transition to a terminal interrupted or failed state with machine-readable reason
- **AND** the live backend execution for that run MUST be actively terminated
- **AND** it MUST NOT remain in `processing` after runtime execution has stopped.

#### Scenario: Queued translation is abandoned before execution starts
- **WHEN** administrative timeout handling abandons a translation before the worker starts active execution
- **THEN** the persisted task MUST transition to a terminal skipped, interrupted, or failed state according to the configured policy
- **AND** later queue reconciliation MUST NOT resurrect it as an active `processing` task.

#### Scenario: Budget exhaustion ends remedial execution
- **WHEN** a translation run stops because a remedial budget or hard timeout is exhausted
- **THEN** the cleanup path MUST persist the corresponding terminal reason on the task record
- **AND** if the system handles that stop through cancellation, it MUST actively terminate the live backend execution for the run
- **AND** downstream status APIs MUST observe that terminal state instead of stale active execution metadata.

#### Scenario: Fatal upstream-provider termination persists terminal state
- **WHEN** a translation run terminates because bounded fatal-provider handling determines the upstream path is non-recoverable
- **THEN** the cleanup path MUST persist the corresponding provider-failure terminal reason on the task record
- **AND** no abandoned runtime execution from that run may remain observable as active `processing`.

#### Scenario: Cancellation is not complete until runtime termination and terminal persistence both succeed
- **WHEN** timeout, budget exhaustion, or equivalent policy decides to cancel a translation run
- **THEN** the system MUST treat the cancellation as incomplete until it has both persisted a terminal task state and issued active termination against the live backend execution
- **AND** it MUST NOT report cancellation success while either half is still missing.

*** Add File: D:\future\antigravity\LaTexTrans\openspec\changes\update-translation-retry-budgets-and-curation-timeouts\specs\web-api\spec.md
## ADDED Requirements

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
