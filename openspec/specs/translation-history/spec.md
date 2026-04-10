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
The system SHALL ensure that authenticated users can access only their own persisted translation tasks through application-layer ownership checks backed by the local database.

#### Scenario: Query the current user's task list
- **WHEN** an authenticated user requests `GET /api/history`
- **THEN** the system SHALL return only rows owned by the current local user id
- **AND** the results SHALL remain sorted by `created_at` descending.

#### Scenario: Query another user's task
- **WHEN** an authenticated user requests a task that is not owned by the current local user id
- **THEN** the system SHALL return the existing access-denied or not-found behavior for that endpoint
- **AND** it SHALL not depend on Supabase RLS to hide the row.

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
The system SHALL delete persisted task metadata from the local database while continuing to clean only `outputs` and `terms` directories and preserving shared `uploads` directories as reusable cache.

#### Scenario: Delete a completed task from history
- **WHEN** an authenticated user confirms deletion for one of their history tasks
- **THEN** the system SHALL delete the task's persisted row from the local database
- **AND** it SHALL delete local `outputs/{task_id}/` and `terms/{task_id}/` directories
- **AND** it SHALL NOT delete shared uploads directories
- **AND** the frontend SHALL continue to show a success notification.

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
The system SHALL delay authenticated task persistence until translation start and SHALL persist those rows into the local database instead of Supabase.

#### Scenario: Upload does not create a persisted row yet
- **WHEN** a user uploads source files before starting translation
- **THEN** the system SHALL create only the in-memory task state
- **AND** it SHALL NOT create a persisted translation-task row yet.

#### Scenario: Authenticated translation persists on first translation start
- **WHEN** an authenticated user starts translation for a task that has not been persisted yet
- **THEN** the system SHALL create the persisted task row in the local database
- **AND** that row SHALL include the full task metadata needed for history and later recovery.

#### Scenario: Guest translation remains non-persistent
- **WHEN** a guest user starts translation without a local authenticated identity
- **THEN** the system SHALL skip authenticated-history persistence
- **AND** the task SHALL remain guest-only runtime state.

### Requirement: Non-Terminal Task Status Reconciliation
The system MUST reconcile non-terminal task rows against local task logs and SHOULD asynchronously repair the local database record when a terminal status can be inferred.

#### Scenario: Reconcile status from local log
- **WHEN** a user requests task history and a persisted task is still marked `pending`, `processing`, or `queued`
- **AND** a local `task_log.json` contains a terminal event for that task
- **THEN** the API response MUST return the inferred terminal status and 100% progress
- **AND** the system SHOULD asynchronously update the local database row to match the inferred status.

### Requirement: Frontend Terminal Failure Display
The frontend MUST correctly distinguish and display various terminal failure states without defaulting to generic error messages.

#### Scenario: Display Structure Invalid Badge
- **WHEN** a task has a status of `structure_invalid`
- **THEN** the History UI MUST display a specific "Structure Invalid" (或 "结构无效") badge
- **AND** clicking the task SHOULD navigate the user to the processing page to see the detailed error log.

