# 变更：LangGraph 代理演进

## 动因
在加固了确定性翻译流水线（阶段 1-3）之后，编排逻辑仍然复杂且呈单体结构。采用 LangGraph 可以实现更细粒度的跨步骤编排，通过诊断循环更好地处理包冲突，并提供结构化的报告。此架构演进采用单架构迁移路径，按严格阶段顺序执行，绝不引入双架构并行或双机制对比。演进的核心在于工程结构重组，而非逻辑颠覆。

## 核心演进原则（不变量约束）
为了确保演进的安全性，本变更在工程实现上严格锁定以下原则：
1. **Phase 4a 迁移本质**：仅为**执行权的迁移**（由 coordinator 转向 StateGraph），绝对不是逻辑重写。
2. **Phase 4a 节点语义**：现有 agent 在 Phase 4a 中语义上已等价于 LangGraph node，**不进行全量 node 化改造**。LangGraph node 在该阶段仅作为执行边界，绝不承载新逻辑、不引入 retry、不做流程判断。
3. **Phase 4b 能力准入**：Phase 4b 的任何诊断能力必须被显式 gate（开关隔离），**默认不可达**。绝对不得通过“顺手扩展”的借口进入主流程。

## 变更内容与执行路径
本变更被严格拆解为以下 4 个顺序阶段，必须按序执行，严禁跨阶段混入：

### Step 1：Phase 4a — Coordinator → StateGraph 迁移
- **目标**：仅替换编排层（coordinator），由 StateGraph 完全接管执行顺序与失败路径。
- **约束**：现有 agent 逻辑保持绝对不变，不进行全量 node 化。采用单一 LangGraph 架构直接生效。
- **完成判据**：通过人工重跑一篇已通过的论文完成验证。验证目标是确认**行为、失败语义、降级路径与 Phase 4a 基线完全一致**，而不是对比新旧输出差异（禁止 shadow run）。

### Step 2：Phase 4b 准入条件实现（不引入新行为）
- **目标**：实现 Gate 4b-1 ~ 4b-4 的工程基础设施，使 Phase 4b 在工程上“可被拒绝 / 可被验收”。
- **包含内容**：
  - 定义明确的节点级 schema 与 I/O 契约。
  - 构建可回放的流转审计日志。
  - 注入资源与循环边界（最大轮次、超时策略）。
  - 编写并合入不变量守护测试（Guard Assertions）。
- **禁止**：此阶段绝对禁止引入 `DiagnosticNode`，禁止引入任何新推理或修复能力。

### Step 3：全量 agent → LangGraph node 结构化改造
- **前置条件**：仅在 Step 2 完全验收后执行。
- **目标**：将所有现有 agent 显式 node 化，封装到标准的 LangGraph 节点规范下。
- **作用**：仅用于接管资源隔离、审计边界落地和明确 I/O 契约。
- **约束**：绝对不引入任何新行为，不改变 Phase 4a 的既定执行语义！

### Step 4：Phase 4b 功能引入（Intelligent Diagnostics）
- **前置条件**：必须在前三步全部完成后才允许接入。
- **目标**：引入高阶封装的结构化诊断推理能力。
- **约束**：
  - Diagnostic / reasoning / suggestion 必须是独立节点。
  - 必须可配置启停，且**默认禁用**。
  - 绝对禁止字符级结修补，绝对禁止隐式的文档修改。
  - 所有可能改变文档的动作必须由明确的节点以白名单策略执行，全过程记录可审计、可回滚。

## 影响
- 影响的规格说明（Specs）：`langgraph-orchestration`。
- 影响的代码：
  - `backend/app/services/agents/langgraph_orchestrator.py` [新文件]
  - `backend/app/services/agents/coordinator_agent.py` [废弃/重构]
