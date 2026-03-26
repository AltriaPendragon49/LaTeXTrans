# community-paper-intake-api Specification

## Purpose
TBD - created by archiving change add-community-day-02-paper-intake-and-feed-api. Update Purpose after archive.
## Requirements
### Requirement: Community admission is official-first
The system SHALL treat community papers as curated content, with official translations taking priority and user translations filling gaps only when no official community version exists.

#### Scenario: Normal user creates a fallback arXiv paper
- **WHEN** an authenticated non-admin user submits an `arxiv_id`
- **AND** no community paper exists for that `arxiv_id`
- **THEN** the system SHALL create one canonical `paper` record
- **AND** it SHALL mark the paper as `user_fallback`.

#### Scenario: Normal user reuses an official arXiv paper
- **WHEN** an authenticated non-admin user submits an `arxiv_id`
- **AND** a community paper already exists for that `arxiv_id` with `community_status = official`
- **THEN** the system SHALL reuse the existing official paper
- **AND** it SHALL not create a second community paper row.

#### Scenario: Official submission overrides fallback visibility
- **WHEN** an authenticated admin or moderator submits an `arxiv_id`
- **AND** a fallback paper already exists for that `arxiv_id`
- **THEN** the system SHALL update the existing paper into an official community paper
- **AND** subsequent community feed and detail reads SHALL default to the official selection.

### Requirement: Unified paper submit API
The community paper intake layer SHALL support silent import/reuse for arXiv papers so the community flow can create readable English paper pages without an extra confirmation step.

#### Scenario: Import an arXiv paper into the community flow
- **WHEN** the system needs to bring an arXiv paper into the community as part of discovery, agent conversation, or detail-flow translation
- **THEN** the intake layer SHALL reuse an existing community paper when possible or create a new one when needed
- **AND** the resulting paper SHALL be usable by the community detail flow as an English-readable paper before translated output exists.

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

