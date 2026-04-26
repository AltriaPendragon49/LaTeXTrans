## MODIFIED Requirements
### Requirement: Partition queues by API Token Hash
The TaskQueue macro dispatcher MUST NOT rely on token-hash partitioning as the sole isolation boundary for production LLM throughput. It MUST route translation execution through a central LLM member scheduler that understands configured endpoint-credential members, per-member limits, pool/shared-base limits, task leases, and reserve capacity.

#### Scenario: Mapping task to scheduler-managed member lease
- **WHEN** a translation task is admitted for execution
- **THEN** the system MUST request a task-level LLM member lease from the scheduler
- **AND** the lease MUST identify a preferred member without exposing the raw API key
- **AND** outbound LLM requests for that task MUST acquire scheduler permission before dispatch.

#### Scenario: Token hash remains diagnostic only
- **WHEN** the system records queue or task logs
- **THEN** it MAY record a masked token hash or member identifier for diagnostics
- **AND** it MUST NOT treat hash partitioning alone as proof that provider quota or relay capacity is isolated.

### Requirement: Concurrent processing of divergent tokens
The TaskQueue MUST concurrently process translation bundles only when the scheduler reports enough healthy independent capacity. Independent API keys from distinct accounts MAY increase active task capacity, while keys sharing a base or account MUST remain subject to shared pool limits unless explicitly configured otherwise.

#### Scenario: One configured key runs one community translation task
- **GIVEN** production has one configured healthy LLM member
- **WHEN** community translation tasks are queued
- **THEN** the community production dispatcher MUST run at most one active translation task by default
- **AND** additional tasks MUST wait rather than fan out nested LLM bursts through the same key.

#### Scenario: Three independent keys run two community translation tasks with reserve
- **GIVEN** production has three healthy LLM members configured as independent accounts
- **AND** the community reserve member count is `1`
- **WHEN** community translation tasks are queued
- **THEN** the dispatcher SHOULD run at most two active translation tasks by default
- **AND** one healthy member SHOULD remain available for failover or transient spikes.

#### Scenario: Same relay is conservative without independent-account config
- **GIVEN** multiple members share the same `base_url`
- **AND** they are not explicitly configured with independent account or quota scope metadata
- **WHEN** the scheduler computes available capacity
- **THEN** it MUST apply shared pool limits to those members
- **AND** it MUST NOT assume their quotas are independent solely because their API keys differ.

### Requirement: Member-level 503 handling uses bounded cooldown with current-member exhaustion retry
The system-managed token-pool layer SHALL cool down individual members after repeated HTTP 503 responses without forcing blind rotation when every member is temporarily unavailable. Cooldown and retry handling MUST be performed by the central LLM scheduler before new dispatch attempts.

#### Scenario: One member hits repeated 503
- **WHEN** the same endpoint-credential member receives consecutive HTTP 503 responses
- **THEN** the system SHALL place that member into a bounded cooldown longer than the current one-second behavior
- **AND** that cooldown SHALL apply to that member only.

#### Scenario: All members are unavailable after 503 pressure
- **WHEN** every eligible member in the applicable pool is cooling down or unavailable
- **THEN** the current request SHALL wait on a bounded scheduler retry interval
- **AND** it SHALL NOT rotate blindly across equally unavailable members.

#### Scenario: Fatal provider errors stop rescue amplification
- **WHEN** an LLM member returns a deterministic fatal provider error such as authentication failure, quota exhaustion, unsupported model, or equivalent non-retryable denial
- **THEN** the scheduler MUST mark that member or lease as fatal for the task
- **AND** translation orchestration MUST NOT convert that error into source passthrough or fake translated output.

## ADDED Requirements
### Requirement: Task-Level LLM Member Lease
The system SHALL assign each active translation task a preferred LLM member lease and use that lease for first-pass translation calls unless bounded failover is required.

#### Scenario: Task prefers its leased member
- **WHEN** a task has an active member lease
- **AND** a first-pass section, environment, or caption translation request is made
- **THEN** the scheduler MUST prefer the leased member
- **AND** the request MUST still obey per-member and pool-level rate/concurrency limits.

#### Scenario: Lease failover is explicit
- **WHEN** the leased member is cooling down or fatally unavailable
- **AND** a healthy eligible reserve member exists
- **THEN** the scheduler MAY fail over the request
- **AND** it MUST record the failover reason in task observability.

### Requirement: Scheduler Covers All LLM Call Sites
Every outbound LLM call in production translation, repair, rescue, diagnostics, and structured insight generation MUST pass through the same scheduler permission boundary.

#### Scenario: Direct LLM client bypass is rejected
- **WHEN** a production callsite attempts to dispatch to an LLM client without scheduler permission metadata
- **THEN** the system MUST reject or flag the call as an invariant violation in tests or runtime guardrails
- **AND** the call MUST NOT silently bypass configured member limits.
