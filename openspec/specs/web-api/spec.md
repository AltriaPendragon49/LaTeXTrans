# web-api Specification

## Purpose
定义 LaTeXTrans 后端 REST API 接口规范，包括翻译任务管理、文件下载、状态查询等端点。
## Requirements
### Requirement: Translation Task Initiation
The system SHALL accept translation requests via REST API and process them asynchronously in the background.  
During translation initialization, the system SHALL attempt runtime config snapshot capture when enabled, and capture failure SHALL NOT fail the translation task.

#### Scenario: Start translation for uploaded file
- **WHEN** user sends `POST /translate/{task_id}` for a valid task with uploaded source files
- **THEN** the system updates task status to processing, triggers background translation, and returns HTTP 202

#### Scenario: Runtime Config Capture Enabled
- **WHEN** translation initialization has built effective runtime configuration
- **AND** `ENABLE_TASK_CONFIG_CAPTURE=true`
- **THEN** the system attempts to persist a config snapshot under `data/task_configs`

#### Scenario: Runtime Config Capture Failure Is Non-Blocking
- **WHEN** config snapshot capture fails due to module/path/write/runtime error
- **THEN** the system logs a warning
- **AND** translation initialization continues without raising task-fatal error from capture

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
The system SHALL report granular progress updates during translation workflow stages, with optimized database I/O for local persistent operations.

#### Scenario: Async route DB calls do not pin event loop
- **WHEN** async API routes perform local database operations during task or persistence flows
- **THEN** blocking DB work SHALL execute through async-safe wrapper offload
- **AND** event-loop responsiveness for `/api/health` and task-status polling SHALL remain stable during compile load.

#### Scenario: Behavior-level event-loop health gate
- **WHEN** parser or validator phases run with simulated blocking work
- **THEN** automated tests SHALL verify scheduler or tick latency stays under the configured threshold
- **AND** concurrent task wall time SHALL indicate non-serialized behavior.

### Requirement: API Health Monitoring
The system SHALL expose a health check endpoint to verify backend readiness.

#### Scenario: Successful health check
- **WHEN** user or monitoring tool sends `GET /health`
- **THEN** the system returns HTTP 200 with `{status: "ok", latex: <true|false>, timestamp: <ISO8601>}`

#### Scenario: LaTeX unavailable warning
- **WHEN** health check detects `xelatex` is not available on system PATH
- **THEN** response includes `latex: false` and warning message "LaTeX compiler not detected"

### Requirement: PDF预览端点
系统 SHALL 提供独立的 PDF 预览端点，支持在浏览器 iframe 中内嵌显示译文 PDF。  
当普通任务启用 COS 主存储时，预览仍 SHALL 由后端代理，不直接把签名 URL 暴露为前端必须拼接的下载地址。

#### Scenario: 获取 PDF 用于浏览器预览
- **WHEN** 前端请求 `GET /api/preview/{task_id}/pdf`
- **THEN** 系统返回 PDF 文件，响应头包含 `Content-Disposition: inline; filename="preview_{task_id}.pdf"`，允许浏览器内嵌显示

#### Scenario: 预览未完成的任务
- **WHEN** 用户请求 preview 端点但任务状态不是 `completed` 或 `completed_with_warnings`
- **THEN** 系统返回 HTTP 400 错误，提示 "Translation not completed"

#### Scenario: 预览不存在的任务
- **WHEN** 用户请求 preview 端点但 `task_id` 不存在
- **THEN** 系统返回 HTTP 404 错误，提示 "Task not found"

#### Scenario: COS 模式普通任务 PDF 预览由后端代理
- **WHEN** `STORAGE_BACKEND_MODE=cos` 且普通任务译文 PDF 已持久化到 COS
- **THEN** `GET /api/preview/{task_id}/pdf` SHALL 通过后端代理返回内联 PDF 内容
- **AND** 前端不需要自行拼接或解析 COS 签名下载地址

### Requirement: Advanced Configuration in Translation Request

The web API SHALL support advanced configuration overrides seamlessly. Prior user-level saved configurations MUST NOT supersede active advanced_config overrides provided with the request.

#### Scenario: 后端处理自定义 API 配置
- **WHEN** 后端接收到 `use_author_api = false` 的请求或使用系统后台预设配置
- **THEN** 后端优先读取 `advanced_config.custom_api_key` 进行验证并使用 `normalize_base_url` 逻辑处理 `base_url`
- **AND** 若找不到前端附带配置且存在 user_id，才降级读取持久化的用户级 `user_api_config`
- **AND** 若 URL 已包含 `/chat/completions`，则保持原样
- **AND** 若为短路径（如仅域名或 `/v1`），则自动补全为 `/v1/chat/completions`
- **AND** 确保对 Nvidia NIM API 等包含完整路径的端点具有 100% 兼容性

### Requirement: Terminology Table Download Endpoint
后端 SHALL 提供术语表下载端点。  
当普通任务启用 COS 主存储时，下载类接口 SHALL 使用签名 URL 交付而不是依赖长期本地文件。

