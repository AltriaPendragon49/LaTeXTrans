## Context
The translation pipeline repeatedly failed on structurally sensitive LaTeX content. Early hardening (Phase1-3) reduced generic Type C failures, but structurally dense environments (`eqnarray`, `enumerate`, `itemize`) still triggered fallback-heavy behavior. The unsaved round extends the deterministic safety model from section-level logic into environment-level handling.

## Goals / Non-Goals
- Goals:
- Remove LLM responsibility for environment structure integrity.
- Add deterministic env-specific guards for math/list environments.
- Persist richer env-level observability for regression analysis.
- Keep final validation errors at zero while reducing fallback blast radius.
- **Non-Goals**:
- No broad semantic translation quality rewrite.
- No broad semantic translation quality rewrite.
- No aggressive compile-warning elimination in this round.

## Decisions
- Decision: Eqnarray row-safe deterministic processing.
- Why: Eqnarray combines math delimiters, alignment tokens, and occasional natural-language rows. Whole-block LLM translation is fragile.
- Implementation:
- mask `%` comments with `<EQCOMMENT_n>`;
- split/rebuild rows with exact `\\` separators;
- classify rows (`math` vs `text`) and translate text rows only;
- preserve math rows as-is;
- enforce immutable sequence checks.

- Decision: List item anchoring with immutable placeholders.
- Why: Reordered/dropped `\item` markers are frequent structural regressions.
- Implementation:
- replace item commands with `<ITEM_n>` anchors before env translation;
- validate exact count/order;
- restore original item command strings after successful translation.

- Decision: Environment-level fallback subtype and row-level counters.
- Why: Section-level fallback counts hide where regressions happen.
- Implementation:
- persist `translation_status`, `fallback_subtype`, `row_fallback_count` in `envs_map.json`;
- subtype taxonomy: `math_env_fallback`, `list_env_fallback`, `other_env_fallback`, `none`.

- Decision: Validator immutable placeholder and list-structure checks.
- Why: Existing math checks do not cover list/item and row-anchor corruption.
- Implementation:
- add `ITEM/EQROW` span extraction and immutable-sequence validation;
- add list structure validation (`\item` count/order/boundary);
- classify errors: list/item mismatches -> `C1`, eqrow mismatch -> `C2`.

- Decision: Validation summary env subtype counters in coordinator.
- Why: We need run-level trend metrics for env fallback composition.
- Implementation:
- add `fallback_count_env_math/list/other` to `validation_completed`.

## Non-Negotiable Invariants
- Placeholders are immutable.
- Deterministic repair/validation always precedes compile-first fallback.
- Fallback remains the last resort.
- Environment-boundary and item-order integrity cannot be relaxed for translation gain.

## Implementation Status Snapshot (2026-03-03)

### Implemented
- `backend/app/services/latex/utils.py`
- eqnarray comment masking/restoration;
- strict row split/rebuild and row classification;
- list item anchor helpers;
- immutable placeholder sequence validator;
- skip-tag extension to `ITEM/EQROW/EQCOMMENT`.
- `backend/app/services/agents/translator_agent.py`
- env-specialized translation paths for eqnarray/list;
- row-level fallback path for eqnarray text rows;
- env metadata persistence (`translation_status`, `fallback_subtype`, `row_fallback_count`);
- underscore escaping skip-span extension to `ITEM/EQROW`.
- `backend/app/services/agents/validator_agent.py`
- immutable placeholder checks (`ITEM/EQROW`);
- list structure checks for enumerate/itemize;
- C1/C2 classification updates for new structural errors.
- `backend/app/services/agents/coordinator_agent.py`
- env fallback subtype counters in `validation_completed`.

### Deferred
- None. (Phase 4 LangGraph evolution split to a separate change).

## Verification Evidence

### Round 1 (already recorded)
- Baseline: `backend/data/outputs/4e77eb07-581f-4d38-881d-81012f202431/zh_2602.23750`
- Rerun: `backend/data/outputs/7275536f-bc97-4d99-befa-4024bf09303b/zh_2602.23750`
- `final errors: 12 -> 0`, `fallback_count: 12 -> 5`.

### Round 2 (unsaved env hardening)
- Baseline: `backend/data/failed_tasks/0b8f59ea-ce29-4177-936f-5197138029f5/zh_2602.23750`
- Rerun: `backend/data/outputs/2fa4ad88-5343-4bf2-94f6-b7ce834ccc3f/zh_2602.23750`
- `fallback_count: 29 -> 3`
- `fallback_ratio: 0.237705 -> 0.02459`
- `fallback_parts` env entries: `26 -> 0`
- `final_errors_count` remains `0`.

### Tests
- Local regression set passed, including `test_immutable_placeholder_integrity.py`.

## Known Residual Risks
- Some section-level compile-first fallbacks still remain (`2`, `3_1`, `12` in latest output).
- Translation text contains encoding/mojibake artifacts in parts of Chinese output.
- Compilation still reports warnings/errors under `lualatex` in output artifacts.
