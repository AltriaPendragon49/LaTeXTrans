# latex-translation-core Specification Deltas

## MODIFIED Requirements

### Requirement: LaTeX Parsing and Translation
The standalone open-source CLI SHALL inherit the current backend translation-core behavior instead of reverting to the legacy prototype implementation.

#### Scenario: Standalone CLI uses current extracted core
- **WHEN** a user runs the standalone `NiuTrans/LaTeXTrans` CLI
- **THEN** the system MUST execute the extracted current translation core
- **AND** MUST preserve the current structure protection, fallback routing, repair orchestration, replay bundle generation, and compilation fallback behavior
- **AND** MUST NOT fall back to the obsolete prototype-only translation pipeline.