#### Scenario: 下载术语表
- **WHEN** 用户请求 `GET /download/{task_id}/terminology`
- **THEN** 系统返回 CSV 格式的术语表文件
- **AND** 响应头包含 `Content-Disposition: attachment`

#### Scenario: 术语表不存在
- **WHEN** 任务未生成术语表（`generate_terminology_table = false`）
- **THEN** 系统返回 HTTP 404 错误

#### Scenario: COS 模式术语表下载使用签名 URL
- **WHEN** `STORAGE_BACKEND_MODE=cos` 且普通任务术语表已持久化到 COS
- **THEN** `GET /download/{task_id}/terminology` SHALL 返回到签名 COS URL 的下载交付
- **AND** 客户端无需依赖长期本地输出目录

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

#### Scenario: Polling fallback and task deletion (NEW)
- **WHEN** client cannot establish SSE connection and relies on `GET /api/task/{task_id}` polling fallback
- **AND** the requested task returns HTTP 404 (due to deletion)
- **THEN** the frontend gracefully terminates the polling loop instead of retrying infinitely.

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

#### Scenario: Enabling completion emails
- **WHEN** a user enables task email notifications and a task later reaches a terminal state
- **THEN** the product SHALL use PaperX-branded completion or failure wording in its outward-facing notification surfaces
- **AND** the user-facing status email content SHALL keep the task identifier and terminal status details.

### Requirement: Translated PDF Resolution Logic
The system SHALL accurately locate the final translated PDF while avoiding deep-nested source directories.

#### Scenario: Optimized PDF search
- **WHEN** resolving a PDF for download or preview
- **THEN** the system MUST use `_find_translated_pdf` to scan only the top-level output directory
- **AND** prioritize files matching `{task_id}_translated.pdf`.

### Requirement: Compilation Failure Status Semantics
The API layer SHALL expose compilation-stage failures as explicit terminal task status `failed_compilation` with actionable summaries.

#### Scenario: Coordinator reports compilation failure
- **WHEN** translation orchestration returns compile failure (`status=failed_compilation` or missing compiled PDF)
- **THEN** `/translate` background workflow MUST set task status to `failed_compilation`
- **AND** MUST store readable compile summary in task `error` and `message` fields.

#### Scenario: Orchestrator returns non-existent PDF path
- **WHEN** orchestration returns a non-empty `pdf_path` but the file does not exist on disk
- **THEN** API workflow MUST treat the task as `failed_compilation` (not generic runtime failure)
- **AND** error summary MUST include the missing path for diagnostics.

#### Scenario: Compilation completes with warnings
- **WHEN** orchestration reports `completed_with_warnings`
- **THEN** task status MUST be `completed_with_warnings`
- **AND** warning details MUST be surfaced to clients.

### Requirement: Translated PDF Resolution Safety
Download/preview endpoints SHALL resolve translated PDFs deterministically and MUST avoid selecting copied source PDFs.

#### Scenario: Resolve by task log first
- **WHEN** `task_log.json` contains `compilation_completed` or `compilation_completed_with_warnings` entries with `pdf_path`
- **THEN** resolver MUST prioritize those paths if they exist under the task output root.

#### Scenario: Safe fallback without deep recursion
- **WHEN** no valid task-log PDF path is available
- **THEN** resolver MAY use strict naming-convention fallback only
- **AND** MUST NOT use unrestricted deep recursive PDF search.

#### Scenario: Nested source PDF exists but translated PDF missing
- **WHEN** output tree contains copied source PDF in nested source subdirectory
- **AND** translated PDF is absent
- **THEN** resolver MUST return no translated PDF instead of returning the nested source PDF.

### Requirement: Terminal State Propagation for Streaming and Polling
Task status streaming and polling SHALL treat compilation-specific terminal states consistently.

#### Scenario: SSE terminal status includes compilation outcomes
- **WHEN** task status becomes `completed_with_warnings` or `failed_compilation`
- **THEN** SSE stream MUST emit terminal complete event and close.

#### Scenario: Frontend polling stops on compilation failure
- **WHEN** polling receives `failed_compilation`
- **THEN** client MUST stop polling and render failure UI without "View Result" actions.

### Requirement: Progress UI Feedback for Rate Limits
The task management system SHALL support atomic progress message updates without altering percentage values to accommodate rate-limiting feedback.

#### Scenario: Atomic message-only update
- **WHEN** a progress update is received with `percentage=-1`
- **THEN** the system MUST update only the task's `message` field
- **AND** MUST preserve the last known `progress` and `stage`.

#### Scenario: Deadlock-free task updates
- **WHEN** processing an atomic message update
- **THEN** the system MUST NOT perform re-entrant locking on the task state
- **AND** MUST ensure UI components (like amber-pulse bars) receive the data promptly.

#### Scenario: Rate-limited visual feedback
- **WHEN** a task message contains "rate limited"
- **THEN** frontend components MUST render the progress bar and status text with amber pulsing visual cues
- **AND** MUST display a global warning banner if the task is in the active processing view.

[Checklist: Delta validation]
- [x] -1 percentage logic implemented in TaskManager
- [x] TaskManager deadlock fixed
- [x] Frontend amber-pulse styles applied to TaskList/Processing
- [x] Rate limit warning text includes performance suggestion

