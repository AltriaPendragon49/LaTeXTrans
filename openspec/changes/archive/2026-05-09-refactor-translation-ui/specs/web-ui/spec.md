## MODIFIED Requirements

### Requirement: Translation Workspace UX MUST implement a seamless, cardless layout
The Translation Workspace MUST omit any boxed components (e.g. Card, PanelShell) to form a seamless content layout that visually integrates with the surrounding sidebar framework without structural borders.

#### Scenario: User loads the Translation Workspace
- Given the user navigates to `/translate`
- When the page renders
- Then the main components (input, configuration, actions) are laid out seamlessly against the page shell without nested `Card` wrappers
- And the tab headers align with the page topography seamlessly

### Requirement: History Workspace UX MUST use an unboxed data layout
The UI components rendering the History Workspace MUST dispense with drop shadows, explicit card boundaries, and visually segregated rows, instead adopting an edge-to-edge layout design for greater coherence.

#### Scenario: User views the Translation History list
- Given the user has translation tasks in their history
- When the user navigates to `/workspace/history`
- Then the `DataTable` must span the container without outer borders or drop shadows
- And the expanded rows must use flattened configuration lists rather than nested `PanelShell` elements
