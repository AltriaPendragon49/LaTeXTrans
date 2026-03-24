## MODIFIED Requirements

### Requirement: Unified paper submit API
The community paper intake layer SHALL support silent import/reuse for arXiv papers so the community flow can create readable English paper pages without an extra confirmation step.

#### Scenario: Import an arXiv paper into the community flow
- **WHEN** the system needs to bring an arXiv paper into the community as part of discovery, agent conversation, or detail-flow translation
- **THEN** the intake layer SHALL reuse an existing community paper when possible or create a new one when needed
- **AND** the resulting paper SHALL be usable by the community detail flow as an English-readable paper before translated output exists.

### Requirement: Community paper detail contract
The community paper detail contract SHALL distinguish readable English-source state from translated-reader state and SHALL not equate compile failure with total translated unreadability.

#### Scenario: Detail contract exposes best available readable mode
- **WHEN** a public community paper has English HTML, English PDF, translated HTML, or translated PDF artifacts in any healthy or degraded combination
- **THEN** the detail contract SHALL expose the best available readable mode and its fallback options
- **AND** the frontend SHALL not need to infer that state from raw paper status alone.

#### Scenario: Failed task still yields readable artifacts
- **WHEN** a terminal translation task still produced translated preview or translated PDF artifacts
- **THEN** the detail contract SHALL surface those artifacts as readable output
- **AND** the paper SHALL not be represented as fully untranslated just because compile validation failed.