### Requirement: Persisted Task Recovery
The task manager MUST recover task configurations from the local file system and local database without depending on Supabase fallback behavior.

#### Scenario: Task missing from local database
- **WHEN** a task is not found in the local persistent store
- **THEN** the backend SHALL search the local file system using the configured `outputs_dir` and `uploads_dir`
- **AND** it SHALL retrieve metadata gracefully without requiring a Supabase fallback path.

### Requirement: Configurable CORS Origin Allowlist
Backend SHALL support comma-separated CORS origin configuration via `CORS_ORIGINS`.

#### Scenario: Parse multiple origins from env
- **WHEN** `CORS_ORIGINS` contains a comma-separated list
- **THEN** backend MUST parse and trim each origin
- **AND** backend MUST ignore empty entries

#### Scenario: Wildcard is rejected
- **WHEN** `CORS_ORIGINS` includes `*`
- **THEN** backend configuration MUST reject this value
- **AND** startup MUST not silently downgrade to wildcard behavior

#### Scenario: Middleware uses parsed allowlist
- **WHEN** backend app initializes CORS middleware
- **THEN** middleware MUST use parsed configured allowlist directly

### Requirement: External API Namespace Prefix
All externally exposed backend API endpoints SHALL be namespaced under `/api`.

#### Scenario: Public API request uses /api prefix
- **WHEN** a client requests history data
- **THEN** the request path is `GET /api/history`
- **AND** the endpoint is handled by backend API routing.

#### Scenario: Legacy non-prefixed path is not handled
- **WHEN** a client requests `GET /health`
- **THEN** FastAPI does not expose this endpoint as a public API route.

#### Scenario: Health endpoint under API namespace
- **WHEN** a monitoring system requests `GET /api/health`
- **THEN** the backend returns HTTP 200 JSON health payload.

### Requirement: Backend Runtime Parity Config Propagation
The web API SHALL pass the effective backend runtime parity configuration into the coordinator/task snapshot instead of relying on implicit defaults.

#### Scenario: Translate request builds parity-complete agent config
- **WHEN** the backend starts a translation task from the web API
- **THEN** it MUST propagate the effective translation/orchestration config into `agent_config`
- **AND** that config MUST include `translation_mode`, `generate_terminology_table`, `use_compilation_diagnostics`, `category`, `model_context_tokens`, `prompt_reserve_tokens`, `task_id`, `output_dir`, and `tex_sources_dir`
- **AND** the captured task configuration snapshot MUST reflect those effective values.

#### Scenario: Task-level LLM concurrency is bounded for parity
- **WHEN** the backend computes the per-task LLM concurrency passed into orchestration
- **THEN** it MUST cap the task-level value to the parity-safe ceiling of `3`
- **AND** MUST record the effective bounded value in the task-start/runtime snapshot.

### Requirement: Community agent run API returns a natural assistant message
The community agent run API SHALL return the assistant’s natural-language reply as a first-class field while preserving run metadata such as citations, tool trace, provider state, and actions, and it SHALL support both blocking and async accepted execution modes.

#### Scenario: Conversational run completes successfully in blocking mode
- **WHEN** `POST /api/community-agent/runs` completes in blocking mode
- **THEN** the response SHALL include `message` containing the assistant’s natural-language reply
- **AND** it SHALL continue to include `citations`, `tool_trace`, `provider_state`, and `action`.

#### Scenario: Compatibility alias remains during migration
- **WHEN** existing consumers still read `summary`
- **THEN** the API SHALL keep `summary` aligned with `message` during the migration window
- **AND** the conversational UI SHALL prefer `message` when present.

#### Scenario: Async mode defers the final message to the stream and result endpoints
- **WHEN** `POST /api/community-agent/runs` is called in async mode
- **THEN** the accepted response MAY omit the final `message` body
- **AND** the final assistant reply SHALL be available through the stream and result endpoints.

### Requirement: Community agent runs support async accepted mode
The community agent run API SHALL support an async accepted mode so the client can start a run, subscribe to the live stream, and later retrieve the final snapshot by `run_id`.

#### Scenario: Async run is accepted
- **WHEN** the client submits a run in async mode
- **THEN** `POST /api/community-agent/runs` SHALL return an accepted payload with `run_id`, `status`, `stream_url`, and `result_url`
- **AND** the actual assistant content SHALL arrive over the stream endpoint.

### Requirement: Community agent exposes an authenticated live SSE stream
The community agent API SHALL expose an authenticated live SSE stream for a running agent session so the client can render assistant deltas, tool lifecycle updates, citations, actions, status, and completion in order.

#### Scenario: Client subscribes to a running agent stream
- **WHEN** the client opens the run event stream with valid authentication
- **THEN** the API SHALL stream ordered events for tokens, tool lifecycle, citations, actions, status, and completion
- **AND** it SHALL close the stream cleanly after completion or failure.

#### Scenario: Unauthorized stream request is rejected
- **WHEN** the client requests the stream without valid auth
- **THEN** the API SHALL reject the request with an auth failure
- **AND** it SHALL NOT leak run state.

