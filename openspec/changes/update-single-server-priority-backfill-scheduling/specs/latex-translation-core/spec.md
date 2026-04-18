## MODIFIED Requirements
### Requirement: API Rate Limit Resilience (429 Handling)
The translation service SHALL handle transient LLM endpoint failures through token-aware short retries, system-managed pool failover, and eventual infinite retry semantics without weakening translation correctness or falsely exhausting healthy capacity.

#### Scenario: Healthy alternative token available
- **WHEN** an LLM request receives HTTP 429
- **AND** another token in the applicable pool is healthy
- **THEN** the request MAY spend only a short local retry window measured in seconds on the current token
- **AND** MUST then fail over to the healthy token instead of entering a long per-request sleep.

#### Scenario: Consecutive 503 triggers quick failover
- **WHEN** an LLM request receives consecutive HTTP 503 responses from the same system-managed endpoint-credential member
- **AND** another member in the applicable system-managed pool is healthy
- **THEN** the request MUST fail over quickly to that healthy member
- **AND** MUST avoid a long retry ladder on the degraded member.

#### Scenario: All pool tokens exhausted
- **WHEN** every token in the applicable pool is rate-limited or cooling down
- **THEN** the request MUST keep retrying with its current token using a bounded retry interval until success or a non-429 fatal error occurs
- **AND** the task MUST NOT fail solely because the pool is temporarily exhausted.

#### Scenario: Waiting on 429 does not monopolize unrelated healthy capacity
- **WHEN** a request waits before retrying after HTTP 429
- **THEN** the system MUST release the fine-grained token or request permit associated with that attempt during the wait
- **AND** unrelated requests that can use other healthy tokens MUST remain runnable.

#### Scenario: User notification for sustained all-pool exhaustion
- **WHEN** a task remains blocked because every applicable token is rate-limited for longer than the short failover window
- **THEN** the system MUST push a progress update describing the rate-limit state
- **AND** the task MUST remain in a retriable non-terminal state.

#### Scenario: Custom user credentials remain single-route in phase 1
- **WHEN** a task uses request-supplied or persisted user custom API credentials
- **THEN** phase-1 system-managed pool logic MUST NOT alter that task's credential routing semantics
- **AND** retry behavior for that task MAY remain on the existing single-credential path until a later approved change extends pooling to user-owned credentials.

#### Scenario: Post-translation structured insight generation reuses the system-managed pool
- **WHEN** the backend performs structured insight generation for a translated paper using system-managed credentials
- **THEN** that chat-completion request MUST reuse the same system-managed pool helper and member health state as the main translation runtime
- **AND** MUST NOT fall back to a hard-coded single-member direct HTTP route.
