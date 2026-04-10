## MODIFIED Requirements

### Requirement: Batch Translation Persistence Retry
The system SHALL retry failed authenticated batch-task persistence against the local database and degrade gracefully if persistence still cannot be completed.

#### Scenario: First persistence attempt fails and background retry starts
- **WHEN** the batch translation flow calls `persist_task_if_needed()` and the local database write fails
- **THEN** the system SHALL start a background retry flow for that persistence attempt
- **AND** the HTTP response for accepted batch work SHALL remain non-blocking.

#### Scenario: Retry later succeeds
- **WHEN** the background retry succeeds within the configured retry budget
- **THEN** the task SHALL become visible in authenticated history
- **AND** later history queries SHALL use the successfully persisted local row.

#### Scenario: All retries fail and task degrades gracefully
- **WHEN** every bounded persistence retry attempt fails
- **THEN** the system SHALL mark the task as persistence-failed in runtime state
- **AND** translation execution SHALL continue instead of being aborted solely by persistence failure
- **AND** the frontend SHALL warn the user that the task was not saved into authenticated history.

#### Scenario: Deferred persistence keeps config hash for output reuse
- **WHEN** an authenticated batch-created task computes its `config_hash` before the first successful local database insert
- **THEN** the eventual successful persistence attempt MUST keep that `config_hash`
- **AND** later matching requests MUST remain eligible for output reuse.
