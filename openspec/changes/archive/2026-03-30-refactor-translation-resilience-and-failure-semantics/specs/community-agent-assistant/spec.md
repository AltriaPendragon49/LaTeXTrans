## ADDED Requirements
### Requirement: Community agent reasoning provider retries transient failures with bounded backoff
The community agent runtime SHALL retry transient reasoning-provider failures with bounded exponential backoff before entering deterministic fallback.

#### Scenario: Transient reasoning-provider failure is retried
- **WHEN** a reasoning-provider call fails with a transient network/HTTP error (for example timeout, 429, or gateway-like 4xx/5xx)
- **THEN** the runtime SHALL retry that call for a bounded number of attempts
- **AND** it SHALL apply increasing backoff delay between retries.

#### Scenario: Retries are exhausted
- **WHEN** all bounded retry attempts fail
- **THEN** the runtime SHALL emit failure diagnostics that include HTTP/network context
- **AND** it SHALL continue with deterministic fallback behavior instead of hanging.

### Requirement: Community agent title bridge fallback resolves papers for translation handoff
The community agent runtime SHALL support a deterministic title-based bridge path that resolves a likely arXiv id, imports/reuses the paper, reads paper context, and starts translation when translated content is unavailable.

#### Scenario: Standalone title query can bridge to translation without pre-bound paper id
- **WHEN** a user asks with a standalone paper title and no paper id is already bound in context
- **THEN** the runtime SHALL attempt title-to-arXiv resolution and import/reuse that paper
- **AND** it SHALL read paper context and auto-start translation if translated-ready content is not available.

#### Scenario: Title bridge emits explicit resolver trace
- **WHEN** title-to-arXiv resolution succeeds or fails
- **THEN** the runtime SHALL record explicit trace metadata for the resolver step
- **AND** downstream UI/diagnostics SHALL be able to distinguish resolution success from fallback failure.
