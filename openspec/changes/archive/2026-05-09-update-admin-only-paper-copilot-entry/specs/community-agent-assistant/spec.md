## MODIFIED Requirements
### Requirement: Community agent runtime can stay retained while product UI entry points are hidden
The community agent runtime SHALL remain restorable from retained code assets even when the product hides its public homepage, paper-detail, and ordinary-user sidebar entry points, while still allowing authenticated admins to access the retained conversation workspace through an admin-scoped product entry.

#### Scenario: Product hides public agent UI entry points from non-admin users
- **WHEN** the current product configuration hides the homepage agent composer, paper-detail public copilot pane, and ordinary-user shared-shell affordances
- **THEN** the retained backend runtime code and underlying tool-calling services SHALL remain present in the codebase
- **AND** guests and authenticated non-admin users SHALL NOT be able to use those product agent flows directly in the current hidden mode.

#### Scenario: Authenticated admin restores the retained workspace through the shell
- **WHEN** an authenticated user with an admin role opens the shared shell
- **THEN** the product SHALL expose a dedicated admin-scoped entry into the retained agent conversation workspace
- **AND** later recovery of that UI entry SHALL not require reintroducing deleted runtime code.
