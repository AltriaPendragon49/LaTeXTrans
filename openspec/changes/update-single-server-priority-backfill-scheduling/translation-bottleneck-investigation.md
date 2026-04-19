# 单机翻译瓶颈排查记录（供 AI 接手分析与修复）

## 1. 文档目的

这份文档用于给后续 AI 或工程师快速接手当前生产环境中的翻译吞吐问题。目标不是重复猜测，而是基于已经拿到的线上证据继续定位并修复。

这次排查的核心约束：

- 不要把“重试路径”简单视为坏逻辑。部分重试与回退是为了翻译质量、结构安全和目标语言保留而存在。
- 优先区分“必要的质量保护”与“异常放大的高成本路径”。
- 优先恢复系统可用性，但不能通过削弱关键质量保护来换吞吐。

## 2. 问题摘要

### 2.1 服务层现象

- 生产后端在问题高峰期，本机访问 `/docs`、`/api/queue/status` 都会超时。
- 后端容器 `latextrans-backend` 长时间接近 `100%` CPU。
- Uvicorn 运行方式为单 worker，因此单个热点任务会拖垮整个 API 响应。

### 2.2 任务层现象

- `translation_tasks` 一度有 3 个 `processing` 任务同时占满翻译并发。
- 存在 `completed_at` 已写入但任务状态仍为 `processing` 的脏状态。
- `community_curation_jobs` 出现 `queued` / `publishing` 卡住，影响后台策展回填吞吐。

### 2.3 日志层现象

- 大量出现 `HARD_FREEZE_PROTOCOL_VIOLATION`。
- 编译阶段不是主要瓶颈，已观察到 `queue_wait=0ms`、`exec≈11s` 的健康编译。
- 问题热点集中在翻译阶段，尤其是 payload invariant / hard-freeze 保护路径之后。

## 3. 已验证事实

### 3.1 系统资源不是首要瓶颈

线上服务器曾观测到：

- 4 vCPU
- 约 7.4 GiB RAM
- 可用内存约 5.8 GiB
- 根盘占用约 43%

结论：

- 不是机器整体内存不足。
- 不是磁盘写满。
- 问题更像是单进程 CPU 饱和。

### 3.2 后端当前仍是单 worker 架构

生产服务启动参数包含：

- `uvicorn backend.app.main:app --host 127.0.0.1 --port 9001 --workers 1`

并且启动日志与代码都明确提示：

- 当前运行时状态仍部分保存在进程内存中。
- 生产环境仍建议单 worker 运行，直到运行时状态完全外部化。

关键代码位置：

- `backend/app/main.py`
- `backend/app/api/routes/translate.py`

### 3.3 主瓶颈位于翻译阶段，不是编译阶段

活跃任务的产物曾显示：

- `audit.jsonl` 只推进到了 `node_enter:translate`
- 没有继续进入 `validate`、`generate` 或 `finalize`

说明：

- 任务主要时间花在 translate node 内部，而不是编译或归档阶段。

### 3.4 HARD_FREEZE 违规本身不是“必然卡死”

重启后新任务 `2210.03629-0419-1425-2ac20337-87ce-480f-b430-5f5bbec9202f` 在同样出现多次 `HARD_FREEZE_PROTOCOL_VIOLATION` 的情况下，仍能在几十秒内从：

- `Translated 2/30 sections`
- 推进到 `Translated 28/30 sections`

说明：

- “出现 invariant violation”不是充分条件。
- 真正的问题更像是：某些论文会把保护路径放大到异常程度。

### 3.5 已出现过任务状态漂移

数据库曾观测到任务：

- `2106.09685-0419-0540-21c68fa0-6689-4df7-a8cf-bb48ec18068e`

表现为：

- `status = processing`
- `completed_at` 已写入

这说明：

- 任务收尾或状态同步逻辑存在不一致。
- 脏状态可能占用并发槽位，进一步拖慢系统。

## 4. 这次排查期间的关键动作与结果

### 4.1 已执行一次受控重启

为恢复系统可用性，已经对生产后端执行过一次重启。

重启后的启动日志显示：

- `fail_interrupted_translation_tasks()` 生效
- 启动恢复阶段一次性将 3 个卡住的翻译任务标记为失败
- 日志中记录：`failed_tasks: 3`

重启后数据库确认：

- 旧热点任务 `2205.14135-0419-0652-6841d012-e03d-4556-a95a-ff1c3abee9e6`
- 已变为 `failed`
- 错误信息为 `Task interrupted by backend restart`

### 4.2 启动后会自动恢复后台策展任务

后端启动后，管理员策展轮询会自动恢复待处理 job，并重新触发翻译任务。

因此：

