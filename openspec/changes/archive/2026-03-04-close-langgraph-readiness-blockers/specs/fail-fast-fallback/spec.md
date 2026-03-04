## MODIFIED Requirements
### Requirement: Removal of Structural Fallback
The translator agent MUST NOT execute speculative structural repair that injects LaTeX structure tokens (for example: placeholder insertion, begin/end completion, or math delimiter injection).  
If structural validation fails, the flow MUST stay in existing C1/C2/Env routing (single allowed retry for C1, fallback/compile-first fallback thereafter) and MUST NOT introduce guessed structure.

#### Scenario: Forbidden speculative repair API is invoked
1. Given a call path reaches a sealed speculative repair API
2. When the API is executed
3. Then the system MUST raise a typed invariant exception with error code `SPEC_REPAIR_FORBIDDEN`
4. And MUST NOT continue speculative repair in that path.
