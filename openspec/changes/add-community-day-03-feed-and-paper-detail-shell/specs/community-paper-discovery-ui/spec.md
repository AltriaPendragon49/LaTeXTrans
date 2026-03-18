## ADDED Requirements
### Requirement: Community feed and paper detail browse shell
The system SHALL provide a browseable community homepage and a paper detail shell before translation and interaction actions are wired in.

#### Scenario: Browse papers from the community homepage
- **WHEN** a user opens the homepage
- **THEN** the system SHALL expose a Feed surface with `最新`, `已翻译`, and `热榜` views
- **AND** each view SHALL support the pagination, sorting, or filtering needed for MVP browsing.

#### Scenario: Navigate from a card to paper detail
- **WHEN** a user selects a paper card from the Feed
- **THEN** the system SHALL route the user to a dedicated paper detail surface
- **AND** the detail shell SHALL render enough metadata to decide whether to browse, translate, preview, or interact later.

#### Scenario: Show translation state in the detail shell
- **WHEN** the detail surface receives paper status data
- **THEN** it SHALL distinguish `未翻译`, `翻译中`, and `已翻译`
- **AND** it SHALL reserve action positions for the translation, preview, download, and interaction controls added in later changes.
