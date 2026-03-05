# Change: fix-batch-task-status-reconciliation

## Why
对于批量翻译任务（以及可能的部分单个翻译任务），如果在任务实际完成或失败前（或者由于 flusher 未能及时同步由于种种原因卡住时），数据库中尚未记录该任务的 `output_path`，当前在 `history.py` 中的惰性状态校正（Lazy Reconciliation）将无法工作。因为该机制强依赖从 Supabase 获取到的 `output_path` 来定位本地的 `task_log.json`，一旦获取为 `None` 就直接跳过校正，导致哪怕本地已经成功生成了 PDF，前端历史记录中依然一直显示为“等待中”。
另外，在 `batch-translate` 发起后台任务的翻译过程中，`run_translation` 函数直到翻译结束的最后阶段才会把 `output_path` 回写进去，这就导致中间任何时候状态同步脱节都会面临这个问题。

## What Changes
1. **完善惰性状态校正支持**：在 `backend/app/api/routes/history.py` 中的 `get_user_history` 接口，当发现非终态任务且其 `output_path` 为空时，通过默认约定 `settings.outputs_dir / task["task_id"]` 自动推断本地输出路径，从而成功读取 `task_log.json` 并根据终端事件正确推断和回写任务最新状态。
2. **提早写入输出路径**：在 `backend/app/api/routes/translate.py` 的 `run_translation` 方法内，一旦创建了 `output_dir`，就在下一次状态更新（如 `PROCESSING`，"Initializing translation..."、"Checking for reusable output..." 等）时尽早将 `output_path` 写入内存和 DB 中。

## Migration & Deprecation
- 本修复纯后端热修复，不仅解决新任务的同步问题，还能兼容处理已有“卡住”的历史任务由于 Lazy Reconciliation 被增强而自动校正展示。

## Impact
- Affected specs: `translation-history`
- Affected code:
  - `backend/app/api/routes/history.py` [UPDATE]
  - `backend/app/api/routes/translate.py` [UPDATE]
