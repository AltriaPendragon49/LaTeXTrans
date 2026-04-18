## ADDED Requirements
### Requirement: Admin curation history batch delete API reports per-job outcomes
The web API SHALL provide an authenticated admin-only batch delete endpoint for curation history records that returns per-job hard-delete outcomes.

#### Scenario: Admin batch delete succeeds for all selected jobs
- **WHEN** an admin submits one or more valid curation job ids to the batch delete endpoint
- **THEN** the API SHALL hard-delete each job using the same logic as the single-delete endpoint
- **AND** the response SHALL include the deleted job ids with a zero failed-count result.

#### Scenario: Admin batch delete partially fails
- **WHEN** at least one submitted curation job id cannot be deleted
- **THEN** the API SHALL continue attempting the remaining submitted job ids
- **AND** the response SHALL include separate success and failure entries so the client can keep failed items selected for retry.
