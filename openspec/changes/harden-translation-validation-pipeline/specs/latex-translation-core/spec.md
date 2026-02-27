## ADDED Requirements

### Requirement: Math-Mode Delimiter Consistency Validation

The system SHALL validate that translated content preserves the same number and structural pattern of math-mode delimiters (`$...$` and `$$...$$`) as the original content.

#### Scenario: Detecting missing math delimiters
- **WHEN** `ValidatorAgent` compares original and translated content of a section, environment, or caption
- **AND** the translation has fewer `$` delimiters than the original
- **THEN** the system SHALL flag a Type C (structural) error with detail `math_delimiter_mismatch`
- **AND** invoke `_repair_math_delimiters()` to copy delimiter patterns from original to translation

#### Scenario: Repairing bare math tokens in text mode
- **WHEN** the translated content contains bare math tokens (`_`, `^`, `\frac`, `\sum`, `\int`, etc.) outside any `$...$` context
- **AND** the original content has those same tokens enclosed in `$...$`
- **THEN** the system SHALL wrap the bare tokens in `$...$` by copying the delimiter boundaries from the original

#### Scenario: Protecting display math environments
- **WHEN** the translated content contains bare math tokens
- **AND** those tokens already reside inside a display math environment (e.g. `\[...\]`, `\(...\)`, `\begin{equation}...\end{equation}`)
- **THEN** the system SHALL NOT wrap the tokens in `$...$` preventing invalid nested math modes

#### Scenario: No false positives on already-valid translations
- **WHEN** translated content has the same `$` count and pattern as the original
- **THEN** no math-delimiter error SHALL be reported

### Requirement: Non-Translatable Environment Exclusion

The system SHALL preserve designated structural environments verbatim without sending their contents to the LLM for translation.

#### Scenario: CCSXML environment exclusion
- **WHEN** the parser encounters a `\begin{CCSXML}...\end{CCSXML}` block
- **THEN** the entire block SHALL be preserved verbatim in the translated output
- **AND** its contents SHALL NOT be sent to the LLM

#### Scenario: Verbatim and code environments exclusion
- **WHEN** the parser encounters `verbatim`, `lstlisting`, `minted`, `filecontents`, `filecontents*`, or `comment` environments
- **THEN** the entire block SHALL be preserved verbatim
- **AND** its contents SHALL NOT be sent to the LLM

#### Scenario: Selective nested placeholder translation
- **WHEN** an environment contains `PLACEHOLDER_CAP` or `PLACEHOLDER_ENV` tags
- **AND** the environment is one of: `frontmatter`, `abstract`, `title`, `author`, `keywords`
- **THEN** the system SHALL proceed with translation of the container content
- **AND** standard placeholder protection SHALL be applied to nested tags.

### Requirement: Resilient Protected Command Placeholder Restoration

The system SHALL restore PROTECTED_CMD placeholders after LLM translation, tolerating common LLM mutations to the placeholder format.

#### Scenario: Exact placeholder restoration
- **WHEN** `unmask_sensitive_commands` processes translated content containing `<PROTECTED_CMD_0>`
- **THEN** the placeholder SHALL be replaced with the original command from the mapping

#### Scenario: LLM-mutated placeholder restoration
- **WHEN** the LLM modifies the placeholder format to `\protect\PROTECTED_CMD_0`, `\\PROTECTED_CMD_0`, `{\PROTECTED_CMD_0}`, or adds whitespace
- **THEN** `unmask_sensitive_commands` SHALL still recognize and restore the placeholder

#### Scenario: Residual placeholder detection
- **WHEN** after unmask restoration, any `PROTECTED_CMD` text remains in the output
- **THEN** the system SHALL attempt force-restoration by positional order from the mapping
- **AND** log a warning for traceability

#### Scenario: Validator residual check
- **WHEN** `ValidatorAgent` validates a translated part
- **THEN** it SHALL additionally check for any remaining `PROTECTED_CMD` text in the translation
- **AND** flag it as a Type C structural error if found

### Requirement: CTeX Package Conflict Auto-Resolution

The system SHALL detect and resolve command name conflicts between the injected `ctex` package and author-defined commands before compilation.

#### Scenario: Detecting \I command conflict
- **WHEN** the original preamble contains `\newcommand{\I}` or `\renewcommand{\I}` or `\def\I`
- **AND** the system injects `\usepackage{ctex}` for Chinese translation
- **THEN** the system SHALL inject `\let\I\relax` before the ctex import to prevent "Command already defined" errors

#### Scenario: No conflict present
- **WHEN** the original preamble does not define any commands that conflict with ctex
- **THEN** no conflict-resolution injection SHALL occur

