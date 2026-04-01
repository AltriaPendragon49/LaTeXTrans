## ADDED Requirements

### Requirement: Paper detail preview math keeps readable fallback rendering
The web UI SHALL keep paper detail preview math readable when asynchronous preview enhancement is unavailable or partially fails.

#### Scenario: Preview enhancement throws while math blocks are present
- **WHEN** the paper detail reader enhancement pipeline fails for a preview containing `.paper-preview__math-block`
- **THEN** the UI SHALL run a fallback math rendering pass for those blocks
- **AND** the user SHALL still see readable formulas in the current session.

#### Scenario: Enhancement completes but math blocks remain unhydrated
- **WHEN** preview enhancement returns without producing KaTeX-rendered nodes while `.paper-preview__math-block` nodes still exist
- **THEN** the UI SHALL perform fallback rendering for remaining unhydrated math blocks
- **AND** the reader SHALL not expose raw math source as final visible output.
