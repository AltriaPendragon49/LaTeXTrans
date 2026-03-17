## MODIFIED Requirements
### Requirement: LaTeX Parsing and Translation
The system SHALL parse LaTeX source files into an Abstract Syntax Tree (AST), translate extracted text content while preserving structure, and reconstruct valid LaTeX output. It MUST continue to prefer target-language recovery for generic text environments before preserving source text.

#### Scenario: Generic text env uses paragraph rescue before source preservation
- **WHEN** a generic text environment such as `abstract` still resolves to unchanged source-language body text after wrapper-safe translation, restoration retry, and plain-text body recovery
- **AND** the source wrapper remains structurally safe to preserve
- **THEN** the system MUST attempt one final paragraph-wise target-language rescue path for the environment body
- **AND** MUST keep the original `\begin{...}` / `\end{...}` wrapper unchanged
- **AND** MUST preserve source text only if the paragraph-wise rescue still returns source-like text or fails structural safety checks.
