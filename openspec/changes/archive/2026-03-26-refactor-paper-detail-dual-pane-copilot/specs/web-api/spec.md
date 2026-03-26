## ADDED Requirements
### Requirement: Paper detail and agent payloads expose stable reader anchors
The API SHALL expose enough metadata for the frontend to map copilot citations and actions onto stable paper-reader locations.

#### Scenario: Paper detail response includes anchor-ready reader metadata
- **WHEN** the client requests a paper detail payload for a readable paper
- **THEN** the response SHALL include stable reader anchor identifiers for readable sections or segments
- **AND** those identifiers SHALL remain usable by the UI for scroll-and-highlight interactions.

#### Scenario: Assistant citation references a current-paper anchor
- **WHEN** the community agent cites or points into the current paper
- **THEN** the run metadata SHALL be allowed to include the current `paper_id` and a stable `anchor_id`
- **AND** the frontend SHALL not need to infer that mapping from raw assistant text alone.

### Requirement: Agent run context supports highlighted reader selection metadata
The API SHALL accept and propagate structured highlighted-reader selection context for paper-detail copilot runs.

#### Scenario: Paper-detail run includes highlighted selection payload
- **WHEN** the paper-detail client submits an agent run with `context.reader_selection`
- **THEN** the API contract SHALL accept `reader_selection.text`, optional `reader_selection.anchor_id`, and optional `reader_selection.mode`
- **AND** the runtime SHALL retain that context for planner/final answer grounding without requiring user-visible prompt rewriting.
