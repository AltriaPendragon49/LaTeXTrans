## MODIFIED Requirements
### Requirement: Admin curation page supports both arXiv and archive intake
The admin curation page SHALL support official community-paper intake through newline-delimited `arXiv ID` entry and TeX-containing archive upload.

#### Scenario: Admin curates by newline-delimited arXiv ids
- **WHEN** an admin pastes one `arXiv ID` per line on the curation page
- **THEN** the page SHALL parse each non-empty line as one intake item
- **AND** it SHALL submit the parsed items into the community curation pipeline
- **AND** the UI SHALL show the parsed item count before submission.

#### Scenario: Admin curates by archive upload
- **WHEN** an admin uploads a TeX-containing archive on the curation page
- **THEN** the page SHALL submit that archive into the same community curation pipeline
- **AND** the UI SHALL show tracked progress for that item.

### Requirement: Admin curation page supports bounded-concurrency batch handling
The admin curation page SHALL support very large multi-item submission while using bounded parallelism behind the scenes.

#### Scenario: Admin submits a large arXiv batch
- **WHEN** an admin submits many newline-delimited `arXiv ID`s in one curation batch
- **THEN** the system SHALL track each paper separately inside the batch
- **AND** the backend SHALL schedule execution with bounded concurrency to improve throughput without dropping the final publication quality bar.

#### Scenario: Admin submits a mixed or multi-item batch
- **WHEN** an admin submits multiple items in one curation batch
- **THEN** the UI SHALL keep batch-level progress tracking
- **AND** individual item failure SHALL not stop the remaining queued items from continuing.

## ADDED Requirements
### Requirement: Admin curation task records page is visible only to local admins
The product SHALL expose an admin-only curation task records page for managing retained curation history.

#### Scenario: Admin opens the task records page
- **WHEN** an authenticated user with the local `admin` role renders the shared shell
- **THEN** the shell SHALL show a navigation entry for the admin curation task records page
- **AND** visiting that page SHALL be allowed for that user.

#### Scenario: Non-admin user opens the shared shell
- **WHEN** an authenticated user without the local `admin` role renders the shared shell
- **THEN** the task records navigation entry SHALL be hidden
- **AND** the corresponding page route SHALL not be available as a normal product action.

### Requirement: Admin curation task records page shows retained task history
The admin curation task records page SHALL show retained curation jobs across queued, processing, completed, and failed states.

#### Scenario: Admin reviews retained curation history
- **WHEN** an admin opens the task records page
- **THEN** the page SHALL show curation jobs with status, task identifiers, batch identifiers, timestamps, and error context
- **AND** it SHALL support simple filtering by status plus search by `arXiv ID` or `batch_id`.

### Requirement: Admin curation task records page supports permanent delete management
The admin curation task records page SHALL allow admins to permanently delete failed or completed curation records.

#### Scenario: Admin permanently deletes a failed curation record
- **WHEN** an admin confirms deletion for a failed curation job
- **THEN** the system SHALL permanently remove the retained curation-job row, retained translation-task row, and retained failed artifacts for that job.

#### Scenario: Admin permanently deletes a completed curation record
- **WHEN** an admin confirms deletion for a completed curation job that published a paper
- **THEN** the system SHALL reuse the existing admin hard-delete flow for the published paper and its assets
- **AND** it SHALL also remove the linked curation-job history row.