### Requirement: Community agent stream events follow a stable schema
The community agent stream SHALL emit a stable event schema so clients can parse assistant deltas, tool transitions, and completion snapshots without depending on ad hoc payload shapes.

#### Scenario: Assistant text delta event
- **WHEN** the runtime emits a token chunk
- **THEN** the event SHALL contain a stable event type, run id, sequence number, and delta text payload.

#### Scenario: Completion event carries final run snapshot
- **WHEN** the run finishes
- **THEN** the stream SHALL emit a completion event containing final `message`, `citations`, `tool_trace`, `provider_state`, and `action`.

### Requirement: Admin API supports manual stale task cleanup
The backend SHALL expose an administrative endpoint to manually trigger restart reconciliation for community-paper translation state across the local database and local filesystem.

#### Scenario: Admin triggers cleanup
- **WHEN** an authenticated local admin user calls `POST /api/admin/cleanup`
- **THEN** the API SHALL mark interrupted in-flight translation tasks as failed and clean related local artifacts
- **AND** it SHALL purge eligible non-success community-paper artifacts across the local database and disk
- **AND** it SHALL return a summary of the operations performed.

### Requirement: Backend automatically cleans up stale tasks on startup
The backend SHALL automatically reconcile community-paper translation state during startup so interrupted work is deterministically failed or cleaned across the local database and filesystem before traffic is served.

#### Scenario: Startup cleanup runs before serving traffic
- **WHEN** the backend process starts with stale queued, processing, or failed community-paper tasks still present
- **THEN** it SHALL mark active interrupted `translation_tasks` as failed and clean local task artifacts
- **AND** it SHALL purge eligible non-success community-paper records in the local database while keeping successful and public papers untouched
- **AND** later API traffic SHALL observe the cleaned state without requiring a manual cleanup call.

#### Scenario: Startup purge is explicitly disabled
- **WHEN** `ENABLE_STALE_PAPER_PURGE` is set to a disabled value
- **THEN** startup reconciliation SHALL skip non-success paper purge operations
- **AND** it SHALL continue to report cleanup execution status without deleting paper records.

### Requirement: Non-success community papers are deleted comprehensively
The backend SHALL remove purge-eligible non-success community papers from all related paper-facing local database tables and local task artifacts, not only from the primary `papers` row.

#### Scenario: Purge-eligible non-success paper has related moderation and reaction data
- **WHEN** a purge-eligible non-success community paper is purged during startup or admin cleanup
- **THEN** the backend SHALL delete related `comments`, `reports`, `moderation_actions`, `paper_assets`, `paper_likes`, `paper_favorites`, related `translation_tasks`, and the `papers` row from the local database
- **AND** it SHALL also delete the corresponding local task artifact directories and `community_papers/<paper_id>` folder.

#### Scenario: Public paper remains available after restart cleanup
- **WHEN** startup or admin cleanup runs
- **THEN** non-success papers that are currently public SHALL NOT be purged by default
- **AND** their reader assets and metadata SHALL remain queryable via normal paper APIs.

### Requirement: In-flight translation tasks fail cleanly after restart
The backend SHALL treat queued/pending/processing translation tasks as interrupted work on restart and convert them to a terminal failed state.

#### Scenario: Restart interrupts an active translation
- **WHEN** the backend restarts while a persisted translation task is in `queued`, `pending`, or `processing`
- **THEN** startup reconciliation SHALL mark the task `failed`, set restart-interruption diagnostics, and clean corresponding local artifacts
- **AND** related `papers` rows that still point to the interrupted task SHALL be updated away from active states.

### Requirement: Community agent API supports deep research execution mode
The community agent API SHALL support a deep research execution mode that returns async progress and a final long-form cited report.

#### Scenario: Client starts a deep research run
- **WHEN** the client requests a community agent run in deep research mode
- **THEN** the API SHALL acknowledge that mode explicitly
- **AND** it SHALL expose progress and final result retrieval compatible with long-running execution.

#### Scenario: Deep research result returns report-oriented payloads
- **WHEN** a deep research run completes
- **THEN** the final run payload SHALL include the long-form report body and citations
- **AND** the client SHALL not need to reconstruct the report from scattered event fragments alone.

### Requirement: Paper detail and agent payloads expose stable reader anchors
The API SHALL expose enough metadata for the frontend to map copilot citations and actions onto stable paper-reader locations.

#### Scenario: Paper detail response includes anchor-ready reader metadata
- **WHEN** the client requests a paper detail payload for a readable paper
- **THEN** the response SHALL include stable reader anchor identifiers for readable sections or segments
- **AND** those identifiers SHALL remain usable by the UI for scroll-and-highlight interactions.

#### Scenario: Assistant citation references a current-paper anchor
- **WHEN** the community agent cites or points into the current paper
- **THEN** the run metadata SHALL be allowed to include the current `paper_id` and a stable `anchor_id`
- **AND** the frontend SHALL not need to infer that mapping from raw assistant text alone.

### Requirement: Agent run context supports highlighted reader selection metadata
The API SHALL accept and propagate structured highlighted-reader selection context for paper-detail copilot runs.

