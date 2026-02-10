# upload-translation-fix Specification

## Purpose
TBD - created by archiving change add-multi-user-support. Update Purpose after archive.
## Requirements
### Requirement: Upload Config Preservation
前端 SHALL 在上传文件后保留用户的翻译配置，不重置为默认值。

#### Scenario: 上传文件后保留用户配置
- **WHEN** 已登录用户在 Settings 中保存了自定义配置
- **AND** 用户在 Dashboard 上传文件
- **THEN** 上传成功后 Advanced Configuration 仍显示用户保存的配置
- **AND** 系统使用 `resetTranslationState()` 而非 `reset()` 重置任务状态

### Requirement: Upload Task Persistence
后端 SHALL 在上传翻译时将任务持久化到 Supabase（仅登录用户）。

#### Scenario: 登录用户上传翻译任务持久化
- **WHEN** 已登录用户通过上传文件创建翻译任务
- **THEN** 系统解析 JWT 获取 user_id
- **AND** 调用 `create_task(user_id=user_id)` 持久化到 Supabase
- **AND** 所有 `update_task()` 调用传递 user_id

#### Scenario: 访客用户上传翻译不持久化
- **WHEN** 未登录用户通过上传文件创建翻译任务
- **THEN** 系统仅在内存中创建任务
- **AND** 任务不写入 Supabase

### Requirement: Folder Upload Source Type
数据库 SHALL 支持 `folder_upload` 类型的 source_type 值。

#### Scenario: 压缩包上传创建任务
- **WHEN** 用户上传压缩包（.zip / .tar.gz / .rar）
- **THEN** 系统使用 `source_type='folder_upload'` 创建任务记录
- **AND** 数据库 CHECK 约束允许 `folder_upload` 值

