# file-management Specification

## Purpose
定义文件管理核心规范。该规范涵盖了系统处理文件的各个生命周期阶段，包括从本地客户端上传 LaTeX 源码及相关依赖文件（如图片、样式表等）、通过 arXiv API 自动下载并提取指定论文的 `.tar.gz` 源码压缩包、支持 `zip`、`tar.gz` 及 `rar` 等多种压缩格式的解析与存储、在编译翻译流程结束后提供目标 PDF 和处理后源码及关联文件的下载，并在云端进行安全和结构化的文件缓存与调度，以保证高效的后续任务复用与存储。
## Requirements
### Requirement: File Upload Handling
The system SHALL accept LaTeX source files via HTTP upload for translation processing.  
When ordinary-task object storage mode is enabled, the uploaded source SHALL be durably persisted to COS while local upload directories remain temporary runtime cache only.

#### Scenario: Upload single .tex file
- **WHEN** user uploads a `.tex` file via `POST /upload`
- **THEN** the system generates a unique task ID, stores the file in `data/uploads/{task_id}/`, and returns `{task_id, status: "pending"}`

#### Scenario: Upload .zip archive
- **WHEN** user uploads a `.zip` file containing LaTeX source
- **THEN** the system extracts the archive to `data/uploads/{task_id}/`, validates the presence of `.tex` files, and returns the task ID

#### Scenario: Invalid file type rejected
- **WHEN** user uploads a file with unsupported extension (not `.tex` or `.zip`)
- **THEN** the system returns HTTP 400 with error message "Unsupported file type"

#### Scenario: File size limit enforcement
- **WHEN** user uploads a file larger than 50MB
- **THEN** the system returns HTTP 413 with error message "File too large (max 50MB)"

#### Scenario: Ordinary-task upload is durably persisted to COS
- **WHEN** `STORAGE_BACKEND_MODE=cos` and an ordinary-task upload passes LaTeX validation
- **THEN** the source tree SHALL be durably written to COS under the logical `data/uploads/...` task location
- **AND** the task record SHALL keep a storage-resolvable `source_path`
- **AND** the local upload directory MAY be deleted after durable persistence succeeds

### Requirement: arXiv Source Retrieval
The system SHALL download LaTeX source files from arXiv when provided with a valid arXiv ID.  
When ordinary-task object storage mode is enabled, the downloaded source SHALL be durably persisted to COS and treated as the authoritative source copy.

#### Scenario: Valid arXiv ID provided
- **WHEN** user submits arXiv ID (e.g., "2508.18791") via `POST /arxiv`
- **THEN** the system downloads the `.tar.gz` source, extracts it to `data/uploads/{task_id}/`, and returns the task ID

#### Scenario: Invalid arXiv ID rejected
- **WHEN** user submits malformed arXiv ID (e.g., "invalid-id")
- **THEN** the system returns HTTP 400 with error message "Invalid arXiv ID format"

#### Scenario: arXiv download failure
- **WHEN** arXiv API is unreachable or paper ID doesn't exist
- **THEN** the system returns HTTP 502 with error message "Failed to download from arXiv: {reason}"

#### Scenario: Ordinary-task arXiv source is durably persisted to COS
- **WHEN** `STORAGE_BACKEND_MODE=cos` and an arXiv ordinary task finishes source download successfully
- **THEN** the source tree SHALL be durably written to COS under the logical `data/uploads/...` location
- **AND** later translation runs SHALL be able to rehydrate the source from COS even if no long-lived local copy remains

### Requirement: File Download Delivery
The system SHALL provide translated output files for download via HTTP endpoints.

#### Scenario: Download translated PDF
- **WHEN** user requests `GET /download/{task_id}/pdf` for a completed task
- **THEN** the system streams the PDF file with `Content-Disposition: attachment; filename="{project_name}.pdf"`

#### Scenario: Download translated source
- **WHEN** user requests `GET /download/{task_id}/source` for a completed task
- **THEN** the system packages all `.tex` files into a `.zip` archive and streams it with appropriate headers

#### Scenario: Download before completion
- **WHEN** user requests download for a task with status "pending" or "processing"
- **THEN** the system returns HTTP 409 with error message "Translation not yet completed"

#### Scenario: Download nonexistent task
- **WHEN** user requests download for an invalid task ID
- **THEN** the system returns HTTP 404 with error message "Task not found"

