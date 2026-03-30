# community-paper-discovery-ui Specification

## Purpose
TBD - created by archiving change add-community-day-03-feed-and-paper-detail-shell. Update Purpose after archive.
## Requirements
### Requirement: Community feed homepage route
The community homepage SHALL act as a low-friction launch surface for paper search, question answering, and translation entry instead of behaving as the long-lived transcript workspace itself, adopting the new Stitch Compact Layout principles.

#### Scenario: Homepage remains a launch surface
- **WHEN** a user lands on the community homepage
- **THEN** the page SHALL emphasize a centered agent-first entry surface
- **AND** detailed transcript interaction SHALL continue in a dedicated conversation workspace after submission utilizing the Stitch Refined Layout structure.

#### Scenario: Homepage removes status-heavy summary clutter
- **WHEN** the homepage renders its first-screen launch surface
- **THEN** tracked / official-style summary bookkeeping SHALL NOT dominate the primary viewport
- **AND** the agent entry SHALL remain the first obvious action, preserving the minimalist intent of the Compact Layout design.

### Requirement: Feed sort and browse shell
The community homepage SHALL provide the MVP browse controls needed to inspect official-first community content.

#### Scenario: Switch feed views
- **WHEN** a user changes between `latest`, `translated`, and `hot`
- **THEN** the system SHALL request the matching community paper list from the Day 2 API
- **AND** the Feed SHALL render loading, empty, and error states without falling back to local mock data.

#### Scenario: Surface official-first guidance
- **WHEN** the Feed homepage renders
- **THEN** the page SHALL communicate that official community content is prioritized
- **AND** fallback user content SHALL appear as a lower-priority community state rather than a peer official source.
- **AND** the page SHALL rely on spacing, grouping, and restrained status emphasis rather than broad accent-colored panels.

### Requirement: Paper card content contract
Each Feed result SHALL render as a dense paper discovery card that helps the viewer decide whether to inspect the paper in detail.

#### Scenario: Render a paper card
- **WHEN** the Feed receives a community paper item
- **THEN** the card SHALL show community status, translation status, title, author summary, category summary, timing, counters, and selected asset summary
- **AND** official papers SHALL be visually distinguishable from user fallback papers.

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

### Requirement: Disabled action-slot contract
The Day 3 detail page SHALL visually reserve the future action positions needed by later changes without exposing active controls yet.

#### Scenario: Show future action positions
- **WHEN** the detail page renders
- **THEN** the page SHALL display translation, preview, download, like, favorite, comment, and report action slots
- **AND** all action slots SHALL be disabled in Day 3
- **AND** the UI SHALL explain that those actions are coming in later changes.

### Requirement: Translation workspace relocation compatibility
The discovery UI SHALL remain compatible with a secondary tools hub that preserves the direct translation workflow.

#### Scenario: Community and tools stay separated
- **WHEN** the user needs the explicit direct translation workflow
- **THEN** the UI SHALL provide that workflow through the tools hub
- **AND** the community homepage SHALL not be forced to carry that explicit workflow as its primary surface.

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

#### Scenario: Highlighted reader text is available to the in-pane copilot thread
- **WHEN** the user highlights text in the reader pane and asks a question in the paper-detail copilot panel
- **THEN** the same in-pane copilot thread SHALL submit the highlight as structured context
- **AND** the response SHALL appear in the continuous paper-detail conversation without falling back to one-shot shortcut mode.

