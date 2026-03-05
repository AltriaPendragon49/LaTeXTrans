# Change: accelerate-translation-workflow

## Why
当前 LaTeX 翻译工作流在处理结构损坏（如特殊字符、环境封闭错误等）时，容易陷入无限重试、由于大范围失败路径引发的等待阻塞（如长时间 API 睡眠）等问题，严重影响处理效率和系统稳定性。通过引入严格的受限状态机和一次性结构修复机制，可以在确保结构安全优先的前提下，彻底杜绝无限重试与阻塞问题，显著缩短单篇论文的整体翻译和处理时间。

## What Changes
- **引入阶段 0：结构不变量检测**：前置检测未转义的 `$` 或 LaTeX 结构 token 泄露，用于状态分流。
- **引入阶段 1：普通翻译路径 (Phase 1)**：针对安全的 env 直接翻译。**可并行执行，受总速率限制，绝不被 Phase 2 的修复队列阻塞。**
- **引入阶段 2：受控 LLM 修复尝试 (Phase 2) 与 Token-Scoped 调度**：
  - **修复 Prompt 必须极其严格**：明确且严厉地禁止任何翻译和语义改写，仅限结构封装、转义或 placeholder 替换。
  - **引入 TokenRepairScheduler**：每个 API token 拥有独立的修复调度队列（FIFO）。同一 token 同一时间最多允许 1 个 Phase 2 修复执行（严格串行）。
  - **排队与超时上界**：每个需要修复的 env 最多排队1次。排队等待时间必须有硬上界，若等待超时或修复执行依然失败，必须立刻终止 LLM 路径。
  - **禁止跨 Token 阻塞**：不同 token 的修复与限流行为彼此完全独立，禁止跨 token 共享修复队列或修复配额。
- **引入阶段 3：决定性降级**：对于无法通过修复的危险 env、修复等待超时的 env，或连续 429 限流的 env，强制选择原文直出、规则翻译或 placeholder + 注释输出，保证结构安全与无尽等待的打破。
- **Token 级的被动限流 (HTTP 429)**：API 429 是 token 级信号。单次修复执行最多允许 1 次 wait-and-retry，若 retry 后仍为 429，立即进入 Phase 3 降级，禁止为了提高修复成功率而增加 retry 或延长 sleep。

## Migration & Deprecation (有限定权力的限流与重试迁移转移)
- **明确三层控制语义边界 (Three-tier Control Boundaries)**：系统必须在规范和概念上绝对隔离以下三种控制机制：
  1. **Infra Guard (安全网/全局锁)**：仅防瞬时异常并发、OS 资源耗尽。**绝对禁止**参与 Phase 2 决定，不得触发降级、不得视为 429、不得消耗 env 修复机会（只负责“别让系统死”）。
  2. **User / Task 限制**：作为接纳控制 (Admission Control, QoS)，仅决定是否接收任务或粗粒度排队。**绝对禁止**被用于控制 Phase 2 LLM 修复或充当 429 限流信号。
  3. **Token-Scoped Scheduler**：**唯一被允许**决定 Phase 2 修复排队、等待、执行、超时的业务机制。
- **“去权力而非去代码”的全局限流迁移**：旧有全局并发锁 `global_llm_semaphore` 可以保留作为 Infra Guard，但**必须彻底剥夺**其对于 LLM 业务调度的干扰力。
- **清除失败路径放大器**：明确禁止并要求移除现存底层的 429 无限重试（指数退避）和外层叠加重试。Phase 2 的失败、超时、429-after-retry 均为不可重试错误。修复机会受控于排队，失败必须可解释并可明确降级。

## Impact
- Affected specs: `ControlledRepairWorkflow`.
- Affected code:
  - `backend/app/services/translation/dispatcher.py` [UPDATE]
  - `backend/app/services/translation/repairer.py` [NEW]
  - `backend/app/services/translation/downgrade.py` [NEW]
