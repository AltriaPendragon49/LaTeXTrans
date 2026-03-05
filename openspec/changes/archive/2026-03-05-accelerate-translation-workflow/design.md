# Design: 加速 LaTeX 翻译工作流（受控修复版）

## 1. 核心状态机 (Env 处理流程)
系统将核心翻译流程改造成严格遵循单向、有终点的状态机：

### 阶段 0：结构不变量检测 (Invariant Check)
- **输入**：从 AST 解析出的 LaTeX 环境（Env）或节点。
- **检测目标**：
  - 未转义的特殊字符（如独立 `$`）。
  - LaTeX 结构 token 泄漏（如裸露的 `\begin{...}` / `\end{...}` 环境标签）。
- **行为**：此阶段仅进行分类并生成 `is_structure_safe` 标志，**不直接截断或判定失败**。

### 阶段 1：正常翻译路径 (Fast Path)
- **条件**：`is_structure_safe == True`
- **行为**：直接交给常规 LLM 翻译链路进行翻译。此路径下不引入任何前置结构修复干预。**不受 Phase 2 修复队列阻塞，受所属 Token 的正常速率控制并发执行**。

### 阶段 2：受控 LLM 修复尝试 (Controlled Repair)
- **条件**：`is_structure_safe == False`，或者阶段 1 过程中发生明确的解析 / LaTeX 闭合异常。
- **调度机制 (Token-Scoped Repair Scheduler)**：
  - **Token 隔离**：每个 API Token 拥有自己独立的修复队列（FIFO）。不同 token 的修复行为绝对独立，不得互相阻塞或抢占。
  - **排队控制**：env 进入分配的 token 的 FIFO 修复队列。每个 env 最多获得 **1次真实排队机会**。排队等待时间具备 **硬性超时上界 (Queue Timeout，非执行超时)**。
  - **串行执行**：每个 token 在同一时间**最多仅能执行 1 个 Phase 2 修复请求**。
- **行为**：
  - 触发专用的结构修复 LLM 调用。**该 Prompt 必须被视为“安全边界”，独立于正常翻译流程**。
  - **独立实现原则**：必须在单独文件开发、单独测试、并进行单独的代码审查，**绝对不允许复用 Phase 1 的任何 Prompt 模板成分**。
  - **最大调用次数：1**（若未超时）。
  - **修复 Prompt 约束 (极其严格)**：
    - ❌ **绝对禁止** 任何形式的语言翻译（严禁将外语翻译为目标语言）。
    - ❌ **绝对禁止** 改写、总结或推测文本的语义和核心意图。
    - ✅ **仅限** 执行极其基础的结构封装、敏感符转义或添加 placeholder 隔离。
    - *约束意义*：如果 Prompt 稍微允许语义改写或没有明确禁止翻译，Phase 2 将会不可控地退化为规律翻译的 Phase 1，重新引入无底线重试与毁坏风险。
- **流转**：
  - 如果此步骤成功：使用修复后的内容（可能需要后续轻量化翻译或直接复用降级）。
  - 如果此步骤排队超时，或执行后失败，或由于 429 终止：立即终止 LLM 介入，强制流转至阶段 3。禁止无限排队或重复排队。

### 阶段 3：决定性降级 (Deterministic Downgrade)
- **条件**：阶段 2 修复排队超时、修复执行失败，或被限流阻断放弃修复的节点。
- **实现 (downgrade_handler.py)**：
  - 100% 同步执行，**绝对禁止 LLM 调用**。
  - 设置 `translation_status` 为 `DOWNGRADE_STATUS`。
  - 记录 `downgrade_reason`（如 `queue_timeout`, `rate_limit_exceeded`）。
  - **行为**：
    1. **原文直出 (Fallback to Source)**：保留原始 LaTeX 代码。
    2. **空内容占位**：若原文为空，插入特定占位符以防编译中断。
- **保障**：此阶段返回的字符串必须 100% 具备结构安全性。

### 阶段 4：失败路径防放大 (Anti-Amplification Guard)
- **机制 (Maxtry Guard)**：
  - 在外层 `Maxtry` 重试循环（`_retranslate_fail_parts`）中，对每个待处理单元（Section/Caption/Env）进行状态预检。
  - **规则**：若单元状态已标记为 `DOWNGRADE_STATUS`，则**直接跳过**，禁止其进入 Phase 1 或 Phase 2。
  - **意义**：确保 Phase 2 的确定性失败不会被外层重试逻辑重新引入，彻底打破“失败 -> 重试 -> 失败 -> 429 -> 全局阻塞”的恶性循环。

## 2. Token-Scoped 并发与容错策略 (Concurrency & Resilience)
当前系统对于失败路径常有“放大”效应，本设计通过 Token 级别的独立调度和并发降级来彻底隔离风险，防止跨用户、跨任务的修复风暴。

