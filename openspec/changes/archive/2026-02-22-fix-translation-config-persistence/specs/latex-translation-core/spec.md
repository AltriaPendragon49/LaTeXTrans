# latex-translation-core

## MODIFIED Requirements
### Requirement: LaTeX Compilation with Intelligent Fallback

The system SHALL compile translated LaTeX files into PDF using a multi-stage compilation strategy with **intelligent language detection**, **three-engine fallback**, and error-based output selection.

#### Scenario: Language-aware engine prioritization
- **WHEN** `compile_with_intelligent_fallback()` is called without explicit engine order
- **THEN** the system detects document language by scanning for CJK characters and Cyrillic characters
- **AND** if CJK character count > 100, uses order: `XeLaTeX → LuaLaTeX → PDFLaTeX`
- **AND** if Cyrillic character count > 50, uses order: `XeLaTeX → LuaLaTeX → PDFLaTeX`
- **AND** if neither exceeds their threshold, uses order: `PDFLaTeX → XeLaTeX → LuaLaTeX`

## ADDED Requirements
### Requirement: Language-Specific Font and Package Injection
The system SHALL dynamically configure LaTeX packages and fonts based on the selected target translation language to ensure accurate PDF rendering.

#### Scenario: Chinese document compilation
- **WHEN** the target language is `zh` or `ch`
- **THEN** the system injects the `ctex` package with UTF-8 encoding
- **AND** comments out pdfLaTeX-specific primitive commands

#### Scenario: Japanese or Korean document compilation
- **WHEN** the target language is `ja` or `ko`
- **THEN** the system injects the `xeCJK` package and explicitly configures its fonts (`UnBatang` for Korean, `IPAexMincho` for Japanese) regardless of `xeCJK`'s prior presence in the document
- **AND** comments out pdfLaTeX-specific primitive commands

#### Scenario: Cyrillic document compilation
- **WHEN** the target language uses Cyrillic script (`ru`, `uk`, `bg`, `sr`, `mk`, `be`)
- **THEN** the system injects `fontspec` and configures it to use the `CMU Serif` font
- **AND** comments out conflicting pdfLaTeX-specific encoding packages (e.g., `fontenc[T1]`, `inputenc[utf8]`, `times`) and primitive commands

#### Scenario: Latin-extended document compilation
- **WHEN** the target language uses extended Latin script (`de`, `fr`, `es`, etc.)
- **THEN** the system preserves native pdfLaTeX encoding packages (`fontenc`, `inputenc`)
- **AND** exclusively comments out pdfLaTeX-specific primitive commands to safely allow `XeLaTeX` fallback compilation
