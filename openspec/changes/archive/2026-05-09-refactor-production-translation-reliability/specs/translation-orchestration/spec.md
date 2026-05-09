## ADDED Requirements
> Current status: partially superseded. Requirements that imply modern fallback/downgrade orchestration are historical only after the May 9, 2026 parity-kernel cleanup.

### Requirement: Production Translation Uses Scheduler-Bounded LLM Calls
The translation orchestration layer SHALL route all section, environment, caption, repair, rescue, force-retry, diagnostic, and structured-insight LLM requests through the central LLM scheduler.

#### Scenario: Section translation acquires scheduler permission
- **WHEN** the translator prepares a section-level LLM request
- **THEN** it MUST acquire scheduler permission for the current task lease before dispatch
- **AND** task logs MUST be able to identify the masked member lease used for the request.

#### Scenario: Repair and rescue calls share the same limiter
- **WHEN** validation or compilation triggers repair, rescue, or diagnostic LLM work
- **THEN** those calls MUST use the same scheduler boundary as first-pass translation
- **AND** they MUST count against the configured member and pool budgets.

## MODIFIED Requirements
### Requirement: Intra-Section Translation Parallelization
The TranslatorAgent SHALL process child environments and captions within each section sequentially by default in production translation. Section-internal parallel phases MAY exist only behind an explicit feature flag and MUST still acquire scheduler permission for every outbound request.

#### Scenario: Sequential environment and caption translation by default
- **WHEN** a section contains multiple environments or captions
- **AND** production translation uses the default configuration
- **THEN** the system MUST translate those child units sequentially inside that section
- **AND** it MUST NOT use `asyncio.gather()` to create nested LLM fan-out for that section.

#### Scenario: Explicit experimental nested parallelism remains bounded
- **WHEN** an operator explicitly enables section-internal parallelism
- **THEN** every child environment and caption request MUST still pass through the central scheduler
- **AND** the feature MUST be disableable without changing code.

### Requirement: Global API Rate Limiting
The system SHALL implement globally shared outbound LLM request control through scheduler-managed per-member and pool-level concurrency/rate limiters rather than a single undifferentiated semaphore defaulting to `10`.

#### Scenario: Enforcing per-member LLM concurrency
- **WHEN** multiple tasks or sub-tasks trigger LLM requests against the same configured member
- **THEN** they MUST acquire that member's scheduler limiter before dispatch
- **AND** excess requests SHALL queue without being converted to fallback output.

#### Scenario: Enforcing shared pool limits
- **WHEN** several members share a provider base, relay, account, or configured quota scope
- **THEN** requests MUST also acquire the shared pool limiter
- **AND** the system MUST prevent aggregate pressure from exceeding that pool's configured capacity.

#### Scenario: Rate-limit wait releases occupied request slots
- **WHEN** a request hits HTTP 429 and enters backoff
- **THEN** the system MUST release active request slots before sleeping
- **AND** it MUST reacquire scheduler permission before retrying.

### Requirement: No-op Re-translation Guardrail
The section translation flow SHALL detect high-similarity no-op outputs and perform exactly one forced retranslation attempt before finalizing section status. Persistent no-op output MUST remain observable and MUST NOT be published to the community library unless the community production quality gate explicitly accepts it under source-fallback thresholds.

#### Scenario: No-op threshold triggers single forced retry
- **WHEN** section output meets no-op thresholds (`SequenceMatcher >= 0.97`, `CJK chars < 16`, `English words >= 80`)
- **THEN** the system MUST execute one strengthened retranslation attempt
- **AND** mark `no_op_detected` as true for the section.

#### Scenario: Persistent no-op is retained only with explicit metadata
- **WHEN** the forced retry still results in a no-op-like output
- **THEN** the task MAY retain the resulting text for debug or user-facing task artifacts under existing safety policy
- **AND** section metadata MUST preserve no-op and fallback status context for traceability
- **AND** community publishing MUST defer to the production quality gate before asset sync.
