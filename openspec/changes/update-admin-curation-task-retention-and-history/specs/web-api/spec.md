## ADDED Requirements
### Requirement: Admin curation history API lists retained curation jobs
The backend SHALL expose an admin-only API for querying retained admin curation jobs independent of public paper visibility.

#### Scenario: Admin lists retained curation jobs
- **WHEN** an authenticated local admin requests the admin curation history API
- **THEN** the API SHALL return retained curation jobs across queued, processing, completed, and failed states
- **AND** each item SHALL include identifiers such as `job_id`, `batch_id`, `task_id`, `paper_id`, status fields, timestamps, and error context.

#### Scenario: Admin filters retained curation jobs
- **WHEN** an authenticated local admin requests the admin curation history API with a status filter or simple search value
- **THEN** the API SHALL support filtering by curation status
- **AND** it SHALL support simple search by `arXiv ID` or `batch_id`.

#### Scenario: Non-admin requests retained curation history
- **WHEN** an authenticated non-admin user requests the admin curation history API
- **THEN** the API SHALL reject the request with a forbidden response
- **AND** it SHALL not disclose retained curation job metadata.

### Requirement: Admin curation job delete API hard-deletes retained records
The backend SHALL expose an admin-only API that permanently deletes failed or completed admin curation records and their retained artifacts.

#### Scenario: Admin deletes a failed retained curation record
- **WHEN** an authenticated local admin calls the curation-job delete API for a failed retained job
- **THEN** the backend SHALL permanently delete the curation-job row, retained translation-task row, and retained failed-task artifacts for that job
- **AND** subsequent admin history reads for that job SHALL fail as missing.

#### Scenario: Admin deletes a completed retained curation record
- **WHEN** an authenticated local admin calls the curation-job delete API for a completed job that published a paper
- **THEN** the backend SHALL reuse the existing admin community-paper hard-delete flow for the published paper and its assets
- **AND** it SHALL also permanently delete the linked curation-job history row.

#### Scenario: Non-admin requests curation-job hard delete
- **WHEN** an authenticated non-admin user calls the curation-job delete API
- **THEN** the API SHALL reject the request with a forbidden response
- **AND** it SHALL not start any delete workflow.
