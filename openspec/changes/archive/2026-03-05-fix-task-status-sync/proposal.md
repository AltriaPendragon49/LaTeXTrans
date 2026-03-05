# Change: fix-task-status-sync

## Why
严重影响用户体验的工作流中断和通知失败问题。
首先，当翻译任务因为结构错误（如 `structure_invalid` 或 `failed_compilation`）而失败时，前端依然会一直显示“等待中”或“处理中”。这是因为后端拦截失败任务时主动从数据库删除了该记录，导致前端历史页面无法获取并渲染正确的失败状态。
其次，对于成功完成的任务，由于数据库 Flusher 的竞态条件或组件因为异常被阻断，最终完成状态偶尔未能正确写入 Supabase，导致本已成功且生成了 PDF 的任务也在历史记录中显示为“等待中”。
最后，由于后端重启时未能正确从数据库 JSON 载荷中反序列化 `email_notification` 布尔标志，以及同步邮件发送逻辑中隐藏的异常捕获机制，导致任务完成或失败时无法可靠地触发邮件通知。

## What Changes
- **保留失败任务历史记录**：修改 `backend/app/services/task_manager.py` 中的 `_intercept_failed_task` 方法，移除删除数据库任务的逻辑，让失败任务的状态能够持久化到 Supabase 中。
- **持久化邮件通知配置**：在 `_recover_from_supabase` 反序列化逻辑中，显式提取 `email_notification` 字段并装载到恢复的 `advanced_config` 中。
- **完善终态 Supabase 写入逻辑**：确保 `completed` 等语义翻转（semantic transitions）能够实时下发到 Supabase，并不受后续的邮件报警超时或异常的干扰。
- **惰性状态校正（Reconciliation）**：在 `backend/app/api/routes/history.py` 中引入校正机制，当历史 API 发现任务状态不一致（DB 为非终态但本地 Log 已完成）时，自动根据本地 `task_log.json` 修正 Supabase 状态。
- **前端支持终态展示**：检查并在必要时重构前端 UI（如历史记录列表），以便能够正确解析并渲染 `structure_invalid` 和 `failed_compilation` 状态（例如展示一个明显的“失败”徽章）。

## Migration & Deprecation
- 如果后续有清理任务存储的需求，应转为定时任务自动清理陈旧错误数据，而非在任务刚失败的拦截阶段立即进行静默删除，以免吞掉用户的错误反馈现场。

## Impact
- Affected specs: `translation-history`, `TaskRuntimeState`
- Affected code:
  - `backend/app/services/task_manager.py` [UPDATE]
  - `backend/app/api/routes/history.py` [UPDATE]
  - `frontend/src/` (History related components) [UPDATE]
  - `backend/tests/unit/test_fix_task_status_sync.py` [NEW]
