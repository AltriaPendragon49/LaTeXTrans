# web-api Specification

## Purpose
定义 LaTeXTrans 后端 REST API 接口规范，包括翻译任务管理、文件下载、状态查询等端点。
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

任务状态 API SHALL 返回完整任务信息，包括高级配置。

#### Scenario: Query task status during processing
- **WHEN** user sends `GET /task/{task_id}` while translation is in progress
- **THEN** the system returns JSON with `{status: "processing", progress: <0-100>, stage: <current_stage>, message: <description>, advanced_config: <config>}`

#### Scenario: Query completed task status (perfect compilation)
- **WHEN** user sends `GET /task/{task_id}` for a successfully completed translation with zero compilation errors
- **THEN** the system returns `{status: "completed", progress: 100, stage: "done", output_path: <path_to_pdf>, advanced_config: <config>}`

#### Scenario: Polling fallback (NEW)
- **WHEN** client cannot establish SSE connection (browser compatibility, proxy issues)
- **THEN** classic `GET /api/task/{task_id}` polling remains available
- **AND** polling interval recommendation is 2 seconds

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

### Requirement: Advanced Configuration in Translation Request

The web API SHALL support advanced configuration overrides seamlessly.

#### Scenario: 后端处理自定义 API 配置
- **WHEN** 后端接收到 `use_author_api = false` 的请求或使用系统后台预设配置
- **THEN** 后端使用 `normalize_base_url` 逻辑处理 `base_url`
- **AND** 若 URL 已包含 `/chat/completions`，则保持原样
- **AND** 若为短路径（如仅域名或 `/v1`），则自动补全为 `/v1/chat/completions`
- **AND** 确保对 Nvidia NIM API 等包含完整路径的端点具有 100% 兼容性

### Requirement: Terminology Table Download Endpoint
后端 SHALL 提供术语表下载端点。

#### Scenario: 下载术语表
- **WHEN** 用户请求 `GET /download/{task_id}/terminology`
- **THEN** 系统返回 CSV 格式的术语表文件
- **AND** 响应头包含 `Content-Disposition: attachment`

#### Scenario: 术语表不存在
- **WHEN** 任务未生成术语表（generate_terminology_table = false）
- **THEN** 系统返回 HTTP 404 错误

### Requirement: Source PDF Preview Endpoint
后端 SHALL 提供原文 PDF 预览端点，支持多种来源策略。

#### Scenario: 预览 arXiv 论文原文
- **WHEN** 用户请求 `GET /preview/{task_id}/source-pdf` 且任务来源为 arXiv
- **THEN** 系统从 arXiv 下载原文 PDF 并返回

#### Scenario: 预览本地上传论文原文
- **WHEN** 用户请求预览本地上传的论文
- **THEN** 系统查找目录中现有的 PDF 或编译源 tex 生成 PDF

### Requirement: ArXiv Download Async Mode
后端 SHALL 将 arXiv 下载端点改为异步模式，立即返回 task_id 并在后台执行下载。

#### Scenario: 发起 arXiv 下载
- **WHEN** 用户请求 `POST /api/arxiv` 包含有效的 arxiv_id
- **THEN** 系统立即创建任务，返回 `{task_id, arxiv_id, status: "downloading"}`
- **AND** 在后台异步执行下载流程

#### Scenario: 查询下载进度
- **WHEN** 用户请求 `GET /api/task/{task_id}` 且任务状态为 "downloading"
- **THEN** 系统返回 `{status: "downloading", progress: <0-100>, stage: <stage_name>, message: <description>}`
- **AND** progress 反映真实的下载和解析进度

#### Scenario: 下载完成后状态变更
- **WHEN** arXiv 下载和解析全部完成
- **THEN** 任务状态变为 "pending"（准备翻译）
- **AND** progress 为 100
- **AND** source_available 为 true

### Requirement: Download Progress Stages
后端 SHALL 在下载过程中报告细粒度的进度阶段。

#### Scenario: 下载 TeX 源码阶段
- **WHEN** 系统正在从 arXiv 下载 tar.gz 文件
- **THEN** stage 为 "downloading"
- **AND** progress 在 0-30% 范围内

#### Scenario: 解压文件阶段
- **WHEN** 系统正在解压 tar.gz 文件
- **THEN** stage 为 "extracting"
- **AND** progress 在 30-60% 范围内

#### Scenario: 下载 PDF 阶段
- **WHEN** 系统正在下载原文 PDF
- **THEN** stage 为 "downloading_pdf"
- **AND** progress 在 60-80% 范围内

#### Scenario: 验证文件阶段
- **WHEN** 系统正在验证 .tex 文件存在性
- **THEN** stage 为 "validating"
- **AND** progress 在 80-100% 范围内

### Requirement: Server-Sent Events for Task Status

The system SHALL provide real-time task status updates via SSE (Server-Sent Events).

> **SSE** is an HTML5 standard technology that allows the server to push data to the client without the client repeatedly initiating requests. Compared to polling, SSE reduces latency from up to 2 seconds to under 100ms, eliminates redundant HTTP requests, and provides smoother user experience.

#### Scenario: SSE connection establishment
- **WHEN** client sends `GET /api/task/{task_id}/stream`
- **THEN** the system returns `Content-Type: text/event-stream` response
- **AND** immediately sends current task status as first event

#### Scenario: SSE progress updates
- **WHEN** task status, progress, or message changes
- **THEN** the system pushes an event within 500ms
- **AND** event data contains full task status JSON

#### Scenario: SSE connection termination
- **WHEN** task reaches terminal status (completed, failed, completed_with_warnings, failed_compilation)
- **THEN** the system sends final status event
- **AND** closes the SSE connection gracefully

#### Scenario: SSE heartbeat
- **WHEN** task is in progress but no status change occurs
- **THEN** the system sends a heartbeat comment (`: heartbeat`) every 15 seconds
- **AND** keeps connection alive

### Requirement: Environment Translation Judgment
The ParserAgent SHALL determine which LaTeX environments need translation with optimized filtering:
1. **Extended skip list**: Skip LLM calls for environments that are clearly translatable or non-translatable based on environment type
2. **Content length filter**: Skip LLM calls for environments with content shorter than 20 characters

The system SHALL maintain the existing concurrency limit (`Semaphore(5)`) to avoid API rate limiting.

#### Scenario: Environment in skip list
- **WHEN** a LaTeX environment is of type `abstract`, `itemize`, `enumerate`, `description`, `proof`, `definition`, `theorem`, or `lemma`
- **THEN** the system SHALL skip LLM judgment for that environment

#### Scenario: Short content filtering
- **WHEN** an environment has content shorter than 20 characters
- **THEN** the system SHALL skip LLM judgment for that environment

#### Scenario: Preserve existing behavior for complex environments
- **WHEN** an environment does not match any skip criteria
- **THEN** the system SHALL call LLM individually (not batched) to determine translation need
- **AND** the concurrency limit of 5 simultaneous calls SHALL be maintained

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

