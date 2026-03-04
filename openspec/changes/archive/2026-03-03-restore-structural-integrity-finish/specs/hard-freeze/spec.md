# Spec: latex-translation-core

## ADDED Requirements

### Requirement: Pre-translation Placeholder Injection
The parser MUST physically replace all mathematical modes (`$...$`, `\(...\)`, `\[...\]`), complex environments (`figure`, `table`, `tabular`, `tikzpicture`, `equation`, `align`), and structural commands (`\label{}`, `\ref{}`, `\cite{}`) with immutable placeholder tokens (e.g., `[PH_MATH_001]`) before passing text to the LLM.占位符映射必须是 chunk-local + document-global 可追踪

#### Scenario: Translating an isolated equation
1. Given the input `Here is an equation: $x = y + 1$.`
2. When the parser processes the block
3. Then the text sent to the LLM MUST be `Here is an equation: [PH_MATH_001].`
4. And the parser MUST perfectly restore the original math upon receiving the LLM output.

### Requirement: Strict Validation (Fail-Fast)
The validator MUST reject any LLM output where the set of placeholders does not identically match (in quantity, order, and type) the input placeholders.

#### Scenario: LLM hallucinates or drops a placeholder
1. Given the LLM output `这有一个方程：[PH_MATH_002].` (mismatched ID) or `这有一个方程。` (missing)
2. When the validator checks the chunk against the input state
3. Then it MUST immediately mark the translation attempt as failed and trigger a fast failure metric without attempting to "repair" the structure via regex.
