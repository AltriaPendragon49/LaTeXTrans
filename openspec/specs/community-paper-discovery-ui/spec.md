# community-paper-discovery-ui Specification

## Purpose
TBD - created by archiving change add-community-day-03-feed-and-paper-detail-shell. Update Purpose after archive.
## Requirements
### Requirement: Community feed homepage route
The system SHALL expose the community Feed as the primary web homepage and present it as a research-discovery surface rather than a translation form.

#### Scenario: Open the product homepage
- **WHEN** a user navigates to `/`
- **THEN** the system SHALL render the community Feed homepage shell
- **AND** the page SHALL visually prioritize browseable community papers over translation inputs
- **AND** the design SHALL follow a restrained dark research-reading direction inspired by alphaXiv without reproducing alphaXiv branding or navigation structure.

#### Scenario: Shared shell avoids redundant kicker labels
- **WHEN** the community homepage or paper detail shell renders
- **THEN** the shared shell SHALL prioritize the page title over decorative kicker labels
- **AND** labels such as `Research Console` SHALL not be required for comprehension or navigation.

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
The system SHALL provide a dedicated paper detail shell that defaults to the community-selected version of a paper.

#### Scenario: Open a paper detail page
- **WHEN** a user navigates to `/paper/:paperId`
- **THEN** the page SHALL load the paper detail from the Day 2 API
- **AND** it SHALL render title, authors, abstract, status badges, counters, source metadata, and community-selected task/asset references
- **AND** it SHALL record a paper view without blocking the detail render if the view counter call fails.

### Requirement: Disabled action-slot contract
The Day 3 detail page SHALL visually reserve the future action positions needed by later changes without exposing active controls yet.

#### Scenario: Show future action positions
- **WHEN** the detail page renders
- **THEN** the page SHALL display translation, preview, download, like, favorite, comment, and report action slots
- **AND** all action slots SHALL be disabled in Day 3
- **AND** the UI SHALL explain that those actions are coming in later changes.

### Requirement: Translation workspace relocation compatibility
The old translation workspace SHALL remain available after the homepage moves to the community Feed.

#### Scenario: Open the translation workspace
- **WHEN** a user navigates to `/translate`
- **THEN** the system SHALL render the existing translation Dashboard experience
- **AND** shared navigation SHALL expose both `Community` and `New Translation` as first-level destinations.

