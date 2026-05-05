## ADDED Requirements
### Requirement: Content Pool Prewarm Translation Uses Origin CLI Parity
Content-pool prewarm translation SHALL start the same origin CLI parity task used by ordinary backend translation triggers.

#### Scenario: Prewarm candidate starts parity translation
- **WHEN** a content-pool prewarm candidate reaches the translation stage
- **THEN** the created translation task SHALL use `origin_cli_parity`
- **AND** discovery, promotion, ranking, or preview-generation metadata SHALL NOT change the translation kernel.

