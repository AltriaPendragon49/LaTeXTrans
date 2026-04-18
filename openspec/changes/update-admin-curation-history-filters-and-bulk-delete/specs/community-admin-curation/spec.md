## MODIFIED Requirements
### Requirement: Admin curation page supports bounded-concurrency batch handling
The admin curation page SHALL support multi-item submission while using bounded parallelism behind the scenes, and the admin history surface SHALL allow durable management of retained task records through accurate status filters and selected-item hard deletion.

#### Scenario: Admin submits a mixed or multi-item batch
- **WHEN** an admin submits multiple items in one curation batch
- **THEN** the system SHALL track each paper separately inside the batch
- **AND** the backend SHALL schedule execution with bounded concurrency to improve throughput without dropping the final publication quality bar.

#### Scenario: Admin filters history records by processing state
- **WHEN** an admin views the curation task history and selects the `processing` filter
- **THEN** the history result SHALL include jobs whose persisted statuses are `processing`, `translating`, or `publishing`
- **AND** the result SHALL exclude `queued`, `completed`, and `failed` jobs unless they also match a different active filter.

#### Scenario: Admin views all history records
- **WHEN** an admin selects the `all` filter on the curation task history page
- **THEN** the history query SHALL not apply a status restriction
- **AND** queued, in-flight, completed, and failed jobs SHALL all remain eligible for display.

#### Scenario: Admin deletes selected history records
- **WHEN** an admin selects one or more currently listed curation history records and confirms batch delete
- **THEN** the system SHALL hard-delete each selected record using the existing per-job deletion rules
- **AND** the response SHALL report which job ids were deleted and which job ids failed deletion so the admin can retry only the remaining items.
