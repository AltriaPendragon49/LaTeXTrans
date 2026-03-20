## MODIFIED Requirements
### Requirement: Batch Translation Persistence Retry
系统 SHALL 在 Supabase 写入失败时自动重试，并在全部失败时降级处理，确保用户得到明确提示。

#### Scenario: 持久化首次失败时后台重试
- **WHEN** `batch_translate` 端点调用 `persist_task_if_needed()` 失败
- **THEN** 系统通过 `asyncio.create_task()` 在后台启动 `persist_task_with_retry()`
- **AND** 重试最多 2 次，每次间隔 5 秒
- **AND** HTTP 响应不受影响，正常返回 `task_ids`

#### Scenario: 重试成功后任务正常持久化
- **WHEN** 后台重试期间 Supabase 网络恢复
- **THEN** 任务成功写入数据库
- **AND** 任务在历史记录中可见

#### Scenario: 全部重试失败后降级处理
- **WHEN** `persist_task_with_retry()` 所有重试均失败
- **THEN** 系统将该任务注册进 `GuestTaskTracker`（纳入 TTL 自动清理）
- **AND** 在内存任务中设置 `persist_failed=True` 标志
- **AND** 翻译任务仍正常执行，不受影响

#### Scenario: 前端检测到持久化失败并警告用户
- **WHEN** `BatchTranslation.tsx` 的 `pollTask` 轮询到 `persist_failed=True`
- **THEN** 前端 MUST 向用户显示该任务未保存到历史记录的明确警告

#### Scenario: Batch persistence retry preserves config_hash for output reuse
- **WHEN** an authenticated batch-created task has already computed `config_hash` before the initial Supabase insert succeeds
- **THEN** the eventual successful persistence attempt MUST keep that `config_hash`
- **AND** later matching single-task or batch-task requests MUST remain eligible for output reuse.
