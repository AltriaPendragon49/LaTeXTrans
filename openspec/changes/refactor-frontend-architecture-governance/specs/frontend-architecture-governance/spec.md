## ADDED Requirements

### Requirement: Frontend architecture SHALL be expressed through file paths

The frontend SHALL use file paths as the primary expression of architectural responsibility so contributors can infer ownership and layering from directory placement alone.

#### Scenario: Contributor classifies a new module
- **WHEN** a contributor adds or moves frontend code
- **THEN** the chosen path SHALL communicate whether the module is a UI primitive, a reusable business feature, or a route-local page concern
- **AND** directory placement SHALL be treated as an architecture decision rather than a cosmetic file move

### Requirement: Page routes SHALL remain route-composition boundaries

Frontend pages SHALL represent route-composition boundaries and SHALL NOT be reused as generic leaf components by other pages.

#### Scenario: A route needs another route's reusable content
- **WHEN** one route needs capability already present inside another page
- **THEN** the shared capability SHALL be extracted into a feature or page-local child component
- **AND** the consuming route SHALL NOT import the other page's top-level route component as a normal reusable child

### Requirement: Component placement SHALL follow business-semantic classification rules

Frontend components SHALL be placed according to whether they are domain-agnostic primitives, reusable business modules, or page-private composition pieces.

#### Scenario: Classifying a reusable generic component
- **WHEN** a component has no business semantics and is reusable across unrelated flows
- **THEN** it SHALL be placed under `src/ui/`

#### Scenario: Classifying a reusable business component
- **WHEN** a component has business semantics and is reused across multiple pages within a domain
- **THEN** it SHALL be placed under `src/features/<feature>/components/`

#### Scenario: Classifying a page-private component
- **WHEN** a component only serves one route and depends on that route's local composition context
- **THEN** it SHALL be placed under `src/pages/<page>/components/`

### Requirement: Hook and utility placement SHALL follow ownership boundaries

Hooks and utilities SHALL be colocated with the narrowest valid ownership boundary that can explain their responsibility.

#### Scenario: Route-local hook
- **WHEN** a hook only supports one route
- **THEN** it SHALL be placed under `src/pages/<page>/hooks/`

#### Scenario: Feature-scoped hook
- **WHEN** a hook provides reusable business behavior across multiple pages in one feature
- **THEN** it SHALL be placed under `src/features/<feature>/hooks/`

#### Scenario: Domain-agnostic helper
- **WHEN** a hook or utility is broadly reusable and domain-agnostic
- **THEN** it MAY remain under shared top-level `hooks/` or `utils/`
- **AND** it SHALL NOT depend on feature-specific domain models

### Requirement: Frontend naming SHALL encode responsibility clearly

Frontend directory and module names SHALL describe product responsibility clearly enough that humans and AI agents can classify them without inspecting internals first.

#### Scenario: Naming page directories
- **WHEN** a page directory is created or renamed
- **THEN** it SHALL use a route- or scenario-based name that reflects the page's responsibility
- **AND** it SHALL avoid ambiguous names where two pages represent different concerns

#### Scenario: Naming feature directories
- **WHEN** a feature directory is created or renamed
- **THEN** it SHALL use a business-domain name such as `community-paper` or `translation-workflow`
- **AND** it SHALL avoid generic buckets that do not communicate domain responsibility

### Requirement: Early migrations SHALL preserve behavior and compatibility

Early frontend architecture migrations SHALL preserve existing behavior and SHALL allow temporary compatibility layers while structure is being normalized.

#### Scenario: First-pass architecture migration
- **WHEN** a migration step is part of the first-pass architecture normalization
- **THEN** it MAY move files, split mixed-responsibility files, and add compatibility re-exports
- **AND** it SHALL NOT intentionally change business behavior in the same step without separate approval

#### Scenario: Import paths are in transition
- **WHEN** existing modules are moved to their target architecture paths
- **THEN** the migration MAY keep old import paths working through temporary re-exports
- **AND** old paths SHALL only be removed after the new structure is validated for the affected page or feature

### Requirement: Migration steps SHALL avoid bundled multi-axis rewrites

A single frontend migration step SHALL keep scope narrow enough that architectural relocation does not become mixed with unrelated redesign or contract churn.

#### Scenario: Planning a migration step
- **WHEN** a contributor defines a migration step
- **THEN** that step SHALL NOT combine structural relocation, UI redesign, state-model rewrite, and API-contract rewrite in one pass
- **AND** the step SHALL focus on one dominant migration concern at a time

### Requirement: Refactor scope SHALL avoid unnecessary fragmentation

The frontend refactor SHALL avoid splitting modules into smaller files unless the split creates a real ownership or readability improvement.

#### Scenario: Evaluating whether to split a file
- **WHEN** a file is already small, readable, and single-purpose
- **THEN** the refactor SHALL leave it intact
- **AND** it SHALL NOT be split solely to satisfy a folder shape

#### Scenario: A file mixes multiple responsibilities
- **WHEN** a file combines UI presentation, state orchestration, and request behavior or otherwise spans multiple unrelated concerns
- **THEN** the refactor SHALL treat it as a valid split candidate
- **AND** the resulting pieces SHALL be placed according to the approved ownership boundaries
