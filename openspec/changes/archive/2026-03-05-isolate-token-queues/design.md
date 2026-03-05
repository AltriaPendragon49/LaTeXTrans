# Design: 基于 TokenHash 的任务并发隔离与严格强制中断

## 1. 全新排队架构：Token-Isolated Queue

原有 `TaskQueue` 实现在本质上是：`Single Queue (FIFO)` + `Global Semaphore(max=3)`。这导致如果 A 用户甩进去 9 篇论文（使用 Token A），此时 B 用户进去 1 篇论文（使用 Token B），B 用户会被堵在 A 任务的后面等待全局并发槽位，完全背离不同 API 通道隔离负载的物理现实。

在不废除 User 级防刷机制（`max_user_active_tasks`）的前提下，我们需要改变并发底座的设计模式：

### 1.1 数据映射与 Token Hash
将单独的 `Queue` 改为 `Dict[str, asyncio.Queue]`, 并发信号量同样改为 `Dict[str, asyncio.Semaphore]`。其中 `Key` 统一使用任务最终决定的 LLM API Token 字符串经过哈希隐藏后的密串（下称 `token_hash`），这样即使恶意用户也能避免在内部系统、日志或异常链中被打印截留明文的高价值 API Key。

### 1.2 动态扩充消费者工作组 
在 `TaskQueue.enqueue(task_id, factory, user_id, token_hash)` 中：
一旦探测到这是首次面对未知的 `token_hash`，通过内部互斥锁动态初始化该 Key 的队列以及设定容量尺寸等同于 `max_concurrent_translations` 的专署信号量。
并发立刻启动专门循环消费此队列的后台 Worker。不同 `token_hash` 的组之间相互不可见且绝不争用配额。

## 2. True Cancellation: `asyncio.Task.cancel()` 接管

传统的放弃方法只是调用 `cancel_task` 设置 `status = failed`。这仅仅让前端在下次轮询发现是取消态，而后端 worker 会原封不动执行直至编译成 PDF 并无视修改报错。不仅烧钱毁环境，还无意义地严重死锁占领了本来已紧张的其他后续正常重试槽位。

### 2.1 任务拦截生命周期追踪
系统中现存的 `_active_tasks[task_id] = asyncio.create_task(...)` 其实早已无意间把能做强打断的指针交给了运行库调度域。我们需要：
1. `TaskQueue` 新增 `cancel_execution(task_id: str)` 接口。
2. 该接口从字典中查询执行指针 `Task` ，如在进行中则显式触发 `.cancel()` 对象方法抛弃执行。 
3. 对于还没发生只呆在 Queue 表里的候补项，采用一个额外的字典标记 `skipped`, 轮到它执行时消费者一旦发现就跳过丢弃即可。

### 2.2 信号量的铁桶闭环 (Absolute Release)
由于协程内部将被从系统底层抛出不可抵抗的异常链，原有吞咽所有运行报错的 `except Exception:` 必须要对 `except asyncio.CancelledError:` 定向特别识别和放行（重抛再接，或合并记录处理）。
**队列 Worker 中的 `finally` 块的义务被明确强调**：
无论是异常崩了、平顺翻译完成、还是被外界无情腰斩（Cancel），它永远都必须：
    - `self._semaphores[token_hash].release()`
    - 安全衰减对应 `user_id` 和隔离容器的在途记录。

### 2.3 `history` 与 `task_configs` 全物理闭环映射
此前的架构在执行 `task_manager.delete_task_full` 仅仅处理了 outputs， uploads 以及 terms。但近期引入的运行期配置快照抓取存放在 `settings.task_configs_dir / f"{task_id}.json"` 系统下，久而久之成为空间毒瘤。
本次借着补充历史清理完善的任务要求，顺势将其纳入 `delete_task_full` 的标准回收范畴。
