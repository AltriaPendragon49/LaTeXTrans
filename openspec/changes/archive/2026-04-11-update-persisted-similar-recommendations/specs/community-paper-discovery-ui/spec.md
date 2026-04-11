## MODIFIED Requirements
### Requirement: Similar pane provides recommendation cards without changing the page layout
The paper-detail side pane SHALL provide similar-paper recommendations inside the existing sidebar region.

#### Scenario: Similar recommendations are available
- **WHEN** the user opens the `Similar` tab and recommendation results exist
- **THEN** the pane SHALL render compact recommendation rows that show the paper title by default
- **AND** each row SHALL let the user expand that item to reveal the stored abstract
- **AND** the cards SHALL reflect the persisted backend recommendation order rather than triggering a new live search during display
- **AND** the sidebar SHALL keep the existing overall theme and layout structure outside those local content substitutions.
