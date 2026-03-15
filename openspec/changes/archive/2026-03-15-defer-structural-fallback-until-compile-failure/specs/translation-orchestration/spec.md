## MODIFIED Requirements
### Requirement: Deterministic LaTeX Structural Repair
The repair strategy MUST rely on deterministic rules rather than context-dependent guessing across translated text, and structural fallback candidates MUST preserve target-language content until compilation proves they are unsafe.

#### Scenario: Limited fallback granularity after compile failure
- **WHEN** an uncorrectable structural failure mandates fallback handling
- **THEN** the system MUST limit this handling to the specific isolated chunk or environment containing the error
- **AND** MUST NOT blanketly revert an entire section or document unless the structure guard already rejected the bundle globally.

### Requirement: C1/C2 Routing Without Speculative Injection
C1/C2 orchestration MUST retain existing retry and deterministic repair semantics while prohibiting speculative structure-token injection and validate-stage source rollback.

#### Scenario: C2 structural error is recorded but translation is preserved
- **WHEN** the validator classifies a section or environment as `C2`
- **THEN** the system MUST record that unit as a post-compile fallback candidate
- **AND** MUST NOT overwrite `trans_content` with source text during validation
- **AND** the first compilation attempt MUST use the preserved target-language text.

#### Scenario: Compile succeeds despite recorded structural risk
- **WHEN** a section or environment is recorded as a structural fallback candidate
- **AND** the first compilation attempt succeeds
- **THEN** the system MUST retain the target-language translation
- **AND** MUST NOT execute deterministic target-language downgrade for that unit.
