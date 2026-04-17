# hard-freeze Specification

## Purpose
TBD - created by archiving change restore-structural-integrity-finish. Update Purpose after archive.
## Requirements
### Requirement: Pre-translation Placeholder Injection
The parser and translation agents MUST physically isolate structural LaTeX content before any structural-risk LLM request, including normal translation, retranslation, targeted retry, environment translation, environment recovery, list-item rescue, and eqnarray row-safe translation. Isolation MUST include a unified hard-freeze registry for all protected placeholders and synthetic structural sentinels that can later be restored only through an exact request-local decode table.

#### Scenario: Every protected placeholder family enters the same hard-freeze registry
1. Given a structural-risk LLM request that contains parser placeholders such as `PLACEHOLDER_ENV`, `PLACEHOLDER_CAP`, `PLACEHOLDER_NEWCOMMAND`, or `PLACEHOLDER_*_begin` / `PLACEHOLDER_*_end`
2. And the request also contains internal sentinels such as `ENV_*`, `ENV_BEGIN_*`, `ENV_END_*`, `INLMATH_*`, `ITEM_*`, `EQROW_*`, `EQCOMMENT_*`, or `PROTECTED_CMD_*`
3. When the payload is prepared for the LLM
4. Then every protected occurrence MUST be replaced by a request-local opaque hard-freeze transport token
5. And the original protected strings MUST NOT be sent to the LLM in cleartext.

#### Scenario: Hard-freeze tokens are request-local and occurrence-unique
1. Given two identical protected placeholders that appear twice in one payload
2. When the hard-freeze manifest is created
3. Then each occurrence MUST receive its own transport token
4. And the decode manifest MUST preserve occurrence order
5. And the transport tokens MUST be scoped so a token from one request cannot be decoded in another request.

### Requirement: Strict Validation (Fail-Fast)
The validator and hard-freeze boundary MUST reject any LLM output where the protected-token stream does not identically match the prepared input stream in quantity, order, and type.

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
4. And MUST leave downstream retry/fallback semantics to orchestration rather than attempting speculative placeholder repair at the boundary.

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

### Requirement: Exact Decode-Only Hard-Freeze Restoration
Protected placeholders and synthetic structural sentinels MUST be restored from model output only through exact decode-table lookups against the request-local hard-freeze manifest.

#### Scenario: Exact hard-freeze token decode succeeds
1. Given a model response that preserves the full hard-freeze token stream exactly
2. When the response passes boundary verification
3. Then the system MUST decode each token back to its original protected artifact using the request-local manifest
4. And the decoded text MAY proceed to existing validation and reconstruction stages.

#### Scenario: Mutated hard-freeze token cannot be decoded
1. Given a model response that contains a transport token with any character mutation or an unknown token value
2. When boundary decoding is attempted
3. Then the system MUST treat the response as invalid before decode
4. And MUST NOT guess or fuzzily reconstruct the intended protected artifact at this boundary.

### Requirement: Hard-Freeze Boundary Guarantee
The system MUST define hard-freeze success as a transport-handshake guarantee rather than model obedience.

#### Scenario: Model may emit invalid output but invalid protected tokens never persist
1. Given a model returns text that mutates one or more hard-freeze tokens
2. When the system evaluates that response
3. Then the response MAY be logged as a failed attempt
4. But the mutated token payload MUST NOT be accepted, decoded, or persisted as a valid translation result.

