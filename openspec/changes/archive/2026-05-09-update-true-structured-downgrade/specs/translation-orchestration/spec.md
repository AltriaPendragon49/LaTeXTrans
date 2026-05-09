## MODIFIED Requirements
> Current status: superseded and not current. The hard-freeze and ultimate-downgrade orchestration described here is historical only and is not part of current production parity orchestration.

### Requirement: Hard-Freeze Protocol Violations Route Through Existing Failure Semantics
The orchestration layer SHALL treat hard-freeze protocol violations as invalid LLM attempts while preserving existing retry, fallback, repair, and compile-aware safety behavior. It MUST distinguish relaxed section-like prose verification from strict high-risk-anchor verification without weakening anchor safety for environments, lists, math, captions, or object-local reference ownership.

#### Scenario: Protocol violation invalidates the attempt but not the task
1. Given a structural-risk LLM call returns a response with a hard-freeze protocol violation
2. When orchestration receives the typed invalid-attempt result
3. Then the system MUST reject that response without persisting decoded translation state
4. And MUST continue through the existing retry or fallback path for that part according to current policy
5. And MUST NOT terminate the whole task solely because one attempt violated the hard-freeze protocol.

#### Scenario: Relaxed verification is limited to section-like prose
1. Given orchestration dispatches a structural-risk translation request
2. When the request targets section-like prose rather than environment wrappers, list anchors, math bodies, or caption ownership shells
3. Then orchestration MAY use the relaxed section verification mode
4. And all non-section structural units MUST continue using strict high-risk-anchor verification.

#### Scenario: Structured downgrade success requires real translated content
1. Given orchestration is about to mark a section or environment as `ultimate_downgrade_applied` or equivalent final target-language fallback
2. When the candidate body contains only source-English prose or fixed fallback boilerplate
3. Then orchestration MUST NOT record that downgrade as successful
4. And it MUST preserve an explicit fallback/terminal reason instead.
