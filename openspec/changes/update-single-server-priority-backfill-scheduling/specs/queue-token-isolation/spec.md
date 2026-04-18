## MODIFIED Requirements
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

## ADDED Requirements
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
