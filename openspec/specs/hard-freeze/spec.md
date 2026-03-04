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

#### Scenario: LLM hallucinates or drops a placeholder
1. Given the LLM output `这有一个方程：[PH_MATH_002].` (mismatched ID) or `这有一个方程。` (missing)
2. When the validator checks the chunk against the input state
3. Then it MUST immediately mark the translation attempt as failed and trigger a fast failure metric without attempting to "repair" the structure via regex.

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

