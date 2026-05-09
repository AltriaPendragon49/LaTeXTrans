## MODIFIED Requirements
> Current status: superseded and not current. The `hard-freeze` capability was removed from current production specs after the May 9, 2026 parity-kernel cleanup.

### Requirement: Strict Validation (Fail-Fast)
The validator and hard-freeze boundary MUST reject any LLM output that violates protected-token safety for the active verification mode. High-risk structural anchors MUST still preserve exact quantity, order, and type. Section-like prose payloads MAY accept relaxed low-risk protected-token ordering, but they MUST still reject loss, duplication, substitution, or cross-object drift of required anchors. Rejection at this boundary MUST preserve the transport safety guarantee, but it MUST leave downstream orchestration free to attempt target-language rescue before any full source passthrough is persisted.

#### Scenario: Immutable chunk never reaches the LLM
1. Given a chunk whose payload is entirely immutable placeholders or non-translatable structural tokens
2. When translation and repair orchestration evaluate the chunk
3. Then the system MUST bypass LLM translation and repair requests for that chunk
4. And MUST persist a passthrough status for auditability.

#### Scenario: High-risk anchors still require exact order
1. Given a prepared request whose protected stream contains high-risk anchors such as begin/end pairs, math anchors, `ITEM` anchors, caption-ownership anchors, or object-local reference/label anchors
2. When the raw model output reorders, substitutes, removes, or duplicates one of those high-risk anchors
3. Then the boundary verifier MUST reject the response as a hard-freeze protocol violation
4. And MUST NOT decode any protected token from that response.

#### Scenario: Section-like prose may relax low-risk protected-token ordering
1. Given a section-like prose request whose protected stream contains both high-risk anchors and lower-risk protected prose sentinels
2. When the raw model output preserves every high-risk anchor exactly and preserves every protected token occurrence without loss, duplication, substitution, or cross-object drift
3. And only the lower-risk protected prose sentinels appear in a different local order inside the same object scope
4. Then the boundary verifier MAY accept the response for downstream decode and validation.

#### Scenario: Missing or duplicated protected token still fails in relaxed mode
1. Given a section-like prose request using the relaxed verification mode
2. When the raw model output omits any protected token occurrence or duplicates one
3. Then the boundary verifier MUST reject the response as a hard-freeze protocol violation
4. And relaxed verification MUST NOT degrade into set-only equality.

#### Scenario: Payload-invariant rejection still prefers target-language rescue
1. Given a section-level translation request is rejected for a hard-freeze protocol violation
2. When downstream orchestration handles that rejection
3. Then the orchestration MUST preserve the boundary rejection semantics
4. And it MUST attempt approved target-language rescue or downgrade flows before persisting a full source-language section fallback.
