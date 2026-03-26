## ADDED Requirements
### Requirement: Community UI exposes deep research as a distinct mode
The community UI SHALL expose deep research as a distinct user-selectable mode so users can request broad literature synthesis without confusing that path with default chat.

#### Scenario: User chooses between chat and deep research
- **WHEN** the user prepares a community agent request
- **THEN** the UI SHALL expose an explicit deep research entry or mode switch
- **AND** the default chat path SHALL remain visually distinct.

### Requirement: Community UI renders long-form cited research reports
The community UI SHALL render deep research output as a report-length cited artifact rather than a short chat bubble only.

#### Scenario: Deep research report is displayed
- **WHEN** a deep research run completes
- **THEN** the UI SHALL render the result as a long-form structured report with citations
- **AND** the report SHALL remain readable without flattening all sections into one undifferentiated paragraph.

### Requirement: Community UI distinguishes deep-research progress from completion
The community UI SHALL treat deep-research progress as provisional and only present a finalized research report once a completion snapshot includes the report payload.

#### Scenario: Progress events arrive before completion
- **WHEN** a deep research run is still in progress and only non-complete stream events have arrived
- **THEN** the UI SHALL keep showing an in-progress state
- **AND** it SHALL not present the finalized deep research report card until a completed snapshot with report content is received.
