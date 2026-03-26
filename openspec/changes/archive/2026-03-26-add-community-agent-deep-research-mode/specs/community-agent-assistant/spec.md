## ADDED Requirements
### Requirement: Community agent supports an explicit deep research mode
The community agent SHALL support an explicit deep research mode that expands retrieval breadth and produces a long-form cited synthesis without changing the default fast chat behavior.

#### Scenario: User chooses deep research mode
- **WHEN** the user explicitly starts a deep research run
- **THEN** the agent SHALL use a research-oriented retrieval and synthesis path
- **AND** the default chat mode SHALL remain available for normal paper questions.

#### Scenario: Deep research run prefers grounded multi-paper synthesis
- **WHEN** the agent completes a deep research run
- **THEN** the result SHALL synthesize multiple papers with citations
- **AND** it SHALL not degrade into a short single-paper chat answer unless the evidence set itself was too narrow.
