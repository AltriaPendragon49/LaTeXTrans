# hard-freeze Specification

## Purpose
TBD - created by archiving change restore-structural-integrity-finish. Update Purpose after archive.
## Requirements
### Requirement: Pre-translation Placeholder Injection
The parser and translation agents MUST physically isolate structural LaTeX content before any structural-risk LLM request, including normal translation, retranslation, targeted retry, and environment-judgement payloads.  
Isolation MUST include math/environment boundary protection and immutable placeholder mapping that is recoverable after model output restoration.

#### Scenario: Retranslation payload is freeze-protected
1. Given a retrans request that includes source content, previous translation, and error context
2. When the request payload is prepared for LLM
3. Then raw `\begin{...}` and `\end{...}` boundaries MUST NOT appear in user payload
4. And unescaped `$` delimiters MUST NOT appear in user payload.

### Requirement: Strict Validation (Fail-Fast)
The validator MUST reject any LLM output where the set of placeholders does not identically match (in quantity, order, and type) the input placeholders.

#### Scenario: Immutable chunk never reaches the LLM
1. Given a chunk whose payload is entirely immutable placeholders or non-translatable structural tokens
2. When translation and repair orchestration evaluate the chunk
3. Then the system MUST bypass LLM translation and repair requests for that chunk
4. And MUST persist a passthrough status for auditability.

#### Scenario: Broken synthetic env boundary markers never persist
1. Given a translated environment result that still contains synthetic `ENV_BEGIN` or `ENV_END` markers
2. When output restoration or validation runs
3. Then the system MUST treat that translation attempt as failed
4. And MUST restore or preserve the source environment wrapper instead of persisting broken synthetic markers.

#### Scenario: Display math does not trigger raw-structure fail-fast
1. Given a translation payload that contains display math such as `$$...$$` or `\[...\]`
2. When payload preparation and fail-fast validation run before the LLM request
3. Then the system MUST protect those math spans before raw-structure checks evaluate the payload
4. And MUST restore the exact original display-math content after the model response is processed.

### Requirement: Raw Structure Payload Guard
Before a structural-risk LLM request is sent, the system MUST enforce a hard payload guard and reject payloads containing forbidden raw structure tokens.

#### Scenario: Guard rejects raw structure tokens
1. Given an outbound payload that contains `\begin{`, `\end{`, or an unescaped `$`
2. When payload validation runs
3. Then the system MUST raise a typed invariant violation
4. And MUST NOT send the payload to the LLM
5. And MUST route through existing retry/fallback semantics.

### Requirement: Environment-Judge Payload Leakage Guard
Environment-judge payload construction MUST reuse freeze preparation and MUST reject long contiguous raw body leakage.

#### Scenario: Long raw env body segment is blocked
1. Given an env body where a contiguous `>= 200` source-character span leaks into judge payload
2. When payload validation runs
3. Then the system MUST reject that payload with typed invariant error
4. And MUST default to existing safe env decision semantics without calling LLM.

