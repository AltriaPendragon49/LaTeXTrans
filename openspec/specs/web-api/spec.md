# web-api Specification

## Purpose
TBD - created by archiving change add-web-mvp-platform. Update Purpose after archive.
## Requirements
### Requirement: Translation Task Initiation
The system SHALL accept translation requests via REST API and process them asynchronously in the background.

#### Scenario: Start translation for uploaded file
- **WHEN** user sends `POST /translate/{task_id}` for a valid task with uploaded source files
- **THEN** the system updates task status to "processing", triggers background translation via `CoordinatorAgent`, and returns HTTP 202 with message "Translation started"

#### Scenario: Start translation for arXiv source
- **WHEN** user sends `POST /translate/{task_id}` for a task created via arXiv download
- **THEN** the system identifies the main `.tex` file, initiates translation, and updates task status accordingly

#### Scenario: Translation request for invalid task
- **WHEN** user sends translation request for nonexistent task ID
- **THEN** the system returns HTTP 404 with error "Task not found"

#### Scenario: Duplicate translation request
- **WHEN** user sends translation request for a task already in "processing" or "completed" status
- **THEN** the system returns HTTP 409 with error "Translation already in progress or completed"

### Requirement: Task Status Tracking
The system SHALL maintain and expose real-time status information for all translation tasks.

#### Scenario: Query task status during processing
- **WHEN** user sends `GET /task/{task_id}` while translation is in progress
- **THEN** the system returns JSON with `{status: "processing", progress: <0-100>, stage: <current_stage>, message: <description>}`

#### Scenario: Query completed task status (perfect compilation)
- **WHEN** user sends `GET /task/{task_id}` for a successfully completed translation with zero compilation errors
- **THEN** the system returns `{status: "completed", progress: 100, stage: "done", output_path: <path_to_pdf>}`

#### Scenario: Query completed task status (with warnings)
- **WHEN** user sends `GET /task/{task_id}` for a translation that produced a PDF but with compilation warnings
- **THEN** the system returns `{status: "completed_with_warnings", progress: 100, stage: "done", output_path: <path_to_pdf>, warnings: <warning_summary>}`

#### Scenario: Query failed compilation task status
- **WHEN** user sends `GET /task/{task_id}` for a translation that succeeded but PDF compilation failed
- **THEN** the system returns `{status: "failed_compilation", progress: 100, stage: "compilation_failed", error: <combined_log_errors>, source_available: true}`

#### Scenario: Query failed task status (translation error)
- **WHEN** user sends `GET /task/{task_id}` for a failed translation (before compilation)
- **THEN** the system returns `{status: "failed", error: <error_message>, stage: <failed_stage>}``

#### Scenario: Query nonexistent task
- **WHEN** user sends `GET /task/{task_id}` for an invalid task ID
- **THEN** the system returns HTTP 404 with error "Task not found"

### Requirement: Translation Progress Reporting
The system SHALL report granular progress updates during translation workflow stages.

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

### Requirement: API Health Monitoring
The system SHALL expose a health check endpoint to verify backend readiness.

#### Scenario: Successful health check
- **WHEN** user or monitoring tool sends `GET /health`
- **THEN** the system returns HTTP 200 with `{status: "ok", latex: <true|false>, timestamp: <ISO8601>}`

#### Scenario: LaTeX unavailable warning
- **WHEN** health check detects `xelatex` is not available on system PATH
- **THEN** response includes `latex: false` and warning message "LaTeX compiler not detected"

### Requirement: PDF预览端点
系统 SHALL 提供独立的PDF预览端点，支持在浏览器iframe中内嵌显示译文PDF。

#### Scenario: 获取PDF用于浏览器预览
- **WHEN** 前端请求 `GET /api/preview/{task_id}/pdf`
- **THEN** 系统返回PDF文件，响应头包含 `Content-Disposition: inline; filename="preview_{task_id}.pdf"`，允许浏览器内嵌显示

#### Scenario: 预览未完成的任务
- **WHEN** 用户请求preview端点但任务状态不是 `completed` 或 `completed_with_warnings`
- **THEN** 系统返回 HTTP 400 错误，提示"Translation not completed"

#### Scenario: 预览不存在的任务
- **WHEN** 用户请求preview端点但task_id不存在
- **THEN** 系统返回 HTTP 404 错误，提示"Task not found"