- 单纯重启不能长期“清空现场”
- 如果后续需要静态复现某个问题，需要临时停掉后台策展恢复逻辑或先清空待调度 job

关键代码位置：

- `backend/app/main.py`
- `backend/app/services/paper_service.py`

## 5. 核心根因判断

### 5.1 一句话总结

系统不是因为机器资源不够，而是因为翻译阶段某些论文触发了高成本保护路径的异常放大，在单 worker 架构下将整个后端拖入 CPU 密集阻塞，同时任务状态收尾不一致又放大了吞吐损失。

### 5.2 根因排序

#### 根因 1：翻译阶段异常保护路径被异常放大

最强信号来自：

- `HARD_FREEZE_PROTOCOL_VIOLATION`
- paragraph rescue / masked rescue 路径
- protection log 中 fail part 的大范围扩散

重点不是“某一次重试”，而是：

- 某个任务中很多不同 part 都进入了 rescue
- 部分 part 被重复送回模型多轮
- 这些路径包含大量同步字符串处理、正则处理、保护 token 校验和恢复

对于旧热点任务 `2205...`，曾观测到：

- `77` 个唯一 fail part
- `165` 次 paragraph 路径命中

而相对健康的新任务 `2210...` 当前仅观测到：

- `32` 个唯一 fail part
- `11` 个唯一 paragraph fail part

这说明“放大范围”比“是否违规”更关键。

#### 根因 2：单 worker 架构把单任务热点放大为全站阻塞

在 `workers = 1` 的前提下：

- 某个任务一旦进入 CPU 热点
- API 请求、本机健康检查、队列状态查询都会一起受影响

这不是根因本身，但它把问题的影响面扩大到了整个后端。

#### 根因 3：任务状态未正确收尾，吞吐进一步锁死

已确认至少存在：

- `completed_at` 非空但状态仍 `processing`
- `publishing` 卡住
- output_path 或任务产物缺失但 DB 仍显示处理中

这会导致：

- 并发槽位长期不释放
- 队列看起来“满了”但其中包含脏任务
- 重启后仍需要额外恢复逻辑兜底

#### 根因 4：后台策展恢复机制会让问题持续复发

只要待处理的 curation job 还在：

- 后端启动后会自动恢复
- 新任务会再次被调度进来

如果底层热点路径未修复：

- 问题会在下一批任务上继续复现

## 6. 已验证排除项

这些方向已经有较强证据表明不是主因：

### 6.1 不是 compile queue 饱和

证据：

- compile queue wait 曾观测到 `0ms`
- 编译执行约 `11s`
- translate node 比 compile node 明显更早成为热点

### 6.2 不是全局内存吃满

证据：

- 系统总内存仍有明显余量
- 问题更像主线程长时间占用 CPU，而不是整体 OOM

### 6.3 不是统一的供应商限流风暴

已有日志中虽然出现个别请求失败，但暂未观察到：

- 持续大面积 `429`
- 持续大面积 `503`

因此：

- 上游 relay / provider 问题可能是局部触发因素
- 但不是这次瓶颈的主要解释

## 7. 线上证据重点

### 7.1 任务 `2205.14135...` 的特征

在被重启清理前，这个任务具备以下特征：

- `38` 个 section
- `80` 个 env
- `41` 个 caption
- `task_log.json` 和 `audit.jsonl` 长时间停在 translate 阶段
- protection log 高密度增长

这是已知最接近“卡死样本”的任务。

### 7.2 任务 `2210.03629...` 的对照价值

这是已知“有 hard-freeze 违规但仍持续推进”的对照任务。

它的重要价值在于：

- 证明 invariant violation 不是充分条件
- 可以用来和 `2205...` 对比 fail part 扩散范围、rescue 深度、每个 part 的重试轮数

## 8. 关键代码路径

下面这些文件和函数是后续 AI 优先阅读的入口。

### 8.1 翻译与保护路径

- `backend/app/services/agents/translator_agent.py`

重点关注：

- `_prepare_llm_payload_text`
- `_restore_llm_output_text`
- `_request_llm_for_trans`
- `_request_llm_for_trans_with_terms`
- `_request_llm_for_retrans_error_parts`
- `_rescue_plain_text_by_paragraph`
- `_translate_plain_text_rescue_piece`
- `_translate_masked_plain_text_rescue_piece`
- `_rescue_plain_text_by_fragment`
- `_is_noop_translation`
- `_is_source_preserved_translation`

### 8.2 hard-freeze 校验

- `backend/app/services/latex/utils.py`

重点关注：

- `freeze_protected_tokens`
- `verify_hard_freeze_token_stream`
- `restore_hard_freeze_tokens`

注意：

- 这里当前是严格按 token 顺序做完整对比
- 丢失、重排、缺少 token 都会触发 violation

