# file-management Specification Delta

## ADDED Requirements

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
