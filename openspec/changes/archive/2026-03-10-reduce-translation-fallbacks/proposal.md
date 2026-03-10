# OpenSpec Proposal: Reduce Translation Fallbacks

## Problem
The diagnostic report `fallback_analysis_report.md` revealed that while silent fallbacks are now detectable, many sections still revert to source text due to recoverable LLM errors such as "Total Erasure" (returning empty content for complex segments) and "Math Delimiter Mismatch" (losing `$` during translation).

## Proposed Solution
Enhance the `TranslationRepairAgent` to be more specialized and context-aware. Instead of a generic repair prompt, it will use the `validation_evidence` to pinpoint errors and apply targeted repair strategies. **Contextual repair focuses on structural correctness, not semantic improvement.**

### This change MUST NOT:
- Increase repair retry limits.
- Increase edit budgets.
- Bypass ultimate downgrade.
- Introduce new macros or environments.

## Implementation Details
1. **Contextual Repair**: Pass the specific error type (e.g., `bracket_mismatch`, `math_missing`) to the repair LLM. **Phase 2 contextual repair is strictly single‑attempt. No additional LLM retries are permitted regardless of error type.**
2. **Total Erasure Recovery**: If the previous translation was empty, the prompt will instruct the model to perform a structural recovery translation. **CRITICAL:** This recovery is ONLY allowed if the source `token_count <= MAX_ERASURE_RECOVERY_TOKENS` (e.g., 256). Otherwise, it must directly trigger a downgrade. This distinguishes between a repairable LLM glitch and an unrepairable overly complex structure.
3. **Math Guarding**: Explicitly instruct the model to balance explicit, countable math delimiters (e.g., `$`, `\(`, `\)`) based on the source text count. It MUST NOT attempt to repair complex math environments (`align`, `cases`, etc.).
4. **Anchor Preservation**: Ensure itemize/enumerate placeholders are strictly preserved.
5. **Verifiable Failure**: All enhancements must fail verifiably. Math delimiter repair must pass explicit count checks, anchor preservation must pass the placeholder guard. Any failure translates to no retry, direct ultimate downgrade. The repair agent is an "attempt to repair", not a loop of "trial and error".
6. **Direct C2 Structural Downgrade**: If the upstream validation identifies a total environment structural collapse (`c2_structural_collapse`), do not execute LLM repair, as LLM explanations will contaminate the raw structural code resulting in broken nested LaTeX blocks (e.g. `geminils`). Enforce an immediate `ultimate_downgrade` (`c2-direct-downgrade`).
7. **Rejection Telemetry**: Log distinct reasons for triggering the `ultimate_downgrade` (e.g., `math-guard`, `token-gate`, `budget-guard`) via downstream reporting to enable analytical visibility into the repair agent's rejection rates.