#### Scenario: Paper-detail run includes highlighted selection payload
- **WHEN** the paper-detail client submits an agent run with `context.reader_selection`
- **THEN** the API contract SHALL accept `reader_selection.text`, optional `reader_selection.anchor_id`, and optional `reader_selection.mode`
- **AND** the runtime SHALL retain that context for planner/final answer grounding without requiring user-visible prompt rewriting.

### Requirement: Community paper APIs retry transient database transport failures
Community paper service-layer API paths SHALL retry transient local database or driver-level transport failures before returning an error.

#### Scenario: Transient timeout recovers within retry budget
- **WHEN** a local database operation fails with transient transport or timeout exceptions
- **THEN** the API layer SHALL retry with bounded backoff
- **AND** it SHALL return success if a later retry succeeds within the configured retry budget.

#### Scenario: Transient timeout persists beyond retry budget
- **WHEN** retries are exhausted for transient transport or timeout exceptions
- **THEN** the API layer SHALL surface the final failure
- **AND** it SHALL not loop indefinitely.

### Requirement: Authentication API issues local sessions after NiuTrans verification
The backend SHALL expose authentication endpoints that verify credentials against the NiuTrans login API and then establish the current application's own authenticated session.

#### Scenario: Local login succeeds through upstream verification
- **WHEN** the client submits valid credentials to the current application's login endpoint
- **THEN** the backend SHALL verify those credentials through the NiuTrans login API
- **AND** it SHALL upsert the mapped local user record
- **AND** it SHALL return a local authenticated session or JWT for subsequent project API calls.

#### Scenario: Login response follows a stable auth contract
- **WHEN** the backend returns a successful login response
- **THEN** the payload SHALL include `access_token`, `token_type`, `expires_in`, and a normalized local `user` object
- **AND** clients SHALL NOT need to inspect raw upstream NiuTrans token fields to bootstrap the session.

#### Scenario: Session bootstrap returns the current local user
- **WHEN** the client calls `GET /api/auth/me` with a valid local token
- **THEN** the API SHALL return the normalized local authenticated user payload
- **AND** it SHALL be the canonical frontend bootstrap endpoint for restoring auth state.

#### Scenario: Local logout clears current application auth state
- **WHEN** the client requests logout through the current application's auth API
- **THEN** the backend and frontend SHALL clear the current application's local session state
- **AND** later protected API calls SHALL require a fresh local login.

#### Scenario: Auth failures use stable error codes
- **WHEN** login or session validation fails
- **THEN** the API SHALL return a machine-readable auth error code such as invalid credentials, invalid session, forbidden, or upstream unavailable
- **AND** the response SHALL still include a user-facing message.

### Requirement: Paper detail response exposes translated-PDF interaction metadata
The API SHALL expose translated-PDF reader metadata required for interactive in-document operations in paper detail.

#### Scenario: Paper detail payload includes embeddable translated-PDF metadata
- **WHEN** a paper has translated PDF assets available
- **THEN** the paper-detail response SHALL include a translated-PDF reader URL suitable for inline embedding
- **AND** it SHALL include metadata required by the UI to attempt stable location mapping.

#### Scenario: Translated-PDF locator metadata is unavailable
- **WHEN** translated-PDF assets exist but locator metadata is not ready
- **THEN** the API SHALL explicitly indicate locator unavailability
- **AND** the response SHALL remain backward-compatible for non-interactive PDF viewing.

### Requirement: Agent run context supports translated-PDF locator selection fields
The API SHALL accept optional translated-PDF locator fields in `context.reader_selection` while preserving existing selection fields.

#### Scenario: Paper-detail run includes translated-PDF locator context
- **WHEN** the paper-detail client submits `context.reader_selection` from translated-PDF mode
- **THEN** the API SHALL accept existing fields (`text`, optional `anchor_id`, optional `mode`) plus optional locator fields
- **AND** runtime orchestration SHALL preserve these fields for planner/final answer grounding.

#### Scenario: Legacy clients submit reader_selection without locator fields
- **WHEN** clients only send current `reader_selection` fields
- **THEN** the API SHALL process the request without contract breakage
- **AND** behavior SHALL remain compatible with existing HTML-reader workflows.

### Requirement: Citation-target metadata supports translated-PDF location resolution
The API SHALL support citation/action metadata that can target translated-PDF positions for current-paper navigation.

#### Scenario: Assistant references a translated-PDF location in current paper
- **WHEN** an assistant run emits current-paper citation/action metadata for translated-PDF mode
- **THEN** metadata SHALL be able to carry stable location identifiers usable by the UI
- **AND** unresolved identifiers SHALL be distinguishable from successfully resolved targets.

### Requirement: Admin curation API supports single and batch community intake
The backend SHALL expose admin-only API contracts for community curation intake via both `arXiv ID` submission and archive upload, including batch submission support and per-item status tracking.

#### Scenario: Admin submits one or more arXiv ids for community curation
- **WHEN** an authenticated local admin submits one or more `arXiv ID`s to the admin curation API
- **THEN** the API SHALL accept the submission as a tracked curation job or batch
- **AND** it SHALL return enough per-item identifiers or status metadata for the admin UI to monitor progress.

