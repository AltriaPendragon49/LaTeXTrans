## MODIFIED Requirements

### Requirement: Community feed homepage route

The community homepage SHALL remain the primary application entry and SHALL evolve into a magazine-like discovery surface that prioritizes internal paper exploration while preserving the existing search and feed capability.

#### Scenario: Homepage uses internal community search as the top interaction
- **WHEN** a user lands on the community homepage
- **THEN** the page SHALL present a search-first surface for internal community paper lookup
- **AND** that search surface SHALL match community papers by `arXiv ID`, title, author, and abstract fields
- **AND** it SHALL only search formal public community papers
- **AND** it SHALL exclude ordinary tool results, incomplete curation items, and deleting or deleted papers

#### Scenario: Homepage adopts a stronger editorial hierarchy
- **WHEN** the homepage renders after this rollout
- **THEN** the page MAY significantly redesign its visual language, typography, spacing, hero treatment, and feed framing
- **AND** it SHALL still preserve the functional ability to browse, sort, and open papers without reducing capability

#### Scenario: Feed cards expose direct research actions
- **WHEN** a public paper card is rendered on the homepage
- **THEN** the card SHALL expose direct actions for downloading the source PDF, downloading the translated PDF when available, opening the canonical arXiv page, and opening the associated GitHub repository when available
- **AND** those actions SHALL reuse the shared `ui/` primitive layer instead of introducing card-local button patterns

### Requirement: Translation workspace relocation compatibility

The discovery UI SHALL keep the direct translation workflow as a first-class route while removing `ToolsHub` as the long-term architecture center.

#### Scenario: User needs the explicit direct translation workflow
- **WHEN** the user chooses to translate content directly
- **THEN** the UI SHALL provide that workflow through the canonical `/translate` route
- **AND** the community homepage SHALL not be forced to carry the entire translation workbench as its primary first-screen surface

#### Scenario: Legacy tools routes remain compatible during migration
- **WHEN** the user accesses `/tools`, `/translate`, `/history`, `/settings`, or `/glossary` through legacy entry behavior
- **THEN** the UI MAY redirect to canonical workspace routes
- **AND** the old architecture SHALL not remain the long-term source of truth
