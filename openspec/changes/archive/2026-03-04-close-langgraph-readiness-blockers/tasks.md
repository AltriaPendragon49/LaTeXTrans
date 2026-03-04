## 1. Implementation

### 1.1 PR1: Hard Freeze Full-Path Closure
- [x] Add shared invariant module with typed errors and payload guards.
- [x] Refactor translator structural-risk calls (normal/retrans/retry) to one freeze/restore LLM entrypoint.
- [x] Refactor parser env-judge payload preparation to freeze pipeline + no-raw-structure + long-span guard.
- [x] Ensure structural-risk callsites cannot bypass unified entrypoint.

### 1.2 PR2: Zero Speculative Structural Repair
- [x] Seal `_fix_missing_placeholders` with forbidden invariant exception.
- [x] Seal `ValidatorAgent.repair_math_delimiters` with forbidden invariant exception.
- [x] Remove active C1/C2 structural injection repair path and keep classify->retry/fallback routing.
- [x] Ensure broad catches re-raise `PipelineInvariantViolation`.

### 1.3 PR3: Replay Evidence Consistency + Stage3 Non-Regression
- [x] Implement scoped quarantine replay-reference rewrite for task logs and replay bundle paths.
- [x] Add evidence-chain reachability self-check and warning event with `evidence_chain_broken=true`.
- [x] Keep task status semantics unchanged when evidence chain breaks.
- [x] Add Stage 3 entrypoint non-bypass and multiline trigger non-regression tests.

## 2. Tests
- [x] Add `test_retrans_payload_no_raw_structure_tokens`.
- [x] Add `test_env_judge_payload_reuses_freeze_pipeline`.
- [x] Add `test_env_judge_payload_no_long_raw_span`.
- [x] Add `test_llm_client_no_freeze_bypass`.
- [x] Add `test_fix_missing_placeholders_forbidden_error_contract`.
- [x] Add `test_repair_math_delimiters_forbidden_error_contract`.
- [x] Add `test_no_structural_token_injection_after_c1_c2_routing`.
- [x] Add `test_quarantine_rewrites_replay_refs_in_scoped_domain`.
- [x] Add `test_quarantine_rewrite_idempotent`.
- [x] Add `test_quarantine_non_target_paths_unchanged`.
- [x] Add `test_evidence_chain_broken_flag_warning_without_status_mutation`.
- [x] Add `test_stage3_entrypoint_not_bypassed_on_image_compile_failure`.
- [x] Add `test_pdf_inclusion_multiline_variant_triggers_stage3`.

## 3. Spec & Validation
- [x] Add spec deltas for `hard-freeze`, `fail-fast-fallback`, `translation-orchestration`, `latex-translation-core`, `file-management`, `tiered-compilation`.
- [x] Run `openspec validate close-langgraph-readiness-blockers --strict --no-interactive`.

## 4. Execution Record (2026-03-04)
- [x] `openspec validate close-langgraph-readiness-blockers --strict --no-interactive` -> pass.
- [x] `PYTHONPATH=. pytest backend/tests/unit/test_langgraph_readiness_invariants.py backend/tests/unit/test_task_manager_replay_quarantine.py backend/tests/unit/test_compiler_intelligent_fallback.py -q` -> `16 passed`.
