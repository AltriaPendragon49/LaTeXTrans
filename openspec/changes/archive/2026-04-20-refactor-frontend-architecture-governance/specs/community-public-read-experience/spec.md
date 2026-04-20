## MODIFIED Requirements

### Requirement: Reader exposes explicit source and translated mode control

The public reader SHALL let users intentionally switch between English-source and translated reading whenever both modes are available, while operating inside the new community-first application shell.

#### Scenario: Both English and translated readers exist
- **WHEN** a paper has both source-readable and translated-readable modes
- **THEN** the detail page SHALL expose explicit mode switches for `英文`, `译文 PDF`, `译文 HTML`, and `中英双栏对照` in that order whenever the underlying assets for those modes are available
- **AND** changing modes SHALL preserve the existing reader-first shell instead of leaving the paper detail workflow

#### Scenario: Reader remains available to anonymous users
- **WHEN** an unauthenticated user opens a paper detail page
- **THEN** the detail route SHALL remain readable inside the community shell
- **AND** login SHALL not be required merely to consume public reading content

## ADDED Requirements

### Requirement: Paper detail uses a coordinated dual-pane copilot workspace

The web UI SHALL present paper detail as a coordinated dual-pane workspace with a reading-dominant pane and a persistent paper-scoped support pane, integrated into the new editorial application shell.

#### Scenario: Desktop paper detail keeps both panes visible
- **WHEN** the user opens the paper detail page on a desktop-width viewport
- **THEN** the reader SHALL remain the dominant pane
- **AND** the support pane SHALL stay visible without visually displacing the reader from its primary role

#### Scenario: Shell redesign does not reduce paper-detail capability
- **WHEN** the paper detail page is migrated into the new community-first shell
- **THEN** translated mode controls, insights, similar-paper support, and reader-first behavior SHALL remain available
- **AND** the redesign SHALL not reduce current paper-detail functionality
