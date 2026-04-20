# frontend-architecture-governance Specification

## Purpose
TBD - created by archiving change refactor-frontend-architecture-governance. Update Purpose after archive.
## Requirements
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

### Requirement: Reusable UI primitives SHALL be normalized through a Uiverse-first adoption workflow

The frontend SHALL evaluate Uiverse as the first sourcing option for generic UI primitives and SHALL adapt selected patterns into the repository's own `src/ui/` system before product use.

#### Scenario: A new reusable primitive is needed
- **WHEN** the rollout needs a sidebar, button, input, tabs, search surface, card, sheet, or similarly generic primitive
- **THEN** contributors SHALL check Uiverse first for a suitable starting pattern
- **AND** any chosen pattern SHALL be refactored into the local `src/ui/` layer with the project's own tokens, accessibility, and interaction conventions
- **AND** feature pages SHALL NOT paste raw Uiverse snippets directly as product code

#### Scenario: No suitable Uiverse pattern exists
- **WHEN** no Uiverse pattern meets the product need or integration constraints
- **THEN** the project MAY implement a local primitive directly
- **AND** that primitive SHALL still live under `src/ui/` when it is domain-agnostic

### Requirement: Shared presentation shells SHALL be normalized under `src/ui/`

The frontend SHALL treat domain-agnostic composition shells such as page intros, state panels, filter toolbars, notice banners, upload surfaces, and section wrappers as part of the governed `src/ui/` layer rather than page-local styling utilities.

#### Scenario: A repeated page shell appears across multiple routes
- **WHEN** multiple pages need the same structural pattern for route headers, empty or error states, banners, segmented filters, or section framing
- **THEN** that pattern SHALL be implemented or promoted under `src/ui/`
- **AND** consuming pages SHALL configure it with content and actions instead of recreating the visual contract locally

#### Scenario: A page already has a governed shell available
- **WHEN** a page needs behavior already covered by a governed shell in `src/ui/`
- **THEN** the page SHALL reuse the existing shell
- **AND** it SHALL NOT introduce a parallel page-local version unless the existing shell cannot support the requirement without breaking shared semantics

### Requirement: Full rollout steps SHALL preserve behavior coverage while allowing shell-level change

The full frontend rollout MAY change visual language, route organization, shell hierarchy, and internal state composition, but it SHALL preserve feature coverage.

#### Scenario: A route or page is redesigned
- **WHEN** a page is reorganized, renamed, or moved during the rollout
- **THEN** its capability set SHALL remain available to users through the new shell
- **AND** the rollout SHALL not remove existing business-critical functionality as a side effect of architecture cleanup

### Requirement: Migration steps SHALL avoid unnecessary fragmentation

The frontend refactor SHALL avoid splitting modules into smaller files unless the split creates a real ownership or readability improvement.

#### Scenario: Evaluating whether to split a file
- **WHEN** a file is already small, readable, and single-purpose
- **THEN** the refactor SHALL leave it intact
- **AND** it SHALL NOT be split solely to satisfy a folder shape

#### Scenario: A file mixes multiple responsibilities
- **WHEN** a file combines UI presentation, state orchestration, and request behavior or otherwise spans multiple unrelated concerns
- **THEN** the refactor SHALL treat it as a valid split candidate
- **AND** the resulting pieces SHALL be placed according to the approved ownership boundaries

