# Change: 添加任务队列、并发控制与临时用户清理

## Why
当前系统存在三个核心问题：
1. **临时用户文件泄漏**：Guest 用户的翻译 output 永久存储在 `data/outputs/`，从不清理
2. **无并发控制**：`asyncio.create_task()` 直接启动翻译，无队列限制。多任务并发时可能耗尽 16GB 内存
3. **无批量翻译**：登录用户不支持一次提交多个 arXiv ID 的批量翻译

## What Changes
- **Guest 行为收窄**：Guest 仅可使用单论文翻译，不可使用批量翻译。离开翻译界面后任务不可重新访问。前端对批量/历史等受保护功能统一提示"登录以使用"
- **Guest 输出清理**：通过定时清理 + 内存 TTL 追踪，自动清除 Guest 用户过期的 output 文件（TTL=2h）
- **任务队列 & 并发控制**：引入 `asyncio.Semaphore(3)` + FIFO 队列，全局最多 3 个翻译并发执行
- **登录用户配额**：每个登录用户最多同时拥有 9 个活跃任务（排队中 + 执行中），无论逐个提交还是批量
- **批量翻译 API（仅登录用户）**：新增 `POST /api/batch-translate` 端点，接受最多 9 个 arXiv ID
- **上传 ArXiv ID 提取与标准化**：上传文件夹时自动从文件名/内容推断 arXiv ID，将 UUID 目录标准化命名为 `arxiv_XXXX.XXXXX`，任务自动关联 `arxiv` 类型并记录论文 ID，提升历史记录辨识度与资源复用率

## Impact
- Affected specs: `user-auth`, `web-ui`, 新增 `task-queue`, `guest-cleanup`, `batch-translation`
- Affected code:
  - `backend/app/services/task_manager.py` — 队列调度器、Guest TTL、用户配额
  - `backend/app/api/routes/translate.py` — 通过队列启动翻译、配额检查
  - `backend/app/api/routes/arxiv.py` — 批量下载支持
  - `backend/app/main.py` — 注册定时清理、启动队列
  - `backend/app/core/config.py` — 新配置项
  - `frontend/src/` — 批量翻译 UI（仅登录用户）、Guest 登录提示
