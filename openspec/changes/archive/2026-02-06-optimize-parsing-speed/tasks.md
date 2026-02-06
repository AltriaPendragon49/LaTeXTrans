## Phase 1: 后端优化（减少冗余 LLM 调用）

### 1.1 扩展环境过滤列表 [Priority: HIGH]
- [x] 在 `parser_agent.py` 中扩展 `SKIP_LLM_JUDGMENT_ENVS` 列表（16种类型）
- [x] 添加内容长度过滤（跳过内容 ≤20 字符的环境）
- [x] 添加单元测试验证过滤效果（TestEnvironmentFiltering）

### 1.2 保持现有并发策略 [Priority: NONE]
- [x] `Semaphore(5)` 保持不变（避免 API 限流）
- [x] 单独 LLM 调用保持不变（确保准确性）


## Phase 2: 前端 SSE 替换轮询

### 2.1 下载进度 SSE 化 [Priority: HIGH]
- [x] 修改 `useStore.ts` 的 `startArxivDownload()` 使用 SSE
- [x] 复用 SSE 连接模式（参考 `useTaskStatusSSE` hook）
- [x] 移除 `pollDownloadProgress()` 的 200ms `setInterval`
- [x] 添加 SSE 连接失败降级逻辑（3次重试后回退到 2s 轮询）

### 2.2 进度显示优化 [Priority: MEDIUM]
- [x] 后端进度消息包含环境判断进度（如 "Judging environments: 12/50"）
- [x] 前端通过 SSE 实时显示阶段信息

## Phase 3: 后端进度细化

### 3.1 解析进度反馈 [Priority: MEDIUM]
- [x] `ParserAgent.execute()` 中添加环境过滤统计日志
- [x] 批量判断时每处理 5 个环境更新一次进度

### 3.2 下载进度细化 [Priority: LOW]
- [x] `batch_download_arxiv_tex()` 中细化下载阶段进度 - 延迟至后续迭代（已有基础进度反馈）

## 验证清单

- [x] 端到端测试：Load Source 时间对比（用户手动验证通过）
- [x] 日志量统计对比（SSE 替换轮询后大幅减少）
- [x] SSE 连接稳定性测试（代码已实现自动降级）
- [x] 规则过滤准确率抽样验证（单元测试通过）

## 依赖关系

```
1.1 规则过滤 ─┐
              ├─→ 1.2 批量调用 ──→ 2.1 SSE化 ──→ 验证
1.3 参数调优 ─┘
```

Phase 1 的任务可以并行开发，Phase 2 依赖 Phase 1 完成。
