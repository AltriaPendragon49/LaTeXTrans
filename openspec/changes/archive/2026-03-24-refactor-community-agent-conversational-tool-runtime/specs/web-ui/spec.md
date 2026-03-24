## ADDED Requirements

### Requirement: Community conversation UI renders natural assistant chat output
The community conversation workspace SHALL render assistant runs as normal chat messages instead of reconstructing hard-coded summary cards from structured section headings.

#### Scenario: Assistant turn contains a natural-language reply
- **WHEN** the conversation page renders an assistant turn produced by the community agent
- **THEN** it SHALL display the run’s conversational message as the assistant content body
- **AND** it SHALL NOT require section headers such as “Conclusion/Current status” or “Core points” to render that turn.

#### Scenario: Citations, tool trace, and paper actions remain visible
- **WHEN** an assistant run includes citations, tool trace entries, or a paper navigation action
- **THEN** the conversation workspace SHALL continue to render those affordances alongside the conversational answer
- **AND** the UI SHALL keep the assistant answer in chat form rather than decomposing it into summary cards.
