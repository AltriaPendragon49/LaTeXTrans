## ADDED Requirements

### Requirement: Shared shell prioritizes community and minimizes operational complexity
The frontend shared shell SHALL foreground the community reading flow and minimize the need for users to think in terms of separate operational modes or tool surfaces.

#### Scenario: Community is the primary shell destination
- **WHEN** a user enters the authenticated/shared frontend shell
- **THEN** the shell SHALL make the community homepage the primary first-level destination
- **AND** the legacy translation-oriented pages SHALL remain available through a secondary tools entry rather than competing equally with the community shell.

#### Scenario: Shared shell uses a compact navigation rail
- **WHEN** the shared shell renders on desktop
- **THEN** the left navigation SHALL behave like a compact research rail rather than a wide dashboard sidebar
- **AND** the main content canvas SHALL remain visually dominant.

#### Scenario: Sidebar and canvas remain spatially coordinated
- **WHEN** the shared shell renders the community layout
- **THEN** the sidebar SHALL reserve space with visible labels instead of collapsing into an unlabeled icon strip
- **AND** the main content SHALL not be visually overlapped or cramped by the navigation rail.

#### Scenario: Agent shell preserves per-user conversation history
- **WHEN** an authenticated user uses the agent workspace
- **THEN** the shared shell SHALL preserve access to saved conversations for that user
- **AND** creating a new chat SHALL remain lightweight and not reset the overall shell structure.

#### Scenario: Tools hub preserves the old direct translation workflow
- **WHEN** a user opens the tools hub
- **THEN** the translation tool SHALL still expose the old direct translation workflow as a first-class utility
- **AND** community-first navigation SHALL not erase that explicit tool path.
