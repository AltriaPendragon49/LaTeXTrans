## ADDED Requirements
### Requirement: Reusable paper source export modes
The repository SHALL provide one export workflow that supports hot-paper and new-paper source modes through a shared script entrypoint.

#### Scenario: Export hot top papers
- **WHEN** an operator runs the export script in `hot-top-n` mode
- **THEN** the script SHALL read alphaXiv hot-feed data
- **AND** the default hot interval for that mode SHALL be `All time`
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

#### Scenario: Export an evergreen core paper pool
- **WHEN** an operator runs the export script in `core-pool` mode
- **THEN** the script SHALL build candidates from multiple long-window public signals rather than one momentum feed
- **AND** it SHALL export a bounded high-value paper subset intended for pretranslation.

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

#### Scenario: Scheduled exports refresh the latest source view
- **WHEN** the operator reruns the same source mode on the server
- **THEN** the script SHALL overwrite that source directory's `latest.json` and `latest.md`
- **AND** the artifacts SHALL reflect only the newest export results for that source mode.

#### Scenario: Core pool artifacts live alongside daily feeds
- **WHEN** the operator runs the `core-pool` export
- **THEN** the script SHALL write the latest artifacts under `backend/arxiv_id/core_pool/`
- **AND** missing directories SHALL not block the export.

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

### Requirement: Core pool selection balances real distribution with minimum representation
The core paper pool SHALL approximate the real research-category distribution while still preserving a minimum representation for lower-volume fields.

#### Scenario: Core pool quotas are allocated
- **WHEN** the script builds the `core-pool`
- **THEN** it SHALL use an arXiv-led category distribution as the primary quota baseline
- **AND** it SHALL allow auxiliary platform data to adjust that allocation
- **AND** it SHALL enforce a minimum floor of 50 papers per included major category.

#### Scenario: Very recent papers are not used as evergreen seed content
- **WHEN** the script builds the `core-pool`
- **THEN** it SHALL exclude papers inside the configured recent-paper cutoff from the evergreen pool
- **AND** those papers SHALL remain eligible for the daily `hot` and `new` workflows instead.
