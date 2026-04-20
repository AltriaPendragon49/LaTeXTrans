## MODIFIED Requirements

### Requirement: Responsive Web Dashboard

The system MUST provide a responsive translation workspace while allowing the product shell to become community-first. Translation capabilities SHALL remain first-class, but the dashboard SHALL no longer define the application's primary identity.

#### Scenario: User navigates to the translation workspace
- **WHEN** the user accesses `/translate`
- **THEN** the translation workspace SHALL be displayed as its own route page
- **AND** shared navigation SHALL remain available
- **AND** the previous translation capabilities for arXiv input, upload, batch translation, and advanced configuration SHALL remain accessible

#### Scenario: Legacy tools entry remains compatible during migration
- **WHEN** the user accesses a legacy tools entry such as `/tools?panel=translate`
- **THEN** the frontend MAY redirect or bridge that route to the canonical translation workspace
- **AND** the translation workflow SHALL remain reachable during rollout

### Requirement: User-visible static UI copy uses centralized i18n resources

All non-diagnostic user-visible frontend copy MUST come from centralized i18n resources instead of hardcoded strings.

#### Scenario: Main pages render localized UI copy
- **WHEN** the user visits the community homepage, paper detail, translation workspace, workspace history, workspace settings, workspace glossary, processing, preview, login, or profile
- **THEN** titles, buttons, descriptions, empty states, toast copy, and accessibility text MUST be resolved from locale resources
- **AND** changing the active UI language MUST update those strings consistently

### Requirement: Shared shell prioritizes community and minimizes operational complexity

The frontend shared shell SHALL foreground community discovery and reading while preserving translation as an explicit primary action for authenticated users.

#### Scenario: Community is the primary shell destination
- **WHEN** a user enters the shared frontend shell
- **THEN** the shell SHALL make the community homepage the primary first-level destination
- **AND** translation SHALL remain a visible top-level route rather than a hidden utility

#### Scenario: Shared shell uses a persistent readable navigation instead of a hover-expand rail
- **WHEN** the shared shell renders on desktop
- **THEN** the left navigation SHALL reserve stable space with readable labels by default
- **AND** it SHALL not depend on hover expansion to become understandable

#### Scenario: Admin capabilities appear in the main navigation only for admins
- **WHEN** an admin user renders the shared shell
- **THEN** the main navigation SHALL include admin curation and admin task entries
- **AND** those entries SHALL remain hidden for non-admin users

### Requirement: Anonymous users are browse and read only

The shared shell SHALL allow unauthenticated users to explore community papers and read paper detail, while gating translation and persistent workspace capabilities behind login.

#### Scenario: Guest opens the community homepage
- **WHEN** an unauthenticated user visits `/`
- **THEN** the homepage SHALL remain usable for search, browse, and paper discovery

#### Scenario: Guest opens paper detail
- **WHEN** an unauthenticated user visits `/paper/:paperId`
- **THEN** the reading experience SHALL remain available
- **AND** the page SHALL not require login merely to browse and read

#### Scenario: Guest attempts to access translation or workspace routes
- **WHEN** an unauthenticated user opens `/translate`, `/workspace/history`, `/workspace/settings`, or `/workspace/glossary`
- **THEN** the frontend SHALL prompt or redirect the user into the local login flow
- **AND** those routes SHALL not behave as anonymous-first product surfaces
