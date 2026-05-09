## ADDED Requirements
> Current status: partially superseded. Requirements about fake fallback detection remain useful historical context; structural fallback/downgrade behavior is not current production design after the May 9, 2026 parity-kernel cleanup.

### Requirement: Fake Chinese Fallback Is Forbidden in Final Output
The translation pipeline MUST NOT emit fixed generic Chinese downgrade phrases as final translated content for community production. Such phrases are diagnostic sentinels, not valid translations.

#### Scenario: Fixed fallback phrase reaches final text
- **WHEN** final reconstructed text, preview HTML, or extracted PDF text contains a configured fake fallback phrase such as `相关内容已转为简要中文表述` or `此处内容已做保守中文降级处理`
- **THEN** the translation MUST be marked invalid for community publishing
- **AND** the system MUST record a stable fallback-quality failure reason.

#### Scenario: API failure cannot become fake Chinese output
- **WHEN** an LLM request fails due to timeout, rate limit exhaustion, authentication, quota, model availability, or upstream provider denial
- **THEN** the fallback path MUST NOT synthesize a fixed Chinese sentence as translated content
- **AND** it MUST preserve explicit failure metadata for retry, failover, or terminal failure handling.

### Requirement: Semantic Minimal-LaTeX Structural Fallback
When structured translation fails but semantic translation is still possible, the system SHALL produce a minimal structurally safe LaTeX fallback from actual translated Chinese text rather than fixed generic text or wholesale source passthrough.

#### Scenario: Structure fails after translated prose exists
- **WHEN** a section or environment cannot preserve its original LaTeX structure after bounded repair
- **AND** the system has or can obtain semantically translated prose for the affected unit
- **THEN** it MUST rebuild the unit using minimal safe LaTeX paragraph structure
- **AND** it MUST preserve essential sectioning commands, citations, math placeholders, and non-translatable blocks where safe.

#### Scenario: Semantic fallback requires real model output
- **WHEN** no real translated prose was obtained because the provider call failed or returned empty/source-like output
- **THEN** the semantic fallback path MUST NOT invent generic Chinese filler
- **AND** the unit MUST resolve through retry, failover, explicit source fallback metadata, or terminal failure.

#### Scenario: Minimal fallback is traceable
- **WHEN** semantic minimal-LaTeX fallback is used
- **THEN** the section or environment metadata MUST record the fallback subtype, source unit identifier, and whether source prose remains.

## MODIFIED Requirements
### Requirement: Oversize Source Pass-Through Path Isolation
The system SHALL isolate oversize-downgraded chunks from secondary mutation pipelines and forward them directly to final reconstruction merge only as an explicit last-resort source fallback. For prose chunks, the system MUST first attempt safe splitting or semantic minimal-LaTeX fallback before allowing source pass-through.

#### Scenario: Oversize prose chunk attempts safe splitting
- **WHEN** a prose chunk exceeds the safe input limit
- **AND** a safe paragraph, sentence, or structural boundary can be found
- **THEN** the system MUST split the chunk into bounded requests
- **AND** it MUST NOT mark the full chunk as source pass-through solely due to initial size.

#### Scenario: Oversize prose chunk attempts semantic fallback
- **WHEN** a prose chunk exceeds the safe input limit
- **AND** structured preservation cannot safely process the chunk
- **THEN** the system MUST attempt semantic minimal-LaTeX fallback when model translation can be obtained for smaller prose units.

#### Scenario: Oversize downgraded chunk bypasses mutation chains
- **WHEN** a chunk is marked with `translated=false` and `downgrade_reason=oversize_no_safe_boundary`
- **THEN** the chunk MUST bypass translator invocation for that full chunk
- **AND** the chunk MUST bypass structural extraction, placeholder refill, terminology replacement, and macro rewrite chains
- **AND** the chunk MAY only enter final reconstruction merge as source pass-through content with explicit metadata.

### Requirement: API Rate Limit Resilience (429 Handling)
The translation service SHALL handle API rate limits (HTTP 429) gracefully with scheduler-managed retry and graduated backoff while maintaining system concurrency. Rate-limit handling MUST NOT return original text or fake translated text as successful output.

#### Scenario: Concurrent project isolation during 429 wait
- **WHEN** a translation sub-task hits a 429 error
- **THEN** the system MUST release scheduler request slots before sleeping
- **AND** MUST resume only after the backoff period expires and scheduler permission is reacquired.

#### Scenario: Graduated backoff strategy
- **WHEN** consecutive 429 errors occur for the same request or member lease
- **THEN** the system MUST follow a graduated retry strategy with quick retry, progressive delay, and bounded long-wait phases
- **AND** the member cooldown state MUST be observable.

#### Scenario: User notification for persistent rate-limiting
- **WHEN** 429 hits exceed the configured persistent-rate-limit threshold
- **THEN** the agent MUST push a progress update with a specific rate-limit warning message to the task manager.

#### Scenario: Rate limit never creates source-success output
- **WHEN** a 429 error occurs
- **THEN** the system MUST NOT return the original text, source passthrough, or fake Chinese text as a successful translation solely due to rate limits
- **AND** it MUST loop, fail over, or terminate with explicit provider failure according to configured policy.
