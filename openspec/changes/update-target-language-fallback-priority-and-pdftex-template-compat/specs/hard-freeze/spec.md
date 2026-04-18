## MODIFIED Requirements
### Requirement: Strict Validation (Fail-Fast)
The validator and hard-freeze boundary MUST reject any LLM output where the protected-token stream does not identically match the prepared input stream in quantity, order, and type. Rejection at this boundary MUST preserve the transport safety guarantee, but it MUST leave downstream orchestration free to attempt target-language rescue before any full source passthrough is persisted.

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
1. Given a translation payload that contains display math such as `$$...$$` or `\\[...\\]`
2. When payload preparation and fail-fast validation run before the LLM request
3. Then the system MUST protect those math spans before raw-structure checks evaluate the payload
4. And MUST restore the exact original display-math content after the model response is processed.

#### Scenario: Reordered or substituted hard-freeze tokens are rejected before decode
1. Given a prepared request whose hard-freeze token stream is `[T1, T2, T3]`
2. When the raw model output contains `[T1, T3, T2]` or `[T1, T2, T9]`
3. Then the boundary verifier MUST reject the response as a hard-freeze protocol violation
4. And MUST NOT decode any protected token from that response
5. And MUST NOT persist that raw response as translated content.

#### Scenario: Duplicate or missing hard-freeze tokens are rejected before decode
1. Given a prepared request whose hard-freeze token stream is `[T1, T2, T3]`
2. When the raw model output contains `[T1, T2]` or `[T1, T2, T2, T3]`
3. Then the boundary verifier MUST reject the response as a hard-freeze protocol violation
4. And MUST leave downstream retry, rescue, and fallback semantics to orchestration rather than attempting speculative placeholder repair at the boundary.

#### Scenario: Payload-invariant rejection still prefers target-language rescue
1. Given a section-level translation request is rejected for a hard-freeze protocol violation
2. When downstream orchestration handles that rejection
3. Then the orchestration MUST preserve the boundary rejection semantics
4. And it MUST attempt approved target-language rescue or downgrade flows before persisting a full source-language section fallback.
