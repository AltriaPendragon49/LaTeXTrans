# 任务：LangGraph 代理演进

## Step 1：Phase 4a — Coordinator → StateGraph 迁移
- [ ] 构建单一 `StateGraph` 骨架并直接替换现状编排层，由其接管解析、翻译、验证、编译的执行顺序与失败路径。
- [ ] 保持现有 agent 逻辑完全不变，仅将现有方法连接到执行边界位置，坚决不进行全量 node 化。
- [ ] 人工重跑一篇已通过的论文作为验证，确认其行为、失败语义及降级路径与 Phase 4a 基线完全一致。

## Step 2：Phase 4b 准入条件实现（准入基础设施）
- [ ] 为 LangGraph 执行通道定义严格的强类型（Pydantic）输入/输出 Schema，搭建基于 JSONL 的可回放审计日志（Gate 4b-1）。
- [ ] 在状态机 conditional edges 中注入硬性的最大执行轮次限制与超时上下文拦截器（Gate 4b-2）。
- [ ] 编写并合入不可变守护测试套件（Guard Assertions），硬性锁定 freeze/guard 及 Stage 3 sanitizer 的不可侵犯行为，防止被绕过（Gate 4b-4）。
- *（注：此阶段严禁引入任何 DiagnosticNode 逻辑或新推理能力）*

## Step 3：全量 agent → LangGraph node 结构化改造
- [ ] 将所有现有 agent 显式 node 化，封装为标准的 LangGraph 节点结构。
- [ ] 对接 Step 2 的准入基础设施，全面落实资源隔离、流转审计记录和明确的 I/O 契约。
- [ ] 进行回归运行，验证全量 node 化后未引入任何新行为，完全继承 Phase 4a 核心语义。

## Step 4：Phase 4b 功能引入（Intelligent Diagnostics）
- [ ] 实现独立且功能明确的 `CompilationDiagnosticNode`，且须默认配置特性开关（Feature Flag）为关闭状态（Gate 4b-3）。
- [ ] 限制新增节点仅能输出纯结构化诊断建议，在链路层级绝对封杀并禁止字符级内容预修补和隐式文档修改。
- [ ] 配置并验证受控白名单内的修改动作，确认其可审计性与可回滚性保障到位，并验证安全降级路径有效。
