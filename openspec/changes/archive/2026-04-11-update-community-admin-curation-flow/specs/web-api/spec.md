## ADDED Requirements
### Requirement: Admin curation API supports single and batch community intake
The backend SHALL expose admin-only API contracts for community curation intake via both `arXiv ID` submission and archive upload, including batch submission support and per-item status tracking.

#### Scenario: Admin submits one or more arXiv ids for community curation
- **WHEN** an authenticated local admin submits one or more `arXiv ID`s to the admin curation API
- **THEN** the API SHALL accept the submission as a tracked curation job or batch
- **AND** it SHALL return enough per-item identifiers or status metadata for the admin UI to monitor progress.

#### Scenario: Admin uploads one or more archives for community curation
- **WHEN** an authenticated local admin uploads one or more TeX-containing archives to the admin curation API
- **THEN** the API SHALL accept the upload as a tracked curation job or batch
- **AND** it SHALL preserve per-item status reporting across metadata extraction, translation, structured insight generation, and publication.

### Requirement: Admin curation APIs require local admin role
The backend SHALL require the current local admin role for community curation write actions.

#### Scenario: Non-admin requests admin curation write API
- **WHEN** an authenticated non-admin user calls an admin curation write endpoint
- **THEN** the API SHALL reject the request with a forbidden response
- **AND** it SHALL not start the curation pipeline.

### Requirement: Admin paper deletion API hard-deletes community papers
The backend SHALL expose an admin-only community-paper deletion API that immediately removes the paper from public product surfaces and then completes a persistent asynchronous hard delete across local database rows, local filesystem assets, caches, and search/index artifacts.

#### Scenario: Admin deletes a community paper
- **WHEN** an authenticated local admin calls the community-paper delete API for an existing paper
- **THEN** the backend SHALL make that paper immediately unavailable to homepage feed, search, and detail reads
- **AND** it SHALL persist a background delete job that removes the paper row, related paper-facing local rows, structured insights, corresponding community asset directories, derived preview/translation/source artifacts, and related cache/index entries
- **AND** subsequent community reads for that paper SHALL fail as a missing paper.

#### Scenario: A hard-delete cleanup step fails
- **WHEN** a persisted community-paper hard-delete job encounters a cleanup failure
- **THEN** the system SHALL keep retrying that delete job automatically until cleanup completes
- **AND** it SHALL not restore the paper to public visibility while retries continue.

#### Scenario: Service restarts during hard delete
- **WHEN** the service restarts while a community-paper hard-delete job is unfinished
- **THEN** startup reconciliation SHALL resume the persisted delete job
- **AND** retries SHALL continue until the hard delete completes.

### Requirement: Hidden community-agent mode blocks direct product access
The backend SHALL reject direct product access to community-agent routes while the current product mode keeps the public agent surface hidden.

#### Scenario: Authenticated user calls community-agent run APIs in hidden mode
- **WHEN** an authenticated user, including an admin, calls the community-agent product APIs while hidden mode is active
- **THEN** the API SHALL reject the request instead of starting a visible product agent run
- **AND** the hidden-mode contract SHALL still preserve the underlying code assets for future restoration.
