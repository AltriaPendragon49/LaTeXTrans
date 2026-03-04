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
- **行为**：直接交给常规 LLM 翻译链路进行翻译。此路径下不引入任何前置结构修复干预。

### 阶段 2：受控 LLM 修复尝试 (Controlled Repair)
- **条件**：`is_structure_safe == False`，或者阶段 1 过程中发生明确的解析 / LaTeX 闭合异常。
- **行为**：
  - 触发专用的结构修复 LLM 调用。
  - **最大调用次数：1**。
  - **修复 Prompt 约束**：
    - ❌ **禁止** 翻译语义内容。
    - ❌ **禁止** 改写文本核心意图。
    - ✅ **仅限** 执行结构封装、敏感符转义或添加 placeholder 隔离。
- **流转**：
  - 如果此步骤成功：使用修复后的内容（可能需要后续轻量化翻译或直接复用降级）。
  - 如果此步骤失败（解析依然异常，或模型拒绝响应）：立即终止 LLM 介入，流转至阶段 3。

### 阶段 3：决定性降级 (Deterministic Downgrade)
- **条件**：阶段 2 修复失败，或被限流阻断超过阈值的节点。
- **行为**：
  - 禁止任何 LLM 再度介入。
  - 从以下降级策略中确立单一产出：
    1. **原文直出 (Fallback to Source)**。
    2. **规则翻译 (Regex/Rule-based Translation)**（如仅替换显然的外部标签）。
    3. **Placeholder 替换 + 警告注释**（保留宏包依赖，但清空损坏内部文本以免编译崩盘）。
- **保障**：此阶段返回的字符串必须 100% 具备结构安全性与可编译性。

## 2. 并发与容错策略 (Concurrency & Resilience)
当前系统对于失败路径常有“放大”效应，即一批错误一起失败重试引发风暴。本设计通过调整并发拓扑来隔离风险。

### 2.1 重试与延迟上限 (Strict Retry Limitation)
- **无限 Retry 阻断**：完全移除任何基于 `while True` 的翻译重试机制。
- **被动限流 (HTTP 429) 限度**：针对大模型 API 频率限流，单 env **最多允许 1 次退避等待 (Wait+Retry)**，如果等待后仍为 429，立即视同修复失败，流转至阶段 3 降级。
- **禁止固定长时间休眠**：不允许出现为了消解 API QPS 压力而进行的未加限制的长程 `time.sleep(N)` 放大。

### 2.2 隔离并发模型 (Isolated Concurrency)
- **正常资源池** (`is_structure_safe == True`)：放开最大承载并发，多协程/线程满载运行，提升吞吐量。
- **受控串行队列** (`is_structure_safe == False`)：将高违规概率、极难啃的骨头压入独立的**串行执行队列**。以此抑制错误密集片段并发请求 LLM 导致的大面积死锁和重试风暴。

## 3. 输出契约 (Output Contract)
为了避免 Silent Failure（如被忽略丢失的内容段落），系统定义了如下输出标识机制：
- 每个处理完的 env 必须在其封装模型上附加显式标识：
  - `translation_status`：`SUCCESS` | `REPAIRED` | `DOWNGRADED`
  - `quality_flag`：如 `STRUCTURE_UNSAFE_BUT_PASSED`
- 产物在被聚合拼接回 `.tex` 文件前，会对这些 Flag 进行日志汇总，甚至可在原文件中用特定的 LaTeX Comment `% LaTeXTrans: DOWNGRADED` 预警用户。
