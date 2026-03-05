# Change: isolate-token-queues

## Why
1. 当前的任务排队系统（`TaskQueue`）是一个全局的 FIFO 队列和有限的共享信号量。不同用户如果使用自定义的不同 LLM API Token，依然会因为撞上系统硬编码的全局 `max_concurrent_translations` 被迫排队，无法互相独立并行。这违背了自带独立 Key 或专线资源应该独享并发配额的预期。
2. 现有系统缺乏真正的运行时任务中断（Cancellation）机制。无论是从页面取消单篇翻译，还是在历史记录中删除运行中的任务，系统仅仅是在内存中打上取消标记（甚至仅从缓存字典移除），后台的翻译协程（`asyncio.Task`）却仍在继续进行 LLM 请求消耗账单额度和系统并发槽位。
3. 清理历史记录时，后端本地存储目录下自动生成的任务调试配置文件（`backend/data/task_configs/{task_id}.json`）未被同步删除，经过高频运行会导致数据文件无痕残留。

## What Changes
- **Token维度的独立编排隔离 (Token-Isolated Queue)**：重构 `backend/app/services/task_manager.py` 中的 `TaskQueue`。在入队逻辑中，将任务持有的 LLM API Token 提取加密（如 MD5）获取 `token_hash`，并按此哈希在内存中动态创立各自专属的无冲突 FIFO 队列（Queue）和独立工作协程。确保相异 Token 的任务始终互不阻塞完全并行计算。
- **真正的强制任务打断 (True Promise Cancellation)**：系统接管对排队中及运行中任务的绝对所有权。在前端发出取消或删除信号时，不再只有被动的状态修改，而是强行查到 `_active_tasks` 的 `Task` 指针调用底层 `.cancel()` 强制发出强中断。利用 Python 异常链终止一切 LLM 和解析步骤阻塞，确保信号槽位安全回收释放。
- **垃圾文件根除闭环**：在 `delete_task_full` 操作中追加读取 `settings.task_configs_dir` 并同步从物理层断绝 `{task_id}.json` 配置，确保历史清除的无遗漏清理。

## Impact
- Affected specs: `queue-token-isolation`, `task-cancellation`
- Affected code:
  - `backend/app/services/task_manager.py` [UPDATE] (引入动态字典隔离和取消代理)
  - `backend/app/api/routes/translate.py` [UPDATE] (提取 token 标识进入队列映射)
  - `backend/app/api/routes/history.py` [UPDATE]
