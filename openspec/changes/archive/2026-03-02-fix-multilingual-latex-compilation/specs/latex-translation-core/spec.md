## RENAMED Requirements
- FROM: `### Requirement: Language-Specific Font and Package Injection`
- TO: `### Requirement: Unified Language-Specific Package Mapping`

## MODIFIED Requirements

### Requirement: Unified Language-Specific Package Mapping
The system SHALL configure LaTeX packages based on the target translation language following a strict architecture: **Language determines the package. Engines are dumb executors.**

#### Scenario: Japanese document compilation
- **WHEN** the target language is `ja`
- **THEN** the system MUST inject the `luatexja` package
- **AND** MUST NOT inject `xeCJK` or manual font configurations
- **AND** SHOULD apply `_fix_page_overflow_for_cjk` mitigations

#### Scenario: Korean document compilation
- **WHEN** the target language is `ko`
- **THEN** the system MUST inject the `kotex` package
- **AND** MUST NOT comment out pdfLaTeX font/encoding primitive commands (Zero-Touch for non-XeLaTeX packages)
- **AND** SHOULD apply `_fix_page_overflow_for_cjk` mitigations

#### Scenario: Chinese document compilation
- **WHEN** the target language is `zh` or `ch`
- **THEN** the system MUST inject `\usepackage[UTF8]{ctex}`
- **AND** MAY comment out pdfLaTeX commands for legacy `ctex` compatibility
- **AND** SHOULD apply `_fix_page_overflow_for_cjk` mitigations

#### Scenario: Latin-script/English document compilation
- **WHEN** the target language is `en`, `de`, `fr`, `es`, `it`, etc.
- **THEN** the system MUST NOT modify the document preamble's existing font, encoding, or pdfLaTeX primitive commands (Zero-Touch)
- **AND** MUST NOT call `_comment_out_pdflatex_commands`
