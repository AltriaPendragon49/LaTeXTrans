## ADDED Requirements
### Requirement: Community Paper Translation Bridge Uses Origin CLI Parity
Community paper translation entry points SHALL use the origin CLI parity kernel for newly started translation tasks.

#### Scenario: Paper-owned translation starts parity task
- **WHEN** a community paper starts translation from its latest source asset or arXiv bridge
- **THEN** the created translation task SHALL use `origin_cli_parity`
- **AND** the resulting translated assets SHALL come from the legacy CLI translation core behavior.

#### Scenario: Existing translated asset reuse does not alter parity contract
- **WHEN** the bridge reuses an already translated paper asset
- **THEN** it SHALL NOT start a new translation task
- **AND** newly created replacement tasks SHALL still use `origin_cli_parity`.
