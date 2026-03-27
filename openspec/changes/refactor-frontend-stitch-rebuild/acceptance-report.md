# Stitch Frontend 重构验收报告（全流程复测）

- 验收日期: 2026-03-27
- 验收方式: 真实浏览器（Playwright）+ 本地真实前后端联调
- 前端: `http://127.0.0.1:5173`
- 后端: `http://127.0.0.1:9001`
- 验收目标: 全流程可跑通、关键按钮可点击有效、前后端联调可用

## 1. 本轮结论

- 结论: **部分通过（仍有阻断项）**
- 通过概览:
  - 社区首页核心浏览与搜索跳转可用
  - `/agent` 入口、会话页核心交互可用
  - Paper Detail 页面已无崩溃，下载按钮可用
  - Tools Hub 多面板可进入，设置保存可用，翻译任务可成功提交
- 失败概览:
  - 首页 `New Project` 按钮仍无效（无跳转）
  - 真实翻译任务最终仍失败于编译阶段（`failed_compilation`）

## 2. 成功验收项

### 2.1 社区首页与路由

- 首页加载与论文流拉取正常:
  - `GET /api/papers?sort=latest` 200
  - `GET /api/papers?sort=hot` 200
- `Hot / Latest / Filters` 可点击，页面状态正常
- 首页 `Search` 可用:
  - 输入后跳转到 `/agent/{conversationId}`
  - 观测到 `GET /api/community-agent/conversations` 200
- 侧边栏 `/agent` 入口可用:
  - 从 `/agent` 自动进入 `/agent/{conversationId}`，非白屏

### 2.2 Paper Detail 页面

- 社区论文卡片点击可进入详情页:
  - 示例: `/paper/a4960207-1695-46b2-838c-1d168e8fd661`
- 之前崩溃点已修复:
  - 未再出现 `ReferenceError: Download is not defined`
- 译文论文下载按钮可用（真实下载触发）:
  - 示例论文: `/paper/9ecee3a1-e926-4b90-b1a3-a1aab3d86aee`
  - 下载文件名:
    - `2603.12111-0326-1711-42e86b1b-2368-423c-8f39-c913e26abce4-zh_2603.12111.pdf`

### 2.3 Tools Hub 与后端联调

- 面板入口可访问:
  - `开始翻译` `/tools?panel=translate`
  - `翻译历史` `/tools?panel=history`
  - `系统设置` `/tools?panel=settings`
  - `术语库管理` `/tools?panel=glossary`
- 设置保存可用:
  - `PUT /api/settings` 200
- arXiv 导入与翻译提交流程可启动:
  - 测试论文: `1706.03762`
  - `POST /api/arxiv` 200
  - `POST /api/translate/1706.03762-0327-1905-d254250b-8242-415d-bcad-12cb93eda1ec` 200
  - `GET /api/task/{task_id}/stream` 200

### 2.4 Agent 页面（社区助手）

- 新建对话可用:
  - 点击 `新建对话` 后跳转并生成新 `conversationId`
- 运行助手可用:
  - `POST /api/community-agent/runs` 202
  - `GET /api/community-agent/runs/{run_id}/events` 200
  - 页面出现分步进度与最终回答
- 删除对话可用:
  - `DELETE /api/community-agent/conversations/{id}` 200

### 2.5 全局界面控件

- 语言切换可用（中文 <-> English）
- 主题切换可用（Day / Dark）

## 3. 失败项

### 失败 1: 首页 `New Project` 按钮仍无效

- 现象:
  - 点击 `New Project` 后 URL 仍停留在 `/`
  - 未跳转到 `/agent/{conversationId}`
- 复测证据:
  - 浏览器捕获到的 API 请求仅有 `GET /api/papers?sort=latest`
  - 未观察到预期会话相关请求（如 `community-agent/conversations` 的新建链路）
- 影响:
  - 首页关键转化入口不可用

### 失败 2: 翻译任务最终编译失败

- 任务 ID:
  - `1706.03762-0327-1905-d254250b-8242-415d-bcad-12cb93eda1ec`
- 最终状态:
  - `failed_compilation`
- 错误摘要:
  - `xelatex` 失败（`exit code 125`）
  - `lualatex` 失败（`exit code 125`）
  - 文件: `ms.tex`
- 影响:
  - 前后端“可提交、可处理、可追踪”已打通，但“最终产出 PDF”未形成闭环

## 4. 关键证据

- 后端日志:
  - `.tmp-backend-acceptance.out.log`
  - `.tmp-backend-acceptance.err.log`
- 前端启动日志:
  - `.tmp-frontend-acceptance.out.log`
- 下载证据（Playwright 输出目录）:
  - `C:\Users\xhs\AppData\Local\Temp\playwright-mcp-output\1774607076865\2603-12111-0326-1711-42e86b1b-2368-423c-8f39-c913e26abce4-zh-2603-12111.pdf`

## 5. 复测后状态对比（相对上一轮）

- 已确认修复:
  - `/agent` 入口可用（不再白屏）
  - 首页 `Search` 可正常跳转到会话页
  - Paper Detail 不再崩溃，下载按钮有效
- 仍未修复:
  - 首页 `New Project` 无效
  - 翻译最终编译失败（本轮更换论文后仍复现）