### Requirement: Multi-Format Archive Upload
后端 SHALL 支持多种压缩格式的 LaTeX 工程上传。

#### Scenario: Upload TAR.GZ file
- **WHEN** user uploads a `.tar.gz` or `.tgz` file containing LaTeX source
- **THEN** the system extracts the archive using tarfile to `data/uploads/{task_id}/`
- **AND** validates the presence of `.tex` files

#### Scenario: Upload RAR file
- **WHEN** user uploads a `.rar` file containing LaTeX source
- **THEN** the system extracts the archive using rarfile to `data/uploads/{task_id}/`
- **AND** validates the presence of `.tex` files
- **IF** unrar is not installed
- **THEN** the system returns HTTP 400 with error "RAR format not supported, please use ZIP or TAR.GZ"

### Requirement: LaTeX Directory Validation
后端 SHALL 在创建翻译任务前校验 LaTeX 目录结构。

#### Scenario: Detect main entry file
- **WHEN** directory contains `.tex` files
- **THEN** system detects main entry file
- **AND** prioritizes `main.tex` or files containing `\documentclass`
- **IF** no clear main entry found
- **THEN** uses the first `.tex` file and returns a warning

#### Scenario: No tex files detected
- **WHEN** uploaded archive contains no `.tex` files
- **THEN** system returns HTTP 400 with error "No LaTeX files detected in archive"

### Requirement: Folder Upload Source Type
任务记录 SHALL 支持 `folder_upload` 来源类型。

#### Scenario: Record folder upload source
- **WHEN** task is created via drag-and-drop upload
- **THEN** task record contains `source_type = "folder_upload"`
- **AND** includes `latex_validation` information (main_file, tex_files, warnings)

### Requirement: Upload Storage Structure
arXiv 论文上传目录 SHALL 以 arxiv_id 为 key 存储，支持跨任务共享。

#### Scenario: arXiv 论文下载存储
- **WHEN** 用户请求下载 arXiv 论文（arxiv_id）
- **THEN** 系统将源文件存储到 `uploads/arxiv_{arxiv_id}/` 目录
- **AND** 任务的 source_path 指向该共享目录

#### Scenario: 重复下载同一论文
- **WHEN** 用户请求下载已存在的 arXiv 论文
- **AND** `uploads/arxiv_{arxiv_id}/` 目录已存在
- **THEN** 系统跳过下载，source_path 直接指向已有目录
- **AND** Load 操作秒级完成

#### Scenario: 文件上传推断 arxiv_id
- **WHEN** 用户上传 .zip/.tar.gz/.rar 文件
- **AND** 系统从目录名或文件名推断出 arxiv_id
- **AND** `uploads/arxiv_{arxiv_id}/` 目录已存在
- **THEN** source_path 指向已有共享目录，避免重复存储

#### Scenario: 无法推断 arxiv_id 的上传
- **WHEN** 用户上传文件且无法推断 arxiv_id
- **THEN** 系统保持 `uploads/{task_id}/` 存储结构不变

### Requirement: Upload Deletion Protection
系统 SHALL 在删除历史任务时保留 Upload 目录内容。

#### Scenario: 删除任务保留 uploads
- **WHEN** 用户删除翻译任务记录
- **THEN** 系统删除 `outputs/{task_id}/` 和 `terms/{task_id}/` 目录
- **AND** 系统 SHALL NOT 删除 uploads 相关目录
- **AND** uploads 内容作为缓存保留供未来使用

### Requirement: Source PDF Preview Compatibility
系统 SHALL 在共享 Upload 目录下正确缓存编译的源 PDF。

#### Scenario: 编译源 PDF 缓存
- **WHEN** 系统编译源 tex 生成预览 PDF
- **THEN** 缓存文件命名为 `source_compiled.pdf`（不含 task_id）
- **AND** 同一 uploads 目录的后续请求直接使用缓存

### Requirement: Upload Failure Cleanup
系统 SHALL 在上传失败时自动清理已创建的临时目录，避免垃圾缓存累积。

#### Scenario: 上传文件格式无效
- **WHEN** 用户上传的文件格式无效（损坏的 ZIP、缺少 RAR 工具等）
- **THEN** 系统返回错误响应
- **AND** 系统 SHALL 自动删除已创建的临时上传目录

