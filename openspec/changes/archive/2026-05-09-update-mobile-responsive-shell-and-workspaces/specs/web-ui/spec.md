## ADDED Requirements
### Requirement: Shared shell provides a mobile bottom-navigation layout
The frontend shared shell SHALL provide an explicit narrow-screen navigation model instead of compressing the desktop sidebar into the mobile viewport.

#### Scenario: Narrow screen enters the shared shell
- **WHEN** a user opens a shared-shell route on a narrow/mobile viewport
- **THEN** the UI SHALL replace the desktop sidebar-first layout with a mobile shell that uses a top action region and a fixed bottom navigation
- **AND** that bottom navigation SHALL expose exactly four primary destinations
- **AND** the page content SHALL reserve safe-area-aware space so bottom navigation does not overlap interactive content

#### Scenario: Desktop shell remains unchanged in principle
- **WHEN** a user opens a shared-shell route on a desktop-width viewport
- **THEN** the UI SHALL continue using the desktop navigation model
- **AND** the mobile bottom-navigation pattern SHALL not displace the desktop reading and workspace layout

### Requirement: Route families use explicit mobile degradation patterns
The frontend SHALL apply consistent responsive layout rules across public, workflow, workspace, and admin route families instead of squeezing desktop compositions onto narrow screens.

#### Scenario: Public browse routes render on narrow screens
- **WHEN** a user opens public browse routes such as `/`, `/tools`, `/favorites`, `/profile`, or `/login` on a narrow/mobile viewport
- **THEN** those pages SHALL render as single-column mobile-safe compositions
- **AND** search, filters, and primary actions SHALL stack or wrap without overlapping

#### Scenario: Workflow and workspace routes render on narrow screens
- **WHEN** a user opens workflow or workspace routes such as `/translate`, `/processing`, `/workspace/history`, `/workspace/settings`, or `/workspace/glossary` on a narrow/mobile viewport
- **THEN** the UI SHALL prioritize the primary task or record content in a stacked layout
- **AND** secondary controls, logs, or configuration panels SHALL move into collapsible, tabbed, or subsequent stacked sections rather than stay in competing side-by-side regions

#### Scenario: Admin routes render on narrow screens
- **WHEN** an admin user opens `/admin/curation`, `/admin/curation/tasks`, or `/agent` on a narrow/mobile viewport
- **THEN** the UI SHALL preserve route capability with mobile-safe stacked layouts
- **AND** desktop tables, rails, or multi-column controls SHALL degrade into cards, expansions, drawers, or stacked action groups instead of remaining horizontally compressed
