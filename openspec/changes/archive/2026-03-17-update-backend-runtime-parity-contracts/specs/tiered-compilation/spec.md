## ADDED Requirements
### Requirement: CJK Final PDF Selection Preference
The compiler SHALL prefer `xelatex` as the final artifact source for CJK outputs whenever `xelatex` successfully produces a PDF.

#### Scenario: CJK document has both XeLaTeX and LuaLaTeX PDFs
- **WHEN** a CJK task reaches final PDF selection
- **AND** both `xelatex` and `lualatex` produced candidate PDFs
- **THEN** the final selected PDF MUST prefer the `xelatex` artifact
- **AND** `lualatex` MAY remain as a fallback candidate only when `xelatex` failed to produce a PDF.
