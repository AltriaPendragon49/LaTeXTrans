## Context
Production runtime stays `worker=1` because task runtime state and cancellation pointers are process-local. The performance issue is not worker count itself, but event-loop blocking due to synchronous heavy operations in async call chains.

## Goals / Non-Goals
- Goals:
  - Remove event-loop blocking from critical async translation paths.
  - Preserve API contract and translation semantics.
  - Ensure compilation cancellation kills process trees and converges task state.
  - Improve responsiveness under compile load.
- Non-Goals:
  - Multi-worker rollout.
  - Prompt/context strategy changes.
  - Intra-task chunk parallelism changes.

## Decisions
- Decision: introduce `run_blocking` / `run_db_blocking` utility wrappers.
  - Why: centralizes async-safe thread offload with rollback flag.
- Decision: default DB execution mode `per_call_client`.
  - Why: safer under uncertain shared-client thread-safety.
- Decision: async compiler path uses `asyncio.create_subprocess_exec`.
  - Why: supports cancellation, timeout, and non-blocking wait.
- Decision: async orchestration now runs a native async intelligent fallback state machine (`await compile_latex_async`) across Stage 0/1/2/3.
  - Why: preserve event-loop responsiveness and keep compile cancellation tied to real subprocess PIDs.
  - Rollback: `ASYNC_COMPILER_ENABLED=false` keeps a thread-wrapped legacy fallback path available.
- Decision: subprocess spawned as isolated process-group/session.
  - Linux: `start_new_session=True`
  - Windows: `CREATE_NEW_PROCESS_GROUP`
- Decision: compilation concurrency semaphore only wraps compile await region.
  - Why: avoid oversized critical section.
- Decision: remove compile semaphore from `node_generate` and acquire it inside `GeneratorAgent.execute_async` immediately before `compile_with_intelligent_fallback_async`.
  - Why: `node_generate`-level locking serialized reconstruction/formatting/guard work and caused long `Generating PDF` queue inflation.
- Decision: expose compile queue/exec timings in generation outputs and audit logs.
  - Why: make "waiting for slot" vs "actual compile time" observable for tuning.
- Decision: runtime compile metadata tracked in memory task state only.
  - Why: aligns with current single-worker runtime-state architecture.

## Risks / Trade-offs
- Risk: full async fallback selection logic can drift from legacy heuristics.
  - Mitigation: regression gates verify warning-PDF success semantics and path existence checks at generator/orchestrator boundaries.
- Risk: DB per-call client adds latency.
  - Mitigation: configurable `DB_EXECUTION_MODE`.

## Rollback Plan
1. Disable `ASYNC_COMPILER_ENABLED` to revert compile path.
2. Disable `ASYNC_BLOCKING_WRAPPERS_ENABLED` to revert thread wrappers.
3. Keep `worker=1` unchanged.

## Validation Strategy
- Behavior-gate tests for event-loop health and parallel wall-time.
- Cancellation and timeout tests for async compiler process teardown.
- Semaphore serialization tests for compile critical section.
- Existing orchestrator/pipeline regression tests.
- Regression test verifies `node_generate` no longer serializes full generator execution.
- Regression test verifies compile semaphore serialization at generator compile phase only.