#### Scenario: Admin uploads one or more archives for community curation
- **WHEN** an authenticated local admin uploads one or more TeX-containing archives to the admin curation API
- **THEN** the API SHALL accept the upload as a tracked curation job or batch
- **AND** it SHALL preserve per-item status reporting across metadata extraction, translation, structured insight generation, and publication.

### Requirement: Admin curation APIs require local admin role
The backend SHALL require the current local admin role for community curation write actions.

#### Scenario: Non-admin requests admin curation write API
- **WHEN** an authenticated non-admin user calls an admin curation write endpoint
- **THEN** the API SHALL reject the request with a forbidden response
- **AND** it SHALL not start the curation pipeline.

### Requirement: Admin paper deletion API hard-deletes community papers
The backend SHALL expose an admin-only community-paper deletion API that immediately removes the paper from public product surfaces and then completes a persistent asynchronous hard delete across local database rows, local filesystem assets, caches, and search/index artifacts.

#### Scenario: Admin deletes a community paper
- **WHEN** an authenticated local admin calls the community-paper delete API for an existing paper
- **THEN** the backend SHALL make that paper immediately unavailable to homepage feed, search, and detail reads
- **AND** it SHALL persist a background delete job that removes the paper row, related paper-facing local rows, structured insights, corresponding community asset directories, derived preview/translation/source artifacts, and related cache/index entries
- **AND** subsequent community reads for that paper SHALL fail as a missing paper.

#### Scenario: A hard-delete cleanup step fails
- **WHEN** a persisted community-paper hard-delete job encounters a cleanup failure
- **THEN** the system SHALL keep retrying that delete job automatically until cleanup completes
- **AND** it SHALL not restore the paper to public visibility while retries continue.

#### Scenario: Service restarts during hard delete
- **WHEN** the service restarts while a community-paper hard-delete job is unfinished
- **THEN** startup reconciliation SHALL resume the persisted delete job
- **AND** retries SHALL continue until the hard delete completes.

### Requirement: Hidden community-agent mode blocks direct product access
The backend SHALL reject direct product access to community-agent routes while the current product mode keeps the public agent surface hidden.

#### Scenario: Authenticated user calls community-agent run APIs in hidden mode
- **WHEN** an authenticated user, including an admin, calls the community-agent product APIs while hidden mode is active
- **THEN** the API SHALL reject the request instead of starting a visible product agent run
- **AND** the hidden-mode contract SHALL still preserve the underlying code assets for future restoration.

### Requirement: Paper detail API exposes similar-paper recommendations for public community papers
The backend SHALL expose a public paper-detail recommendation API for similar papers under `/api/papers/{paper_id}/similar`.

#### Scenario: Newly curated papers read persisted recommendations
- **WHEN** a client requests similar papers for a public community paper that has persisted similar recommendations
- **THEN** the backend SHALL return the stored recommendation package directly
- **AND** it SHALL not re-run live candidate retrieval during that read.

#### Scenario: Persisted recommendations preserve ranking and routing metadata
- **WHEN** the backend returns persisted similar recommendations
- **THEN** the API SHALL preserve the stored display order and recommendation fields including `arxiv_id`, title, abstract, `arxiv_url`, `community_paper_id`, and `link_type`
- **AND** the client SHALL still be able to deep-link into the community detail page when `community_paper_id` exists.

#### Scenario: Legacy papers are not backfilled by this change
- **WHEN** a public community paper predates this persisted recommendation pipeline and has no stored similar recommendations
- **THEN** the backend SHALL not silently trigger a new live-retrieval generation path as part of this change
- **AND** it MAY return an empty or unavailable recommendation state for that paper.

### Requirement: Public API metadata uses the current product brand
The API SHALL expose outward-facing service metadata using the current PaperX product brand.

#### Scenario: Root metadata reflects the current brand
- **WHEN** a client requests the API root endpoint
- **THEN** the response message and descriptive service metadata SHALL identify the backend as PaperX rather than legacy LaTeXTrans branding.

### Requirement: Ordinary Task Download Delivery Supports Signed COS URLs
When ordinary-task object storage mode is enabled, download-class endpoints SHALL deliver ordinary-task artifacts through signed COS URLs while preserving the existing API entry points.

#### Scenario: COS mode translated PDF download uses signed URL
- **WHEN** `STORAGE_BACKEND_MODE=cos` and a completed ordinary task requests `GET /download/{task_id}/pdf`
- **THEN** the backend SHALL resolve the durable translated PDF object from the stored output manifest
- **AND** the response SHALL deliver the file through a short-lived signed COS URL with attachment semantics

#### Scenario: COS mode translated source download uses signed URL
- **WHEN** `STORAGE_BACKEND_MODE=cos` and a completed ordinary task requests `GET /download/{task_id}/source`
- **THEN** the backend SHALL resolve the durable translated-source archive from the stored output manifest
- **AND** the response SHALL deliver the file through a short-lived signed COS URL with attachment semantics

#### Scenario: COS mode logs download uses signed URL
- **WHEN** `STORAGE_BACKEND_MODE=cos` and an ordinary task requests `GET /download/{task_id}/logs`
- **THEN** the backend SHALL resolve an available durable log artifact from the stored output manifest
- **AND** the response SHALL deliver the file through a short-lived signed COS URL with attachment semantics

