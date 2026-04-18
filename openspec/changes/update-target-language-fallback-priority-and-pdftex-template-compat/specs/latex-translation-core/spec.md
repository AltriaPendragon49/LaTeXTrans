## MODIFIED Requirements
### Requirement: LaTeX Parsing and Translation
The system SHALL parse LaTeX source files into an Abstract Syntax Tree (AST), translate extracted text content while preserving structure, and reconstruct valid LaTeX output. It MUST continue to prefer target-language recovery for generic text environments before preserving source text. It MUST also prefer the strongest structurally safe target-language downgrade for section-level hard-freeze failures instead of preserving full source-English sections whenever rescue produced materially translated content.

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
- **AND** all approved target-language rescue paths still return source-like text, structurally unsafe text, or empty output
- **THEN** the system MAY preserve the original source section as a final fallback
- **AND** it MUST record that outcome as an explicit last-resort fallback state for auditability.

#### Scenario: Extra sectioning commands in translated prose are demoted instead of persisted
- **WHEN** a source section chunk starts with a sectioning block such as `\section{...}` / `\subsection{...}`
- **AND** the remaining source body contains no sectioning commands
- **AND** the translated candidate preserves the expected leading section hierarchy but introduces extra sectioning commands inside prose body text
- **THEN** the system MUST demote those extra sectioning commands back to plain target-language text before persisting the translated section
- **AND** it MUST keep the translated section content instead of reverting the whole chunk to source solely because of that body-level drift.

### Requirement: CJK Font Compatibility Fix
The system MUST dynamically neutralize incompatible pdfLaTeX-specific font packages and explicit pdfTeX driver locks to ensure correct XeLaTeX/LuaLaTeX rendering of CJK characters.

#### Scenario: Neutralizing conflicting font macro-packages
- **WHEN** the document class or local style files load `fontenc[T1]`, `newtxtext`, or `txfonts`
- **THEN** the system MUST comment out these commands in the main file and all local `.cls`/`.sty` files prior to compilation.

#### Scenario: Neutralizing explicit pdfTeX graphics driver locks for CJK compilation
- **WHEN** the target language is a CJK language such as `zh`
- **AND** the source template explicitly locks a package driver to pdfTeX semantics such as `\usepackage[pdftex]{graphicx}`
- **THEN** the compile sanitization path MUST remove or neutralize that explicit pdfTeX driver lock before XeLaTeX/LuaLaTeX compilation
- **AND** it MUST preserve the underlying package import semantics needed by the paper.
