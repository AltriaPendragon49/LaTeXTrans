## ADDED Requirements

### Requirement: Biblatex Backend Support
The system MUST correctly compile bibliographies for LaTeX documents that utilize the `biblatex` package, even when original `.bib` files are missing.

#### Scenario: Compiling with biblatex dependency and missing .bib
- **WHEN** a user translates an arXiv project using `biblatex` with incompatible `.bbl` files
- **THEN** the system MUST implement a Python-based fallback to extract `author`, `title`, and `year`
- **AND** automatically replace `\printbibliography` with a native `thebibliography` block.

### Requirement: CJK Font Compatibility Fix
The system MUST dynamically neutralize incompatible pdfLaTeX-specific font packages to ensure correct XeLaTeX rendering of CJK characters.

#### Scenario: Neutralizing conflicting font macro-packages
- **WHEN** the document class or local style files load `fontenc[T1]`, `newtxtext`, or `txfonts`
- **THEN** the system MUST comment out these commands in the main file and all local `.cls`/`.sty` files prior to compilation.

### Requirement: Intra-Section Translation Parallelization
The TranslatorAgent SHALL translate child environments and captions within each section concurrently using `asyncio.gather()`.

#### Scenario: Concurrent environment and caption translation
- **WHEN** a section contains multiple environments or captions
- **THEN** the system SHALL execute `_translate_env` and `_translate_caption` calls in parallel phases
- **AND** total processing time SHALL be optimized without missing captions discovered inside environments.

### Requirement: Global API Rate Limiting
The system SHALL implement a globally shared concurrency limit for all outbound LLM API requests.

#### Scenario: Enforcing global LLM concurrency
- **WHEN** multiple tasks or sub-tasks trigger LLM requests
- **THEN** they MUST acquire a global `asyncio.Semaphore` (default: 30)
- **AND** excess requests SHALL queue without blocking or timing out.

### Requirement: Translation Completeness Validation
The system MUST algorithmically verify that the translation output does not improperly skip or retain large blocks of source-language prose.

#### Scenario: Flagging incomplete translations
- **WHEN** the retention ratio of source-language English words exceeds 55%
- **THEN** the section MUST be flagged as an incomplete (Type T) error
- **AND** trigger an automated re-translation with explicit completeness instructions.

### Requirement: Robust LaTeX Syntax Validation
The system SHALL accurately identify LaTeX syntax errors without generating false positives for common document structures like numbered lists.

#### Scenario: Parentheses in enumerated lists ignored
- **WHEN** the system validates a document containing `(1)` or `1)` in an `enumerate` environment
- **THEN** it SHALL NOT flag these as unmatched brackets
- **AND** it SHALL only track `[]` and `{}` pairs for syntax validation.

### Requirement: Thread-Safe Prompt Isolation
The system SHALL isolate language prompt states across concurrent tasks to prevent race conditions.

#### Scenario: Isolated prompt instantiation
- **WHEN** a translation task begins
- **THEN** it MUST use `pm.create_prompts` under a threading lock to obtain an isolated dictionary of prompt templates
- **AND** all subsequent logic MUST use this instance-specific dictionary instead of global variables.

### Requirement: Persistent Task Logging
The system SHALL maintain a structural JSON log of critical task state transitions within the output directory.

#### Scenario: Writing task log events
- **WHEN** a task achieves a major milestone (parsing end, translation start, etc.)
- **THEN** the system SHALL append a JSON entry to `task_log.json` containing a timestamp, event name, and auxiliary data.
