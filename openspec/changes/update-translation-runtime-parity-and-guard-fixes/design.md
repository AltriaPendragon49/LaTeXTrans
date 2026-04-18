## Context
The current backend path differs from the standalone CLI in several ways, but the recent investigation showed they do not all belong to the same change boundary.

Internal defects confirmed in this change:

- Runtime concurrency: backend defaults and API route caps constrain per-task LLM fan-out to `3`, while the standalone CLI uses `10`.
- Guardrail execution: recent hard-freeze work correctly blocks mutated protected tokens at the boundary, but downstream orchestration still needed correction:
  - `structure_guard` assembled `\input` trees by appending child files after parent text, which can reorder environment closures and create false positives.
  - Section, caption, and environment invariant failures were not always tagged as explicit passthrough states, so the pipeline could keep revisiting the same bad subparts.
  - Plain API failures could still bleed into rescue / fail-part bookkeeping and create misleading retry work after transport failure.

External or higher-layer runtime issues observed during the same investigation:

- the shared provider route can return upstream `503 Service Unavailable`;
- the backend does not yet have a health-aware token/provider pool with cooldown and fast failover;
- single-server lane scheduling, backfill behavior, and post-success sidecarization live outside this change boundary.

The user wants this round to preserve quality guardrails, keep repair and validation behavior intact, and make the OpenSpec record honest about what was fixed locally versus what still belongs to the broader bucket/pool scheduling work.

## Goals / Non-Goals
- Goals:
  - Restore backend LLM concurrency parity with the standalone CLI for a single task.
  - Eliminate the observed `structure_guard` false-positive class around nested `\input`.
  - Prevent hard-freeze invariant failures from amplifying retries for sections, captions, and environments.
  - Stop plain API failures from being mistaken for placeholder-protection failures by short-circuiting rescue escalation when the transport path is already exhausted.
  - Document the exact boundary between this change and the separate token-pool / scheduler work.
  - Capture this work in OpenSpec and an implementation record.
- Non-Goals:
  - Re-architect task-queue topology.
  - Implement provider health scoring, token cooldown, or multi-token failover inside this change.
  - Increase compile concurrency in production.
  - Remove validation, repair, or compile-aware fallback guardrails.
  - Claim that this change solves upstream provider instability by itself.

## Decisions
- Decision: Raise backend default `llm_max_concurrent_requests` and route-level parity cap to `10`.
  - Why: This is the clearest runtime mismatch between CLI and backend for single-paper throughput.
  - Alternatives considered:
    - Leave the backend at `3`: rejected because it preserves a known parity regression.
    - Raise compile concurrency too: deferred because compile remains resource-heavy and lacks the same parity evidence.

- Decision: Fix `structure_guard` at project-text assembly rather than weakening precompile checks.
  - Why: The root cause was file-order assembly, not overly strict validation.
  - Alternatives considered:
    - Downgrade the guard to warning-only: rejected because it would hide real structural failures.

- Decision: Route caption/env invariant failures to explicit passthrough statuses and deduplicate failed identifiers.
  - Why: This keeps hard-freeze safety intact while stopping unnecessary repeat work.
  - Alternatives considered:
    - Soften hard-freeze verification: rejected because it would weaken the placeholder boundary guarantee.

- Decision: Short-circuit rescue after plain API failure instead of continuing deeper placeholder-oriented retry logic.
  - Why: Provider transport failure and hard-freeze violation are different failure classes; once the API path is exhausted, continuing rescue work adds latency without improving quality.
  - Alternatives considered:
    - Let rescue handle API-failure outputs the same way as invariant failures: rejected because it conflates upstream outages with local placeholder corruption and made slowdown analysis misleading.

- Decision: Record bucket/token-pool/provider instability explicitly as related but separate work, with the main follow-up tracked under `update-single-server-priority-backfill-scheduling`.
  - Why: The user needs the spec record to explain why these fixes are still not enough when the upstream relay is unstable.
  - Alternatives considered:
    - Expand this change to include the full token-pool and lane scheduler redesign: rejected because that would duplicate another active change and blur delivery boundaries.

## Risks / Trade-offs
- Raising backend LLM concurrency to `10` may increase provider-side throttling pressure in multi-task bursts. Existing global semaphore behavior and 429 handling remain in place, but upstream `503` remains possible.
- Compile serialization remains a residual bottleneck for multiple simultaneous tasks, so this change improves single-task parity more than cluster-wide throughput.
- Because the provider route is still external and unstable, a failed live translation after these fixes does not automatically mean the placeholder-protection logic regressed.
- Server validation depends on access to the current production host and its operational secrets boundary.

## Migration Plan
1. Update OpenSpec deltas.
2. Add fail-first coverage for the concurrency parity change.
3. Implement the runtime/config and guard fixes, including the API-failure short-circuit.
4. Record provider-instability findings and boundary notes in the change directory.
5. Run focused local verification.
6. Commit and deploy to the server.
7. Validate admin ingest for `2006.11239`.

## Open Questions
- If live latency remains poor mainly because of upstream `503`, should the next delivered change prioritize token-pool cooldown/failover before any further placeholder-quality tuning?
- If multi-paper admin ingest remains slow after provider failover work lands, should the next change target compile concurrency and externalized compile workers rather than further per-task tuning?
