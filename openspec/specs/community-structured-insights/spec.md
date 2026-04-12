# community-structured-insights Specification

## Purpose
TBD - created by archiving change update-community-admin-curation-flow. Update Purpose after archive.
## Requirements
### Requirement: Paper guides use a fixed five-module system-owned structure
The system SHALL represent prepared paper guides with a fixed five-module structure instead of free-form sidebar content or model-defined schemas.

#### Scenario: Curated paper stores five fixed modules
- **WHEN** the system prepares paper guides for a community paper
- **THEN** it SHALL store content for `problem`, `solution`, `innovation`, `experiment`, and `future`
- **AND** each module SHALL be stored under `guide_sections.<key>` as a system-owned object containing at least `content`
- **AND** the detail UI SHALL render those same five modules in a stable order.

### Requirement: Paper guides are generated from title, abstract, and translated paper excerpts
The system SHALL generate paper-guide content from `title + abstract + module-relevant translated excerpts` rather than from only metadata or one shared full-paper payload.

#### Scenario: Curation prepares module-specific analysis input
- **WHEN** the system starts paper-guide generation for a translated community paper
- **THEN** it SHALL include `title + abstract` in every module input as a shared semantic anchor
- **AND** it SHALL prepare module-specific analysis input from the translated paper body
- **AND** it SHALL not treat one shared full-paper payload as the normal source for all modules.

### Requirement: Paper guides are Chinese-only in this version
The system SHALL persist and display a Chinese-only paper-guide package in this version.

#### Scenario: User switches reader modes
- **WHEN** the paper detail page switches between source and translated reader modes
- **THEN** the guide pane SHALL continue to display the same persisted Chinese guide package
- **AND** the guide pane SHALL not require an English variant for this version.

### Requirement: Five-module guide generation is required before curated publication
Five-module paper-guide generation SHALL be part of the admin curation completion gate for new public community papers.

#### Scenario: Guide generation succeeds during admin curation
- **WHEN** admin curation reaches the paper-guide stage successfully
- **THEN** that stage SHALL count toward the paper's complete publication-ready state
- **AND** the paper MAY proceed toward public visibility if the other required stages are also complete.

#### Scenario: Any guide module remains unavailable
- **WHEN** admin curation fails to produce all five required modules with `guide_sections.<key>.content` that is present, non-empty after trimming, minimally readable, and not an exact duplicate of another module
- **THEN** the paper SHALL remain outside the public community feed
- **AND** the system SHALL not publish the paper as a formal curated community item.

### Requirement: Guide generation uses independent module prompts
The system SHALL generate paper guides through explicit backend-owned prompts where the system controls structure and the model returns only module content.

#### Scenario: One module generation fails
- **WHEN** one module generation attempt fails or returns empty content
- **THEN** the backend SHALL retry that module independently
- **AND** it SHALL not require regenerating the other already-successful modules.

### Requirement: Guide generation supports bounded fallback
The system SHALL support bounded fallback content generation so transient LLM instability does not permanently deadlock publication.

#### Scenario: Module fallback is used after retries
- **WHEN** a module still fails after the configured retries
- **THEN** the system SHALL generate or derive a simplified Chinese fallback for that module from trusted translated paper inputs
- **AND** the fallback path SHALL write a displayable Chinese body text into that module's `content`
- **AND** that module MAY count as complete only if its stored `content` passes the same minimum readability checks as normal generation.

### Requirement: Detail pane uses collapsible guide modules
The paper-detail UI SHALL render the five modules as compact accordion-style sections that can expand and collapse inside the existing right-side pane.

#### Scenario: User opens a guide module
- **WHEN** the user selects one guide module in the right-side pane
- **THEN** the selected module SHALL expand to reveal its markdown/text content
- **AND** the pane SHALL remain usable within the narrower right-side layout.

### Requirement: New guide prompts enforce module boundaries
The guide pipeline SHALL keep module intent boundaries explicit so the five modules do not collapse into one another.

#### Scenario: Solution and innovation stay distinct
- **WHEN** the system generates `solution` and `innovation`
- **THEN** `solution` SHALL explain how the method works
- **AND** `innovation` SHALL explain what is fundamentally new compared with prior work
- **AND** the pipeline SHALL reject or retry outputs that collapse into identical content.

### Requirement: Legacy or degraded papers show a compact guide placeholder
The system SHALL allow a placeholder state for visible papers that do not yet have prepared guides in the new pipeline.

#### Scenario: Visible paper has no prepared guides
- **WHEN** a visible paper detail page lacks prepared guides outside the normal curated-success path
- **THEN** the right-side pane SHALL show a compact Chinese guide not-ready placeholder
- **AND** the paper detail page SHALL remain readable without exposing a public copilot fallback in that pane.

### Requirement: Paper guides are system-generated and read-only in this version
The current version SHALL treat paper guides as system-generated content and SHALL not expose end-user editing for those modules.

#### Scenario: User views or expands a guide module
- **WHEN** a user interacts with the guide pane in the current version
- **THEN** the pane SHALL expose read-only generated content
- **AND** the current version SHALL not require inline editing controls for those modules.

### Requirement: Structured insight reads expose a normalized rendering contract
The structured-insight read path SHALL normalize stored guide text into deterministic rendering fields so the detail UI can render stable hierarchy without depending on the raw model formatting.

#### Scenario: Guide content contains recognizable subheadings
- **WHEN** a stored guide module contains readable text with supported subheadings
- **THEN** the API SHALL return the original normalized text as `raw_content`
- **AND** it SHALL split that text into ordered `blocks` with stable `heading` and `content` fields
- **AND** it MAY return leading prose before the first block as `summary`.

#### Scenario: Guide content does not match the preferred heading format
- **WHEN** a stored guide module contains usable text but no recognizable subheading boundaries
- **THEN** the API SHALL still return `raw_content`
- **AND** it SHALL provide one fallback block so the UI can render the module without flattening all content into one undifferentiated paragraph.

