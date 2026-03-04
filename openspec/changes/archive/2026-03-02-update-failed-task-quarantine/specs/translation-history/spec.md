## MODIFIED Requirements

### Requirement: History Page Display
The system SHALL provide a history page that shows translation tasks currently visible to the user.  
Failed tasks that were automatically quarantined and deleted from `translation_tasks` SHALL NOT appear in history results.

#### Scenario: View History Records
- **WHEN** the user requests the history page (`/history` or `GET /api/history`)
- **THEN** the system returns the visible task list with key metadata (task id, languages, status, timestamps)

#### Scenario: Download Historical Result
- **WHEN** the user selects a completed task from history
- **THEN** the system provides the corresponding translated output artifact (for example PDF or source package)

#### Scenario: Auto-Removed Failed Tasks Are Hidden
- **WHEN** a task reaches terminal status `failed` or `failed_compilation`
- **AND** the backend failure-interception flow deletes the row from `translation_tasks`
- **THEN** `GET /api/history` SHALL NOT return that task

#### Scenario: Cancelled Tasks Do Not Trigger Auto-Removal
- **WHEN** a task transitions to failed state due to explicit user cancellation
- **THEN** failure-interception auto-removal SHALL NOT be triggered by quarantine logic
- **AND** history retention behavior for cancelled tasks remains governed by existing policy