#### Scenario: LaTeX 项目校验失败
- **WHEN** 用户上传的文件解压成功但 LaTeX 项目校验失败
- **THEN** 系统返回校验错误信息
- **AND** 系统 SHALL 自动删除已创建的临时上传目录

#### Scenario: 上传成功保留目录
- **WHEN** 用户上传的文件格式有效且 LaTeX 校验通过
- **THEN** 系统保留上传目录
- **AND** 系统 SHALL NOT 删除该目录

### Requirement: Failed Output Quarantine
The system SHALL quarantine failed task outputs into `data/failed_tasks`, and SHALL move only `outputs/{task_id}` artifacts.  
The system SHALL NOT move `terms/{task_id}` and SHALL NOT move or delete upload cache artifacts as part of this quarantine behavior.  
After quarantine, the system SHALL perform scoped replay-evidence reference rewrite so replay references remain reachable from the new quarantine root.

#### Scenario: Quarantine Failed Task Output
- **WHEN** task status is updated to `failed` or `failed_compilation`
- **THEN** the system moves `data/outputs/{task_id}` to `data/failed_tasks/{task_id}`
- **AND** the quarantined files remain available for debugging.

#### Scenario: Scoped replay reference rewrite after quarantine
- **WHEN** output quarantine succeeds
- **THEN** replay references under old task root (`.../outputs/{task_id}/...`) are rewritten to the new failed root
- **AND** rewrite applies only to scoped evidence fields (`replay_bundle_ref`, `main_tex_path`, and bundle keys ending `_path`/`_ref` when in-scope)
- **AND** unrelated absolute paths MUST remain unchanged.

#### Scenario: Evidence chain warning without status mutation
- **WHEN** rewritten `replay_bundle_ref` or `main_tex_path` is unreachable
- **THEN** the system writes `evidence_chain_broken=true` and a warning event in task log
- **AND** task terminal status semantics remain unchanged.

### Requirement: Runtime Task Config Snapshot Storage
The system SHALL persist runtime translation config snapshots under `data/task_configs` when config capture is enabled.  
The snapshot format SHALL remain compatible with config validator tooling and SHALL NOT persist raw API keys.

#### Scenario: Capture Task Config Snapshot
- **WHEN** translation initialization builds `advanced_config`, `agent_config`, and `llm_config`
- **AND** `ENABLE_TASK_CONFIG_CAPTURE` is enabled
- **THEN** the system writes a snapshot file to `data/task_configs/config_<task8>_<timestamp>.json`

#### Scenario: Disabled Config Capture
- **WHEN** `ENABLE_TASK_CONFIG_CAPTURE` is disabled
- **THEN** the system skips writing config snapshots
- **AND** translation continues normally

#### Scenario: Config Capture Write Failure
- **WHEN** config snapshot write fails due to filesystem/runtime error
- **THEN** the system logs a warning
- **AND** translation MUST continue without failing the task

#### Scenario: API Key Masking
- **WHEN** `llm_config` contains an API key
- **THEN** snapshot output stores masked key metadata only
- **AND** raw API key value SHALL NOT be persisted

### Requirement: Ordinary Task Durable Output Persistence
When ordinary-task object storage mode is enabled, the system SHALL persist translation outputs to COS as the durable source of truth and SHALL keep local output directories only as temporary runtime cache.

#### Scenario: Successful translation output is durably persisted
- **WHEN** an ordinary task reaches `completed` or `completed_with_warnings` in COS mode
- **THEN** the output tree SHALL be durably written to COS under the logical `data/outputs/{task_id}` location
- **AND** the system SHALL persist an output manifest that identifies translated PDF, translated-source archive, terminology CSV, and available log files for later retrieval
- **AND** the local runtime output directory MAY be deleted after durable persistence succeeds

#### Scenario: Failed translation output still preserves durable artifacts
- **WHEN** an ordinary task reaches a terminal failure state in COS mode and output artifacts exist
- **THEN** the available output files SHALL be durably written to COS under the logical `data/outputs/{task_id}` location before local cache cleanup
- **AND** later log retrieval SHALL NOT require a pre-existing long-lived local output directory

#### Scenario: Ordinary task rehydrates source from COS for runtime execution
- **WHEN** an ordinary task in COS mode starts translation without a reusable local source directory
- **THEN** the backend SHALL materialize the source tree from COS into a temporary local runtime directory
- **AND** the translation runtime SHALL use that hydrated local directory without changing the durable `source_path`

