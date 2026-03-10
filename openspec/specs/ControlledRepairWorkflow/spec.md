# ControlledRepairWorkflow Specification

## Purpose
TBD - created by archiving change accelerate-translation-workflow. Update Purpose after archive.
## Requirements
### Requirement: Strict State Machine Enforcement
Env processing MUST strictly follow a four-phase state machine to prevent infinite retries and unbounded execution times.

#### Scenario: Normal flow vs Downgrade flow
- **WHEN** an environment is processed
- **THEN** it undergoes Phase 0 (invariant check)
- **AND** if safe, it proceeds (Phase 1) normally
- **AND** if unsafe, it triggers Phase 2 (controlled repair) queued by token
- **AND** if repair fails or wait timeout is exceeded, it executes Phase 3 (deterministic downgrade)
- **AND** the environment processing MUST NEVER loop infinitely

### Requirement: Token-Scoped Independent Repair Scheduling
Phase 2 repair scheduling MUST be isolated per API token using a TokenRepairScheduler, ensuring repairs and rate limits for one token do not block or interfere with another.

#### Scenario: Multi-token repair isolation
- **WHEN** multiple unsafe envs assigned to Token A and Token B trigger Phase 2 concurrently
- **THEN** Token A's envs enter Token A's FIFO repair queue
- **AND** Token B's envs enter Token B's FIFO repair queue
- **AND** execution of Token A's repair MUST NOT be blocked by Token B's rate limits or queue status
- **AND** across any token, Phase 2 repairs MUST NOT share a queue or quota

### Requirement: Serial Per-Token Phase 2 Execution with Wait Bounds
For any single token, Phase 2 repair execution MUST be strictly serial, environments MUST queue at most once, and queue wait times MUST have a hard upper bound.

#### Scenario: Hard bounds on queue execution
- **WHEN** an unsafe env enters a token's Phase 2 repair queue
- **THEN** it MUST be allowed at most one queuing attempt
- **AND** the queue MUST execute at most one Phase 2 request concurrently per token
- **AND** if the env's queue wait time exceeds the configured hard upper bound
- **THEN** the env MUST immediately be ejected from the queue and fall back to Phase 3 (deterministic downgrade)

### Requirement: Extremely Strict Controlled LLM Repair Prompting
Controlled LLM repair (Phase 2) execution MUST be attempted at most once per unsafe env. The system MUST employ an extremely strict Prompt that explicitly forbids any form of translation or semantic rewriting, except under specific context-aware recovery conditions. The prompt MUST incorporate `validation_evidence` to target specific repairs (e.g., math balancing, placeholder preservation).

#### Scenario: Prompt constraints for structure repair
- **WHEN** an env triggers its Phase 2 repair execution
- **THEN** the LLM is prompted to fix structure exclusively using detailed `validation_evidence`
- **AND** the Prompt MUST explicitly prohibit translating the text or altering its semantics (unless handling total erasure)
- **AND** if the output still fails verifiable structure checks (e.g., math count mismatch, placeholder mismatch)
- **THEN** the system MUST move to Phase 3 rather than retrying the LLM

### Requirement: Phase 1 Parallelism Isolation
Phase 1 (normal translation) and Phase 2 (structural repair) MUST share a token's request quota but their run scheduling MUST be isolated. Phase 1 processing MUST NEVER be blocked by the Phase 2 serial queues.

#### Scenario: Phase 1 throughput unobstructed by Phase 2
- **WHEN** a token's Phase 2 repair queue is occupied processing an unsafe env
- **THEN** the system MUST NOT pause or delay the dispatch of structurally safe envs assigned to that same token for Phase 1 parallel translation

### Requirement: Token-Bounded 429 Passivation
API 429 rate limits during Phase 2 MUST be interpreted as a token-scoped limit. A max of one wait-and-retry is permitted within a Phase 2 execution before triggering a Phase 3 downgrade.

