## Context
The current backend path differs from the standalone CLI in two important ways:

- Runtime concurrency: backend defaults and API route caps constrain per-task LLM fan-out to `3`, while the standalone CLI uses `10`.
- Guardrail execution: recent hard-freeze work correctly blocks mutated protected tokens at the boundary, but two downstream behaviors still needed correction:
  - `structure_guard` assembled `\input` trees by appending child files after parent text, which can reorder environment closures and create false positives.
  - Caption and environment invariant failures were not always tagged as explicit passthrough states, so the pipeline could keep revisiting the same bad subparts.

The user wants this round to preserve quality guardrails, keep repair and validation behavior intact, and synchronize the verified fix to the server.

## Goals / Non-Goals
- Goals:
  - Restore backend LLM concurrency parity with the standalone CLI for a single task.
  - Eliminate the observed `structure_guard` false-positive class around nested `\input`.
  - Prevent hard-freeze invariant failures from amplifying retries for captions and environments.
  - Capture this work in OpenSpec and an implementation record.
- Non-Goals:
  - Re-architect task-queue topology.
  - Increase compile concurrency in production.
  - Remove validation, repair, or compile-aware fallback guardrails.

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

## Risks / Trade-offs
- Raising backend LLM concurrency to `10` may increase provider-side throttling pressure in multi-task bursts. Existing global semaphore behavior and 429 handling remain in place.
- Compile serialization remains a residual bottleneck for multiple simultaneous tasks, so this change improves single-task parity more than cluster-wide throughput.
- Server validation depends on access to the current production host and its operational secrets boundary.

## Migration Plan
1. Update OpenSpec deltas.
2. Add fail-first coverage for the concurrency parity change.
3. Implement the runtime/config and guard fixes.
4. Run focused local verification.
5. Commit and deploy to the server.
6. Validate admin ingest for `2006.11239`.

## Open Questions
- If multi-paper admin ingest remains slow after LLM parity is restored, should the next change target compile concurrency and externalized compile workers rather than further per-task tuning?
