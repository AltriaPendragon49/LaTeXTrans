## ADDED Requirements
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
