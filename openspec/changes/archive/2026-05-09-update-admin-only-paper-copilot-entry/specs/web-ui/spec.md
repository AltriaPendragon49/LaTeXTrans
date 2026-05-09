## ADDED Requirements
### Requirement: Shared shell exposes Paper Copilot only to admins
The shared shell SHALL show a dedicated `Paper Copilot` navigation entry only for authenticated admin users, and it SHALL place that entry directly below `Paper Tool`.

#### Scenario: Authenticated admin sees the Paper Copilot entry
- **WHEN** an authenticated user with an admin role renders the shared desktop shell
- **THEN** the main sidebar SHALL show a `Paper Copilot` navigation item below `Paper Tool`
- **AND** activating that item SHALL navigate to the retained conversation workspace.

#### Scenario: Guest or non-admin user renders the shared shell
- **WHEN** the shell renders for a guest or an authenticated user without an admin role
- **THEN** the `Paper Copilot` navigation item SHALL remain hidden
- **AND** public community, favorites, and paper-tool navigation behavior SHALL remain unchanged.

### Requirement: Community conversation route enforces admin access
The web UI SHALL protect `/agent` conversation routes so only authenticated admin users can access the retained Paper Copilot workspace.

#### Scenario: Guest opens an agent route
- **WHEN** an unauthenticated user opens `/agent` or `/agent/:conversationId`
- **THEN** the frontend SHALL redirect that user to `/login`
- **AND** it SHALL not render the retained conversation workspace before login.

#### Scenario: Authenticated non-admin user opens an agent route
- **WHEN** an authenticated user without an admin role opens `/agent` or `/agent/:conversationId`
- **THEN** the frontend SHALL redirect that user to `/tools`
- **AND** it SHALL not render the retained conversation workspace for that session.

### Requirement: Admin Paper Copilot workspace keeps the current structure while improving polish
The community conversation workspace SHALL keep its current rail-plus-main-panel structure while presenting a more refined admin-facing Paper Copilot visual treatment.

#### Scenario: Admin opens the Paper Copilot workspace
- **WHEN** an authenticated admin user opens the retained conversation workspace
- **THEN** the layout SHALL preserve the existing conversation rail, header, message thread, and composer structure
- **AND** the header, chat bubbles, metadata surfaces, and composer SHALL use a more polished visual hierarchy than the current baseline presentation.
