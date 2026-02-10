# translation-history Specification

## Purpose
TBD - created by archiving change add-multi-user-support. Update Purpose after archive.
## Requirements
### Requirement: Task Metadata Persistence
系统 SHALL 将翻译任务元数据持久化存储在 Supabase Postgres。

#### Scenario: 创建任务时持久化
- **WHEN** 用户通过上传文件或 arXiv ID 创建新翻译任务
- **THEN** 系统在 `translation_tasks` 表中创建记录
- **AND** 记录包含 task_id, user_id, source_type, source_language, target_language, status, created_at

#### Scenario: 任务状态更新时同步
- **WHEN** 翻译任务状态发生变化（progress, status, stage）
- **THEN** 系统同步更新 Supabase 中的对应记录

### Requirement: User Task Isolation
系统 SHALL 确保用户只能访问自己的翻译任务。

#### Scenario: 查询任务列表
- **WHEN** 用户请求 `GET /api/history`
- **THEN** 系统只返回当前用户的任务列表
- **AND** 结果按 created_at 降序排列

#### Scenario: 查询单个任务
- **WHEN** 用户请求 `GET /api/task/{task_id}`
- **AND** 该任务不属于当前用户
- **THEN** 系统返回 HTTP 404 错误

#### Scenario: 下载任务文件
- **WHEN** 用户请求下载某任务的 PDF 或源文件
- **AND** 该任务不属于当前用户
- **THEN** 系统返回 HTTP 403 Forbidden 错误

### Requirement: History Page Display
前端 SHALL 提供翻译历史页面展示用户的所有翻译任务。

#### Scenario: 查看历史记录
- **WHEN** 用户访问 `/history` 页面
- **THEN** 系统显示任务列表，包含任务 ID、源语言、目标语言、状态、创建时间

#### Scenario: 下载历史任务结果
- **WHEN** 用户在历史记录页面点击某已完成任务的下载按钮
- **THEN** 系统下载对应的翻译 PDF 或源文件

#### Scenario: 查看任务详情
- **WHEN** 用户点击某任务条目
- **THEN** 系统显示任务详情，包括完整进度和错误信息

### Requirement: Task Deletion
系统 SHALL 支持用户删除自己的翻译任务记录及关联文件。

#### Scenario: 单条删除已完成任务
- **WHEN** 用户在历史记录页面点击某任务的删除按钮
- **AND** 用户在确认弹窗中点击「确认删除」
- **THEN** 系统删除 Supabase 中该任务记录
- **AND** 系统删除本地 `uploads/{task_id}/`、`outputs/{task_id}/`、`terms/{task_id}/` 目录
- **AND** 前端显示「任务已删除」Toast 通知
- **AND** 任务从列表中移除

#### Scenario: 批量删除任务
- **WHEN** 用户在选择模式下勾选多个任务
- **AND** 点击「删除选中」按钮
- **THEN** 系统批量删除所有选中任务的 Supabase 记录和本地文件
- **AND** 前端显示删除结果 Toast 通知

#### Scenario: 删除处理中任务
- **WHEN** 用户删除状态为 processing 的任务
- **THEN** 系统先标记该任务为 cancelled
- **AND** 等待翻译协程检测到取消标记后退出
- **THEN** 再执行 Supabase 记录删除和本地文件删除

#### Scenario: 删除他人任务被拒绝
- **WHEN** 用户尝试删除不属于自己的任务
- **THEN** 系统返回 HTTP 404 错误（RLS 过滤）

### Requirement: Task Cancellation Support
系统 SHALL 支持取消正在执行的翻译任务。

#### Scenario: 取消运行中的翻译
- **WHEN** 翻译任务被标记为 cancelled
- **AND** `run_translation()` 函数在入口处检测到取消标记
- **THEN** 翻译函数立即返回，不继续处理

