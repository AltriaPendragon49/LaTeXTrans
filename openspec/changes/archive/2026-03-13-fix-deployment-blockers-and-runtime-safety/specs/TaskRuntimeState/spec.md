## ADDED Requirements
### Requirement: Single-Worker Runtime Safety Guardrail
Until runtime task state is fully externalized, production runtime MUST operate with a single worker.

#### Scenario: Startup warning about multi-worker risk
- **WHEN** backend starts
- **THEN** logs MUST state that runtime state is partially in-process
- **AND** logs MUST state that multi-worker deployment is unsupported in current model

#### Scenario: Deployment defaults align with guardrail
- **WHEN** production runtime command is used
- **THEN** default worker count MUST be `1`
