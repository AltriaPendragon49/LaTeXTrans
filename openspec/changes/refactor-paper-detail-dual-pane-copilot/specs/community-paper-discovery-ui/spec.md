## MODIFIED Requirements
### Requirement: Paper detail shell contract
The community paper detail page SHALL keep reading dominant while providing a persistent same-screen AI copilot workspace that behaves as a coordinated dual-pane study surface.

#### Scenario: Reader remains the dominant surface
- **WHEN** the paper detail shell renders
- **THEN** the reader SHALL occupy the primary visual area
- **AND** the AI copilot pane SHALL remain persistent but secondary to reading.

#### Scenario: Discovery cards focus on reading entry
- **WHEN** community papers are shown in discovery results or conversation answer cards
- **THEN** the UI SHALL prioritize paper title, summary, and open-reader actions
- **AND** status decorations SHALL remain secondary supporting metadata instead of the main emphasis.

#### Scenario: Detail page behaves as a dual-pane reading workspace
- **WHEN** the user opens a paper detail page
- **THEN** the page SHALL keep the reader and copilot visible in a coordinated dual-pane layout
- **AND** the user SHALL not need to leave the paper detail route to continue the same paper-scoped reading conversation.

## ADDED Requirements
### Requirement: Dual-pane reader supports anchored copilot references
The paper detail workspace SHALL let the AI copilot reference concrete paper locations and drive the reader to those locations through anchor-aware interactions.

#### Scenario: User clicks an assistant citation
- **WHEN** the copilot answer includes a citation or reference tied to the current paper
- **THEN** clicking that reference SHALL scroll the reader to the corresponding location
- **AND** the reader SHALL highlight that location without leaving the current paper detail route.

#### Scenario: Reader upgrades softly when translated mode becomes ready
- **WHEN** translated HTML becomes ready while the user is already reading the paper detail page
- **THEN** the workspace SHALL surface a lightweight upgrade cue
- **AND** switching to translated reading SHALL preserve the same dual-pane shell instead of forcing a hard page replacement.
