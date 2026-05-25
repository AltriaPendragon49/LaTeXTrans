# queue-token-isolation Specification

## Purpose
TBD - created by archiving change isolate-token-queues. Update Purpose after archive.
## Requirements
### Requirement: Partition queues by API Token Hash
The scheduler MUST bind each LLM request to a concrete token lease whose health state is tracked independently, and task routing MAY select that lease from a configured token pool instead of one hard-coded token.

#### Scenario: Mapping task to a token-specific lease
- **WHEN** a translation request or retry is ready to call the LLM
- **THEN** the system selects a concrete endpoint-credential member from the configured system-managed pool or uses task-specific credentials directly
- **AND** records rate-limit and cooldown state against that token only
- **AND** MUST NOT treat one token's 429 response as a global provider-wide pause.

### Requirement: Concurrent processing of divergent tokens
The TaskQueue MUST keep unrelated healthy tokens independently usable, even when another token or pool member is cooling down due to 429 responses.

#### Scenario: Healthy token continues while another token cools down
- **GIVEN** token A recently hit 429 and entered cooldown
- **WHEN** token B from the same configured pool remains healthy
- **THEN** new eligible requests MAY lease token B immediately
- **AND** token A's cooldown MUST NOT block token B's execution slots.

### Requirement: Maintain Independent User Admission Control
The TaskQueue MUST maintain user connection limits scaling (`max_user_active_tasks` guard rails) entirely independent from the aforementioned hashed token queuing model, gracefully dropping/refusing overload admissions per User ID prior to applying mapping algorithms.

#### Scenario: Exceeding global active tasks limit
- **Given** user A has reached the maximum permitted active tasks threshold globally across the platform.
- **When** user A attempts to enqueue another translation utilizing any valid LLM Token.
- **Then** the system MUST block the admission entirely at the User ID level limits.
- **And** the task is never subjected to the token-partitioned Queue mapping.

### Requirement: Structured insight supports task-local base preference without global base bans
The system-managed token-pool layer SHALL allow structured insight generation to prefer a healthier `base_url` within the current task while keeping global health tracking strictly member-level.

#### Scenario: One relay base accumulates repeated 503 during one structured-insight task
- **WHEN** structured insight generation records three cumulative HTTP 503 responses from members sharing the same `base_url` during the current task
- **AND** another `base_url` in the same applicable pool still has a healthy member
- **THEN** later member selection for that structured-insight task SHALL prefer the healthier base
- **AND** the system SHALL NOT globally mark the failing base unavailable for unrelated tasks
- **AND** healthy members on that base MAY still be used by other requests according to normal member-level health rules.

### Requirement: Member-level 503 handling uses bounded cooldown with current-member exhaustion retry
The system-managed token-pool layer SHALL cool down individual members after repeated HTTP 503 responses without forcing blind rotation when every member is temporarily unavailable.

#### Scenario: One member hits repeated 503
- **WHEN** the same endpoint-credential member receives consecutive HTTP 503 responses
- **THEN** the system SHALL place that member into a bounded cooldown longer than the current one-second behavior
- **AND** that cooldown SHALL apply to that member only.

#### Scenario: All members are unavailable after 503 pressure
- **WHEN** every eligible member in the applicable pool is cooling down or unavailable
- **THEN** the current request SHALL keep retrying its current member on a short bounded interval
- **AND** it SHALL NOT rotate blindly across equally unavailable members.

### Requirement: Token Pool Failover And Exhaustion Policy
The system-managed token-pool layer SHALL prefer quick failover to healthy endpoint-credential members and SHALL avoid blind member thrashing when every member in the pool is unavailable.

#### Scenario: System-managed pool spans two base URLs and five keys
- **WHEN** the backend uses system-managed credentials
- **THEN** the applicable pool MUST support two configured `base_url` groups
- **AND** MUST support five independent endpoint-credential members total across those groups
- **AND** each member's health and cooldown state MUST be tracked independently.

#### Scenario: Healthy alternative token is available
- **WHEN** the current token receives HTTP 429
- **AND** another token in the same applicable pool is not cooling down
- **THEN** the system MUST prefer quick failover after a short request-local retry budget measured in seconds
- **AND** MUST avoid long sleeps on the rate-limited token before trying the healthy alternative.

#### Scenario: Healthy alternative member exists after consecutive 503
- **WHEN** the current endpoint-credential member receives consecutive HTTP 503 failures
- **AND** another member in the same applicable system-managed pool is healthy
- **THEN** the system MUST fail over quickly to that healthy member
- **AND** MUST avoid waiting through a long retry ladder on the degraded member first.

#### Scenario: Every token in the pool is rate-limited
- **WHEN** all tokens in the applicable pool are simultaneously cooling down or rate-limited
- **THEN** the system MUST keep retrying with the current token until success or a non-429 fatal error occurs
- **AND** MUST NOT rotate blindly across equally exhausted tokens.

#### Scenario: Custom user credentials bypass the system-managed pool
- **WHEN** a request uses `custom_api_key/custom_base_url` from the request or user settings
- **THEN** the system MUST preserve the current single-credential behavior for that request
- **AND** MUST NOT silently enroll those user-owned credentials into the system-managed pool in phase 1.

#### Scenario: Structured insight sidecar calls share pool health state
- **WHEN** a translated paper triggers structured insight generation with system-managed credentials
- **THEN** the request MUST use the same configured pool members and routing key family as the translation runtime for that backend deployment
- **AND** failover and exhaustion handling MUST observe the same per-member health state instead of maintaining an isolated direct-call path.

