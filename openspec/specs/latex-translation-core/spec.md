# latex-translation-core Specification

## Purpose
定义 LaTeX 翻译核心引擎规范，包括解析、翻译、编译流程及智能回退策略。
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

The system SHALL compile translated LaTeX files into PDF using a multi-stage compilation strategy with **intelligent language detection**, **three-engine fallback**, and error-based output selection.

#### Scenario: Language-aware engine prioritization (NEW)
- **WHEN** `compile_with_intelligent_fallback()` is called without explicit engine order
- **THEN** the system detects document language by scanning for CJK characters (Chinese, Japanese, Korean)
- **AND** if CJK character count > 100, uses order: `XeLaTeX → LuaLaTeX → PDFLaTeX`
- **AND** if CJK character count ≤ 100, uses order: `PDFLaTeX → XeLaTeX → LuaLaTeX`

#### Scenario: LuaLaTeX compilation support (NEW)
- **WHEN** compilation falls back to LuaLaTeX (or LuaLaTeX is prioritized for CJK documents)
- **THEN** the system invokes `latexmk -lualatex` via subprocess
- **AND** captures the `.log` file for error analysis
- **AND** follows the same error counting logic as pdflatex/xelatex

#### Scenario: Primary engine compilation attempt (MODIFIED)
- **WHEN** `GeneratorAgent.execute()` is called with translated `.tex` files
- **THEN** the system first detects document language to determine engine priority
- **THEN** attempts compilation using the first engine in the priority list via `subprocess`, captures the `.log` file, and records the exit code and error count

#### Scenario: Fallback to secondary engine on primary failure (MODIFIED)
- **WHEN** the primary engine compilation fails (non-zero exit code) or produces errors
- **THEN** the system attempts compilation using the second engine in the priority list
- **AND** if the second engine also fails or produces errors, attempts the third engine

#### Scenario: Perfect compilation (zero errors) - early exit (UNCHANGED)
- **WHEN** any engine produces a PDF with zero errors in the `.log` file
- **THEN** the system immediately returns that PDF as the final output and marks task status as "completed"

#### Scenario: Selecting best output from three-engine attempts (MODIFIED)
- **WHEN** multiple engines produce PDFs but all have errors in their `.log` files
- **THEN** the system compares error counts across all attempted engines and selects the PDF with the fewest errors, marking task status as "completed_with_warnings"

#### Scenario: Total compilation failure with source preservation (UNCHANGED)
- **WHEN** all three engines (pdflatex, xelatex, lualatex) fail to produce any PDF output
- **THEN** the system preserves the translated `.tex` source files, marks task status as "failed_compilation", stores combined error details from all `.log` files in the task error field, and makes the source files available for download via the `/download/{task_id}/source` endpoint

### Requirement: PDF Generation Readiness Verification

The system SHALL verify that generated PDF files are fully written and accessible before marking translation tasks as completed.

#### Scenario: PDF file verification after generation
- **WHEN** `GeneratorAgent` successfully compiles a PDF and moves it to the output directory
- **THEN** the system verifies the PDF file exists, has non-zero size, and contains a valid PDF header (`%PDF-`)
- **AND** only after verification passes, updates task progress to 100%

#### Scenario: PDF file verification during move operation
- **WHEN** `shutil.move()` is called to relocate the generated PDF
- **THEN** the system waits for the filesystem to fully commit the write operation
- **AND** verifies file accessibility by attempting to open and read the PDF header

#### Scenario: Preview endpoint PDF readiness check
- **WHEN** client requests `/preview/{task_id}/pdf` endpoint
- **THEN** the system checks that the PDF file has non-zero size and valid PDF header
- **AND** if the PDF is not ready (empty or invalid header), returns HTTP 503 with message "PDF generation in progress, please retry"

#### Scenario: Download endpoint PDF readiness check
- **WHEN** client requests `/download/{task_id}/pdf` endpoint
- **THEN** the system performs the same readiness check as the preview endpoint
- **AND** returns HTTP 503 if the PDF is not ready

#### Scenario: Handling filesystem race conditions
- **WHEN** the task status is "completed" but the PDF file is not yet readable
- **THEN** the preview/download endpoints return HTTP 503 (Service Unavailable) instead of HTTP 404 (Not Found)
- **AND** the response includes a "Retry-After" header suggesting client retry in 1-2 seconds

