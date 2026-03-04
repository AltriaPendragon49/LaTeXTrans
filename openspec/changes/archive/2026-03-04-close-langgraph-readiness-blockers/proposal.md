# Change: Close LangGraph Readiness Blockers

## Why
LangGraph Phase 4a is currently blocked by three correctness risks:
- Structural LaTeX tokens can still leak into LLM payloads on retrans/env-judge paths.
- Legacy speculative repair entrypoints can still be invoked.
- Failed-task quarantine can break replay evidence references.

This change closes those blockers without introducing new capabilities and without changing existing C1/C2/Env + compile-first fallback semantics.

## What Changes
- Enforce one freeze/restore LLM entry for structural-risk translation calls (normal/retrans/retry/env-judge).
- Add hard payload guardrails that reject raw `\begin{`, `\end{`, and unescaped `$` in outbound LLM payloads.
- Forbid speculative structure-repair APIs via typed invariant exceptions and remove active call paths.
- Add scoped, idempotent replay-reference rewriting after failed-task quarantine.
- Add evidence-chain reachability checks and warning events (`evidence_chain_broken=true`) without changing task terminal status semantics.
- Add Stage 3 sanitizer non-regression tests only (no sanitizer algorithm rewrite).

## Impact
- Affected specs:
  - `hard-freeze`
  - `fail-fast-fallback`
  - `translation-orchestration`
  - `latex-translation-core`
  - `file-management`
  - `tiered-compilation`
- Affected code:
  - `backend/app/services/agents/translator_agent.py`
  - `backend/app/services/agents/parser_agent.py`
  - `backend/app/services/agents/validator_agent.py`
  - `backend/app/services/agents/pipeline_invariants.py` (new)
  - `backend/app/services/task_manager.py`
  - `backend/app/api/routes/task.py`
  - `backend/tests/unit/*` (new and updated tests)

## Relation to Prior PDF Sanitizer Work
- `2026-03-03-latex-sanitization-layer-finish` remains the implementation baseline for Stage 3 sanitizer behavior.
- This change does not supersede or rewrite that implementation.
- Scope here is admission-guard and regression-proofing for LangGraph readiness only.

## Implementation Progress (2026-03-04)
- Completed code changes:
  - `backend/app/services/agents/pipeline_invariants.py` (new invariant contract + guards)
  - `backend/app/services/agents/translator_agent.py`
  - `backend/app/services/agents/parser_agent.py`
  - `backend/app/services/agents/validator_agent.py`
  - `backend/app/services/task_manager.py`
  - `backend/app/api/routes/task.py`
- Completed test coverage:
  - `backend/tests/unit/test_langgraph_readiness_invariants.py`
  - `backend/tests/unit/test_task_manager_replay_quarantine.py`
  - `backend/tests/unit/test_compiler_intelligent_fallback.py`
- Validation record:
  - `openspec validate close-langgraph-readiness-blockers --strict --no-interactive` passed on 2026-03-04.
  - `PYTHONPATH=. pytest backend/tests/unit/test_langgraph_readiness_invariants.py backend/tests/unit/test_task_manager_replay_quarantine.py backend/tests/unit/test_compiler_intelligent_fallback.py -q` passed (`16 passed`) on 2026-03-04.
