# optimize-parsing-speed

## Status
IMPLEMENTING

## Problem Statement
用户反馈前端点击 "Load Source" 后加载过程非常慢（可能需要 1-2 分钟），同时日志充满了高频轮询请求。

经过详细分析，发现三个核心问题：

1. **真正的性能瓶颈**：`ParserAgent._judge_envs_parallel()` 对每个需要判断是否翻译的 LaTeX 环境调用 LLM API，并发限制为 5。复杂论文可能有几十个环境，每个 LLM 调用最多 100 秒超时。

2. **日志爆炸**：前端使用 `setInterval(200ms)` 轮询下载进度，虽然后端已实现 SSE 端点但下载逻辑未使用。

3. **感知问题**：高频轮询给用户造成"系统繁忙但无进展"的错觉。

## User Review Required

> [!NOTE]
> 用户反馈：
> - ❌ 不采用方案 A（规则引擎替代 LLM）
> - ❌ 不采用方案 C（异步判断 + 乐观加载）
> - ⚠️ 方案 B 有风险：批量合并可能导致语境混淆，提高并发可能触发 API 限流

> [!IMPORTANT]
> 采用**保守优化策略**：保留现有单独 LLM 调用逻辑，仅优化冗余判断 + SSE 替换轮询。

## Proposed Solution

### Phase 1: 减少冗余 LLM 调用（保守优化）
1. **消除重复判断**：`parser.py:_extract_envs()` 已通过 `no_translate_envs` 列表标记不需翻译的环境，但 `ParserAgent._judge_envs_parallel()` 会对 `need_trans=True` 的环境再次调用 LLM。应在 `execute()` 中过滤掉 `abstract`/`itemize` 以外的更多明确类型。
2. **保持并发限制 5 不变**：避免触发 API 限流
3. **保留单独 LLM 调用**：不做批量合并，确保判断准确性

### Phase 2: 前端轮询优化
1. 下载进度使用已有的 SSE 端点 (`/api/task/{id}/stream`)
2. 移除 200ms 固定轮询，使用 SSE 实时推送
3. 添加 SSE 回退机制（连接失败时降级为 1-2 秒轮询）

### Phase 3: 进度反馈增强
1. 细化进度阶段（下载 → 解压 → 解析 → 判断环境）
2. 显示当前正在处理的文件/环境数量

## Impact Analysis

### Changed Components
- `backend/app/services/agents/parser_agent.py` - 批量/规则优化
- `frontend/src/store/useStore.ts` - SSE 替换轮询
- `backend/app/api/routes/arxiv.py` - 进度细化

### Risks
- 批量 LLM 调用可能因 token 限制导致截断
- SSE 连接在某些网络环境可能不稳定

## Success Criteria
- Load Source 时间减少 50%+ 
- 日志量减少 80%+
- 用户能够看到细化的进度状态
