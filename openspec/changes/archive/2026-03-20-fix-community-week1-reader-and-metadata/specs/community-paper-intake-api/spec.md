## MODIFIED Requirements
### Requirement: Unified paper submit API
The system SHALL expose one paper submit API that accepts upload or arXiv input under the community admission rules.

#### Scenario: Submit a paper from upload
- **WHEN** an authenticated user submits a supported file to `POST /api/papers/submit`
- **THEN** the system SHALL create a community `paper` record for that submission
- **AND** it SHALL record a `paper_assets` source asset that points to the local source path.

#### Scenario: Submit a paper from arXiv
- **WHEN** an authenticated user submits an `arxiv_id` to `POST /api/papers/submit`
- **THEN** the system SHALL create or reuse one community `paper` record
- **AND** it SHALL preserve the linkage needed to track the underlying intake task and later assets
- **AND** it SHALL populate title, authors, categories, and source abstract whenever arXiv metadata is available.

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

#### Scenario: Completed papers expose a usable abstract and reader
- **WHEN** a community paper has completed translated output
- **THEN** the detail payload SHALL expose the best available abstract, preferring translated abstract when recoverable
- **AND** preview reads SHALL use the completed output to recover `preview_html` when the asset row is missing.
