## MODIFIED Requirements
### Requirement: LaTeX Parsing and Translation
The system SHALL parse LaTeX source files into an Abstract Syntax Tree (AST), translate extracted text content while preserving structure, and reconstruct valid LaTeX output. It MUST continue to prefer target-language recovery for generic text environments before preserving source text. It MUST also prefer the strongest structurally safe target-language downgrade for section-level hard-freeze failures instead of preserving full source-English sections whenever rescue produced materially translated content. A structured downgrade outcome MUST contain materially translated target-language prose; source-English text or fixed placeholder-style fallback boilerplate MUST NOT be recorded as successful target-language downgrade output.

#### Scenario: Generic text env uses paragraph rescue before source preservation
- **WHEN** a generic text environment such as `abstract` still resolves to unchanged source-language body text after wrapper-safe translation, restoration retry, and plain-text body recovery
- **AND** the source wrapper remains structurally safe to preserve
- **THEN** the system MUST attempt one final paragraph-wise target-language rescue path for the environment body
- **AND** MUST keep the original `\begin{...}` / `\end{...}` wrapper unchanged
- **AND** MUST preserve source text only if the paragraph-wise rescue still returns source-like text or fails structural safety checks.

#### Scenario: Section payload-invariant failure prefers target-language downgrade
- **WHEN** a section-level structural-risk translation attempt fails with a hard-freeze protocol violation
- **AND** a paragraph-wise, fragment-wise, or equivalent target-language rescue path yields materially translated content that preserves existing structural safety guarantees
- **THEN** the system MUST persist that rescued target-language content
- **AND** MUST NOT mark the whole section as source-English passthrough.

#### Scenario: Section source fallback remains last resort
- **WHEN** a section-level hard-freeze failure occurs
- **AND** all approved target-language rescue paths still return source-like text, structurally unsafe text, empty output, or only fixed fallback boilerplate
- **THEN** the system MAY preserve the original source section as a final fallback
- **AND** it MUST record that outcome as an explicit last-resort fallback state for auditability.

#### Scenario: Structured downgrade rejects source-English text
- **WHEN** deterministic structured downgrade is evaluated for a section or environment candidate
- **AND** the candidate text still consists of source-English prose rather than materially translated target-language content
- **THEN** the system MUST NOT record structured downgrade as successful for that unit
- **AND** it MUST continue through explicit fallback or terminal handling instead.

#### Scenario: Structured downgrade rejects fixed fallback boilerplate
- **WHEN** deterministic structured downgrade is evaluated for a candidate whose natural-language body is only repeated fixed fallback boilerplate such as a generic placeholder-style Chinese sentence
- **THEN** the system MUST NOT treat that text as valid target-language downgrade content
- **AND** it MUST keep explicit fallback metadata instead of reporting downgrade success.
