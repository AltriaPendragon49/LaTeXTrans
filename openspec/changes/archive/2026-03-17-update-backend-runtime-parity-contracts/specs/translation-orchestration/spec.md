## ADDED Requirements
### Requirement: Validation Retry Stagnation Short-Circuit
The orchestration layer SHALL terminate validation retry loops early when repeated retries no longer reduce the remaining structural error set.

#### Scenario: Retry loop makes no progress
- **WHEN** validation is rerun after a retry/repair step
- **AND** the remaining error set is unchanged from the previous validation round
- **THEN** the system MUST short-circuit further retry rounds for that run
- **AND** MUST record a `validation_retry_short_circuited_no_progress` event in `task_log.json`
- **AND** MUST continue with the existing fallback / compile path instead of looping again.

### Requirement: Task-Start Runtime Observability
The orchestration layer SHALL persist the effective runtime configuration used for a task start, including masked LLM settings required for parity debugging.

#### Scenario: Task-start log records effective LLM runtime config
- **WHEN** the coordinator writes the `task_started` event into `task_log.json`
- **THEN** the payload MUST include the effective runtime configuration used by the task
- **AND** MUST include masked `llm_config` fields such as `base_url`, `model`, timeout-related values, and masked API-key presence
- **AND** MUST NOT persist the raw API key.
