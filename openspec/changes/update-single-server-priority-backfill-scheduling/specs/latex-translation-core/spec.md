## MODIFIED Requirements
### Requirement: API Rate Limit Resilience (429 Handling)
The translation service SHALL handle API rate limits through token-aware short retries, pool failover, and eventual infinite retry semantics without weakening translation correctness or falsely exhausting healthy capacity.

#### Scenario: Healthy alternative token available
- **WHEN** an LLM request receives HTTP 429
- **AND** another token in the applicable pool is healthy
- **THEN** the request MAY spend only a short local retry window measured in seconds on the current token
- **AND** MUST then fail over to the healthy token instead of entering a long per-request sleep.

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
