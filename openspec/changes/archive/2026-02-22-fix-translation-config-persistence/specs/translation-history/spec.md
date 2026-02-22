# translation-history

## MODIFIED Requirements
### Requirement: Task Metadata Persistence
系统 SHALL 将翻译任务元数据持久化存储在 Supabase Postgres。为了保证历史记录显示的准确性，持久化的元数据必须包含用户实际选择的精确配置，而不能仅仅是默认值。

**Why:**
To provide an accurate history log to users. Previously, tasks saved the default languages instead of user-selected languages, confusing users viewing their history.

#### Scenario: 创建任务时持久化
- **WHEN** 用户通过上传文件或 arXiv ID 创建新翻译任务
- **THEN** 系统在 `translation_tasks` 表中创建记录
- **AND** 记录包含 task_id, user_id, source_type, source_language, target_language, status, created_at
- **AND** 必须确保 `source_language` 和 `target_language` 及其它高级配置都是基于用户的实际请求，而非硬编码的 `"en"` 和 `"zh"` 默认值

#### Scenario: 任务状态更新时同步
- **WHEN** 翻译任务状态发生变化（progress, status, stage）
- **THEN** 系统同步更新 Supabase 中的对应记录

#### Scenario: 跨语言实时翻译记录正确显示
- **Given** a user uploads a paper and selects English as the source language and Japanese as the target language
- **When** the translation task is started and persisted to the database
- **Then** the database record must contain `source_language: "en"` and `target_language: "ja"`
- **And** the history page must correctly display "en -> ja" for this specific task.

#### Scenario: 批量高级配置记录
- **Given** a user inputs multiple arXiv IDs and selects an advanced compilation strategy (e.g., "xelatex")
- **When** the batch translation tasks are created and persisted
- **Then** the database records for each task must contain the selected compilation strategy and language configurations.
