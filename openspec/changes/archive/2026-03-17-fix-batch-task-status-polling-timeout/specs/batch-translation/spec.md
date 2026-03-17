## ADDED Requirements
### Requirement: Batch Task Status Synchronization
The batch translation dashboard MUST keep each visible batch task synchronized with backend task status until that task reaches a terminal state or the batch view is unmounted.

#### Scenario: Long-running batch task outlasts the original polling window
- **WHEN** a batch task remains queued, processing, or compiling for longer than the frontend's previous fixed polling window
- **AND** the backend later marks that task as `completed`, `completed_with_warnings`, `failed`, `failed_compilation`, or `structure_invalid`
- **THEN** the batch task card MUST continue polling and eventually display the terminal backend status
- **AND** the card MUST NOT remain stuck on a stale pre-terminal status such as compile preparation.

#### Scenario: Duplicate polling attempts target the same batch task
- **WHEN** the batch UI rerenders or task submission logic re-invokes status tracking for an already-polled task
- **THEN** the frontend MUST ensure only one active poller exists for that batch task
- **AND** duplicate polling attempts MUST NOT create parallel status request loops for the same task.

#### Scenario: Initial lifecycle replay occurs before polling begins
- **WHEN** the batch translation view experiences a transient mount-cleanup-remount replay before the user-visible polling lifecycle begins
- **THEN** the frontend MUST still start polling active batch tasks once the live view is mounted
- **AND** the task cards MUST continue progressing toward the backend terminal status instead of remaining stuck at their initial waiting state.

#### Scenario: Batch view unmounts while tasks are still active
- **WHEN** the batch translation component unmounts before one or more batch tasks reach terminal state
- **THEN** the frontend MAY stop polling those tasks
- **AND** it MUST release any local polling bookkeeping associated with the unmounted view.
