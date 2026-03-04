## 1. Phase 1 - Input-Layer Defense (Pre-LLM)
- [x] 1.1 Implement inline math hard isolation: extract valid inline math (`$...$`, `\(...\)`) and replace with immutable placeholders (for example `<INLMATH_01>`).
- [x] 1.2 Implement high-risk token preprocessing for text-mode underscores (`_`) before LLM translation.

## 2. Phase 2 - Validation and Retry Routing
- [x] 2.1 Refactor `ValidatorAgent.classify_error` to subclassify Type C errors into C1 (local/contained) and C2 (global/structural).
- [x] 2.2 Add controlled LLM retry logic (max 1) for C1 errors only; C2 bypasses LLM retry.

## 3. Phase 3 - Deterministic Repair Layer
- [x] 3.1 Make text-mode bare underscore escaping (`_ -> \_`) the primary deterministic repair action.
- [x] 3.2 Restrict math delimiter repair to explicit math-signal conditions only.
- [x] 3.3 Keep structural fallback at chunk/paragraph granularity instead of full-section rollback.

## 4. Phase 3 Extension - Environment Structural Hardening
- [x] 4.1 Add strict eqnarray helpers in `utils.py`: comment masking/restoration, row split/rebuild, row-kind classification, immutable placeholder sequence validation, and skip-tag extension for `ITEM/EQROW/EQCOMMENT`.
- [x] 4.2 Add env-specialized translation paths in `translator_agent.py`:
- [x] 4.2.1 eqnarray row-level translation with row-level fallback.
- [x] 4.2.2 enumerate/itemize item-anchor (`<ITEM_n>`) validation path.
- [x] 4.2.3 env metadata persistence: `translation_status`, `fallback_subtype`, `row_fallback_count`.
- [x] 4.3 Extend validator checks in `validator_agent.py`:
- [x] 4.3.1 `ITEM/EQROW` immutable placeholder extraction and validation.
- [x] 4.3.2 list structure checks (`\item` count/order/boundary integrity).
- [x] 4.3.3 classification mapping updates (`item/list -> C1`, `eqrow -> C2`).
- [x] 4.4 Extend coordinator validation summary in `coordinator_agent.py`:
- [x] 4.4.1 add `fallback_count_env_math`, `fallback_count_env_list`, `fallback_count_env_other`.

## 5. Phase 4 - LangGraph Agent Evolution (Split into new Change)
- [x] 5.0 This phase has been split into a dedicated OpenSpec change: `langgraph-agent-evolution`.
- [x] Initial design and task list for LangGraph migration migrated to the new change.

## 6. Verification Record - Final (Phase1-3 Baseline Hardening)
- All deterministic hardening phases (Phase 1-3 and Phase 3 extension) are fully implemented and verified.
- Local regression coverage: `Pass (82 tests)`.
- Critical structural environments (math, lists, eqnarray) show significant reduction in fallback radius.
- Language decision and compiler shims for JA regressions verified.

## 7. Regression Tests
- [x] `pytest backend/tests/unit/test_error_classification.py`
- [x] `pytest backend/tests/unit/test_input_layer_defense.py`
- [x] `pytest backend/tests/unit/test_deterministic_repair.py`
- [x] `pytest backend/tests/unit/test_leakage_downgrade.py`
- [x] `pytest backend/tests/unit/test_parser_chunking.py`
- [x] `pytest backend/tests/unit/test_immutable_placeholder_integrity.py`
- [x] `pytest backend/tests/unit/test_compiler_intelligent_fallback.py`

## 8. Final Status
- [x] All Phase 1-3 tasks are completed.
- [x] Phase 4 (LangGraph) is deferred to `langgraph-agent-evolution`.
- [x] Change is ready for archiving.
