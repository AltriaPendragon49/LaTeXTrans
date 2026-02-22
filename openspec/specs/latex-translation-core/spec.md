# latex-translation-core Specification

## Purpose
定义 LaTeX 翻译核心引擎的技术和行为规范。本规范深入描述了从原始 LaTeX 结构化文档的内容解析到多 Agent（如 ParserAgent、TranslatorAgent、GeneratorAgent）协同处理的过程；涉及了大语言模型（LLM）对具体文本环境化内容的智能判定及重翻译逻辑；并详细规定了最终生成目标 PDF 时的编译流程、包括基于字符出现频率的智能排版引擎（XeLaTeX、LuaLaTeX、pdfLaTeX）切换和回退重试策略。
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

#### Scenario: Parallel need_trans determination (NEW)
- **WHEN** `ParserAgent.execute()` identifies environments requiring translation judgment
- **THEN** the system invokes `_request_llm_for_judge_async()` for all environments in parallel using `asyncio.gather()`
- **AND** limits concurrent LLM requests to 5 via `asyncio.Semaphore`
- **AND** completes all judgments in 3-5 seconds (vs 20+ seconds serial)

#### Scenario: Single judgment failure handling (NEW)
- **WHEN** one parallel LLM request fails (timeout, rate limit, network error)
- **THEN** that environment defaults to `need_trans=True` (conservative behavior)
- **AND** other parallel requests continue unaffected
- **AND** failure is logged with warning level

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

#### Scenario: Language-aware engine prioritization
- **WHEN** `compile_with_intelligent_fallback()` is called without explicit engine order
- **THEN** the system detects document language by scanning for CJK characters and Cyrillic characters
- **AND** if CJK character count > 100, uses order: `XeLaTeX → LuaLaTeX → PDFLaTeX`
- **AND** if Cyrillic character count > 50, uses order: `XeLaTeX → LuaLaTeX → PDFLaTeX`
- **AND** if neither exceeds their threshold, uses order: `PDFLaTeX → XeLaTeX → LuaLaTeX`

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
- **THEN** the error report includes `error_type: "C"`
- **AND** the error is marked for algorithmic repair (not LLM retry)

### Requirement: Error-type-aware Retry Logic

The system SHALL route errors to appropriate handlers based on classification.

#### Scenario: B-type error translation retry
- **WHEN** `TranslatorAgent` processes errors with `error_type: "B"`
- **THEN** the system attempts `_retranslate_error_parts()` at most once
- **AND** if retry fails, marks part as failed

#### Scenario: C-type error algorithmic repair
- **WHEN** `TranslatorAgent` processes errors with `error_type: "C"`
- **THEN** the system invokes `apply_structural_fix()` without LLM call
- **AND** attempts to restore missing tokens from original content

#### Scenario: C-type repair fallback
- **WHEN** `apply_structural_fix()` cannot restore structural consistency
- **THEN** the system prioritizes preserving existing translated content if available
- **AND** falls back to original content only when translation is completely missing
- **AND** logs the failure with detailed mismatch information

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

