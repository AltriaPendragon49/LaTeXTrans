# Verification

## Test Commands
```bash
pytest -q tests/unit/test_event_loop_nonblocking_phase_a.py
pytest -q tests/unit/test_async_compiler_and_compile_semaphore.py
pytest -q tests/unit/test_async_blocking_db_mode.py
pytest -q tests/unit/test_stategraph_orchestrator.py tests/unit/test_pipeline_guard_assertions.py
python -m py_compile backend/app/utils/async_blocking.py backend/app/api/routes/translate.py backend/app/api/routes/settings.py backend/app/api/routes/history.py backend/app/services/agents/generator_agent.py backend/app/services/agents/langgraph_orchestrator.py backend/app/services/latex/compiler.py backend/app/services/task_manager.py backend/app/main.py backend/app/core/config.py backend/app/core/supabase_client.py
```

## Results
- Behavior-gate tests: pass
- Async compiler cancellation/timeout tests: pass
- Compile semaphore serialization test: pass
- Orchestrator/pipeline regression subset: pass
- Python compile checks: pass
- Real output replay regression checks: pass (legacy selection semantics restored)
- True async fallback path tests: pass (no sync-core invocation when `ASYNC_COMPILER_ENABLED=true`)
- Compile critical-section placement fix: pass (full generator no longer serialized; compile phase remains serialized by semaphore)

## Thresholds / Criteria
- Event-loop max scheduler gap under simulated blocking load: `< 50ms`
- Parallel parser wall-time gate: `< 0.5s` for two 0.3s simulated blocking parse jobs
- Compilation timeout/cancel: must call process-tree termination and cleanup callback once

## Failure Taxonomy
- Timeout failure: compile exits `failed_compilation` with timeout exit code semantics and process cleanup.
- Cancellation failure: task cancellation raises cancellation path, tears down process tree, clears runtime compile metadata.
- Compile failure: no valid PDF and engine attempts exhausted -> `failed_compilation`.
- Fallback warning: valid PDF with residual errors -> `completed_with_warnings`.
- DB failure in async wrappers: route-level error handling remains unchanged; wrapper only changes execution mode.

## Regression Replay Evidence (2026-03-13)
- Replayed failed sample `2501.17151-0313-1036-c27a95e3-8858-47c5-a500-c98b25c9777e`:
  - Previous symptom: `Compilation returned a missing PDF path: .../TRODO.pdf` while PDF existed.
  - Current result: `status=completed_with_warnings`, `pdf_path=.../TRODO.lualatex.stage0.pdf`, file exists.
- Replayed failed sample `2501.17284-0313-1036-f32e3763-00eb-4978-987d-6d75a8fb0aaa`:
  - Previous symptom: `missing PDF path .../main-neurips.pdf`.
  - Current result: `status=completed_with_warnings`, `pdf_path=.../main-neurips.lualatex.stage0.pdf`, file exists.
- Replayed failed sample `2503.10324-0313-1036-c3ec1a2e-0225-432f-9bef-2ad345960860`:
  - Previous symptom: compile failure despite generated PDF artifacts.
  - Current result: `status=completed`, `pdf_path=.../CVPR25_ID5397_IDEA_Wang_arXiv.lualatex.stage0.pdf`, file exists.

## Added Regression Gates
- `test_async_intelligent_fallback_uses_async_compile_path_and_preserves_selection`
  - Ensures async intelligent fallback runs via `compile_latex_async`, does not invoke sync fallback core in enabled mode, and still returns warning-level successful PDF selection.
- `test_generator_execute_async_treats_existing_warning_pdf_as_success`
  - Ensures generator async path reports success when compiler returns warning status with an existing PDF path.
- `test_node_generate_no_longer_serializes_full_generator`
  - Ensures orchestrator no longer holds compile semaphore around full generation flow.
- `test_generator_compile_phase_respects_compile_semaphore`
  - Ensures compile semaphore is enforced at actual compile phase in generator async path.

Note: this repository currently ignores `backend/tests/**` in git, so these gates are local verification guards unless test ignore policy is adjusted.

## Audit Artifacts Template
- Runtime fields: `compile_pid`, `compile_engine`, `compile_started_at`
- Task log events: `compilation_completed`, `compilation_completed_with_warnings`, `compilation_failed`, `structure_invalid_aborted`
- Audit log entries: `node_enter:generate`, `node_exit:generate`, `pipeline_start`, `pipeline_end`

## Rollback Steps
1. Set `ASYNC_COMPILER_ENABLED=false` to return to sync compile path.
2. Set `ASYNC_BLOCKING_WRAPPERS_ENABLED=false` to disable thread offload wrappers.
3. Keep `worker=1` unchanged.