### Requirement: Community paper detail bootstrap payload remains lightweight
The web API SHALL keep community paper detail responses lightweight by returning reader bootstrap metadata and asset locators instead of embedding large reader bodies directly in the base detail response.

#### Scenario: Detail response for a preview-ready paper
- **WHEN** a client requests `GET /api/papers/{paper_id}` for a paper with translated preview assets
- **THEN** the API SHALL return metadata, reader state, and stable locators for preview/PDF assets
- **AND** it SHALL NOT require the base detail response to inline the full preview HTML body.

#### Scenario: Dedicated reader asset fetch remains available
- **WHEN** the client needs the actual preview HTML or PDF asset after loading paper detail bootstrap data
- **THEN** the API contract SHALL provide a dedicated asset-fetch path or signed asset locator
- **AND** the client SHALL not need to reconstruct asset paths from raw database fields.

### Requirement: Community asset APIs support object-storage delivery with local fallback
Community preview and download APIs SHALL support canonical assets that live either on object storage or on local disk.

#### Scenario: Object-storage-backed translated PDF is requested
- **WHEN** a client requests a translated community PDF whose canonical asset backend is object storage
- **THEN** the API SHALL resolve that asset through a supported delivery mode such as redirect, signed URL, or first-party proxy response
- **AND** the client-facing route contract SHALL remain stable.

#### Scenario: Local-disk-backed translated PDF is requested
- **WHEN** a client requests a translated community PDF whose canonical asset backend is local disk
- **THEN** the API SHALL continue serving that file through the existing local file response path
- **AND** local development SHALL remain functional without object storage.

### Requirement: Admin curation history API lists retained curation jobs
The backend SHALL expose an admin-only API for querying retained admin curation jobs independent of public paper visibility.

#### Scenario: Admin lists retained curation jobs
- **WHEN** an authenticated local admin requests the admin curation history API
- **THEN** the API SHALL return retained curation jobs across queued, processing, completed, and failed states
- **AND** each item SHALL include identifiers such as `job_id`, `batch_id`, `task_id`, `paper_id`, status fields, timestamps, and error context.

#### Scenario: Admin filters retained curation jobs
- **WHEN** an authenticated local admin requests the admin curation history API with a status filter or simple search value
- **THEN** the API SHALL support filtering by curation status
- **AND** it SHALL support simple search by `arXiv ID` or `batch_id`.

#### Scenario: Non-admin requests retained curation history
- **WHEN** an authenticated non-admin user requests the admin curation history API
- **THEN** the API SHALL reject the request with a forbidden response
- **AND** it SHALL not disclose retained curation job metadata.

### Requirement: Admin curation job delete API hard-deletes retained records
The backend SHALL expose an admin-only API that permanently deletes failed or completed admin curation records and their retained artifacts.

#### Scenario: Admin deletes a failed retained curation record
- **WHEN** an authenticated local admin calls the curation-job delete API for a failed retained job
- **THEN** the backend SHALL permanently delete the curation-job row, retained translation-task row, and retained failed-task artifacts for that job
- **AND** subsequent admin history reads for that job SHALL fail as missing.

#### Scenario: Admin deletes a completed retained curation record
- **WHEN** an authenticated local admin calls the curation-job delete API for a completed job that published a paper
- **THEN** the backend SHALL reuse the existing admin community-paper hard-delete flow for the published paper and its assets
- **AND** it SHALL also permanently delete the linked curation-job history row.

#### Scenario: Non-admin requests curation-job hard delete
- **WHEN** an authenticated non-admin user calls the curation-job delete API
- **THEN** the API SHALL reject the request with a forbidden response
- **AND** it SHALL not start any delete workflow.

### Requirement: Admin curation history batch delete API reports per-job outcomes
The web API SHALL provide an authenticated admin-only batch delete endpoint for curation history records that returns per-job hard-delete outcomes.

#### Scenario: Admin batch delete succeeds for all selected jobs
- **WHEN** an admin submits one or more valid curation job ids to the batch delete endpoint
- **THEN** the API SHALL hard-delete each job using the same logic as the single-delete endpoint
- **AND** the response SHALL include the deleted job ids with a zero failed-count result.

#### Scenario: Admin batch delete partially fails
- **WHEN** at least one submitted curation job id cannot be deleted
- **THEN** the API SHALL continue attempting the remaining submitted job ids
- **AND** the response SHALL include separate success and failure entries so the client can keep failed items selected for retry.

### Requirement: Daily LaTeX Translation Quota
The web API SHALL enforce an independent local daily LaTeX translation quota for authenticated non-admin users. The default quota SHALL be 3 items per authenticated non-admin user per UTC+8 natural day. Authenticated users whose resolved roles include `admin` SHALL bypass only this local daily LaTeX quota.

#### Scenario: Authenticated non-admin user starts an ordinary arXiv translation
- **WHEN** an authenticated non-admin user starts translation work for one arXiv ID
- **AND** the user has at least one remaining local LaTeX quota item for the current UTC+8 day
- **THEN** the API SHALL reserve one local LaTeX quota item before accepting translation work
- **AND** the accepted task SHALL proceed without deducting NiuTrans PDF direct-translation credits.

