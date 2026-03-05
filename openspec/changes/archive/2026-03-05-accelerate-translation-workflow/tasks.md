# Tasks: 加速 LaTeX 翻译工作流（受控修复版）

1. [x] **第一优先级：清除失败路径放大器（弃用旧语义）**
   - [x] 澄清 `services/agents/__init__.py` 中 `global_llm_semaphore` 仅作基础设施保护（Infra Guard），无业务调度权。
   - [x] 移除 `TranslatorAgent._call_llm_with_freeze` 中的 429 `while True` 无限退避重试循环，改为有界重试（最多3次）。
   - [x] 梳理外层 `Maxtry` 重试逻辑：在 `_retranslate_fail_parts` 中添加 `DOWNGRADE_STATUS` guard，确保 Phase 2 失败（排队超时、429弃权）的 env 不再被外层循环重新翻译。
2. [x] **第二优先级：引入 TokenRepairScheduler 并接管 Phase 2**
   - [x] 编写基于 Token 隔离的 `TokenRepairScheduler` 类（`repair_scheduler.py`）。
   - [x] 实现 per-token 的单向 FIFO 修复排队，确保针对特定 Token 同步串行。
   - [x] 实现每个 env 在队列中的"排队硬超时"限制（不包含 LLM 执行时间），超时直接降级。
   - [x] 完整测试覆盖（`test_token_repair_scheduler.py`，8 tests PASSED）。
3. [x] **第三优先级：保证 Phase 1 吞吐不被 Phase 2 阻塞**
   - [x] 引入阶段 0：结构变体检测机制 `structure_checker.py`（12 tests PASSED）。
   - [x] `run_phase1_gather` helper 完全独立于 Phase 2 队列。
4. [x] **第四优先级：实现单步受控 LLM 修复器 (Controlled Repairer)**
   - [x] 独立文件 `controlled_repair_agent.py`，独立测试（9 tests PASSED）。
   - [x] Prompt 绝对禁止翻译、禁止语义改写，仅限结构封装/转义。
   - [x] 最多 1 次 429 wait-and-retry，第 2 次 429 → `RepairRateLimitExceededError`。
5. [x] **第五优先级：实现阶段 3 确定性降级机制 (Deterministic Downgrade)**
   - [x] 实现 `downgrade_handler.py`：同步函数，零 LLM 调用，原文直出策略。
   - [x] 处理 `QueueTimeoutError`、`RepairRateLimitExceededError`、及任意 Phase 2 异常。
   - [x] 设置 `DOWNGRADE_STATUS` 标记，供 Maxtry guard 使用。
   - [x] 独立测试（`test_deterministic_downgrade.py`，11 tests PASSED）。
6. [x] **第六优先级：补充上下文与最终验证**
   - [x] 构建 Phase 2 → Phase 3 集成测试（`test_phase2_to_phase3_integration.py`，6 tests PASSED）。
   - [x] 验证 Token A 超时不影响 Token B（多 Token 并发隔离测试）。
   - [x] 验证 Maxtry guard 正确阻止 Phase 3 降级 env 的重试放大。
   - [x] 全量回归测试：**208 passed, 0 failures**。
7. [x] **第七优先级：前端进度看板精细化（UX 增强）**
   - [x] 重构 `Processing.tsx` 逻辑，解析后端 `message` 字段中的特定模式（B/C1/C2/A）。
   - [x] 实现“Validating Results”子状态动态映射，展示实时 `X/Y` 数字跳动。
   - [x] 实施“单向步进”保护，防止 UI 状态回退。
   - [x] 验证前端构建通过（`npm run build`）。
