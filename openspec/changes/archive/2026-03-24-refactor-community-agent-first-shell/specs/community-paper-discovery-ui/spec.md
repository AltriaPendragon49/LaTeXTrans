## MODIFIED Requirements

### Requirement: Community feed homepage route
The community homepage SHALL act as a low-friction launch surface for paper search, question answering, and translation entry instead of behaving as the long-lived transcript workspace itself.

#### Scenario: Homepage remains a launch surface
- **WHEN** a user lands on the community homepage
- **THEN** the page SHALL emphasize a centered agent-first entry surface
- **AND** detailed transcript interaction SHALL continue in a dedicated conversation workspace after submission.

#### Scenario: Homepage removes status-heavy summary clutter
- **WHEN** the homepage renders its first-screen launch surface
- **THEN** tracked / official-style summary bookkeeping SHALL NOT dominate the primary viewport
- **AND** the agent entry SHALL remain the first obvious action.

### Requirement: Paper detail shell contract
The community paper detail page SHALL keep reading dominant while preserving soft system feedback and a same-level agent workspace.

#### Scenario: Reader remains the dominant surface
- **WHEN** the paper detail shell renders
- **THEN** the reader SHALL occupy the primary visual area
- **AND** the agent panel SHALL remain same-level but secondary to reading.

#### Scenario: Discovery cards focus on reading entry
- **WHEN** community papers are shown in discovery results or conversation answer cards
- **THEN** the UI SHALL prioritize paper title, summary, and open-reader actions
- **AND** status decorations SHALL remain secondary supporting metadata instead of the main emphasis.

### Requirement: Translation workspace relocation compatibility
The discovery UI SHALL remain compatible with a secondary tools hub that preserves the direct translation workflow.

#### Scenario: Community and tools stay separated
- **WHEN** the user needs the explicit direct translation workflow
- **THEN** the UI SHALL provide that workflow through the tools hub
- **AND** the community homepage SHALL not be forced to carry that explicit workflow as its primary surface.
