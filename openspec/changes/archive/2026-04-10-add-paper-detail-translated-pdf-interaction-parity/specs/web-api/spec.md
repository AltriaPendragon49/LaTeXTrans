## ADDED Requirements
### Requirement: Paper detail response exposes translated-PDF interaction metadata
The API SHALL expose translated-PDF reader metadata required for interactive in-document operations in paper detail.

#### Scenario: Paper detail payload includes embeddable translated-PDF metadata
- **WHEN** a paper has translated PDF assets available
- **THEN** the paper-detail response SHALL include a translated-PDF reader URL suitable for inline embedding
- **AND** it SHALL include metadata required by the UI to attempt stable location mapping.

#### Scenario: Translated-PDF locator metadata is unavailable
- **WHEN** translated-PDF assets exist but locator metadata is not ready
- **THEN** the API SHALL explicitly indicate locator unavailability
- **AND** the response SHALL remain backward-compatible for non-interactive PDF viewing.

### Requirement: Agent run context supports translated-PDF locator selection fields
The API SHALL accept optional translated-PDF locator fields in `context.reader_selection` while preserving existing selection fields.

#### Scenario: Paper-detail run includes translated-PDF locator context
- **WHEN** the paper-detail client submits `context.reader_selection` from translated-PDF mode
- **THEN** the API SHALL accept existing fields (`text`, optional `anchor_id`, optional `mode`) plus optional locator fields
- **AND** runtime orchestration SHALL preserve these fields for planner/final answer grounding.

#### Scenario: Legacy clients submit reader_selection without locator fields
- **WHEN** clients only send current `reader_selection` fields
- **THEN** the API SHALL process the request without contract breakage
- **AND** behavior SHALL remain compatible with existing HTML-reader workflows.

### Requirement: Citation-target metadata supports translated-PDF location resolution
The API SHALL support citation/action metadata that can target translated-PDF positions for current-paper navigation.

#### Scenario: Assistant references a translated-PDF location in current paper
- **WHEN** an assistant run emits current-paper citation/action metadata for translated-PDF mode
- **THEN** metadata SHALL be able to carry stable location identifiers usable by the UI
- **AND** unresolved identifiers SHALL be distinguishable from successfully resolved targets.
