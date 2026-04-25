## MODIFIED Requirements
### Requirement: Admin curation task records page shows retained task history
The admin curation task records page SHALL show retained curation jobs across queued, processing, completed, and failed states.

#### Scenario: Admin reviews retained curation history
- **WHEN** an admin opens the task records page
- **THEN** the page SHALL show curation jobs with status, task identifiers, batch identifiers, timestamps, and error context
- **AND** it SHALL support simple filtering by status plus search by `arXiv ID` or `batch_id`.

#### Scenario: Admin opens a completed curated paper directly from task history
- **WHEN** an admin reviews a completed curation history record that has a published paper target
- **THEN** the task records page SHALL expose a direct read action for that record
- **AND** activating that action SHALL navigate into the normal paper detail reading route for the published paper.
