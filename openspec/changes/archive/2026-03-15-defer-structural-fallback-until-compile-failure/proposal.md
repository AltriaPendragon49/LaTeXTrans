# Change: Defer Structural Fallback Until Compile Failure

## Why
The current compile-first structural fallback rewrites `trans_content` back to source text during `validate_and_retry`. That can erase target-language output that still compiles and reads better, as seen in task `2508.18791`. This behavior conflicts with the project's target-language persistence rule.

## What Changes
- Stop validate-stage source rollback for structural fallback candidates.
- Record structural fallback candidates and preserve target-language `trans_content` for the first compile attempt.
- Apply deterministic target-language downgrade only after the first compilation fails, then allow exactly one compile retry.
- Add explicit status, config, audit, and task-log semantics for post-compile fallback.
- Replace the empty `eliminate-silent-enhanced-fallback` placeholder change with this implemented change.
- Replace the skipped `final_language_fallback` test intent with real orchestrator/post-compile fallback tests.

## Impact
- Affected specs: `translation-orchestration`, `ControlledRepairWorkflow`, `fail-fast-fallback`
- Affected code: `backend/app/services/agents/translator_agent.py`, `backend/app/services/agents/langgraph_orchestrator.py`, `backend/app/core/config.py`, `backend/app/api/routes/translate.py`
- Affected tests: `backend/tests/unit/test_immutable_placeholder_integrity.py`, `backend/tests/unit/test_deterministic_repair.py`, `backend/tests/unit/test_stategraph_orchestrator.py`, `backend/tests/unit/test_ultimate_downgrade.py`, `backend/tests/unit/test_post_compile_target_language_fallback.py`
- Supersedes: empty placeholder directory `openspec/changes/eliminate-silent-enhanced-fallback/`
