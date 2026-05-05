## ADDED Requirements
### Requirement: Legacy CLI Remains Canonical Translation Baseline
The legacy CLI implementation under `texts/origin` SHALL remain the canonical behavior baseline for backend `origin_cli_parity` translation.

#### Scenario: Backend parity is compared against legacy CLI
- **WHEN** parity verification runs with deterministic mocked LLM responses
- **THEN** it SHALL execute both the legacy CLI path and backend parity path for the same source and effective config
- **AND** it SHALL fail if kernel artifacts, reconstructed source, compile sequence, or workflow status are not byte-for-byte identical except for explicitly wrapper-owned metadata.
