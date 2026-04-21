## ADDED Requirements
### Requirement: Authenticated folder-based favorites persist for community papers
The system SHALL let authenticated users save community papers into named favorite folders stored in backend and database state.

#### Scenario: Create and manage favorite folders under product rules
- **WHEN** an authenticated user creates or renames a favorite folder for community papers
- **THEN** the system SHALL reject duplicate folder names for the same user
- **AND** it SHALL enforce a maximum of 9 folders per user
- **AND** it SHALL persist successful create and rename operations server-side rather than in frontend-local state

#### Scenario: The same paper belongs to multiple favorite folders
- **WHEN** an authenticated user assigns one community paper to multiple favorite folders
- **THEN** the system SHALL persist every selected folder-paper relation
- **AND** it SHALL treat those relations as belonging to the same paper rather than duplicating the paper entity

#### Scenario: Deleting a folder only removes its favorite relations
- **WHEN** an authenticated user deletes a favorite folder
- **THEN** the system SHALL delete that folder and its folder-paper relations only
- **AND** it SHALL NOT delete the paper itself
- **AND** it SHALL preserve the paper’s membership in any other folders

### Requirement: Favorites workspace exposes folder navigation for authenticated users
The system SHALL provide a dedicated favorites workspace for community papers that is reachable from the shared sidebar for authenticated users.

#### Scenario: Authenticated user sees and opens the favorites entry
- **WHEN** an authenticated user renders the shared sidebar
- **THEN** the sidebar SHALL include a favorites entry for community papers
- **AND** selecting that entry SHALL navigate to the favorites workspace

#### Scenario: Guest access to favorites routes requires login
- **WHEN** an unauthenticated user attempts to open a favorites workspace route directly
- **THEN** the system SHALL enter the login flow instead of rendering a writable favorites workspace

#### Scenario: Favorites workspace shows folder contents and paper navigation
- **WHEN** an authenticated user opens the favorites workspace and enters a folder
- **THEN** the system SHALL render the community papers saved in that folder
- **AND** selecting a paper row SHALL navigate to the community paper detail page

### Requirement: Community-paper favorite picker uses deferred multi-folder submission
The system SHALL use a shared favorite picker for community feed cards and paper detail so users can review and submit folder assignments explicitly.

#### Scenario: Favorited state reflects at least one folder relation
- **WHEN** a community paper belongs to at least one favorite folder for the current user
- **THEN** the favorite button SHALL render in its active highlighted state
- **AND** opening the picker SHALL show the currently selected folders for that paper

#### Scenario: Creating a folder inside the picker does not auto-complete favorite assignment
- **WHEN** an authenticated user creates a new folder from the favorite picker
- **THEN** the new folder SHALL be created successfully and auto-selected in the picker
- **AND** the confirm action SHALL become visibly ready to submit
- **AND** the system SHALL NOT persist the paper-folder relation until the user explicitly confirms

#### Scenario: Confirming picker selections adds and removes relations together
- **WHEN** an authenticated user confirms the selected folder set for a paper
- **THEN** the system SHALL add any new folder relations and remove any deselected relations in backend state
- **AND** it SHALL show clear success feedback for favorite updates or removals
- **AND** clearing all selected folders and confirming SHALL return the paper to the unfavorited state

### Requirement: Community-paper likes are authenticated, unique, and persistent
The system SHALL provide a one-user-one-like toggle for community-paper feed cards with persistent counts.

#### Scenario: Authenticated user toggles like on a community paper
- **WHEN** an authenticated user likes or unlikes a community paper from the feed
- **THEN** the UI SHALL reflect the count and active-state change immediately
- **AND** the backend SHALL persist at most one like record per user and paper
- **AND** later refreshes or other viewers SHALL observe the updated persistent like count

#### Scenario: Guest user attempts to like a paper
- **WHEN** an unauthenticated user activates the like control
- **THEN** the system SHALL require login instead of storing a frontend-local like state

### Requirement: Community-paper view counts only accept detail-entry events with daily de-duplication
The system SHALL count community-paper views only from paper-detail entry events and SHALL de-duplicate repeated reads within the same business day.

#### Scenario: Homepage card exposure does not count as a paper view
- **WHEN** community papers are rendered on the homepage feed without opening detail
- **THEN** the system SHALL NOT increment the paper’s view count

#### Scenario: Authenticated user reopens the same paper on the same day
- **WHEN** an authenticated user enters the same community paper detail page more than once within the same UTC+8 business day
- **THEN** the system SHALL count only the first entry for that user and paper on that day

#### Scenario: Guest view de-duplication uses a stable anonymous principal
- **WHEN** an unauthenticated user enters a community paper detail page
- **THEN** the system SHALL de-duplicate that day’s view using a browser-local anonymous identifier carried to the backend
- **AND** if that local identifier is later cleared or lost, the system MAY count a later visit again

### Requirement: Engagement state is served from backend persistence rather than frontend-local memory
Community-paper engagement UI SHALL render from backend-persisted viewer state and aggregate counts.

#### Scenario: Refresh or re-login preserves engagement state
- **WHEN** a user refreshes the page or restores a later authenticated session
- **THEN** the favorite active state, like active state, and aggregate counts SHALL be reconstructed from backend responses
- **AND** the UI SHALL NOT rely on previous in-memory client state to preserve correctness
