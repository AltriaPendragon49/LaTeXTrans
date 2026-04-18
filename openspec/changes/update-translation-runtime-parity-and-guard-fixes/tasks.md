## 1. Evidence And Spec
- [x] 1.1 Quantify task-stage timings and isolate which slowdown is caused by LLM concurrency caps versus compile serialization.
- [x] 1.2 Add OpenSpec deltas for CLI-parity LLM concurrency defaults and for the structural guard / hard-freeze orchestration fixes.
- [x] 1.3 Record the live investigation result that upstream provider `503` instability is a separate failure layer and not fully addressed by this change.
- [x] 1.4 Clarify in `proposal.md` and `design.md` that bucket/token-pool failover belongs to `update-single-server-priority-backfill-scheduling`, while this change remains focused on verified parity and guard fixes.

## 2. Implementation
- [x] 2.1 Align backend LLM concurrency defaults and route-level cap with standalone CLI parity (`10`).
- [x] 2.2 Fix project-text assembly for `\input` / `\include` callsite ordering and nested relative-path resolution.
- [x] 2.3 Ensure caption/env hard-freeze invariant failures short-circuit to passthrough metadata and deduplicated failure tracking.
- [x] 2.4 Short-circuit rescue escalation after exhausted plain API failures so provider outages do not fan back into placeholder-oriented retry loops.

## 3. Verification
- [x] 3.1 Add or update focused unit tests for concurrency-parity defaults, structure-guard include ordering, and hard-freeze invariant passthrough behavior.
- [x] 3.2 Run focused verification locally and capture any known unrelated test blockers.
- [ ] 3.3 Commit the change, sync it to the production server, restart the backend, and validate admin ingest / translation for `2006.11239`.
- [ ] 3.4 Re-check the live paper against provider health evidence before attributing any remaining slowdown to placeholder protection.

## 4. Documentation
- [x] 4.1 Record the implementation details for this worktree under the change directory so the fixes are traceable before archive.
- [x] 4.2 Cross-link this change with the broader scheduler/token-pool change so future readers do not confuse local guard fixes with provider failover work.
