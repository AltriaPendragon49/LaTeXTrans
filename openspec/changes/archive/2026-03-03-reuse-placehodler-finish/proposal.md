# Change: Refactor Translation Pipeline for Structural Safety and LangGraph Orchestration

## Why
Current high-frequency structural failures (Type C errors) are caused by the LLM mishandling LaTeX math boundaries, list/item structures, and special symbols (e.g., dropping `$`, reordering `\item`, or emitting bare `_` in text mode). This causes validation failures and costly compile-first fallbacks that erase significant portions of translated text. We need to eliminate this by removing structural responsibility from the LLM (freezing structure deterministically outside the model), strengthening environment-level guards (eqnarray/list), and refactoring orchestration to LangGraph in a later phase.

## What Changes
- **Phase 1 (Input-Layer Defense):** Implement hard isolation for inline math by replacing `$...$` and `\(...\)` with strict placeholders (e.g., `<INLMATH_01>`). Preprocess high-risk text tokens to pre-escape `_` outside of math blocks.
- **Phase 2 (Validation & Retry Routing):** Subclassify Type C errors into C1 (Local/Contained) and C2 (Global/Structural). Introduce a strictly controlled 1-max LLM retry exclusively for C1 errors.
- **Phase 3 (Deterministic Repair):** Invert the repair strategy: bare `_` outside math is deterministically escaped to `\_` as the primary rule. Conditional math delimiter repair is heavily restricted. Fallback granularity is reduced to the paragraph/chunk level instead of the full section.
- **Phase 3 Extension (Env Structural Hardening):** Add eqnarray row-level strict processing (comment masking, row split/rebuild, text-row only translation, row-level fallback), list environment item anchoring (`<ITEM_n>`), immutable placeholder sequence validation (`ITEM`/`EQROW`), and env-level fallback subtype accounting.
- **Phase 3 Observability Extension:** Persist env-level translation metadata (`translation_status`, `fallback_subtype`, `row_fallback_count`) and validation summary counters (`fallback_count_env_math/list/other`) for diagnosis and regression tracking.
- **Phase 4 (LangGraph Agent Evolution):** DEFERRED and SPLIT into a dedicated OpenSpec change: `langgraph-agent-evolution`.

## Impact
- Affected specs: `translation-orchestration`.
- Affected code:
  - `backend/app/services/latex/utils.py`
  - `backend/app/services/latex/compiler.py`
  - `backend/app/services/agents/translator_agent.py`
  - `backend/app/services/agents/validator_agent.py`
  - `backend/app/services/agents/generator_agent.py`
  - `backend/app/services/agents/coordinator_agent.py`
  - `backend/tests/unit/test_input_layer_defense.py`
  - `backend/tests/unit/test_deterministic_repair.py`
  - `backend/tests/unit/test_compiler_intelligent_fallback.py`
