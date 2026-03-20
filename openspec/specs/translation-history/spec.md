# translation-history Specification

## Purpose
TBD - created by archiving change add-multi-user-support. Update Purpose after archive.
## Requirements
### Requirement: Task Metadata Persistence

The system SHALL update the translation task metadata to reflect the actual utilized model.

#### Scenario: 任务执行时同步实际使用的模型
- **GIVEN** a translation task is started with a generic `translation_model` (e.g., default placeholder)
- **WHEN** the backend determines the actual LLM config via `build_llm_config()`
- **THEN** it MUST compare the actual model name with the one in metadata
- **AND** if different, UPDATE the metadata in database to reflect the ACTUAL model used
- **AND** ensure the history record displays the actual model name (e.g., `qwen/qwen3-235b-a22b`)

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
The system SHALL provide a history page that shows translation tasks currently visible to the user.  
Failed tasks that were automatically quarantined and deleted from `translation_tasks` SHALL NOT appear in history results.

#### Scenario: View History Records
- **WHEN** the user requests the history page (`/history` or `GET /api/history`)
- **THEN** the system returns the visible task list with key metadata (task id, languages, status, timestamps)

#### Scenario: Download Historical Result
- **WHEN** the user selects a completed task from history
- **THEN** the system provides the corresponding translated output artifact (for example PDF or source package)

#### Scenario: Auto-Removed Failed Tasks Are Hidden
- **WHEN** a task reaches terminal status `failed` or `failed_compilation`
- **AND** the backend failure-interception flow deletes the row from `translation_tasks`
- **THEN** `GET /api/history` SHALL NOT return that task

#### Scenario: Cancelled Tasks Do Not Trigger Auto-Removal
- **WHEN** a task transitions to failed state due to explicit user cancellation
- **THEN** failure-interception auto-removal SHALL NOT be triggered by quarantine logic
- **AND** history retention behavior for cancelled tasks remains governed by existing policy

### Requirement: Task Deletion
系统 SHALL 在删除任务时仅清理 outputs 和 terms 目录，保留 uploads 目录作为共享缓存。

#### Scenario: 单条删除已完成任务
- **WHEN** 用户在历史记录页面点击某任务的删除按钮
- **AND** 用户在确认弹窗中点击「确认删除」
- **THEN** 系统删除 Supabase 中该任务记录
- **AND** 系统删除本地 `outputs/{task_id}/`、`terms/{task_id}/` 目录
- **AND** 系统 SHALL NOT 删除 uploads 目录
- **AND** 前端显示「任务已删除」Toast 通知

### Requirement: Task Cancellation Support
系统 SHALL 支持取消正在执行的翻译任务。

#### Scenario: 取消运行中的翻译
- **WHEN** 翻译任务被标记为 cancelled
- **AND** `run_translation()` 函数在入口处检测到取消标记
- **THEN** 翻译函数立即返回，不继续处理

### Requirement: Translation Output Reuse
系统 SHALL 在启动翻译前检查是否有配置一致的已完成翻译可复用。

#### Scenario: 完全匹配配置时复用 output
- **WHEN** 用户启动翻译任务
- **AND** 存在已完成任务具有相同 arxiv_id、source_language、target_language、translation_mode、compile_strategy
- **THEN** 系统深拷贝已有 output 目录到新任务
- **AND** 新任务标记为 completed，跳过翻译流程
- **AND** 新任务 output 与源 output 目录独立（深拷贝）

### Requirement: Config Hash Storage
The system SHALL store translation configuration signatures in the `translation_tasks` table for fast matching, including formatting configuration when present.

#### Scenario: 创建任务时生成 config_hash
- **WHEN** 翻译任务创建或翻译配置确定时
- **THEN** 系统计算 `config_hash` 并存储到 `translation_tasks` 表
- **AND** `config_hash` 基于 `arxiv_id`、`source_language`、`target_language`、`translation_mode`、`compile_strategy`、`formatting` 生成

#### Scenario: Batch-created authenticated task keeps config_hash through deferred persistence
- **WHEN** an authenticated batch arXiv task computes its final translation configuration before the initial Supabase row exists
- **THEN** the task runtime snapshot MUST retain the computed `config_hash`
- **AND** the first successful persistence attempt, including a background retry after an initial failure, MUST write that `config_hash` into `translation_tasks`.

### Requirement: Deferred Task Persistence
系统 SHALL 在翻译阶段才将任务持久化到数据库，上传/下载阶段仅创建内存任务。

#### Scenario: 上传文件时不创建数据库记录
- **WHEN** 用户通过 POST /upload 上传文件
- **THEN** 系统仅创建内存任务（`persist_to_db=False`）
- **AND** Supabase `translation_tasks` 表中 SHALL NOT 创建新记录

#### Scenario: 下载 arXiv 时不创建数据库记录
- **WHEN** 用户通过 POST /arxiv 下载论文
- **THEN** 系统仅创建内存任务（`persist_to_db=False`）
- **AND** Supabase `translation_tasks` 表中 SHALL NOT 创建新记录

#### Scenario: 翻译时首次持久化
- **WHEN** 用户通过 POST /translate/{task_id} 启动翻译
- **AND** 用户已登录（有 user_id）
- **THEN** 系统调用 `persist_task_if_needed()` 首次创建数据库记录
- **AND** 数据库记录包含完整的任务信息（source_type、arxiv_id、source_language 等）

#### Scenario: Guest 用户任务不持久化
- **WHEN** Guest 用户（无 user_id）启动翻译
- **THEN** 系统跳过数据库持久化
- **AND** 任务仅存在于内存中

#### Scenario: 持久化失败时继续翻译
- **WHEN** `persist_task_if_needed()` 抛出异常
- **THEN** 系统记录警告日志
- **AND** 翻译流程 SHALL 继续执行（不因持久化失败而中断）

### Requirement: Non-Terminal Task Status Reconciliation
The system MUST reconcile the status of tasks that are in a non-terminal state (`pending`, `processing`, `queued`) during history retrieval to prevent users from seeing "Stuck" tasks due to server crashes.

#### Scenario: Reconcile Status from Local Log
- **WHEN** a user requests their task history (`GET /history`)
- **AND** a task in the database is in a non-terminal state
- **AND** a local `task_log.json` exists for that task and contains terminal events (e.g., `compilation_completed`)
- **THEN** the API response MUST return the inferred terminal status and 100% progress
- **AND** the system SHOULD asynchronously update the Supabase database to match this corrected state.

### Requirement: Frontend Terminal Failure Display
The frontend MUST correctly distinguish and display various terminal failure states without defaulting to generic error messages.

#### Scenario: Display Structure Invalid Badge
- **WHEN** a task has a status of `structure_invalid`
- **THEN** the History UI MUST display a specific "Structure Invalid" (或 "结构无效") badge
- **AND** clicking the task SHOULD navigate the user to the processing page to see the detailed error log.

