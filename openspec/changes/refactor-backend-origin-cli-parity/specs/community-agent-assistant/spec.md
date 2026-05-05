## ADDED Requirements
### Requirement: Agent-Triggered Translation Uses Origin CLI Parity
Community-agent initiated translation SHALL delegate to the same origin CLI parity translation task entry as other backend triggers.

#### Scenario: Agent starts a translation tool task
- **WHEN** the community agent executes `start_translation_kernel`
- **THEN** the created backend translation task SHALL use `origin_cli_parity`
- **AND** the agent layer SHALL NOT introduce a separate translation core or modern fallback path.

#### Scenario: Agent auto-start translation uses the same route
- **WHEN** the community agent auto-starts translation after paper import or lookup
- **THEN** the translation SHALL be started through the shared parity task entry
- **AND** its result SHALL come from the legacy CLI translation core behavior.
