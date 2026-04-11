# community-paper-intake-api Specification

## Purpose
TBD - created by archiving change add-community-day-02-paper-intake-and-feed-api. Update Purpose after archive.
## Requirements
### Requirement: Community feed list contract
The system SHALL expose a stable paper-centric list model for community feed surfaces.

#### Scenario: Official papers sort before fallback papers
- **WHEN** the frontend requests `GET /api/papers`
- **THEN** the system SHALL only return community-visible papers
- **AND** it SHALL rank `official` papers before `user_fallback` papers for each Day 2 sort mode.

#### Scenario: Feed results include stable card metadata
- **WHEN** the frontend requests the papers list
- **THEN** the system SHALL return enough metadata to render paper cards
- **AND** the response SHALL include `community_status`, translation state, counts, and latest asset summary.

### Requirement: Community paper detail contract
The community paper detail contract SHALL distinguish readable English-source state from translated-reader state and SHALL not equate compile failure with total translated unreadability.

#### Scenario: Detail contract exposes best available readable mode
- **WHEN** a public community paper has English HTML, English PDF, translated HTML, or translated PDF artifacts in any healthy or degraded combination
- **THEN** the detail contract SHALL expose the best available readable mode and its fallback options
- **AND** the frontend SHALL not need to infer that state from raw paper status alone.

#### Scenario: Failed task still yields readable artifacts
- **WHEN** a terminal translation task still produced translated preview or translated PDF artifacts
- **THEN** the detail contract SHALL surface those artifacts as readable output
- **AND** the paper SHALL not be represented as fully untranslated just because compile validation failed.

### Requirement: Community paper view tracking
The system SHALL support a dedicated paper view write path without introducing a new analytics table.

#### Scenario: Track paper views without breaking the main read path
- **WHEN** a paper detail page is opened
- **THEN** the system SHALL support `POST /api/papers/{paper_id}/view`
- **AND** it SHALL update the paper view count while keeping feed and detail reads available.

### Requirement: Background content pool admission reuses the same canonical paper rules
The community paper intake layer SHALL allow the background content pool to admit or reuse papers using the same canonical paper model that interactive imports already use.

#### Scenario: Background pool admits a new paper
- **WHEN** the content pool decides to warm a paper that does not yet exist in the community database
- **THEN** the intake layer SHALL create one canonical paper record for that `arxiv_id`
- **AND** later interactive imports SHALL reuse that same paper instead of creating a second record.

#### Scenario: Background pool encounters an existing paper
- **WHEN** the content pool decides to warm a paper that already exists in the community database
- **THEN** the intake layer SHALL reuse the existing canonical paper
- **AND** the content pool SHALL enrich that paper’s assets and readiness state rather than creating a duplicate admission path.

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

