# optimize-translation-pipeline

## Summary

优化翻译管道性能与错误处理机制，解决以下五个核心问题：

1. **并行解析优化**：将 `ParserAgent` 中 `Setting need_trans` 的串行 LLM 调用改为并行批处理
2. **状态推送机制**：用 Server-Sent Events (SSE) 替代低效的轮询机制
3. **错误分类体系**：建立 A/B/C 三类错误分类与对应处理策略
4. **确定性修复**：C 类结构一致性错误采用算法修复而非 LLM 重试
5. **会话连续性**：支持临时用户在不刷新前端的情况下创建新任务

## Why

根据生产日志分析：
- **20 秒** 消耗在串行 `Setting need_trans` 操作（每个 env 约 2.5 秒，8 个累计 20 秒）
- **76 秒** 用户感知卡顿来自轮询等待，非实际计算耗时（SSE 可将延迟从 2 秒降至 <100ms）
- 错误重试策略未区分错误类型，导致无效 LLM 调用
- A 类配置错误应降级处理而非中断流程
- C 类结构错误（`expected X, found Y`）无法通过翻译重试修复，需算法性修复
- C 类修复失败时应优先保留译文片段，而非直接回退原文
- 临时用户必须刷新页面才能创建新任务

## Status

- Stage: proposal
- Created: 2026-02-06
- Target: v1.1.0

## Related

- Spec: `latex-translation-core` (解析与校验逻辑)
- Spec: `web-api` (任务状态 API)
- Spec: `web-ui` (前端轮询与状态显示)

