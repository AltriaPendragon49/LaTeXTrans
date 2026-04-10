## MODIFIED Requirements
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

### Requirement: Paper detail shell contract
The community paper detail page SHALL keep reading dominant while replacing the public same-screen AI copilot workspace with a prepared structured-insight pane for the current paper.

#### Scenario: Reader remains the dominant surface
- **WHEN** the paper detail shell renders
- **THEN** the reader SHALL occupy the primary visual area
- **AND** the structured-insight pane SHALL remain secondary to reading.

#### Scenario: Detail page uses structured insights instead of public copilot
- **WHEN** the user opens a paper detail page
- **THEN** the right-side pane SHALL display prepared structured sections for the current paper
- **AND** the page SHALL NOT show the public paper-detail copilot composer or conversation thread in that pane.

#### Scenario: Legacy or abnormal papers can show an insight placeholder
- **WHEN** a visible paper lacks prepared structured insights because it is a legacy or degraded record
- **THEN** the right-side pane SHALL show a compact placeholder message
- **AND** the page SHALL remain readable without exposing a public copilot fallback in that area.

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

## ADDED Requirements
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

## REMOVED Requirements
### Requirement: Dual-pane reader supports anchored copilot references
**Reason**: The public paper-detail copilot pane is being hidden and replaced by prepared structured insights.
**Migration**: Anchor-aware paper reading remains possible through the reader itself, but the public same-screen copilot interactions are no longer part of the default paper-detail contract.
