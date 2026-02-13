# translation-history Specification Delta

## Purpose
新增翻译结果复用能力，通过配置签名匹配已完成任务的 Output 并深拷贝，跳过重复翻译流程。

## ADDED Requirements

### Requirement: Translation Output Reuse
系统 SHALL 在启动翻译前检查是否有配置一致的已完成翻译可复用。

#### Scenario: 完全匹配配置时复用 output
- **WHEN** 用户启动翻译任务
- **AND** 存在已完成任务具有相同 arxiv_id、source_language、target_language、translation_mode、compile_strategy、enable_verification
- **THEN** 系统深拷贝已有 output 目录到新任务
- **AND** 新任务标记为 completed，跳过翻译流程
- **AND** 新任务 output 与源 output 目录独立（深拷贝）

#### Scenario: 跨用户复用
- **WHEN** 用户 A 的翻译配置与用户 B 已完成任务一致
- **THEN** 系统仍可复用用户 B 的 output（使用 admin client 查询）
- **AND** 不向用户 A 暴露用户 B 的其他信息

#### Scenario: 匹配 output 已被删除
- **WHEN** 配置签名匹配到已完成任务
- **BUT** 该任务的 output 目录不存在（已被删除）
- **THEN** 系统跳过复用，启动正常翻译流程

#### Scenario: 配置部分匹配
- **WHEN** 存在已完成任务但配置仅部分匹配
- **THEN** 系统不复用，启动正常翻译流程

### Requirement: Config Hash Storage
系统 SHALL 在 translation_tasks 表中存储翻译配置签名用于快速匹配。

#### Scenario: 创建任务时生成 config_hash
- **WHEN** 翻译任务创建或翻译配置确定时
- **THEN** 系统计算 config_hash 并存储到 translation_tasks 表
- **AND** config_hash 基于 arxiv_id、source_language、target_language、translation_mode、compile_strategy、enable_verification 生成

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

## MODIFIED Requirements

### Requirement: Task Deletion
系统 SHALL 在删除任务时仅清理 outputs 和 terms 目录，保留 uploads 目录作为共享缓存。

#### Scenario: 单条删除已完成任务
- **WHEN** 用户在历史记录页面点击某任务的删除按钮
- **AND** 用户在确认弹窗中点击「确认删除」
- **THEN** 系统删除 Supabase 中该任务记录
- **AND** 系统删除本地 `outputs/{task_id}/`、`terms/{task_id}/` 目录
- **AND** 系统 SHALL NOT 删除 uploads 目录
- **AND** 前端显示「任务已删除」Toast 通知

## Cross-References
- 依赖: file-management (Upload 共享存储、上传失败清理)
- 关联: user-auth (跨用户查询需要 admin client)
- 关联: web-api (POST /translate 触发持久化)
