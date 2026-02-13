# file-management Specification

## Purpose
定义文件管理规范，包括上传、下载、arXiv 源码获取及多格式压缩包支持。
## Requirements
### Requirement: File Upload Handling
The system SHALL accept LaTeX source files via HTTP upload for translation processing.

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

### Requirement: arXiv Source Retrieval
The system SHALL download LaTeX source files from arXiv when provided with a valid arXiv ID.

#### Scenario: Valid arXiv ID provided
- **WHEN** user submits arXiv ID (e.g., "2508.18791") via `POST /arxiv`
- **THEN** the system downloads the `.tar.gz` source, extracts it to `data/uploads/{task_id}/`, and returns the task ID

#### Scenario: Invalid arXiv ID rejected
- **WHEN** user submits malformed arXiv ID (e.g., "invalid-id")
- **THEN** the system returns HTTP 400 with error message "Invalid arXiv ID format"

#### Scenario: arXiv download failure
- **WHEN** arXiv API is unreachable or paper ID doesn't exist
- **THEN** the system returns HTTP 502 with error message "Failed to download from arXiv: {reason}"

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

