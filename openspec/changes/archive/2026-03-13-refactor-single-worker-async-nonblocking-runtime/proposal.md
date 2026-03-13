# Change: Refactor Single-Worker Runtime to Async Non-Blocking Execution

## Why
Current single-worker runtime can degrade into effectively serial execution because heavy synchronous operations run inside async paths. This blocks health/status endpoints and reduces throughput under concurrent translation tasks.

## What Changes
- Add async-safe blocking wrappers for DB and CPU/I/O heavy segments in async paths.
- Introduce async compilation infrastructure with subprocess process-group semantics and cancellation-safe cleanup.
- Implement true async intelligent fallback execution (`await compile_latex_async` across Stage 0/1/2/3) so async orchestration no longer depends on whole-function thread wrapping.
- Restore legacy compile-result evaluation semantics in async orchestration path to prevent false `failed_compilation` when a valid warning PDF exists.
- Move compile semaphore boundary from orchestration `node_generate` full-flow wrapper to the true compile await region in `GeneratorAgent.execute_async`.
- Add explicit compile-slot waiting progress signal and compile timing telemetry (`compile_queue_wait_ms`, `compile_exec_ms`) in generation result/audit logs.
- Add single-worker compilation concurrency governance via configurable semaphore.
- Add runtime-only compile process tracking fields (`compile_pid`, `compile_engine`, `compile_started_at`) in in-memory task state.
- Add feature flags for rollback:
  - `ASYNC_COMPILER_ENABLED`
  - `ASYNC_BLOCKING_WRAPPERS_ENABLED`
  - `DB_EXECUTION_MODE`
  - `MAX_CONCURRENT_COMPILATIONS`

## Impact
- Affected specs:
  - `latex-translation-core`
  - `web-api`
  - `task-cancellation`
  - `TaskRuntimeState`
- Affected code:
  - `backend/app/services/agents/parser_agent.py`
  - `backend/app/services/agents/langgraph_orchestrator.py`
  - `backend/app/services/agents/generator_agent.py`
  - `backend/app/services/latex/compiler.py`
  - `backend/app/services/task_manager.py`
  - `backend/app/api/routes/{translate,settings,history}.py`
  - `backend/app/main.py`
  - `backend/app/core/{config,supabase_client}.py`
  - `backend/app/utils/async_blocking.py`
  - `openspec/changes/refactor-single-worker-async-nonblocking-runtime/*`
