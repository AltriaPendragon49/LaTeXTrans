## ADDED Requirements

### Requirement: Shared shell supports persistent day and dark themes
The frontend SHALL provide a shared theme preference for the application shell so users can switch between a bright daytime interface and the existing dark presentation.

#### Scenario: Default shell keeps the current dark presentation
- **WHEN** a user opens the frontend without a previously saved theme preference
- **THEN** the shared shell SHALL render with the current dark visual system by default
- **AND** the default SHALL preserve the existing dark-first information hierarchy.

#### Scenario: User switches the shell theme
- **WHEN** a user activates the shared theme toggle from the shell header
- **THEN** the frontend SHALL switch between `dark` and `light` themes without a full page reload
- **AND** the toggle copy and icon treatment SHALL remain accessible in both modes.

#### Scenario: Theme preference persists across navigation
- **WHEN** a user selects either day or dark mode
- **THEN** the frontend SHALL persist that preference for later visits
- **AND** navigating between `/`, `/paper/:paperId`, `/translate`, and other shared-shell routes SHALL keep the selected theme active.
