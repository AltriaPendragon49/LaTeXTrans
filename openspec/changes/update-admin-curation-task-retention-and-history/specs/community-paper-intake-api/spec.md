## RENAMED Requirements
- FROM: `### Requirement: Failed admin curation jobs are terminal and self-cleaning`
- TO: `### Requirement: Failed admin curation jobs are terminal and operator-retained`

## MODIFIED Requirements
### Requirement: Batch curation submission supports bounded concurrency
The admin curation intake path SHALL accept both arbitrarily large `arXiv ID` batches and multiple archive uploads and SHALL process them through a bounded-concurrency queue.

#### Scenario: Batch includes many arXiv ids
- **WHEN** an admin submits a large batch of `arXiv ID`s in one curation request
- **THEN** the system SHALL create one tracked curation item per submitted ID with per-item states
- **AND** it SHALL persist those items before execution starts
- **AND** it SHALL process items with configured bounded parallelism instead of unlimited fan-out.

#### Scenario: Batch includes multiple archive uploads
- **WHEN** an admin uploads multiple archive files in one curation batch
- **THEN** the system SHALL track each archive as its own curation item
- **AND** the system SHALL schedule those items through the same bounded-concurrency queue used for arXiv batches.

#### Scenario: One batch item fails while others continue
- **WHEN** one paper in a curation batch fails
- **THEN** the other batch items SHALL continue independently
- **AND** publication readiness SHALL still be decided per paper instead of treating the whole batch as failed.

### Requirement: Failed admin curation jobs are terminal and operator-retained
The admin curation intake pipeline SHALL treat failed or timed-out curation items as terminal failures, SHALL not automatically requeue them, and SHALL retain failed task evidence for later operator analysis.

#### Scenario: Translation task fails during admin curation
- **WHEN** an admin curation item reaches a failed terminal translation state
- **THEN** the curation job SHALL be marked `failed`
- **AND** the system SHALL not automatically restart or requeue that curation job
- **AND** the system SHALL preserve the related `translation_tasks` row
- **AND** the system SHALL retain failed task artifacts under the configured `failed_tasks/{task_id}` namespace
- **AND** the failed curation job row SHALL remain available so an admin can inspect the error and decide whether to delete it manually.

#### Scenario: Admin curation times out while waiting for translation
- **WHEN** the admin curation worker waits 15 minutes for a translation task and the task is still not terminal
- **THEN** the system SHALL mark the curation job `failed`
- **AND** it SHALL cancel that curation task before marking the retained failure when cancellation is still applicable
- **AND** it SHALL require a new operator action for any retry.

#### Scenario: Failed curation created only a private placeholder paper
- **WHEN** a failed curation run created a private `curating` paper and related rows during publication preparation
- **THEN** the system SHALL delete that placeholder paper and its paper-scoped local rows
- **AND** it SHALL not delete an already-published canonical paper that existed before the failed curation attempt.

## ADDED Requirements
### Requirement: Admin curation job history is independent from public paper visibility
The system SHALL keep admin curation job history queryable even when the corresponding paper is absent from public feed surfaces.

#### Scenario: Failed curation job has no public paper
- **WHEN** an admin curation item fails before public publication
- **THEN** the curation job SHALL remain queryable in admin history
- **AND** the failed item SHALL remain absent from the public community feed.

#### Scenario: Completed curation job publishes successfully
- **WHEN** an admin curation item completes publication successfully
- **THEN** the curation job SHALL remain queryable in admin history
- **AND** the public community feed SHALL still be driven by the published paper record rather than the history row itself.
