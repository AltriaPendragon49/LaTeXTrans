# latex-translation-core Specification

## Purpose
TBD - created by archiving change add-web-mvp-platform. Update Purpose after archive.
## Requirements
### Requirement: LaTeX Parsing and Translation
The system SHALL parse LaTeX source files into an Abstract Syntax Tree (AST), translate extracted text content while preserving structure, and reconstruct valid LaTeX output.

#### Scenario: CLI translation workflow (existing)
- **WHEN** user runs `python main.py --arxiv 2508.18791`
- **THEN** the system downloads source, parses LaTeX using `pylatexenc`, translates text chunks via LLM, reconstructs `.tex` files, and compiles PDF in `outputs/` directory

#### Scenario: Web API translation workflow (new)
- **WHEN** backend invokes `CoordinatorAgent.workflow_latextrans()` from a FastAPI background task
- **THEN** the system executes the same parsing → translation → compilation pipeline, updates task progress via callbacks, and writes output to `data/outputs/{task_id}/`

#### Scenario: Progress callback integration (new)
- **WHEN** `ParserAgent`, `TranslatorAgent`, or `GeneratorAgent` completes a processing step
- **THEN** each agent invokes `on_progress(stage, percentage, message)` callback to update `TaskManager` state

#### Scenario: Streamlit-free operation (new)
- **WHEN** any agent runs without Streamlit context (web environment)
- **THEN** the system uses Python `logging` module for output and does not call `st.progress()`, `st.text()`, or `st.spinner()`

#### Scenario: Error propagation to web layer (new)
- **WHEN** translation fails due to LaTeX parsing error, LLM timeout, or compilation error
- **THEN** the agent raises an exception with descriptive message, which is caught by background task handler and stored in `TaskManager` error field

### Requirement: arXiv Source Download
The system SHALL download LaTeX source code from arXiv.org given a valid paper ID.

#### Scenario: CLI arXiv download (existing)
- **WHEN** user provides `--arxiv` argument to CLI
- **THEN** `batch_download_arxiv_tex()` downloads `.tar.gz` source to `tex source/` directory

#### Scenario: Web API arXiv download (new)
- **WHEN** backend receives `POST /arxiv` request with arXiv ID
- **THEN** adapted `batch_download_arxiv_tex()` downloads source to `data/uploads/{task_id}/` and returns task ID to caller

#### Scenario: arXiv metadata extraction (existing)
- **WHEN** downloading from arXiv
- **THEN** the system extracts paper category (e.g., "cs.AI") via `get_arxiv_category()` for potential terminology selection (unused in MVP, used in Phase 2)

### Requirement: LaTeX Compilation with Intelligent Fallback
The system SHALL compile translated LaTeX files into PDF using a multi-stage compilation strategy with automatic engine fallback and error-based output selection.

#### Scenario: Primary pdflatex compilation attempt
- **WHEN** `GeneratorAgent.execute()` is called with translated `.tex` files
- **THEN** the system first attempts compilation using `pdflatex` via `subprocess`, captures the `.log` file, and records the exit code and error count

#### Scenario: Fallback to xelatex on pdflatex failure
- **WHEN** pdflatex compilation fails (non-zero exit code)
- **THEN** the system automatically attempts compilation using `xelatex` via `subprocess`, captures the `.log` file, and records the exit code and error count

#### Scenario: Perfect compilation (zero errors)
- **WHEN** either pdflatex or xelatex produces a PDF with zero errors in the `.log` file
- **THEN** the system immediately returns that PDF as the final output and marks task status as "completed"

#### Scenario: Single successful compilation with errors
- **WHEN** pdflatex produces a PDF (exit code 0) but the `.log` file contains errors
- **THEN** the system attempts xelatex compilation, compares error counts, and selects the PDF with fewer errors

#### Scenario: Selecting best output from imperfect compilations
- **WHEN** both pdflatex and xelatex produce PDFs but both have errors in their `.log` files
- **THEN** the system compares error counts and selects the PDF with fewer errors, marking task status as "completed_with_warnings"

#### Scenario: Partial output preference
- **WHEN** one compiler produces a PDF (even with errors) and the other fails to produce any output
- **THEN** the system returns the available PDF regardless of error count

#### Scenario: Total compilation failure with source preservation
- **WHEN** both pdflatex and xelatex fail to produce any PDF output
- **THEN** the system preserves the translated `.tex` source files, marks task status as "failed_compilation", stores combined error details from both `.log` files in the task error field, and makes the source files available for download via the `/download/{task_id}/source` endpoint

#### Scenario: Error log parsing for comparison
- **WHEN** parsing `.log` files to count errors
- **THEN** the system counts lines matching LaTeX error patterns (e.g., `! LaTeX Error`, `! Undefined control sequence`, `! Missing`)

#### Scenario: MiKTeX auto-install requirement (existing constraint)
- **WHEN** compilation encounters missing LaTeX package
- **THEN** the system relies on MiKTeX's "install on the fly" feature to auto-download packages for both pdflatex and xelatex (requires MiKTeX configured on host for MVP; Docker isolation deferred to Phase 3)

