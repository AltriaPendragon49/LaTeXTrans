## MODIFIED Requirements

### Requirement: Community feed homepage route
The system SHALL expose the community Feed as the primary web homepage and present it as a research-discovery surface rather than a translation form.

#### Scenario: Open the product homepage
- **WHEN** a user navigates to `/`
- **THEN** the system SHALL render the community Feed homepage shell
- **AND** the page SHALL visually prioritize browseable community papers over translation inputs
- **AND** the design SHALL follow a restrained dark research-reading direction inspired by alphaXiv without reproducing alphaXiv branding or navigation structure.

#### Scenario: Homepage first-screen discovery is ready without an empty boot gap
- **WHEN** a user opens the public homepage on a normal healthy deployment
- **THEN** the system SHALL provide first-screen discovery content through an initial-document payload, equivalent bootstrap data, or another non-empty first-load strategy
- **AND** the page SHALL NOT depend on a fully blank client-only boot path before any paper discovery content can appear.

#### Scenario: Initial homepage load is not delayed by search debounce
- **WHEN** the homepage performs its first public feed load for the current route
- **THEN** the system SHALL request or apply the initial feed payload immediately
- **AND** typing-oriented search debounce SHALL only apply to subsequent user query refinement.
