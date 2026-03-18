## ADDED Requirements
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
The system SHALL expose one paper submit API that accepts upload or arXiv input under the community admission rules.

#### Scenario: Submit a paper from upload
- **WHEN** an authenticated user submits a supported file to `POST /api/papers/submit`
- **THEN** the system SHALL create a community `paper` record for that submission
- **AND** it SHALL record a `paper_assets` source asset that points to the local source path.

#### Scenario: Submit a paper from arXiv
- **WHEN** an authenticated user submits an `arxiv_id` to `POST /api/papers/submit`
- **THEN** the system SHALL create or reuse one community `paper` record
- **AND** it SHALL preserve the linkage needed to track the underlying intake task and later assets.

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
The system SHALL expose a stable paper-centric detail model for community paper pages.

#### Scenario: Anonymous users read public paper detail
- **WHEN** an anonymous client requests `GET /api/papers/{paper_id}`
- **THEN** the system SHALL return only public paper detail
- **AND** it SHALL expose viewer-state defaults without requiring authentication.

#### Scenario: Authenticated users read viewer state
- **WHEN** an authenticated client requests `GET /api/papers/{paper_id}`
- **THEN** the system SHALL return the paper detail payload
- **AND** it SHALL include the current user's `liked` and `favorited` flags.

### Requirement: Community paper view tracking
The system SHALL support a dedicated paper view write path without introducing a new analytics table.

#### Scenario: Track paper views without breaking the main read path
- **WHEN** a paper detail page is opened
- **THEN** the system SHALL support `POST /api/papers/{paper_id}/view`
- **AND** it SHALL update the paper view count while keeping feed and detail reads available.
