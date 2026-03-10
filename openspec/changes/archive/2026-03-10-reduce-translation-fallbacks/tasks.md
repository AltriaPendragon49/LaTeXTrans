# Tasks: Reduce Translation Fallbacks

## Phase 1: Context-Aware Repair Enhancements
- [x] Add `validation_evidence` handling to `TranslationRepairAgent._build_repair_prompt`.
- [x] Implement token count gating for Total Erasure Recovery (Category 3A). If estimated `source_tokens > MAX_ERASURE_RECOVERY_TOKENS`, bypass repair and trigger ultimate downgrade directly.
- [x] Implement erasure recovery prompt (only invoked if token gating passes).
- [x] Add explicit math delimiter (`$`, `\(`, `\)`) balancing commands to the prompt.
- [x] Add anchor/placeholder preservation instructions to the prompt.

## Phase 2: Verifiable Failure Enforcement
- [x] Enhance validation logic inside `TranslationRepairAgent._repair_one` to count explicit math delimiters (`$`, `\(`, `\)`) matching the source text.
- [x] Tie the existing `_placeholder_guard` to the verifiable failure workflow.
- [x] Ensure any validation failure (math count mismatch, placeholder mismatch, budget breach) blocks retry and forces an immediate ultimate downgrade.

## Phase 3: Validation & Reporting
- [x] Run end-to-end translation on known failing sections (e.g., `2501.17151`, `2503.21934`).
- [x] Regenerate `fallback_analysis_report.md` using `scripts/analyze_fallback_results.py`.
- [x] Update `analyze_fallback_results.py` to differentiate downgrade reasons (e.g. `downgrade_due_to_unrepairable_structure` vs `downgrade_due_to_budget_exhaustion`).
- [x] Verify reduction in "Ultimate Downgrade" events without an increase in infinite loops or broken structures.

## Phase 4: Follow-up Adjustments (C2 structural mitigation & Telemetry)
- [x] Modify `TranslationRepairAgent.repair()` to immediately skip `c2_structural_collapse` environments and enforce a direct `ultimate_downgrade`.
- [x] Enhance `_repair_one` to return explicit rejection reasons (e.g., `token-gate`, `placeholder-guard`, `math-guard`, `budget-guard`) for telemetry.
- [x] Pass rejection tags down through target mapping dictionaries and update log analytics script `analyze_fallback_results.py` to display these tags.

