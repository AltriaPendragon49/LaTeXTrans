## MODIFIED Requirements

### Requirement: Language-Specific Font and Package Injection
The system SHALL dynamically configure LaTeX packages and fonts based on the selected target translation language to ensure accurate PDF rendering, 并在语言级注入完成后执行用户定义的排版配置注入。

#### Scenario: Korean document compilation
- **WHEN** the target language is `ko`
- **THEN** the system MUST inject the `kotex` package to ensure reliable font selection and page layout natively, rather than relying on `xeCJK` and specific missing fonts
- **AND** comments out pdfLaTeX-specific primitive commands
- **AND** subsequently applies `FormattingConfig` if provided

#### Scenario: Japanese document compilation
- **WHEN** the target language is `ja`
- **THEN** the system injects the `xeCJK` package and explicitly configures its fonts (`IPAexMincho` for Japanese) regardless of `xeCJK`'s prior presence in the document
- **AND** comments out pdfLaTeX-specific primitive commands
- **AND** subsequently applies `FormattingConfig` if provided
