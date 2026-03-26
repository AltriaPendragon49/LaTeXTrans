# community-deep-research Specification

## Purpose
TBD - created by archiving change add-community-agent-deep-research-mode. Update Purpose after archive.
## Requirements
### Requirement: Deep research mode performs expanded multi-paper retrieval
The system SHALL support an explicit deep research mode that gathers a materially larger evidence set than the default chat path before producing its final answer.

#### Scenario: Deep research run expands recall breadth
- **WHEN** the user starts a deep research run
- **THEN** the system SHALL gather a broader evidence set than default chat, targeting approximately 15–20 relevant papers or evidence items
- **AND** it SHALL keep that breadth inside explicit bounded limits.

### Requirement: Deep research mode returns a long-form cited research brief
Deep research mode SHALL produce a report-length synthesis that cites the evidence it used instead of collapsing back into a short conversational answer.

#### Scenario: Deep research completes successfully
- **WHEN** a deep research run completes
- **THEN** the system SHALL return a long-form research brief with section structure and citation markers
- **AND** the brief SHALL synthesize findings across multiple papers rather than summarizing only one source.

### Requirement: Deep research mode exposes bounded progress and degraded outcomes
The system SHALL expose progress, partial completion, and bounded failure behavior for long-running deep research runs.

#### Scenario: Deep research run cannot gather full target breadth
- **WHEN** a deep research run completes with fewer usable sources than the target breadth
- **THEN** the final output SHALL explain that the coverage was partial
- **AND** it SHALL still produce a grounded report from the evidence that was successfully gathered.

