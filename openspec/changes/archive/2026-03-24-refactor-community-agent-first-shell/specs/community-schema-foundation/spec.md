## MODIFIED Requirements

### Requirement: Community schema entities are frozen
The community schema SHALL reserve room for source-readable and translated-readable paper states without requiring a second object model for English vs Chinese paper pages.

#### Scenario: Paper assets support English-readable and Chinese-readable states
- **WHEN** the community stores paper assets
- **THEN** the schema SHALL support asset semantics that distinguish readable English-source artifacts from readable translated artifacts
- **AND** the product SHALL continue to treat those as states of the same `paper` object rather than separate papers.

### Requirement: Community page boundaries are frozen for Days 2-10
The community page-boundary contract SHALL allow the shared shell to prioritize the community flow while moving translation-oriented tool pages behind a secondary tools hub.

#### Scenario: Shared shell prioritizes community over tools
- **WHEN** the frontend shared shell is rendered for this phase
- **THEN** the primary navigation SHALL be allowed to foreground the community homepage as the main first-level destination
- **AND** translation-centric tools MAY move behind a secondary tools entry without violating the community page-boundary contract.
