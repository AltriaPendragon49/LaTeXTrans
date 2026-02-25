## ADDED Requirements

### Requirement: Typography Parameter Bounds Validation
The backend system MUST validate advanced typography parameters to prevent malformed LaTeX commands.

#### Scenario: Backend bounds check
- **WHEN** `apply_formatting_config` receives font size outside `[8, 14]` or line spacing outside `[1.0, 2.5]`
- **THEN** it MUST skip the injection of these parameters
- **AND** append a warning message to the `fmt_warnings` list for user visibility.

### Requirement: Email Notification Service
The system SHALL provide a background email service to notify users of task completion.

#### Scenario: Dispatching status emails
- **WHEN** a task with `email_notify=True` finishes as `COMPLETED` or `FAILED`
- **THEN** the `EmailService` MUST dispatch an HTML email using SMTP credentials
- **AND** include the task ID and final status in the message.

### Requirement: Translated PDF Resolution Logic
The system SHALL accurately locate the final translated PDF while avoiding deep-nested source directories.

#### Scenario: Optimized PDF search
- **WHEN** resolving a PDF for download or preview
- **THEN** the system MUST use `_find_translated_pdf` to scan only the top-level output directory
- **AND** prioritize files matching `{task_id}_translated.pdf`.

## MODIFIED Requirements

### Requirement: Translation Progress Reporting
The system SHALL report granular progress updates during translation workflow stages, with optimized database I/O for download operations.

#### Scenario: AST parsing stage progress
- **WHEN** `ParserAgent` is extracting LaTeX structure
- **THEN** task progress reflects 0-25% with stage "parsing" and message describing current file

#### Scenario: LLM translation stage progress
- **WHEN** `TranslatorAgent` is translating text chunks
- **THEN** task progress reflects 25-80% with stage "translating" and message showing chunk N/M

#### Scenario: LaTeX compilation stage progress
- **WHEN** `GeneratorAgent` is running xelatex
- **THEN** task progress reflects 80-100% with stage "compiling" and message showing compilation pass

#### Scenario: Error during translation
- **WHEN** any agent encounters an unrecoverable error
- **THEN** task status changes to "failed" with error field populated and progress frozen at failure point

#### Scenario: arXiv Download Throttling
- **WHEN** `DownloadProgressCallback` receives progress updates from arXiv download
- **THEN** it MUST only execute a database update when the integer percentage changes or the stage completes
- **AND** total download performance MUST stay independent of database latency.
