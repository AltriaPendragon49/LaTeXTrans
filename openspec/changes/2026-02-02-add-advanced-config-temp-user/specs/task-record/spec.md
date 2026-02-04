# task-record Specification Delta

## Purpose
扩展任务记录结构，包含完整的高级配置信息。

## MODIFIED Requirements

### Requirement: Task Data Structure (from web-api)
任务记录 SHALL 包含创建时的高级配置快照。

#### Scenario: 创建任务时保存配置
- **WHEN** 翻译任务创建成功
- **THEN** 任务记录包含 `advanced_config` 字段
- **AND** 配置值为创建时的实际值（非默认值覆盖）

#### Scenario: 查询任务返回配置
- **WHEN** 前端请求 `/api/task/{task_id}`
- **THEN** 响应包含任务基本信息和 advanced_config
- **AND** 配置格式与创建时一致

### Requirement: Task Status API (from web-api)
任务状态 API SHALL 返回完整任务信息。

#### Scenario: 轮询任务状态
- **WHEN** 前端轮询任务状态
- **THEN** 响应包含 status, progress, message, advanced_config

## ADDED Requirements

### Requirement: Source Type Extension
任务记录 SHALL 支持新的 `folder_upload` 来源类型。

#### Scenario: 记录目录上传来源
- **WHEN** 任务通过拖拽目录创建
- **THEN** source_type = "folder_upload"

#### Scenario: 记录校验信息
- **WHEN** folder_upload 任务创建
- **THEN** 任务记录包含 latex_validation 信息
- **AND** 包含 main_file, tex_files, warnings

### Requirement: Configuration Snapshot
任务配置 SHALL 为创建时的快照，不随后续更改变化。

#### Scenario: 配置不可变
- **WHEN** 任务创建成功后
- **THEN** advanced_config 不可修改
- **AND** 反映创建时的实际配置

## Cross-References
- 修改: web-api (任务管理)
- 关联: advanced-config (配置结构)
- 关联: folder-upload (来源类型)
