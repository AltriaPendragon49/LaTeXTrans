## 1. Implementation
- [x] 1.1 Add behavior-gate tests for event-loop responsiveness and anti-serialization.
- [x] 1.2 Offload parser blocking parse call from async path.
- [x] 1.3 Offload validator blocking execute call from async orchestration path.
- [x] 1.4 Add async blocking wrapper utilities (`run_blocking`, `run_db_blocking`) with feature-flag control.
- [x] 1.5 Add DB execution strategy config (`per_call_client|shared_client`) and default to `per_call_client`.
- [x] 1.6 Migrate async DB calls in translation/settings/history/main async paths to wrapper execution.
- [x] 1.7 Add async compiler subprocess primitives with timeout and cancellation cleanup.
- [x] 1.8 Add async generator execution path and switch orchestration generate node to await async path.
- [x] 1.9 Add compile runtime metadata fields to in-memory task state.
- [x] 1.10 Add compile concurrency semaphore and limit config.
- [x] 1.11 Add tests for async compiler cancellation/timeout and compile semaphore serialization.
- [x] 1.12 Fix async compile regression where valid PDFs were marked missing due to path/selection semantic drift.
- [x] 1.13 Add regression gates ensuring async intelligent fallback preserves legacy payload semantics and warning-PDF success behavior.
- [x] 1.14 Replace async fallback thread wrapper with true async Stage 0/1/2/3 execution based on `compile_latex_async`.
- [x] 1.15 Keep rollback path via `ASYNC_COMPILER_ENABLED=false` to legacy thread-wrapped fallback.
- [x] 1.16 Move compile semaphore acquisition from orchestrator-wide generate block to generator compile await section only.
- [x] 1.17 Add compile wait/exec timing metrics and explicit waiting progress message for compile slot.

## 2. Verification
- [x] 2.1 Run new behavior-gate and compiler tests.
- [x] 2.2 Run orchestrator/pipeline regression subset.
- [x] 2.3 Run Python compile checks for modified modules.
- [x] 2.4 Reproduce and verify real failed task samples from `backend/data/outputs` now resolve to success/warning when PDF exists.
- [x] 2.5 Verify true async fallback path under unit tests and sample replay after implementation.
- [x] 2.6 Verify node-level no-serialization and compile-phase-only semaphore behavior via unit tests.
