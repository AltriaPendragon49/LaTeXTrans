# community-paper-discovery-ui Specification

## Purpose
TBD - created by archiving change add-community-day-03-feed-and-paper-detail-shell. Update Purpose after archive.
## Requirements
### Requirement: Community feed homepage route
The community homepage SHALL prioritize internal community-paper search and feed browsing instead of exposing a public agent-first entry surface, while preserving the current overall layout silhouette for the page.

#### Scenario: Homepage uses internal community search as the top interaction
- **WHEN** a user lands on the community homepage
- **THEN** the page SHALL present a search-first surface for internal community paper lookup
- **AND** that search surface SHALL match community papers by `arXiv ID`, title, author, and abstract fields
- **AND** it SHALL only search formal public community papers
- **AND** it SHALL exclude ordinary tool results, incomplete curation items, and deleting or deleted papers
- **AND** it SHALL NOT expose the public homepage agent composer as the default first-screen action.

#### Scenario: Homepage keeps its established overall shell
- **WHEN** the homepage renders after this change
- **THEN** the page SHALL keep the existing overall feed layout direction intact
- **AND** the change SHALL focus on replacing the top interaction behavior rather than redesigning the entire page architecture.

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

### Requirement: Disabled action-slot contract
The Day 3 detail page SHALL visually reserve the future action positions needed by later changes without exposing active controls yet.

#### Scenario: Show future action positions
- **WHEN** the detail page renders
- **THEN** the page SHALL display translation, preview, download, like, favorite, comment, and report action slots
- **AND** all action slots SHALL be disabled in Day 3
- **AND** the UI SHALL explain that those actions are coming in later changes.

### Requirement: Translation workspace relocation compatibility
The discovery UI SHALL keep the direct translation workflow in the tools hub and SHALL keep ordinary tool translations separate from community publication.

#### Scenario: User needs the explicit direct translation workflow
- **WHEN** the user needs the explicit direct translation workflow
- **THEN** the UI SHALL provide that workflow through the tools hub
- **AND** the community homepage SHALL not be forced to carry that workflow as its primary surface.

#### Scenario: Ordinary tool translation does not publish community content
- **WHEN** a normal user completes a translation through the tools workflow
- **THEN** that result SHALL remain outside the public community library by default
- **AND** only the dedicated admin curation path SHALL publish new community papers.

### Requirement: Admin-only community controls appear inside the existing community shell
The community UI SHALL expose admin-only curation and deletion controls without revealing those controls to ordinary users.

#### Scenario: Admin sees the curation entry in the shared sidebar
- **WHEN** an authenticated admin user renders the community shell
- **THEN** the sidebar SHALL include an entry for the admin-only community curation page
- **AND** that entry SHALL remain hidden for non-admin users.

#### Scenario: Admin sees a delete affordance on community paper cards
- **WHEN** an authenticated admin user views community paper cards on the homepage feed
- **THEN** each card SHALL expose an admin-only delete affordance
- **AND** ordinary users SHALL not see that affordance.

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

