## Context
The original change bundled multiple backend resilience topics. In implementation, only the community-agent bridge scope was completed and validated:
- bounded retries for reasoning-provider calls,
- deterministic title-to-arXiv context bridge,
- conversation-scoped `paper_id` propagation.

This design records the completed scope only.

## Goals / Non-Goals
- Goals:
  - Improve agent reliability under transient provider/network failures.
  - Allow title-only prompts to resolve/import/read paper context deterministically.
  - Prevent cross-conversation paper-id leakage by enforcing active-thread scoping.
- Non-Goals:
  - Translation pipeline fan-out/refume/status taxonomy changes.
  - Compile diagnostics/status-model refactors in this scoped archive.

## Decisions

### Decision 1: Bounded retry/backoff for reasoning-provider calls
- Retry transient HTTP/network failures for a bounded number of attempts.
- Apply exponential backoff with caps to avoid burst retries.
- Fail with explicit runtime diagnostics after retry budget exhaustion.

Why:
- Reduces brittle failures from temporary upstream instability.
- Keeps failures diagnosable and deterministic.

### Decision 2: Deterministic title bridge fallback
- Detect standalone title-like queries when no paper context is bound.
- Resolve candidate arXiv id from title, import/reuse paper, then read paper context.
- Auto-start translation when translated content is unavailable and request intent/context indicates translation.

Why:
- Improves first-message success without requiring manual paper-id handling.
- Keeps context acquisition explicit and traceable.

### Decision 3: Strict conversation-scoped paper context
- Derive outgoing `paper_id` only from the active conversation thread metadata.
- Ignore paper ids from inactive/sibling conversations.

Why:
- Prevents cross-thread context leakage.
- Preserves correctness in multi-conversation workflows.

## Risks / Trade-offs
- Risk: title resolution may produce low-confidence matches.
  - Mitigation: confidence thresholds and explicit resolver trace.
- Risk: retries can increase latency for degraded upstreams.
  - Mitigation: bounded attempt count and capped backoff.
- Risk: stricter context scoping may reduce "helpful" implicit carry-over.
  - Mitigation: explicit import/read-context bridge path remains available.

## Migration Plan
1. Ship retry/backoff and bridge behavior behind existing agent runtime flow.
2. Validate with unit/UI tests for retry and conversation-scoped `paper_id` propagation.
3. Archive this scoped change after OpenSpec validation.

## Open Questions
- None for this scoped archive.
