## ADDED Requirements
### Requirement: Hard-Freeze Protocol Violations Route Through Existing Failure Semantics
The orchestration layer SHALL treat hard-freeze protocol violations as invalid LLM attempts while preserving existing retry, fallback, repair, and compile-aware safety behavior.

#### Scenario: Protocol violation invalidates the attempt but not the task
1. Given a structural-risk LLM call returns a response with a hard-freeze protocol violation
2. When orchestration receives the typed invalid-attempt result
3. Then the system MUST reject that response without persisting decoded translation state
4. And MUST continue through the existing retry or fallback path for that part according to current policy
5. And MUST NOT terminate the whole task solely because one attempt violated the hard-freeze protocol.

#### Scenario: Downstream validators remain active after accepted decode
1. Given a structural-risk LLM response passes hard-freeze boundary verification and is decoded successfully
2. When orchestration proceeds to normal validation
3. Then the existing validator, repair, reconstruction, structure guard, and compile fallback layers MUST still execute as designed
4. And hard-freeze acceptance MUST NOT be treated as proof that later-stage structural validation can be skipped.

### Requirement: Hard-Freeze Violations Are Observable
The orchestration layer SHALL persist explicit observability for hard-freeze protocol violations.

#### Scenario: Invalid attempt is logged with protocol-violation reason
1. Given a hard-freeze protocol violation occurs for a section, caption, or environment translation attempt
2. When task logs or audit records are written
3. Then the system MUST persist a stable reason identifying the violation as a hard-freeze protocol failure
4. And MUST keep it distinguishable from later validator or compile-stage failures.
