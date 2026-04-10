## ADDED Requirements
### Requirement: Processing page uses a fixed workbench layout
The Processing page SHALL open as a fixed-height workbench that keeps the major task surfaces visible together on first render instead of letting the live log expand the page indefinitely.

#### Scenario: Desktop processing view opens with the full workbench visible
- **WHEN** the user opens the Processing page on a desktop-class viewport
- **THEN** the page SHALL present the hero/status area, task-status timeline, completion-or-progress summary, and live-log panel inside one coordinated first-screen workbench
- **AND** the page itself SHALL remain height-bounded rather than extending vertically with log growth

#### Scenario: Live log scrolls only inside the dedicated log window
- **WHEN** new log lines continue to arrive during processing or after completion
- **THEN** the live-log panel SHALL keep a fixed window within the workbench
- **AND** vertical overflow SHALL scroll only inside that log viewport instead of pushing the entire Processing page downward

#### Scenario: Completion state remains visible without needing log-driven page scroll
- **WHEN** the task transitions into `completed` or `completed_with_warnings`
- **THEN** the completion heading and action controls SHALL remain part of the fixed workbench composition
- **AND** the user SHALL not need to scroll past an overgrown log panel just to discover that the translation finished
