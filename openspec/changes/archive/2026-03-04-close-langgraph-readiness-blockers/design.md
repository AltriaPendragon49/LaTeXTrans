## Context
Phase 4a LangGraph migration requires deterministic structural safety. Current backend still has:
- non-unified structural LLM call paths,
- speculative repair codepaths that can inject structure tokens,
- replay references that may become unreachable after quarantine move.

## Goals
- Lock structural invariants so LangGraph migration is functionally equivalent and replayable.
- Keep existing failure routing semantics (C1/C2/Env + compile-first fallback).
- Preserve Stage 3 sanitizer behavior as-is and add non-regression checks.

## Non-Goals
- No new retry strategy.
- No new sanitizer strategy.
- No migration of Stage 3 logic into LangGraph nodes.

## Decisions

### Decision 1: Typed invariant exception contract
- Add `PipelineInvariantViolation` with required `error_code`.
- Add `SpeculativeRepairForbiddenError` (`SPEC_REPAIR_FORBIDDEN`).
- Add `RawStructurePayloadViolation` (`RAW_STRUCTURE_EXPOSED`).
- Add `RawContentLeakageViolation` (`RAW_ENV_BODY_EXPOSED`).
- Any broad catch that touches these paths must re-raise `PipelineInvariantViolation`.

### Decision 2: Raw-structure payload guard
- Guard runs before structural-risk LLM request is sent.
- Mandatory fail patterns:
  - `\begin{`
  - `\end{`
  - unescaped `$` (`(?<!\\)\$`)
- On hit: do not call LLM; route through existing fallback path.

### Decision 3: env-judge freeze coverage
- env-judge payload preparation reuses same freeze pipeline shape as translation:
  - inline math isolation
  - env isolation
  - protected command masking
  - risky token preprocessing
- env-judge additionally enforces contiguous raw-span leakage guard:
  - longest contiguous overlap between source body and payload must be `< 200`.

### Decision 4: Speculative repair is sealed
- `_fix_missing_placeholders` and `ValidatorAgent.repair_math_delimiters` stay in place for compatibility.
- Both are sealed as forbidden invariant entrypoints and raise typed error immediately.
- Active C1/C2 flow no longer calls speculative structure injection repair.

### Decision 5: Replay rewrite domain and idempotence
- Quarantine rewrite scope is strict:
  - rewrite only absolute paths under old task root (`.../outputs/{task_id}/...`)
  - target root is actual quarantine folder (`.../failed_tasks/{task_id}[_{suffix}]/...`)
- Rewrite fields:
  - `task_log[*].replay_bundle_ref`
  - `replay_bundle.main_tex_path`
  - replay-bundle keys ending `_path` or `_ref` only when value starts with old task root
- Non-target absolute paths are not modified.
- Second rewrite pass is byte-stable (no further writes).

### Decision 6: Evidence chain warning semantics
- `evidence_chain_broken=true` only when:
  - `replay_bundle_ref` path unreachable, or
  - `main_tex_path` path unreachable
- On break:
  - append `evidence_chain_warning` event in `task_log.json`
  - do not mutate terminal status semantics.

### Decision 7: Stage 3 sanitizer admission boundary
- Keep existing compiler/sanitizer implementation unchanged.
- Add tests to prove compile-failure image errors still reach Stage 3 entrypoint, including multiline `(pdf inclusion)` variants.

## Risks / Trade-offs
- Payload guard may increase source fallback frequency for malformed diagnostic prompts; this is intentional to enforce zero exposure.
- Replay rewrite is intentionally conservative; only scoped fields are rewritten to avoid path corruption.

## Migration Notes
- No data migration.
- This change is safe to deploy incrementally because invariant violations degrade to existing fallback behavior.

## Change Log (2026-03-04)
- Workflow status:
  - `tasks.md` implementation/test/spec-validation checklist updated to completed.
  - Decision lock in this design is now reflected in code paths listed below.
- Decision-to-code trace:
  - Decision 1/2/4 -> `backend/app/services/agents/pipeline_invariants.py`, `translator_agent.py`, `validator_agent.py`
  - Decision 3 -> `backend/app/services/agents/parser_agent.py`
  - Decision 5/6 -> `backend/app/services/task_manager.py`, `backend/app/api/routes/task.py`
  - Decision 7 (non-regression guard) -> `backend/tests/unit/test_compiler_intelligent_fallback.py`
- Verification snapshot:
  - `openspec validate close-langgraph-readiness-blockers --strict --no-interactive` passed.
  - `PYTHONPATH=. pytest backend/tests/unit/test_langgraph_readiness_invariants.py backend/tests/unit/test_task_manager_replay_quarantine.py backend/tests/unit/test_compiler_intelligent_fallback.py -q` passed (`16 passed`).
