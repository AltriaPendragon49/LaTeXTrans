## MODIFIED Requirements

### Requirement: Community agent run API accepts visible-skill toggles
The community agent run API SHALL accept explicit skill-toggle input so the backend runtime can decide which skill schemas are visible to the planner model.

#### Scenario: Client submits external search toggle
- **WHEN** the client posts a community agent run request with `skill_toggles.external_search`
- **THEN** the API SHALL validate and forward that toggle to the backend service layer
- **AND** omitting `skill_toggles` SHALL remain backward-compatible.

### Requirement: Community agent response remains compatibility-safe
The community agent run API SHALL preserve the existing response contract while allowing the backend to produce model-detected intent, formatter-rendered summary text, and traced generation/validation steps.

#### Scenario: Runtime completes with slot-based finalization
- **WHEN** the backend runtime finalizes an agent run
- **THEN** the API SHALL still return `run_id`, `status`, `intent`, `summary`, `tool_trace`, `citations`, `provider_state`, and `action`
- **AND** clients SHALL NOT be required to consume raw planner JSON.

### Requirement: Community agent API enforces authenticated conversation persistence
The community agent API SHALL require authenticated users for persisted conversation runs and SHALL expose CRUD endpoints for user-owned conversation history stored behind Supabase RLS.

#### Scenario: Guest tries to create an agent conversation run
- **WHEN** an unauthenticated client submits a community agent run
- **THEN** the API SHALL reject the request with HTTP 401 Unauthorized
- **AND** it SHALL not create or persist guest conversation history.

#### Scenario: Authenticated client lists and deletes saved conversations
- **WHEN** an authenticated client requests or deletes community-agent conversation history
- **THEN** the API SHALL read or mutate only that user's conversation records
- **AND** deleted conversations SHALL no longer be returned by subsequent list requests.
