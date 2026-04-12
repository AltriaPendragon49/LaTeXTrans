## ADDED Requirements
### Requirement: Failed admin curation jobs are terminal and self-cleaning
The admin curation intake pipeline SHALL treat failed or timed-out curation items as terminal failures, SHALL not automatically requeue them, and SHALL clean up partial artifacts created by that failed run while preserving the failed job record for operators.

#### Scenario: Translation task fails during admin curation
- **WHEN** an admin curation item reaches a failed terminal translation state
- **THEN** the curation job SHALL be marked `failed`
- **AND** the system SHALL not automatically restart or requeue that curation job
- **AND** the system SHALL delete task-specific translation records and local task artifacts created for that failed run
- **AND** the failed curation job row SHALL remain available so an admin can inspect the error and decide whether to retry manually.

#### Scenario: Admin curation times out while waiting for translation
- **WHEN** the admin curation worker waits 15 minutes for a translation task and the task is still not terminal
- **THEN** the system SHALL mark the curation job `failed`
- **AND** it SHALL cancel that curation task before cleanup when cancellation is still applicable
- **AND** it SHALL require a new operator action for any retry.

#### Scenario: Failed curation created only a private placeholder paper
- **WHEN** a failed curation run created a private `curating` paper and related rows during publication preparation
- **THEN** the system SHALL delete that placeholder paper and its paper-scoped local rows
- **AND** it SHALL not delete an already-published canonical paper that existed before the failed curation attempt.
