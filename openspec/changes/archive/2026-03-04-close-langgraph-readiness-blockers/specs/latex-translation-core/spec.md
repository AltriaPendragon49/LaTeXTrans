## REMOVED Requirements
### Requirement: Math-Mode Delimiter Consistency Validation
**Reason**: The previous requirement mandated speculative delimiter injection repair (`repair_math_delimiters`), which violates LangGraph admission invariants.
**Migration**: Preserve mismatch detection/classification, then route through existing C1/C2 retry/fallback flow without structural token injection.

### Requirement: Intelligent Placeholder Recovery
**Reason**: The previous requirement mandated speculative placeholder completion/insertion (`_fix_missing_placeholders`), which violates LangGraph admission invariants.
**Migration**: Preserve placeholder mismatch detection/classification and route to retry/fallback without guessed structure insertion.

## ADDED Requirements
### Requirement: Typed Invariant Violations for Forbidden Repair Paths
Speculative repair entrypoints that remain for compatibility MUST be sealed by typed invariant exceptions.

#### Scenario: Forbidden repair function is called
1. Given runtime reaches a sealed speculative repair function
2. When the function is invoked
3. Then it MUST raise a typed invariant exception
4. And the exception MUST include a stable error code for observability/replay.
