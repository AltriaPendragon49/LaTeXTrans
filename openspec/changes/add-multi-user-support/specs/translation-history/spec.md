# translation-history Specification Delta

## Purpose
新增用户级翻译历史能力，支持任务元数据持久化和用户隔离。

## ADDED Requirements

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

## Cross-References
- 依赖: user-auth (用户身份)
- 依赖: file-management (文件下载)
- 关联: web-api (任务状态 API)
