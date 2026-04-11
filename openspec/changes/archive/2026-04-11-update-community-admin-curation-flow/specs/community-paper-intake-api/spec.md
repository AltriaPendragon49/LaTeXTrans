## ADDED Requirements
### Requirement: Community admission is admin-curated and complete-only
The system SHALL admit newly visible community papers only through the admin curation flow, and those papers SHALL become publicly visible only after the full curation pipeline succeeds.

#### Scenario: Admin curation run succeeds fully
- **WHEN** an authenticated admin submits a paper through the admin curation flow
- **AND** intake, metadata preparation, translation, and structured insight generation all succeed
- **THEN** the system SHALL create or reuse one canonical community paper record
- **AND** it SHALL publish that paper as visible community content only after that full success state is reached.

#### Scenario: Ordinary tool translation succeeds
- **WHEN** a non-admin user completes a translation through the direct tools workflow
- **THEN** the system SHALL keep that result outside the visible community feed by default
- **AND** it SHALL not create a new public community paper solely because the tool translation succeeded.

#### Scenario: Curation pipeline is incomplete or fails
- **WHEN** a curation run has not yet completed all required stages or ends in failure
- **THEN** the corresponding paper SHALL remain absent from the public community feed
- **AND** users SHALL not see a half-finished public community paper card for that run.

### Requirement: Canonical community paper identity is stable across repeated curation
The system SHALL assign each canonical community paper one immutable internal `paper_id`, and repeated curation for the same canonical paper SHALL reuse that `paper_id` instead of creating a new public paper record.

#### Scenario: Repeat arXiv curation targets an existing canonical paper
- **WHEN** an admin re-curates a paper whose `arXiv ID` already maps to an existing canonical community paper
- **THEN** the system SHALL reuse that existing `paper_id`
- **AND** the latest successful curation output SHALL overwrite the prior published community-facing content for that same paper.

#### Scenario: Archive intake later resolves to an existing canonical paper
- **WHEN** archive-based curation is determined to match an already-known canonical community paper
- **THEN** the system SHALL reuse the existing `paper_id`
- **AND** the latest successful curation output SHALL replace the prior published community-facing content for that same paper.

#### Scenario: Canonical paper id has already been assigned
- **WHEN** a canonical community paper already exists
- **THEN** its `paper_id` SHALL remain unchanged across later curation updates
- **AND** repeated curation SHALL update the paper in place instead of generating a new public identity.

### Requirement: Archive-based admin intake extracts feed metadata
The admin curation intake path SHALL extract enough metadata from TeX-containing archives to support the same paper-card presentation shape expected from arXiv-based curation.

#### Scenario: Admin uploads a TeX-containing archive
- **WHEN** an authenticated admin submits an archive intake that contains TeX sources
- **THEN** the intake pipeline SHALL extract or derive a title and abstract before publication
- **AND** the resulting community feed card SHALL be able to render those fields like an arXiv-curated paper.

### Requirement: Batch curation submission supports bounded concurrency
The admin curation intake path SHALL accept both multiple `arXiv ID`s and multiple archive uploads and SHALL process them through a bounded-concurrency queue.

#### Scenario: Batch includes multiple arXiv ids
- **WHEN** an admin submits multiple `arXiv ID`s in one curation batch
- **THEN** the system SHALL create one tracked batch submission with per-item states
- **AND** it SHALL process items with configured bounded parallelism instead of unlimited fan-out.

#### Scenario: Batch includes multiple archive uploads
- **WHEN** an admin uploads multiple archive files in one curation batch
- **THEN** the system SHALL track each archive as its own curation item
- **AND** the system SHALL schedule those items through the same bounded-concurrency queue used for arXiv batches.

#### Scenario: One batch item fails while others continue
- **WHEN** one paper in a curation batch fails
- **THEN** the other batch items SHALL continue independently
- **AND** publication readiness SHALL still be decided per paper instead of treating the whole batch as failed.

## REMOVED Requirements
### Requirement: Community admission is official-first
**Reason**: Public community admission is no longer a mixed normal-user/admin submission path; it is now admin-curated and complete-only.
**Migration**: Official-vs-fallback ranking is replaced by the rule that newly published community papers are admitted only through the admin curation flow.

### Requirement: Unified paper submit API
**Reason**: Silent public community intake from discovery or public agent flows is no longer the default community-publication contract.
**Migration**: Admin curation becomes the formal publication path for new visible community papers, while ordinary tool workflows remain outside public community publication.
