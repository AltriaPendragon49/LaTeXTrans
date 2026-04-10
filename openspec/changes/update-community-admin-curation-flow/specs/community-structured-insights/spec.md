## ADDED Requirements
### Requirement: Structured paper insights use a fixed six-section schema
The system SHALL represent prepared paper insights with a fixed section schema instead of free-form sidebar content.

#### Scenario: Curated paper stores structured insights
- **WHEN** the system prepares structured insights for a community paper
- **THEN** it SHALL store content for `problem`, `method`, `key_idea`, `experiment`, `result`, and `limitation`
- **AND** each section SHALL include at least language-aligned `summary`, `bullets`, `body`, `status`, and `updated_at` fields
- **AND** the detail UI SHALL render those same six sections in a stable order.

### Requirement: Structured insights are bilingual and follow reader mode
The system SHALL store language-aligned structured insight content and display the version that matches the current reader mode.

#### Scenario: User reads source mode
- **WHEN** the paper detail page is in English/source reading mode
- **THEN** the structured-insight pane SHALL show the English version of each section
- **AND** switching sections SHALL not require a separate language toggle.

#### Scenario: User reads translated mode
- **WHEN** the paper detail page is in translated reading mode
- **THEN** the structured-insight pane SHALL show the Chinese version of each section
- **AND** the pane SHALL remain aligned with the translated reading experience.

#### Scenario: Required language variant is unavailable on a visible legacy paper
- **WHEN** a visible paper needs a structured-insight language variant that is unavailable
- **THEN** the pane SHALL show an explicit not-ready placeholder for that section language
- **AND** it SHALL not silently fall back to the other language variant.

### Requirement: Structured insights are required before curated publication
Structured insight generation SHALL be part of the admin curation completion gate for new public community papers.

#### Scenario: Insight generation succeeds during admin curation
- **WHEN** admin curation reaches the structured insight stage successfully
- **THEN** that stage SHALL count toward the paper's complete publication-ready state
- **AND** the paper MAY proceed toward public visibility if the other required stages are also complete.

#### Scenario: Insight generation fails during admin curation
- **WHEN** admin curation fails to produce the required structured insights
- **THEN** the paper SHALL remain outside the public community feed
- **AND** the system SHALL not publish the paper as a formal curated community item.

### Requirement: Detail pane uses collapsible structured-insight modules
The paper-detail UI SHALL render the six structured sections as compact modules that can expand and collapse inside the existing right-side pane.

#### Scenario: User opens a structured section
- **WHEN** the user selects one structured-insight section in the right-side pane
- **THEN** the selected section SHALL expand to reveal its content
- **AND** the pane SHALL remain usable within the narrower right-side layout.

### Requirement: Legacy or degraded papers show a compact insight placeholder
The system SHALL allow a placeholder state for visible papers that predate the new curation pipeline or otherwise lack prepared structured insights.

#### Scenario: Visible paper has no prepared insights
- **WHEN** a visible paper detail page lacks prepared structured insights outside the normal curated-success path
- **THEN** the right-side pane SHALL show a compact “not ready” placeholder
- **AND** the paper detail page SHALL remain readable without exposing a public copilot fallback in that pane.

### Requirement: Structured insights are system-generated and read-only in this version
The current version SHALL treat structured insights as system-generated content and SHALL not expose end-user editing for those sections.

#### Scenario: User views or expands a structured-insight section
- **WHEN** a user interacts with the structured-insight pane in the current version
- **THEN** the pane SHALL expose read-only generated content
- **AND** the current version SHALL not require inline editing controls for those sections.
