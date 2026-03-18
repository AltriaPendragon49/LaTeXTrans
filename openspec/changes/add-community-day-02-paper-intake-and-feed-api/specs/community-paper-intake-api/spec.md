## ADDED Requirements
### Requirement: Unified paper intake and read APIs
The system SHALL treat uploaded papers and arXiv-imported papers as one unified paper object that can be listed, opened, and tracked from community surfaces.

#### Scenario: Submit a paper from upload or arXiv
- **WHEN** a user submits a paper by file upload or arXiv identifier
- **THEN** the system SHALL create or hydrate one `paper` record as the canonical community object
- **AND** it SHALL preserve the linkage needed to start a translation task later.

#### Scenario: Read the feed and detail data from one contract
- **WHEN** the frontend requests the papers list or a paper detail payload
- **THEN** the system SHALL expose a stable paper-centric response model for list cards and detail views
- **AND** the model SHALL include enough metadata to render status, authorship, and asset availability.

#### Scenario: Track paper views without breaking the main read path
- **WHEN** a paper detail page is opened
- **THEN** the system SHALL support a dedicated view-tracking write path
- **AND** feed and detail reads SHALL remain available even if analytics handling is simple or deferred.