#### Scenario: Authenticated non-admin user starts an ordinary uploaded-source translation
- **WHEN** an authenticated non-admin user starts translation work for one uploaded LaTeX file, source folder, or source archive
- **AND** the user has at least one remaining local LaTeX quota item for the current UTC+8 day
- **THEN** the API SHALL reserve one local LaTeX quota item before accepting translation work
- **AND** the accepted task SHALL proceed without deducting NiuTrans PDF direct-translation credits.

#### Scenario: Local daily quota is exhausted for a non-admin user
- **WHEN** an authenticated non-admin user has no remaining local LaTeX quota items for the current UTC+8 day
- **AND** the user attempts to start quota-managed LaTeX translation work
- **THEN** the API SHALL return a quota-exceeded error before creating or enqueuing new translation work
- **AND** the error payload SHALL include the quota limit, used count, remaining count, requested count, and reset date.

#### Scenario: Admin user starts quota-managed LaTeX translation work
- **WHEN** an authenticated user whose resolved roles include `admin` attempts to start quota-managed LaTeX translation work
- **THEN** the API SHALL accept the work without reserving or incrementing local daily LaTeX quota usage
- **AND** the task SHALL remain subject to existing upstream/provider quotas, queue limits, active-task limits, batch-size limits, and task execution safeguards.

#### Scenario: Daily quota refreshes
- **WHEN** the UTC+8 natural day changes
- **THEN** a non-admin user's local LaTeX quota usage SHALL reset for the new quota date
- **AND** prior-day usage SHALL NOT reduce the new day's remaining count.

#### Scenario: Failed accepted non-admin task does not refund quota
- **WHEN** non-admin translation work has already been accepted and later fails, is cancelled, or fails compilation
- **THEN** the local LaTeX quota item reserved for that accepted work SHALL remain consumed
- **AND** NiuTrans PDF direct-translation credits SHALL remain unaffected.

### Requirement: Translation Quota Snapshot API
The web API SHALL provide an authenticated quota snapshot that separates local LaTeX quota from NiuTrans PDF direct-translation credits.

#### Scenario: Authenticated non-admin user requests quota snapshot
- **WHEN** an authenticated non-admin user requests the current quota snapshot through login, session bootstrap, or a dedicated quota endpoint
- **THEN** the API SHALL return local LaTeX quota fields including limit, used, remaining, quota date, and reset timezone
- **AND** it SHALL return PDF direct-translation credit fields based on NiuTrans `unusedNumIntegral` when available
- **AND** the response SHALL make clear that PDF direct-translation credits are积分 rather than a `remaining/limit` daily quota.

#### Scenario: Authenticated admin user requests quota snapshot
- **WHEN** an authenticated user whose resolved roles include `admin` requests the current quota snapshot through login, session bootstrap, or a dedicated quota endpoint
- **THEN** the API SHALL return a local LaTeX quota snapshot that indicates the admin bypass or unlimited local quota state
- **AND** the response SHALL NOT present the admin user as blocked by local daily LaTeX quota usage
- **AND** PDF direct-translation credit fields SHALL remain based on the user's NiuTrans balance snapshot when available.

#### Scenario: NiuTrans balance is unavailable
- **WHEN** no valid NiuTrans `unusedNumIntegral` snapshot is available
- **THEN** the API SHALL still return the local LaTeX quota snapshot
- **AND** it SHALL mark the PDF direct-translation credit status as unavailable or stale instead of failing the entire quota response.

### Requirement: Web Translation APIs Default To Origin CLI Parity
The web API SHALL start translation tasks with the origin CLI parity kernel unless a future approved spec introduces another default.

#### Scenario: Uploaded file translation uses parity
- **WHEN** a user starts translation for an uploaded archive or source directory through the web API
- **THEN** the task SHALL run with `origin_cli_parity` as its effective translation core.

#### Scenario: Direct arXiv translation uses parity
- **WHEN** a user starts translation from an arXiv id through the web API
- **THEN** the task SHALL run with `origin_cli_parity` as its effective translation core after source download and extraction.

#### Scenario: Effective config is visible
- **WHEN** a web API translation task captures its runtime config
- **THEN** the snapshot SHALL include the effective parity mode
- **AND** it SHALL indicate that modern backend translation systems are not invoked for that task.

### Requirement: Community paper list API supports paginated public feed reads
The public community paper list API MUST support paginated reads so clients can incrementally load the feed without requesting the entire corpus.

#### Scenario: Client requests the first latest-feed page
- **WHEN** a client calls `GET /api/papers` with `sort=latest`, `limit`, and `offset=0`
- **THEN** the API MUST return `items`, `total`, `offset`, `limit`, `has_more`, and `next_offset`
- **AND** the payload MUST contain only that page's items rather than the whole public list.

#### Scenario: First latest-feed page is cacheable
- **WHEN** the client requests the public latest feed with an empty query and `offset=0`
- **THEN** the backend MAY serve a short-lived cached first-page payload
- **AND** later public-paper mutations MUST invalidate that cache before the next response is generated.

