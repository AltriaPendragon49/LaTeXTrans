# Spec Delta: recover-mangled-placeholders

## MODIFIED Requirements

### Requirement: Placeholder Integrity and Recovery

The translation pipeline MUST aggressively protect and recover all injected placeholders (e.g., `<PLACEHOLDER_ENV_{ID}>`) to ensure zero leakage of placeholder tags into the final compiled PDF and zero misfires of translation reassembly logic.

#### Scenario: LLM escapes placeholders natively
- **Given** an LLM translates a segment and outputs `<$PLACEHOLDER_ENV_10$>` or `\textless PLACEHOLDER\_CAP\_1\textgreater` instead of the exact expected tag.
- **When** the coordinator processes the translated text prior to checking for missing placeholders (`_fix_missing_placeholders`) and prior to the environment/caption substitution step (`reconstruct.py`).
- **Then** the `restore_mangled_placeholders` utility MUST execute a fuzzy regex scan against the list of known original placeholders for that segment.
- **And** it MUST perfectly restore the escaped/wrapped text back into the standard exact string (e.g. `<PLACEHOLDER_ENV_10>`) to proceed normally.

#### Scenario: Proper tags remain untouched
- **Given** an LLM correctly preserves the exact tag `<PLACEHOLDER_ENV_10>`.
- **When** the translated text is processed by `restore_mangled_placeholders`.
- **Then** the text MUST remain completely untouched and valid, preventing any double-formatting or greedy-regex collateral damage.
