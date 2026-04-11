## MODIFIED Requirements
### Requirement: Paper detail shell contract
The community paper detail page SHALL keep reading dominant while providing a persistent right-side reading-support workspace that behaves as a coordinated dual-pane study surface.

#### Scenario: Reader remains the dominant surface
- **WHEN** the paper detail shell renders
- **THEN** the reader SHALL occupy the primary visual area
- **AND** the right-side workspace SHALL remain persistent but secondary to reading.

#### Scenario: Discovery cards focus on reading entry
- **WHEN** community papers are shown in discovery results or conversation answer cards
- **THEN** the UI SHALL prioritize paper title, summary, and open-reader actions
- **AND** status decorations SHALL remain secondary supporting metadata instead of the main emphasis.

#### Scenario: Detail page behaves as a dual-pane reading workspace
- **WHEN** the user opens a paper detail page
- **THEN** the page SHALL keep the reader and right-side support pane visible in a coordinated dual-pane layout
- **AND** the user SHALL not need to leave the paper detail route to continue the same paper-scoped reading workflow.

#### Scenario: Right pane focuses on insights and similar reading support
- **WHEN** the paper detail page renders after this change
- **THEN** the right-side pane SHALL expose only `Insights` and `Similar` tabs
- **AND** it SHALL not expose `Notes` or `Comments` in this version.

## ADDED Requirements
### Requirement: Insights pane defaults to compact collapsed reading support
The paper-detail insights pane SHALL prioritize direct module reading over explanatory chrome.

#### Scenario: Insights tab opens
- **WHEN** the user views the `Insights` tab
- **THEN** the pane SHALL render the five prepared insight modules without an extra introductory summary card above them
- **AND** every module SHALL be collapsed by default until the user expands one.

### Requirement: Similar pane provides recommendation cards without changing the page layout
The paper-detail side pane SHALL provide similar-paper recommendations inside the existing sidebar region.

#### Scenario: Similar recommendations are available
- **WHEN** the user opens the `Similar` tab and recommendation results exist
- **THEN** the pane SHALL render compact recommendation cards that show the paper identifier, title, and abstract
- **AND** the cards SHALL reflect the backend's merged BM25 reranking across station-local and arXiv candidates rather than forcing a source-specific priority
- **AND** the sidebar SHALL keep the existing overall theme and layout structure outside those local content substitutions.