#### Scenario: Localized 429 fallback limit
- **WHEN** the LLM API returns a 429 error during a Phase 2 repair translation attempt
- **THEN** the system MUST execute a wait-and-retry exactly once for that environment
- **AND** if the API returns a 429 error again
- **THEN** the token is considered unfit for current heavy repair operation
- **AND** the system MUST immediately apply the Phase 3 downgrade for this request without increasing retries or sleep values

### Requirement: Strict Deprecation of Global Business Limits and Infinite Retries
The system MUST NOT use cross-token global concurrency locks to make business-level LLM scheduling decisions. The system MUST strictly prohibit any form of infinite retries or unbounded exponential backoff for LLM API calls, specifically during Phase 2.

#### Scenario: Handling of legacy rate limiting mechanisms
- **WHEN** configuring LLM API concurrency and retry logic
- **THEN** the system MUST execute infinite `while True` retry loops upon receiving HTTP 429 errors -> MUST NOT
- **AND** ANY failure, queue timeout, or 429-after-retry in Phase 2 MUST be treated as a definitive, non-retryable error prompting an immediate Phase 3 downgrade
- **AND** the system MUST NOT attempt to prolong sleep times or increment retries merely to "improve repair success rates"

### Requirement: Irrevocable Semantic Separation of Three-Tier Controls
The system MUST strictly compartmentalize limits into "Infra Guard" (system survival), "User/Task Limits" (QoS admission), and "Token-Scoped Scheduler" (business logic). Operations across these bounds MUST NOT mix.

#### Scenario: Absolute prohibition of Infra/QoS interference in business logic
- **WHEN** evaluating Phase 2 queuing, wait timeouts, and fallback behaviors
- **THEN** the Token-Scoped Repair Scheduler MUST be the ONLY deciding factor
- **AND** Infra Guards (like global OS lock semaphores) MUST NOT consume an env's repair opportunity, nor can failure of an Infra Guard trigger Phase 3
- **AND** User/Task QoS limits MUST NOT be misconstrued as HTTP 429 rate limits or influence the scheduling of individual env repairs within the Token queue

### Requirement: Token-Gated Total Erasure Recovery
When `translated_text` is empty (Total Erasure), Phase 2 MAY instruct the LLM to perform a structural recovery translation ONLY IF the estimated source token count is within a strictly safe threshold (`source_tokens <= MAX_ERASURE_RECOVERY_TOKENS`). If the token delta exceeds this hard safety threshold, erasure recovery MUST be bypassed and the system MUST trigger Phase 3 immediately.

#### Scenario: Safely handling empty translations
- **WHEN** an env triggers Phase 2 repair with an empty `translated_text`
- **THEN** the system computes the estimated token count of the source text (`estimated_tokens = ceil(len(utf8_bytes)/3)`)
- **AND** if the `estimated_tokens <= MAX_ERASURE_RECOVERY_TOKENS`, recovery translation is attempted
- **AND** if the `estimated_tokens > MAX_ERASURE_RECOVERY_TOKENS`, the system skips repair and moves straight to Phase 3 downgrade

### Requirement: Verifiable Failure Enforcement
All Phase 2 repair attempts MUST be subjected to strict verifiable checks against the source text. These include matching the exact number of explicit mathematical delimiters (e.g., `$`, `\(`, `\)`) and absolute placeholder preservation. The repair MUST NOT attempt to balance or repair complex environments like `align` or `cases`. Any failure to pass these automated checks MUST result in immediate Phase 3 downgrade without further retries.

#### Scenario: Deterministic repair verification
- **WHEN** the LLM returns a repaired text in Phase 2
- **THEN** the system counts explicit math delimiters (`$`, `\(`, `\)`) and compares them to the source
- **AND** the system verifies all `PLACEHOLDER_*` strings match the source exactly
- **AND** if any count or match fails
- **THEN** the system immediately delegates the env to Phase 3 (deterministic downgrade)

