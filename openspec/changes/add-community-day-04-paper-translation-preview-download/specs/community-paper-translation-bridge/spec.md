## ADDED Requirements
### Requirement: Paper-driven translation, preview, and download bridge
The system SHALL let a community paper detail page trigger translation, observe the latest translated asset, and access preview and download through controlled paper-based routes.

#### Scenario: Start translation from paper detail
- **WHEN** a user starts translation from a paper detail surface
- **THEN** the system SHALL create or reuse the appropriate translation task using the selected paper as the owning context
- **AND** the user SHALL be able to continue into existing processing feedback surfaces.

#### Scenario: Expose the latest translated asset on paper detail
- **WHEN** a translation succeeds for a paper
- **THEN** the system SHALL associate the latest successful output with that paper through `paper_assets`
- **AND** the paper detail payload SHALL expose enough metadata to render preview and download actions.

#### Scenario: Enforce controlled download access
- **WHEN** a user requests a translated artifact from a paper surface
- **THEN** the system SHALL route the request through a permission-checked gateway
- **AND** the download path SHALL support short-lived authorization or equivalent access control for MVP safety.
