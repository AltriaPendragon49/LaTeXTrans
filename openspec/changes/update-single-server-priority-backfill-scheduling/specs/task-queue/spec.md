## MODIFIED Requirements
### Requirement: Translation Task Queue
The system SHALL manage translation tasks with priority-aware FIFO lanes on a single-machine scheduler, limiting total active translation slots while allowing backfill work to borrow idle interactive capacity.

#### Scenario: Interactive task admission
- **WHEN** a user submits an interactive translation request
- **THEN** the system enqueues that task into the interactive lane
- **AND** the task remains eligible ahead of waiting backfill work.

#### Scenario: Backfill task admission
- **WHEN** the system submits an internal backfill translation
- **THEN** the system enqueues that task into the backfill lane
- **AND** backfill ordering remains FIFO within the backfill lane.

#### Scenario: Idle capacity is borrowed by backfill
- **WHEN** no interactive task is waiting
- **AND** a translation slot would otherwise remain idle
- **THEN** the scheduler MAY start or resume a backfill task in that slot.

#### Scenario: Recent frontend traffic defers new backfill starts
- **WHEN** the worker runtime has observed recent frontend pressure from the web runtime
- **AND** only backfill tasks are waiting for admission
- **THEN** the scheduler MUST defer starting a new backfill task until the pressure window expires or new capacity becomes explicitly available to backfill
- **AND** this deferral MUST NOT block already-waiting interactive work.

#### Scenario: Interactive work claims the next eligible slot
- **WHEN** at least one backfill task is running
- **AND** a new interactive task arrives while all translation slots are occupied
- **THEN** the scheduler MUST reserve the next eligible safe-interrupt slot for the interactive task
- **AND** MUST NOT abruptly terminate an in-flight backfill LLM call or compile subprocess
- **AND** interactive priority is satisfied at the next cooperative checkpoint rather than after the entire backfill paper finishes.

#### Scenario: Task completion or yield releases resources
- **WHEN** a running task completes, fails, or yields a slot at an approved checkpoint
- **THEN** the scheduler releases the active slot
- **AND** the highest-priority waiting task that is eligible to run starts next.

### Requirement: Task terminal state remains monotonic within one execution attempt
The system SHALL prevent same-attempt stale updates from regressing a task from terminal back to non-terminal state.

#### Scenario: Late progress callback arrives after completion
- **WHEN** a translation attempt has already written a terminal task state
- **AND** a delayed progress or message update from that same attempt arrives later
- **THEN** the system MUST ignore the stale non-terminal regression
- **AND** MUST keep the existing terminal `status` and `completed_at`.

#### Scenario: Fresh retry starts a new execution attempt
- **WHEN** the scheduler or operator intentionally retries a previously terminal task
- **THEN** the system MUST create a fresh execution attempt boundary before accepting new non-terminal progress updates
- **AND** MAY clear stale terminal markers only for that fresh attempt.

### Requirement: Impossible persistent task states are reconciled before they can block operators
The system SHALL treat contradictory durable task rows as recoverable failures instead of leaving them non-terminal.

#### Scenario: Persistent row has completed timestamp but non-terminal status
- **WHEN** durable task state shows a non-terminal `status`
- **AND** `completed_at` is already populated
- **THEN** the system MUST reconcile that task into an explicit terminal failure state
- **AND** MUST record a recovery-oriented message instead of leaving the task indefinitely active.

#### Scenario: Admin curation waits across memory loss or runtime split
- **WHEN** admin curation waits for a translation task to reach terminal state
- **AND** the in-memory task snapshot is missing or stale
- **THEN** the wait path MUST fall back to durable `translation_tasks` state
- **AND** MUST NOT remain blocked forever on an already-terminal or already-reconciled task.

### Requirement: Queue Status API
The system SHALL expose lane-aware queue status without breaking existing aggregate queue-status consumers.

#### Scenario: Query queue status
- **WHEN** a client requests `GET /api/queue/status`
- **THEN** the response MUST still include aggregate active, waiting, and max-concurrency values
- **AND** MAY additionally include `interactive_active`, `interactive_waiting`, `backfill_active`, `backfill_waiting`, and `borrowed_slots`
- **AND** authenticated callers continue to receive current quota usage.

## ADDED Requirements
### Requirement: Cooperative Backfill Yield And Resume
Backfill tasks SHALL yield only at scheduler-approved interruptible boundaries and SHALL resume from the last durable checkpoint when capacity becomes available again.

#### Scenario: Backfill yields at a safe checkpoint
- **WHEN** the scheduler has issued a yield request for a running backfill task
- **AND** the task reaches a safe boundary such as parse completion, section-batch flush, validation-round completion, pre-compile boundary, or post-compile boundary
- **THEN** the task MUST persist checkpoint metadata
- **AND** transition to a yielded/waiting state without losing completed work.

#### Scenario: Yield request arrives during an unsafe step
- **WHEN** a yield request arrives while a backfill task is inside an LLM request or compile subprocess
- **THEN** the task MUST finish or fail that step before yielding
- **AND** MUST NOT interrupt the step mid-flight.

#### Scenario: Backfill reclaims idle capacity after interactive drain
- **WHEN** interactive demand drops and a yielded backfill checkpoint is available
- **THEN** the scheduler MAY resume the yielded task before starting newer backfill work
- **AND** resumption MUST continue from the last durable checkpoint rather than restarting the paper.
