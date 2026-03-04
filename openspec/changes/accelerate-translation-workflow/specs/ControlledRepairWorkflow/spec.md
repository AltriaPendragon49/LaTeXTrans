# Capability: ControlledRepairWorkflow

## ADDED Requirements

### Requirement: Strict State Machine Enforcement
Env processing MUST strictly follow a four-phase state machine to prevent infinite retries and unbounded execution times.

#### Scenario: Normal flow vs Downgrade flow
- **WHEN** an environment is processed
- **THEN** it undergoes Phase 0 (invariant check)
- **AND** if safe, it proceeds (Phase 1) normally
- **AND** if unsafe, it triggers Phase 2 (controlled repair)
- **AND** if repair fails, it executes Phase 3 (deterministic downgrade)
- **AND** the environment processing MUST NEVER loop infinitely

### Requirement: Controlled LLM Repair
Controlled LLM repair (Phase 2) MUST be attempted at most once per unsafe env and MUST not alter semantic translation intent.

#### Scenario: Broken brackets trigger repair
- **WHEN** an env with broken brackets triggers Phase 2
- **THEN** the LLM is prompted to fix structure only
- **AND** if the output still fails structure checks
- **THEN** the system MUST move to Phase 3 rather than retrying the LLM

### Requirement: Deterministic Downgrade
The system MUST enforce a deterministic downgrade (Phase 3) when structural repair fails or API rate limits persist, guaranteeing an output for every env.

#### Scenario: Downgrade application
- **WHEN** the Phase 2 LLM repair fails
- **THEN** the system MUST apply the Phase 3 downgrade
- **AND** output the raw source block or placeholder
- **AND** ensure compilation safety and allow the process to continue

### Requirement: API Rate Limit Bounding
API 429 rate limits MUST result in at most one wait-and-retry cycle per env before triggering a deterministic downgrade.

#### Scenario: 429 rate limit fallback
- **WHEN** the LLM API returns a 429 error during translation
- **THEN** the system MUST wait and retry exactly once
- **AND** if the API returns a 429 error again
- **THEN** the system MUST immediately apply the Phase 3 downgrade

### Requirement: Serial Execution for Unsafe Envs
Concurrent execution MUST be isolated such that structurally unsafe envs are processed serially to prevent retry storms, while safe envs may run in parallel.

#### Scenario: Serializing unsafe envs
- **WHEN** a batch of mixed envs are parsed
- **THEN** safe envs SHALL be processed in parallel
- **AND** unsafe envs MUST be routed to a serial queue
