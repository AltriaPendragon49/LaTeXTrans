## MODIFIED Requirements
### Requirement: Feed sort and browse shell
The community homepage SHALL provide the browse controls needed to inspect public community content using the requested production sort semantics.

#### Scenario: Switch feed views
- **WHEN** a user changes between `latest`, `views`, and `likes`
- **THEN** the system SHALL request the matching community paper list from the backend API
- **AND** the feed SHALL render loading, empty, and error states without falling back to local mock data

#### Scenario: Sort values fall back to the latest rule
- **WHEN** multiple community papers share the same `view_count` or `like_count`
- **THEN** the system SHALL break ties using original arXiv publication time descending
- **AND** it SHALL continue falling back to creation time descending when publication time is unavailable

#### Scenario: Surface official-first guidance
- **WHEN** the feed homepage renders
- **THEN** the page SHALL communicate that official community content is prioritized
- **AND** fallback user content SHALL appear as a lower-priority community state rather than a peer official source
- **AND** the page SHALL rely on spacing, grouping, and restrained status emphasis rather than broad accent-colored panels

### Requirement: Paper-detail interaction slot contract
The community paper detail page SHALL expose the active favorite interaction required for this rollout while allowing non-scoped future interactions to remain absent or inactive.

#### Scenario: Detail page favorite action is active
- **WHEN** an authenticated user activates the favorite control on a community paper detail page
- **THEN** the UI SHALL open the same folder-based favorite picker used on the homepage cards
- **AND** the control SHALL render in its active highlighted state whenever that paper belongs to at least one favorite folder for the current user

#### Scenario: Out-of-scope future actions do not block this rollout
- **WHEN** the paper detail page renders in this rollout
- **THEN** non-scoped future interactions such as comments or reports MAY remain hidden, reserved, or inactive
- **AND** the page SHALL not imply that those non-scoped interactions are already fully implemented by this change

## RENAMED Requirements
- FROM: `### Requirement: Disabled action-slot contract`
- TO: `### Requirement: Paper-detail interaction slot contract`
