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

