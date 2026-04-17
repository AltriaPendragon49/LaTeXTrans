## MODIFIED Requirements
### Requirement: Partition queues by API Token Hash
The scheduler MUST bind each LLM request to a concrete token lease whose health state is tracked independently, and task routing MAY select that lease from a configured token pool instead of one hard-coded token.

#### Scenario: Mapping task to a token-specific lease
- **WHEN** a translation request or retry is ready to call the LLM
- **THEN** the system selects a concrete token from the configured pool or task-specific credentials
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
The token-pool layer SHALL prefer quick failover to healthy tokens and SHALL avoid blind token thrashing when every token in the pool is rate-limited.

#### Scenario: Healthy alternative token is available
- **WHEN** the current token receives HTTP 429
- **AND** another token in the same applicable pool is not cooling down
- **THEN** the system MUST prefer quick failover after a short request-local retry budget measured in seconds
- **AND** MUST avoid long sleeps on the rate-limited token before trying the healthy alternative.

#### Scenario: Every token in the pool is rate-limited
- **WHEN** all tokens in the applicable pool are simultaneously cooling down or rate-limited
- **THEN** the system MUST keep retrying with the current token until success or a non-429 fatal error occurs
- **AND** MUST NOT rotate blindly across equally exhausted tokens.
