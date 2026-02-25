# latex-translation-core Specification Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
