## MODIFIED Requirements
### Requirement: Public paper detail avoids a user-visible metadata-to-preview waterfall
The system SHALL provide a first-read contract that keeps paper detail bootstrap lightweight while still making translated reading assets immediately discoverable for normal users.

#### Scenario: Open a paper detail page that has a ready preview
- **WHEN** a user navigates to a paper detail route for a preview-ready paper
- **THEN** the system SHALL deliver metadata, reader state, and reader asset locators without embedding large multi-megabyte preview bodies directly in the main detail payload
- **AND** the page SHALL be able to begin rendering normal reading flow without a visibly serialized metadata request followed by a second blocking preview-discovery step.

#### Scenario: Navigate to a paper detail page whose reader is still warming
- **WHEN** a user opens a paper detail route for a paper whose preview is not yet reader-ready
- **THEN** the page SHALL communicate that the reader is warming or unavailable
- **AND** the non-reader metadata SHALL still render without pretending that full reading is immediately ready.