### Requirement: Package-Aware Engine Selection

The system SHALL optimize compilation engine selection based on detected package compatibility constraints.

#### Scenario: Skipping lualatex for xypdf documents
- **WHEN** the document preamble includes the `xypdf` package (via `\usepackage{xypdf}` or `xy` package with `pdf` option)
- **THEN** the system SHALL skip `lualatex` from the engine fallback order
- **AND** log the reason for the engine skip

### Requirement: Engine-Specific Compilation Logging

The system SHALL preserve compilation logs for each attempted engine run without overwriting previous attempts to maintain a full diagnostic audit trail.

#### Scenario: Storing lualatex log before fallback
- **WHEN** `lualatex` compilation fails
- **THEN** the system SHALL rename `main.log` to `main.lualatex.log` (or equivalent) before attempting fallback engines.

### Requirement: CJK-Aware Engine Prioritization and Exclusion

The system SHALL prioritize CJK-compatible engines (`lualatex`, `xelatex`) for CJK documents and exclude `pdflatex` results from high-quality selection if superior alternatives exist.

#### Scenario: CJK-aware engine prioritization and exclusion
- **WHEN** `target_language` is "ja", "zh", or "ko"
- **THEN** it SHALL prioritize `lualatex` or `xelatex` and use `pdflatex` only as the final fallback
- **AND** if a PDF was generated by modern engines, the `pdflatex` result SHALL be EXCLUDED from selection.

#### Scenario: Latin-script engine priority maintenance
- **WHEN** `target_language` is a Latin-script language (en, de, fr, es, it, pl, nl)
- **THEN** the system SHALL maintain the standard multi-engine priority loop
- **AND** `pdflatex` SHALL remain a primary candidate for compilation.

### Requirement: Intelligent Placeholder Recovery

The system SHALL intelligently recover `\input` and environment placeholder tags to prevent reconstruction exceptions from mismatched tag stacks.

#### Scenario: Healing misspelled tags sequentially
- **WHEN** `_fix_missing_placeholders` evaluates that the translation outputted the exact same number of placeholder tags as the source
- **AND** some tag strings mismatch (e.g. typographical error)
- **THEN** the system SHALL apply sequential replacement pairing the original and translated placeholders by order of appearance.

#### Scenario: Paired anchor restoring
- **WHEN** a `_begin` tag is missing but its corresponding `_end` tag is present
- **THEN** the system SHALL safely insert the missing `_begin` tag immediately prior to the `_end` tag
- **AND** vice versa for a missing `_end` tag relative to its `_begin` anchor.

### Requirement: Precise Preamble Definition Extraction

The system SHALL correctly extract and preserve `\newenvironment` definitions including both begin and end code blocks without truncation.

#### Scenario: Extracting two-block environments
- **WHEN** the parser extracts a `\newenvironment{name}{begin-code}{end-code}` definition
- **THEN** it SHALL capture the entire definition into the `<PLACEHOLDER_NEWCOMMAND_N>`
- **AND** the end-code block SHALL NOT be left behind as stray text

### Requirement: Severe Translation Corruption Detection

The system SHALL detect severe structural corruption in inline mathematical contexts, even if delimiter counts match.

#### Scenario: Catching malformed inline math combinations
- **WHEN** translated inline math contains unbalanced structural braces (`\{`, `\}`) or untranslated trailing English fragments
- **THEN** the system SHALL flag this as a Type C (structural) error despite matching `$` counts.

## MODIFIED Requirements

### Requirement: Validation Error Classification

The system SHALL classify validation errors into three categories with distinct handling strategies.

#### Scenario: A-type error detection (configuration/resource)
- **WHEN** `ValidatorAgent` encounters an error containing "not found", "missing", or "configuration"
- **THEN** the error report includes `error_type: "A"`
- **AND** the error triggers graceful degradation (e.g., load empty terminology table)

#### Scenario: B-type error detection (fixable syntax)
- **WHEN** `ValidatorAgent` encounters LaTeX syntax errors (unescaped special chars, misspelled commands)
- **AND** error does not match A-type or C-type patterns
- **THEN** the error report includes `error_type: "B"`
- **AND** the error is eligible for translation retry (max 1)

#### Scenario: C-type error detection (structural mismatch)
- **WHEN** `ValidatorAgent` encounters command_error containing pattern `expected \d+, found \d+`
- **OR** `ValidatorAgent` encounters a `math_delimiter_mismatch` error
- **OR** `ValidatorAgent` encounters residual `PROTECTED_CMD` text
- **THEN** the error report includes `error_type: "C"`
- **AND** the error is marked for algorithmic repair (not LLM retry)
