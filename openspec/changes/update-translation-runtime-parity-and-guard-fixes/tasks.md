## 1. Evidence And Spec
- [x] 1.1 Quantify task-stage timings and isolate which slowdown is caused by LLM concurrency caps versus compile serialization.
- [x] 1.2 Add OpenSpec deltas for CLI-parity LLM concurrency defaults and for the structural guard / hard-freeze orchestration fixes.

## 2. Implementation
- [x] 2.1 Align backend LLM concurrency defaults and route-level cap with standalone CLI parity (`10`).
- [x] 2.2 Fix project-text assembly for `\input` / `\include` callsite ordering and nested relative-path resolution.
- [x] 2.3 Ensure caption/env hard-freeze invariant failures short-circuit to passthrough metadata and deduplicated failure tracking.

## 3. Verification
- [x] 3.1 Add or update focused unit tests for concurrency-parity defaults, structure-guard include ordering, and hard-freeze invariant passthrough behavior.
- [x] 3.2 Run focused verification locally and capture any known unrelated test blockers.
- [ ] 3.3 Commit the change, sync it to the production server, restart the backend, and validate admin ingest / translation for `2006.11239`.

## 4. Documentation
- [x] 4.1 Record the implementation details for this worktree under the change directory so the fixes are traceable before archive.
