## ADDED Requirements
### Requirement: Web Translation APIs Default To Origin CLI Parity
The web API SHALL start translation tasks with the origin CLI parity kernel unless a future approved spec introduces another default.

#### Scenario: Uploaded file translation uses parity
- **WHEN** a user starts translation for an uploaded archive or source directory through the web API
- **THEN** the task SHALL run with `origin_cli_parity` as its effective translation core.

#### Scenario: Direct arXiv translation uses parity
- **WHEN** a user starts translation from an arXiv id through the web API
- **THEN** the task SHALL run with `origin_cli_parity` as its effective translation core after source download and extraction.

#### Scenario: Effective config is visible
- **WHEN** a web API translation task captures its runtime config
- **THEN** the snapshot SHALL include the effective parity mode
- **AND** it SHALL indicate that modern backend translation systems are not invoked for that task.
