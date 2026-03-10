# ControlledRepairWorkflow Specification Deltas

## MODIFIED Requirements

### Requirement: Extremely Strict Controlled LLM Repair Prompting
Controlled LLM repair (Phase 2) execution MUST be attempted at most once per unsafe env. The system MUST employ an extremely strict Prompt that explicitly forbids any form of translation or semantic rewriting, except under specific context-aware recovery conditions. The prompt MUST incorporate `validation_evidence` to target specific repairs (e.g., math balancing, placeholder preservation).

#### Scenario: Prompt constraints for structure repair
- **WHEN** an env triggers its Phase 2 repair execution
- **THEN** the LLM is prompted to fix structure exclusively using detailed `validation_evidence`
- **AND** the Prompt MUST explicitly prohibit translating the text or altering its semantics (unless handling total erasure)
- **AND** if the output still fails verifiable structure checks (e.g., math count mismatch, placeholder mismatch)
- **THEN** the system MUST move to Phase 3 rather than retrying the LLM

## ADDED Requirements

### Requirement: Token-Gated Total Erasure Recovery
When `translated_text` is empty (Total Erasure), Phase 2 MAY instruct the LLM to perform a structural recovery translation ONLY IF the estimated source token count is within a strictly safe threshold (`source_tokens <= MAX_ERASURE_RECOVERY_TOKENS`). If the token delta exceeds this hard safety threshold, erasure recovery MUST be bypassed and the system MUST trigger Phase 3 immediately.

#### Scenario: Safely handling empty translations
- **WHEN** an env triggers Phase 2 repair with an empty `translated_text`
- **THEN** the system computes the estimated token count of the source text (`estimated_tokens = ceil(len(utf8_bytes)/3)`)
- **AND** if the `estimated_tokens <= MAX_ERASURE_RECOVERY_TOKENS`, recovery translation is attempted
- **AND** if the `estimated_tokens > MAX_ERASURE_RECOVERY_TOKENS`, the system skips repair and moves straight to Phase 3 downgrade

### Requirement: Verifiable Failure Enforcement
All Phase 2 repair attempts MUST be subjected to strict verifiable checks against the source text. These include matching the exact number of explicit mathematical delimiters (e.g., `$`, `\(`, `\)`) and absolute placeholder preservation. The repair MUST NOT attempt to balance or repair complex environments like `align` or `cases`. Any failure to pass these automated checks MUST result in immediate Phase 3 downgrade without further retries.

#### Scenario: Deterministic repair verification
- **WHEN** the LLM returns a repaired text in Phase 2
- **THEN** the system counts explicit math delimiters (`$`, `\(`, `\)`) and compares them to the source
- **AND** the system verifies all `PLACEHOLDER_*` strings match the source exactly
- **AND** if any count or match fails
- **THEN** the system immediately delegates the env to Phase 3 (deterministic downgrade)