### 8.3 翻译校验与错误分类

- `backend/app/services/agents/validator_agent.py`

重点关注：

- `_validate`
- `_extract_parts_need_validate`

### 8.4 任务调度与状态收尾

- `backend/app/api/routes/translate.py`
- `backend/app/services/task_manager.py`
- `backend/app/main.py`
- `backend/app/services/paper_service.py`

重点关注：

- `run_translation`
- `create_progress_callback`
- `update_task`
- `fail_interrupted_translation_tasks`
- `resume_pending_admin_curation_jobs`
- `_wait_for_task_terminal_state`

## 9. 当前最值得验证的假设

### 假设 A：某些论文触发了过宽的 rescue 扩散面

判断标准：

- 同一个任务中，很多 section/env/caption 都进入 paragraph rescue
- fail part 数量异常多
- 同一 base part 被送进模型多轮

建议验证方式：

- 对比 `2205...` 与 `2210...` 的 protection log
- 不要只看 token 审计条数，优先看：
  - 唯一 fail part 数
  - 唯一 paragraph fail part 数
  - 每个 base part 的唯一 `request_nonce` 数

### 假设 B：某条本地字符串处理路径在异常任务里成本极高

此前 `strace` 看到主线程重复出现大块 `mmap/munmap`，但离线对 `SequenceMatcher` 的单次测试没有复现 200MB 量级峰值。

说明：

- `SequenceMatcher` 可能是放大器，但不太像唯一根因
- 更可能是多段同步文本处理与重复序列化叠加造成的热点

建议验证方式：

- 在下次出现热点任务时，对主线程抓 Python 栈
- 不要只看系统调用，必须定位到 Python 函数级

### 假设 C：状态漂移来自异常退出路径未统一收尾

表现包括：

- `completed_at` 已写但 `status` 未转终态
- `publishing` 不退出
- output 目录缺失但任务仍显示处理中

建议验证方式：

- 沿 `try/except/finally` 路径审查 `run_translation`、watcher、paper sync 和 curation job 收尾逻辑

## 10. 推荐修复优先级

### P0：系统止血

1. 保留受控重启能力，用于从热循环中脱身。
2. 保证启动时能清理中断的 `processing` 任务。
3. 修正脏状态，确保已完成或已中断任务释放槽位。

### P1：阻断“无限放大式”的保护路径

1. 为 hard-freeze 后续 rescue 路径增加清晰的轮数上限。
2. 对单个 base part 的二次、三次送模次数做显式约束。
3. 对持续 invariant violation 的 part 提供可控失败或可控降级，而不是无限尝试。

注意：

- 这里不是要删掉 hard-freeze 保护。
- 目标是限制“保护路径的放大倍数”。

### P2：修复状态一致性

1. 保证任务终态写入和 DB 同步不会分叉。
2. 审查 `translation_tasks`、paper sync、curation job 三方状态更新是否存在竞态。
3. 保证异常退出、重启退出、成功退出都走统一收尾路径。

### P3：增强可观测性

建议新增每任务指标：

- 唯一 fail part 数
- 唯一 paragraph fail part 数
- 每个 base part 的 request_nonce 数
- payload invariant 次数
- 进入 masked rescue / fragment rescue 的次数
- 每阶段耗时

## 11. 后续 AI 建议工作流

如果后续 AI 要继续分析并修复，建议按下面顺序进行：

1. 先读本文件。
2. 再读 `openspec/changes/update-single-server-priority-backfill-scheduling/proposal.md` 与 `design.md`，理解当前单机调度方案的边界。
3. 不要先改重试次数，先确认具体是哪个函数或哪类论文导致扩散最严重。
4. 优先做“观察增强”而不是直接削弱保护。
5. 只有在拿到函数级证据后，才修改 rescue / fail-fast 逻辑。

## 12. 注意事项

- 不要把服务器密钥、数据库密码等敏感信息再写入新的文档。若需要服务器访问，请读取现有的运维密钥文档。
- 不要默认用 destructive 命令清理运行现场。
- 不要把“恢复可用性”和“彻底修复根因”混为一步。
- 不要为了吞吐去掉目标语言保留、结构校验、compile-aware fallback 等关键质量保护。

## 13. 当前结论

当前最可靠的结论是：

> 系统的核心瓶颈不在机器资源，而在翻译阶段某些任务触发了异常放大的保护/救援路径；单 worker 架构把单任务热点放大成全站阻塞，而任务状态未正确收尾进一步锁死了吞吐。

下一步最优先的不是“简单减少重试”，而是：

1. 找出哪些 base part 被反复送模；
2. 找出哪一段本地同步处理在热点任务中最耗 CPU；
3. 给放大路径加可观测性与可控上限；
4. 修复任务终态一致性。
