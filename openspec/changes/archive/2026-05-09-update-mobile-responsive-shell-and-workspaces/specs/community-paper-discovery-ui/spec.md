## ADDED Requirements
### Requirement: Community discovery controls remain conflict-free on mobile
The community discovery surface SHALL provide a narrow-screen layout that preserves browse capability without relying on the desktop sidebar or cramped control rows.

#### Scenario: Mobile homepage uses single-column discovery framing
- **WHEN** a user opens the community homepage on a narrow/mobile viewport
- **THEN** the page SHALL render its hero, search, sort, and feed content in a single-column flow
- **AND** the browse controls SHALL not overlap, clip, or compete for the same horizontal space

#### Scenario: Mobile discovery shell uses shared bottom navigation
- **WHEN** the community discovery routes render on a narrow/mobile viewport
- **THEN** navigation to first-level destinations SHALL use the shared four-item bottom navigation
- **AND** the previous left-rail shell SHALL not consume persistent reading width on those screens