### 2.0 限流分层与三层控制语义边界 (Three-Tier Control Boundaries)
“实现上在一起 ≠ 语义上在一起”。系统必须在概念层严格切割三类不同层级的控制，禁止其相互越权混用：
1. **基础设施级限流 / 安全网 (Infra Guard)**
   - **目的**: 防止瞬时异常并发打挂系统，防止进程 / OS 资源（文件句柄、sockets 等）耗尽。旧有的 `global_llm_semaphore` 属于此类。
   - **绝对禁止项 ❌**: 绝对禁止 Infra Guard 参与或干预 Phase 1 / Phase 2 的业务调度决策；绝对禁止将被其阻塞的请求解释为 token-scoped 429；绝对禁止以此理由触发 Phase 3 降级或变相消耗 env 的唯一修复机会。安全网的唯一原则是“别让系统死”，不负责“事情该不该继续”。
2. **User / Task 限制 (Admission / QoS Control)**
   - **目的**: 决定产品公平性、吞吐量配额等（例如针对未登录用户或任务并发的宏观限流）。决定是否接收宏观任务或使其排队。
   - **绝对禁止项 ❌**: 绝对禁止将其影响渗透至底层的 Phase 2 修复排队中，绝对禁止被当作微观的 LLM API 429 限流进行重试/退避决策。
3. **业务级限流与受控修复 (Token-Scoped Scheduler)**
   - **目的**: 控制 LLM 修复行为的调度。
   - **唯一授权项 ✅**:  Phase 2 的并发、是否排队、是否等待、是否执行修复、是否降级，**必须完全且唯一地由基于 token 的单一修复调度器决定**。禁止 Infra Guard 与 User 限制染指本域决策。

### 2.1 Token-Scoped 限流与重试限度 (Token-Level Rate Limiting)
- **Token 限流语义**：API 429 是针对 **特定 Token** 的速率满载信号，非系统级信号。
- **被动限流 (HTTP 429) 限度**：在 Phase 2 单次修复执行中，**最多允许 1 次退避等待 (Wait+Retry)**。
  - 如果等待后仍为 429，则视作该 Token 在当前负载下“**不适合继续执行该修复任务**”。
  - 必须**立即终止并进入 Phase 3 降级**。
  - **绝对禁止 (Deprecation)**：必须清除底层原有的 `while True` 429 无限重试逻辑。禁止通过延长 sleep、增加 retry 次数、或叠加外层 `Maxtry` 等“失败路径放大器”来盲目提高修复成功率。Phase 2 的失败、超时或重复 429 均被定义为绝对的**不可重试错误**（Non-retryable Error）。
- **无交叉感染**：不得因其他 token 的负载情况或者 429 行为影响当前 token 的修复决策。全局限流绝不能隐式剥夺特定 env 的修复机会。

### 2.2 Phase 1 与 Phase 2 并发关系 (Phase Concurrency Isolation)
- **Phase 1 (正常翻译)**：多协程/线程满载运行，提升吞吐量。**完全不被 Phase 2 的串行队列阻塞**。
- **Phase 2 (结构修复)**：由 `TokenRepairScheduler` 严格接管，按分配的 Token 在其独立的单向 FIFO 队列中**串行执行**。
- **资源共享限制**：Phase 2 在执行时与 Phase 1 共享当前 token 的并发/速率预算，但这二者的内部代码调度必须解耦。Phase 2 的排队、失败或限流永远不得卡死或降低同一进程内无需修复的 Phase 1 env 的吞吐。

## 3. 输出契约与观测性 (Output Contract & Observability)
为了避免 Silent Failure 并提供精细的进度反馈，系统定义了如下机制：

### 3.1 状态契约
- 每个处理完的 env 必须在其封装模型上附加显式标识：
  - `translation_status`：`SUCCESS` | `REPAIRED` | `DOWNGRADE_STATUS`
  - `quality_flag`：如 `STRUCTURE_UNSAFE_BUT_PASSED` | `PHASE2_TIMEOUT`

### 3.2 前端精细化进度看板 (Fine-Grained UI Feedback)
前端通过解析后端 `message` 字段中的特定模式，将粗粒度的“Validating”阶段拆解为用户可感知的子状态（Sub-stages）：

| 后端消息模式 | 前端展示子状态 | 对应业务阶段 |
|:---|:---|:---|
| `Retranslated (X/Y) (B:retry)` | `Retrying failed sections (X/Y)` | Phase 1 Retry |
| `Processed (X/Y) (C1:...)` | `Restoring LaTeX structure (X/Y)` | Phase 2 Controlled Repair |
| `Processed (X/Y) (C2:fallback)` | `Applying fallback translations (X/Y)` | Phase 2 Fallback |
| `Processed (X/Y) (A:degraded)` | `Restoring LaTeX environments (X/Y)` | Phase 1 Degradation |
| `Validating translation results` | `Verifying structure integrity` | Phase 0/2 Final Check |

**UI 约束**：
- **数字跳动**：必须展示 `X/Y` 进度数字，消除假死感。
- **步进只进不退**：利用 `progress >= 95` 或 Validating 关键词锚定 UI 步骤，防止状态回跳。
- **五大阶段**：侧边栏明确展示 `Downloading` -> `Parsing` -> `Translating` -> `Validating Results` -> `Compiling`。
