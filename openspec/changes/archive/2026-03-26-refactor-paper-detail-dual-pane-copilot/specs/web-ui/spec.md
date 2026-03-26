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

#### Scenario: URL hash deep-link resolves after asynchronous preview rendering
- **WHEN** the user opens paper detail with a URL hash anchor whose target appears after asynchronous preview rendering/enhancement
- **THEN** the reader SHALL retry anchor activation until that target is available within bounded time
- **AND** the resolved target SHALL be scrolled into view and visibly highlighted without requiring a second user action.

#### Scenario: Translation upgrade does not reset the copilot
- **WHEN** the paper switches from source-first reading to translated reading
- **THEN** the copilot pane SHALL stay mounted with its current context
- **AND** the user SHALL not lose the active paper-scoped assistant conversation.

### Requirement: Paper-detail copilot supports true multi-turn chat with reader selection context
The web UI SHALL let users run a real multi-turn paper-scoped conversation inside paper detail, and SHALL include highlighted reader selection context in copilot runs.

#### Scenario: User highlights a reader passage and asks a follow-up question
- **WHEN** the user highlights a passage in the reader pane and sends a copilot question from the detail-side composer
- **THEN** the run payload SHALL include structured `reader_selection` context (`text`, optional `anchor_id`, and reader `mode`)
- **AND** the copilot response SHALL render in the same right-pane conversation thread without route changes.

#### Scenario: Highlighted selection remains visually discoverable while chatting
- **WHEN** the user highlights reader text and then moves focus to the copilot input to ask questions
- **THEN** the reader pane SHALL keep a visible highlight marker for the active selected passage
- **AND** clearing the selection context from the composer SHALL remove that reader highlight marker.

#### Scenario: Paper-detail chat keeps conversation memory within the same paper
- **WHEN** the user asks a second question in the same paper detail copilot thread
- **THEN** the next run SHALL include prior user/assistant turns as history context
- **AND** the thread SHALL continue rendering as one continuous in-pane conversation.

#### Scenario: Copilot composer stays visible and actionable in the right pane
- **WHEN** the paper detail workspace renders with tall reader content or long articles
- **THEN** the right-pane copilot composer (input plus run controls) SHALL remain visibly discoverable without requiring users to hunt through unrelated static filler content
- **AND** the default empty state SHALL prioritize direct chat entry over large decorative description or asset cards.
