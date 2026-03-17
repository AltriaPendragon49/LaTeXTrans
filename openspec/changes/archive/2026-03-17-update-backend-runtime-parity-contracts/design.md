# Design: Backend Runtime Parity Contracts

## Context
The backend and standalone CLI now share the same translation kernel, but parity work in the backend added several behavior-level fixes that were previously only implicit in code:
- task-level LLM concurrency is capped to the CLI-compatible ceiling before orchestration starts;
- safe-limit configuration (`model_context_tokens`, `prompt_reserve_tokens`) is propagated into the runtime config snapshot used by the coordinator;
- validation/retry loops stop early when repeated retries make no progress;
- task-start logs now carry masked LLM runtime configuration for postmortem comparisons;
- abstract-like generic text environments receive one last paragraph-wise rescue attempt before the system gives up and preserves source text;
- CJK final PDF selection prefers `xelatex` whenever it successfully produces a PDF, instead of allowing a lower-error `lualatex` artifact to become the final result by default.

## Conflict Review
### Active changes
- `extract-standalone-cli-translation-core` already documents the CLI extraction target and is marked complete. It does not define the backend-specific runtime contract that emerged during parity fixing.
- `add-fallback-model` focuses on retry model selection, not runtime parity.
- `implement-rag-terminology` focuses on terminology retrieval and injection, not orchestration/runtime behavior.

### Archived changes
- Archived compiler proposals describe earlier fallback orders and broader "choose the fewest-error modern engine" behavior. The current backend code is more specific for CJK final artifact selection and must supersede those historical assumptions.
- Archived runtime-safety changes explain async/non-blocking goals, but they do not define the new retry-stagnation short-circuit or task-start runtime observability.

## Decisions
1. Create a new change instead of reopening `extract-standalone-cli-translation-core`.
   - Reason: the extraction change is complete and CLI-oriented, while the current work is backend-runtime specific.
2. Treat the current backend code as the source of truth.
   - Reason: the user explicitly requested that conflicts be resolved in favor of the current behavior.
3. Update existing capabilities instead of adding a brand-new capability.
   - Reason: these fixes refine `latex-translation-core`, `translation-orchestration`, `tiered-compilation`, and `web-api` rather than introducing a new product surface.

## Spec Mapping
- `latex-translation-core`
  - generic text env recovery must include a final paragraph-wise rescue path before source preservation.
- `translation-orchestration`
  - runtime logging must include masked task-start LLM config.
  - validation retries must short-circuit when the retry loop stops making progress.
- `tiered-compilation`
  - CJK final PDF selection must prefer `xelatex` when it exists.
- `web-api`
  - the backend API must propagate the effective runtime parity config into the coordinator/task snapshot, including bounded task-level concurrency and safe-limit inputs.
