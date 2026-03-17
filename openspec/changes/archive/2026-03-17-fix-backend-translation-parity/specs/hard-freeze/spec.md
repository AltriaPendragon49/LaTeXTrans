## MODIFIED Requirements

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
