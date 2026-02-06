# Tasks: optimize-translation-pipeline

## 阶段一：并行解析优化

- [x] 1.1 新增 `_request_llm_for_judge_async()` 异步方法
  - 使用 `aiohttp` 替代 `requests`
  - 添加 `asyncio.Semaphore(5)` 并发控制
- [x] 1.2 重构 `ParserAgent.execute()` 为 `async`
  - 使用 `asyncio.gather()` 并行调用
  - 异常处理：单个失败返回默认值 `True`
- [x] 1.3 更新 `CoordinatorAgent` 适配 async 调用
- [x] 1.4 编写并行解析单元测试

## 阶段二：错误分类体系

- [x] 2.1 新增 `classify_error()` 函数
  - A 类：资源/配置缺失
  - B 类：可修复语法错误
  - C 类：结构一致性错误
- [x] 2.2 扩展 `error_report` 格式，添加 `error_type` 字段
- [x] 2.3 修改 `TranslatorAgent` 重试逻辑
  - A 类：触发降级处理（如加载空术语表），不中断流程
  - B 类：允许最多 1 次翻译重试
  - C 类：进入算法修复路径
- [x] 2.4 编写错误分类单元测试

## 阶段三：C 类确定性修复

- [x] 3.1 实现 `apply_structural_fix()` 方法
  - Token 补齐逻辑
  - 占位符恢复逻辑
- [x] 3.2 实现修复失败降级策略
  - 优先保留现有译文片段
  - 译文缺失时才回退使用原文片段
- [x] 3.3 集成到 `TranslatorAgent` 错误处理流程
- [x] 3.4 编写结构修复单元测试

## 阶段四：SSE 状态推送

> **SSE (Server-Sent Events)** 是 HTML5 标准技术，允许服务器主动推送数据，相比轮询：延迟从 2 秒降至 <100ms，HTTP 请求数从 38 次降至 1 次连接。

- [x] 4.1 新增 `GET /api/task/{task_id}/stream` SSE 端点
  - 返回 `StreamingResponse` 类型
  - 任务完成/失败时自动关闭连接
- [x] 4.2 前端新增 `useTaskStatusSSE` hook
  - 使用 `EventSource` 订阅
  - 实现自动重连逻辑
- [x] 4.3 实现轮询降级策略
  - SSE 连接失败时回退到 `setInterval` 轮询
- [x] 4.4 验证 SSE 端点在浏览器中正常工作

## 阶段五：会话连续性

- [x] 5.1 前端新增 `resetTranslationState()` 函数
  - 清除 `taskId`、`taskStatus`、`progress` 等状态
  - 关闭现有 SSE 连接
- [x] 5.2 添加"新建翻译"按钮
  - 翻译完成/失败后显示
  - 点击调用 `resetTranslationState()`
- [x] 5.3 验证不刷新页面可连续创建多个任务

## 阶段六：Spec 更新与验证

- [x] 6.1 更新 `latex-translation-core/spec.md`
  - 新增并行解析场景
  - 新增错误分类与修复场景
- [x] 6.2 更新 `web-api/spec.md`
  - 新增 SSE 端点规范
- [x] 6.3 更新 `web-ui/spec.md`（如适用）
  - 新增会话连续性场景
- [x] 6.4 运行 `openspec validate optimize-translation-pipeline --strict`
