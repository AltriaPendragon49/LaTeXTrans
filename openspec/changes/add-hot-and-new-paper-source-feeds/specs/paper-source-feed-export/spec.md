## ADDED Requirements
### Requirement: Reusable paper source export modes
The repository SHALL provide one export workflow that supports hot-paper and new-paper source modes through a shared script entrypoint.

#### Scenario: Export hot top papers
- **WHEN** an operator runs the export script in `hot-top-n` mode
- **THEN** the script SHALL read alphaXiv hot-feed data
- **AND** it SHALL return the requested number of valid unique paper records in feed order.

#### Scenario: Export hot papers from the last 24 hours
- **WHEN** an operator runs the export script in `hot-new-24h` mode
- **THEN** the script SHALL read alphaXiv hot-feed data
- **AND** it SHALL filter records using the configured hot freshness field
- **AND** it SHALL export only valid unique records that satisfy the last-24-hours window.

#### Scenario: Export newly submitted arXiv papers
- **WHEN** an operator runs the export script in `new-24h` mode
- **THEN** the script SHALL query arXiv by submitted date
- **AND** it SHALL export the valid unique papers submitted in the last 24 hours.

### Requirement: Server-ready source artifact layout
The export workflow SHALL write source artifacts into the repository's server-oriented `backend/arxiv_id/` directory tree.

#### Scenario: Missing source directories do not block export
- **WHEN** a target source directory under `backend/arxiv_id/` does not yet exist
- **THEN** the script SHALL create the required directory path automatically
- **AND** it SHALL still produce the configured export artifacts.

#### Scenario: Structured and human-readable artifacts are both written
- **WHEN** an export run succeeds
- **THEN** the script SHALL write a machine-readable JSON artifact
- **AND** it SHALL write a human-readable Markdown artifact
- **AND** both artifacts SHALL describe the same exported paper set.

### Requirement: Global paper identity and source priority
The source export workflow SHALL treat `arxiv_id` as the canonical paper identity and SHALL preserve priority rules between `hot` and `new` sources.

#### Scenario: Same paper appears in hot after appearing in new
- **WHEN** a paper already discovered or translated from `new` later appears in a `hot` export
- **THEN** downstream workflows SHALL be able to treat that `hot` record as the preferred display or ranking source
- **AND** the workflow SHALL not require a second translation solely because the higher-priority source changed.

#### Scenario: Invalid or non-paper source ids are encountered
- **WHEN** upstream source data contains malformed IDs or non-primary paper routes
- **THEN** the script SHALL exclude those records from the exported paper set
- **AND** it SHALL continue exporting the remaining valid records.
