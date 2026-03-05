## isolate-token-queues

- [x] 1. **实现 Token Hash 提取与传递**  
  在 `backend/app/api/routes/translate.py` 的关键流程点（主要是批量后台恢复进程 `_download_and_enqueue` 及其调用入口）内，提取解析出的 `llm_config.api_key` 并基于加密 MD5 脱敏导出为 `token_hash`，作为第五个入参交接给 `TaskQueue.enqueue()` 供调度隔离使用。

- [x] 2. **重构 TaskQueue 为多租户编排模式**  
  修改 `backend/app/services/task_manager.py` 的 `TaskQueue` 类。废除单体的 `_queue`、`_semaphore`、`_worker_task`。将它们转换为 `Dict[str, asyncio.Queue]` 体系：即收到新 `token_hash` 时动态扩建其专职队列及设置容量封顶为 `max_concurrent_translations` 的专属 `asyncio.Semaphore`，并拉起专属的长程待机 `_worker(token_hash)` 随叫随到，实现跨 Token 并发不相干预。

- [x] 3. **对接底层的 asyncio.Task.cancel() 中断执行流**  
  拓展 `TaskQueue`，增加 `cancel_execution(task_id: str)` 强制杀除接口：通过注册的 `_active_tasks` （如果在案）直接调用 `.cancel()` 对象方法。配合在消费者 `_worker` 中严谨铺设对 `except asyncio.CancelledError:` 飞升报错的接管逻辑，确保释放本专属槽位的配额不产生泄露。

- [x] 4. **同步外部业务打断与持久任务根除**  
  重写 `task_manager.py` 里的常规注销事件如 `cancel_task` 和 `delete_task_full`：第一步对在途协程挂载新暴露的 `cancel_execution` 后台强杀；第二步对 `data/task_configs/{task_id}.json` 进行附带擦除处理，防止历史遗留物理空壳残留堵塞节点。

