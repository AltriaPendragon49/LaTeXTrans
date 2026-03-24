## ADDED Requirements

### Requirement: Community agent run API returns a natural assistant message
The community agent run API SHALL return the assistant’s natural-language reply as a first-class field while preserving run metadata such as citations, tool trace, provider state, and actions.

#### Scenario: Conversational run completes successfully
- **WHEN** `POST /api/community-agent/runs` completes
- **THEN** the response SHALL include `message` containing the assistant’s natural-language reply
- **AND** it SHALL continue to include `citations`, `tool_trace`, `provider_state`, and `action`.

#### Scenario: Compatibility alias remains during migration
- **WHEN** existing consumers still read `summary`
- **THEN** the API SHALL keep `summary` aligned with `message` during the migration window
- **AND** the conversational UI SHALL prefer `message` when present.
