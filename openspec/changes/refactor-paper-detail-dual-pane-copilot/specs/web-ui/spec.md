## ADDED Requirements
### Requirement: Paper detail uses a coordinated dual-pane copilot workspace
The web UI SHALL present paper detail as a coordinated dual-pane workspace with a reading-dominant pane and a persistent paper-scoped copilot pane.

#### Scenario: Desktop paper detail keeps both panes visible
- **WHEN** the user opens the paper detail page on a desktop-width viewport
- **THEN** the reader SHALL remain the dominant pane
- **AND** the copilot pane SHALL stay visible without visually displacing the reader from its primary role.

#### Scenario: Narrow screens keep reading continuity
- **WHEN** the user opens the paper detail page on a narrower viewport
- **THEN** the UI SHALL preserve access to both reading and copilot functions
- **AND** it SHALL do so with an explicit responsive behavior instead of collapsing into an unusable cramped layout.

### Requirement: Reader and copilot interactions stay synchronized
The web UI SHALL keep active anchor, reader mode, and paper-scoped copilot metadata synchronized inside the dual-pane workspace.

#### Scenario: Citation click highlights the corresponding reader block
- **WHEN** the user clicks a copilot citation or anchor-aware action
- **THEN** the reader SHALL scroll to the target block
- **AND** the target block SHALL receive visible focus or highlight feedback.

#### Scenario: Translation upgrade does not reset the copilot
- **WHEN** the paper switches from source-first reading to translated reading
- **THEN** the copilot pane SHALL stay mounted with its current context
- **AND** the user SHALL not lose the active paper-scoped assistant conversation.
