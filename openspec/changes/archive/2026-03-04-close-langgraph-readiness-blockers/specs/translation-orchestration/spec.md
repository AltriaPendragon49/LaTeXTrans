## ADDED Requirements
### Requirement: Unified Structural-Risk LLM Entry
All structural-risk translation requests MUST use one freeze/restore LLM entrypoint so payload guarding and restoration are applied consistently.

#### Scenario: Structural-risk call bypass attempt
1. Given a structural-risk callsite for section/env/caption translation or retranslation
2. When the call is executed
3. Then it MUST pass through the unified freeze entrypoint
4. And direct raw client invocation outside that entrypoint MUST NOT occur.

### Requirement: C1/C2 Routing Without Speculative Injection
C1/C2 orchestration MUST retain existing retry/fallback semantics while prohibiting speculative structure-token injection.

#### Scenario: C2 structural error handling
1. Given a part classified as C2
2. When error routing executes
3. Then the system MUST skip speculative repair injection
4. And MUST go directly to existing compile-first fallback semantics.
