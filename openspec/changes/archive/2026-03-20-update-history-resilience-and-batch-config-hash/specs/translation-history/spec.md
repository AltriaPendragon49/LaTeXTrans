## MODIFIED Requirements
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

#### Scenario: Returning to history after a transient authenticated fetch failure
- **WHEN** an authenticated user revisits the history page after opening a historical task
- **AND** the first history fetch fails because the auth token is temporarily unavailable or the backend hits a recoverable history-query failure
- **THEN** the system MUST retry loading the history automatically without requiring a manual refresh
- **AND** once credentials and the backend query path recover, the visible history list MUST render normally.

## MODIFIED Requirements
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
