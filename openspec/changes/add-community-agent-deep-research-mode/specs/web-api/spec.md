## ADDED Requirements
### Requirement: Community agent API supports deep research execution mode
The community agent API SHALL support a deep research execution mode that returns async progress and a final long-form cited report.

#### Scenario: Client starts a deep research run
- **WHEN** the client requests a community agent run in deep research mode
- **THEN** the API SHALL acknowledge that mode explicitly
- **AND** it SHALL expose progress and final result retrieval compatible with long-running execution.

#### Scenario: Deep research result returns report-oriented payloads
- **WHEN** a deep research run completes
- **THEN** the final run payload SHALL include the long-form report body and citations
- **AND** the client SHALL not need to reconstruct the report from scattered event fragments alone.
