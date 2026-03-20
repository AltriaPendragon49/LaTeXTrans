## MODIFIED Requirements

### Requirement: Community feed homepage route
The system SHALL expose the community Feed as the primary web homepage and present it as a research-discovery surface rather than a translation form.

#### Scenario: Open the product homepage
- **WHEN** a user navigates to `/`
- **THEN** the system SHALL render the community Feed homepage shell
- **AND** the page SHALL visually prioritize browseable community papers over translation inputs
- **AND** the default experience SHALL preserve the restrained dark research-reading direction inspired by alphaXiv without reproducing alphaXiv branding or navigation structure.

#### Scenario: Switch community browsing to daytime mode
- **WHEN** a user changes the shared shell theme from dark to day mode
- **THEN** the community feed and paper detail surfaces SHALL adopt a bright, white-led reading palette
- **AND** cards, toolbars, metadata chips, and preview surfaces SHALL remain visually grouped without depending on dark-only contrast tricks
- **AND** the daytime mode SHALL preserve the same browse and reading information hierarchy as dark mode.
