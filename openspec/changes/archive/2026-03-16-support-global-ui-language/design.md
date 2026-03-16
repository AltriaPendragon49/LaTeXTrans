# 设计：全局 UI 语言与工程硬化

## 1. i18n 资源策略
- 使用单 namespace 的扁平 key，继续保持 `keySeparator: false`
- 所有 locale 共享同一组语义化 key，避免使用中文整句或短词复用 key
- React 组件统一使用 `useTranslation().t`
- 非 React 模块统一使用 `i18n.t`

## 2. UI 文案分层
### UI Copy
- 按钮、标签、标题、空态、Toast、提示文案、a11y 文案统一走 i18n

### 结构化任务状态
- 前端主流程 UI 由 `status / stage / detail_code / detail_params / failure_reason_code` 驱动
- 集中映射由 `frontend/src/i18n/task-copy.ts` 负责
- 不再通过 `message.includes()` 或正则解析自然语言消息决定 UI

### 诊断文本
- 原始 `message` 与日志仅保留在日志/调试场景

## 3. 后端状态模型
- 在任务 API 与 SSE 中增加 `detail_code` / `detail_params`
- `message` 保留用于诊断兼容，不再作为前端主显示逻辑来源
- 任务状态更新在 `TaskManager` 内统一贯穿，减少页面层兜底逻辑

## 4. 前端工程治理
### 路由懒加载
- 对 `Layout` 及主页面路由使用 `React.lazy` + `Suspense`
- 目标是在功能不变前提下控制首屏 bundle 回归风险

### 稳定分包
- 在 Vite 中对 i18n、Supabase、Radix、图标、动画等依赖进行稳定 manual chunks
- 避免空 chunk、循环 chunk 和超大 chunk 告警

### 校验策略
- 前端：`lint`、`test`、`build`
- 后端：`pytest backend/tests -q`
- OpenSpec：`openspec validate support-global-ui-language --strict --no-interactive`
