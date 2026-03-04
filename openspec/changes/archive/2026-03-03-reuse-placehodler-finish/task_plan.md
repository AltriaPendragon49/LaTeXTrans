# Task Plan: Phase1-3 + Env Hardening (Phase4 Deferred)

## Goal
Harden the LaTeX translation pipeline against structural corruption by combining:
- pre-LLM isolation,
- deterministic validation/repair,
- environment-specific safeguards for `eqnarray` and list environments,
while keeping LangGraph migration deferred.

## Completed Scope
- [x] Phase 1: inline math isolation + high-risk token preprocessing
- [x] Phase 2: C1/C2 classification + one-shot C1 retry budget
- [x] Phase 3: deterministic underscore repair + constrained math repair + local fallback granularity
- [x] Phase 3 extension:
- [x] eqnarray strict comment/row processing and row-level fallback
- [x] list item-anchor integrity enforcement
- [x] ITEM/EQROW immutable placeholder validation
- [x] env-level metadata and env fallback subtype counters
- [x] Round 3 JA deterministic hardening:
- [x] compiler target-language-priority language decision (`ja/zh/ko -> cjk`) with include-aware detection fallback
- [x] engine compatibility shims (`hwemoji` disable/fallback, pdfTeX primitive noops, CJK preamble swap)
- [x] compile diagnostics fields (`language_decision`, `engine_order_reason`, `compat_shims_applied`)
- [x] generator compile call forwarding `target_language`
- [x] regression unit tests for key immutability, pgfplots code-like suppression, and compiler shim/language behavior

## Deferred Scope
- [ ] Phase 4a/4b LangGraph orchestration and diagnostics nodes

## Validation Snapshot
- Round 1 (4e77 -> 7275): `final_errors 12 -> 0`, `fallback_count 12 -> 5`
- Round 2 (0b8f -> 2fa4): `fallback_count 29 -> 3`, `fallback_ratio 0.237705 -> 0.02459`
- Residual section-level fallbacks in latest run: `2, 3_1, 12`
- Round 3 (local targeted unit regression): `56 passed`
- command: `PYTHONPATH=. pytest -q backend/tests/unit/test_input_layer_defense.py backend/tests/unit/test_deterministic_repair.py backend/tests/unit/test_compiler_intelligent_fallback.py`
- Round 4 (5-task JA forensic checklist): completed root-cause classification and controls.
- Key outcomes:
- structural-path failure confirmed for `2504.10471` (chunk boundary + pre-refill mutation evidence; text-only/skip-structural experiment compiles).
- compile-compatibility root causes confirmed for `2504.07951` and `2503.08429` (reproducible in source-only compile).
- asset-level root cause confirmed for `2503.04565` (`imgs/HOTA.pdf` inclusion failure in failed run).
- Round 5 (latest JA rerun task set from `task_configs`, 2026-03-03):
- task statuses: `1 success + 3 compilation_failed + 1 structure_invalid_aborted`.
- `structure_invalid` short-circuit path is active in runtime (`2504.10471`: no `compilation_*` event).
- remaining failures are deterministic compile/resource paths, not new LLM-structure mutation patterns.
- observed observability issue: `replay_bundle_ref` path points to `outputs/...` while actual replay bundle is under `failed_tasks/...`.

## Notes
- The current hardening reduces untranslated fallback area significantly but does not resolve all translation-quality issues (for example mojibake artifacts).
- Compile warnings remain and are tracked separately from structural validation success.
- Current phase gate remains unchanged: deterministic hardening stays first; LangGraph remains deferred until deterministic compile/resource paths converge.

## V7 Hard Pins (New Mandatory Constraints)
- Safe input gate must be versioned and replayable:
- freeze `safe_limit_v1(model_context_tokens, prompt_reserve_tokens)`;
- persist `safe_limit_id`, `model_context_tokens`, `prompt_reserve_tokens`, `safe_input_limit` in replay bundle.
- Oversize downgrade path must be deterministic and isolated:
- for chunks with `translated=false` and `downgrade_reason=oversize_no_safe_boundary`, bypass translator and bypass all secondary processing chains (structural extraction, placeholder refill, terminology replacement, macro rewrite) and only enter final reconstruction merge.
- Deterministic observability and test gates:
- add deterministic test for safe limit calculation reproducibility under fixed config;
- add pipeline call-sequence tests to assert downgraded chunks do not invoke translator or secondary transforms.
