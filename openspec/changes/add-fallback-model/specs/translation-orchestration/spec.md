# translation-orchestration Specification Deltas

## MODIFIED Requirements

### Requirement: Validation Subclassification and Controlled LLM Retry
The validation agent SHALL subclassify structural (Type C) errors to differentiate between isolated slip-ups and total structural collapse, deploying controlled LLM retries only for safe scenarios using the configured fallback model.

#### Scenario: Controlled 1-Max Retry for C1
- **WHEN** a C1 error is identified
- **THEN** the system MUST execute exactly 1 targeted retry using the LLM
- **AND** the LLM request MUST use the configured `fallback_model` instead of the primary translation model
- **AND** use the exact same API endpoint and credentials as the primary model
- **AND** inject 100-200 characters of surrounding context alongside the error type
- **AND** strictly instruct the LLM: *Only restore missing symbols; do not modify placeholders; do not retranslate content.*

## ADDED Requirements

### Requirement: General LLM Retry Fallback Routing
The system SHALL route general translation/timeout retries to the fallback model.

#### Scenario: Retrying translation chunk
- **WHEN** a standard translation chunk fails and requires a retry (`attempt > 1`)
- **THEN** the retry MUST invoke the configured `fallback_model` instead of the primary model
- **AND** rely on the identical API gateway configuration (URL and Key) to avoid multi-gateway credential management scenarios.
