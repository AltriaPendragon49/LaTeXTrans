## ADDED Requirements
### Requirement: Community agent prefers prewarmed translated evidence when available
The community agent SHALL prefer prewarmed translated evidence from the community content pool before starting new on-demand translation work for the same paper.

#### Scenario: Internal search finds a prewarmed translated paper
- **WHEN** the agent retrieves a relevant community paper whose translated evidence is already available
- **THEN** it SHALL ground the answer on that prewarmed translated evidence first
- **AND** it SHALL avoid starting redundant translation work for the same paper in that turn.

#### Scenario: Content pool miss falls back to on-demand import and translation
- **WHEN** the agent cannot find suitable prewarmed translated evidence for the requested paper
- **THEN** it SHALL continue to use the existing on-demand import and translation fallback behavior
- **AND** the absence of a content-pool hit SHALL not block the conversation.
