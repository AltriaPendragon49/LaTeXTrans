## 1. 任务队列 & 并发控制
- [x] 1.1 在 `backend/app/services/task_manager.py` 中添加 `TaskQueue` 类（asyncio.Semaphore(3) + asyncio.Queue + worker）
- [x] 1.2 在 `TaskQueue` 中实现 `_user_task_count` 登录用户配额追踪（最多 9 个活跃任务/用户）
- [x] 1.3 添加配置项到 `config.py`：`MAX_CONCURRENT_TRANSLATIONS=3`, `MAX_USER_ACTIVE_TASKS=9`
- [x] 1.4 在 `config.py` 中添加 `TaskStatus.QUEUED` 状态枚举
- [x] 1.5 修改 `translate.py` 中的 `start_translation()` 端点：用 `task_queue.enqueue()` 替代 `asyncio.create_task()`
- [x] 1.6 登录用户入队前检查 `_user_task_count >= MAX_USER_ACTIVE_TASKS`，超出返回 HTTP 429
- [x] 1.7 新增 `GET /api/queue/status` 端点，返回活跃数/队列大小/最大并发/用户配额
- [x] 1.8 在 `main.py` startup 事件中初始化 `TaskQueue` 并启动 worker

## 2. Guest 输出清理
- [x] 2.1 在 `task_manager.py` 中添加 `GuestTaskTracker` 类（task_id → expires_at 映射）
- [x] 2.2 在 `config.py` 中添加 `GUEST_TASK_TTL_HOURS=2` 配置项
- [x] 2.3 修改 `TaskManager.create_task()`：若无 user_id，调用 `guest_tracker.register(task_id)`
- [x] 2.4 在 `main.py` startup 中注册定时清理后台任务（每 30 分钟，清理 outputs/ 和 terms/ 目录）

## 3. 批量翻译（仅登录用户）
- [x] 3.1 在 `translate.py` 中新增 `POST /api/batch-translate` 端点（需要 JWT 认证）
- [x] 3.2 批量端点：验证 arxiv_ids 数量 ≤ 9，检查用户配额，循环下载→创建任务→入队
- [x] 3.3 在 `api.ts` 中添加 `startBatchTranslation()` 和 `getQueueStatus()` 函数

## 4. 前端 UI
- [x] 4.1 新建 `LoginPrompt.tsx`：统一登录提示组件（含渐变登录按钮）
- [x] 4.2 新建 `BatchTranslation.tsx`：多行 arXiv ID 输入框 + 独立进度任务列表面板
- [x] 4.3 修改 `Dashboard.tsx`：添加 Batch Tab（登录用户显示 BatchTranslation，Guest 显示 LoginPrompt）
- [x] 4.4 修改 `Processing.tsx`：Guest 用户在页面顶部显示"离开后无法重访"警告横幅

## 5. Bug 修复与 UI 完善（后续迭代）
- [x] 5.1 修复 `BatchTranslation.tsx` 主题兼容性：将 `text-white`/`bg-white/5` 等暗色硬编码颜色改为 `text-foreground`/`bg-background`/`border-input` 等 CSS 变量，确保亮/暗模式均可见
- [x] 5.2 修复 `LoginPrompt.tsx` 主题兼容性：同上，改用主题 CSS 变量
- [x] 5.3 重写 `BatchTranslation.tsx`：新增文件批量上传 Tab（拖拽/多选/文件队列管理），支持 `.zip .rar .tar.gz .tex`，最多 9 个文件，单文件限 50MB
- [x] 5.4 修复 `translate.py` `batch_translate` 端点 ImportError：移除对不存在的 `download_arxiv_source` 的动态导入，改为在顶部静态导入 `batch_download_arxiv_tex` 和 `extract_arxiv_ids`，直接在端点内执行下载逻辑
- [x] 5.5 修复 `BatchTranslation.tsx` 文件上传进度问题：将串行上传改为 `Promise.all` 并行处理；在 `startTranslation` 调用前提前启动 `pollTask`，确保 output reuse（去重）导致任务瞬间完成时前端也能捕获到最终状态
- [x] 5.6 修复 `batch_translate` 端点 HTTP 阻塞问题：将 arXiv 下载从 HTTP 请求期间（串行 `await asyncio.to_thread`）移出，提取为独立的 `_download_and_enqueue()` 后台协程，通过 `asyncio.create_task()` 并发启动，端点立即返回 `task_ids`，前端按钮在 1-2 秒内解除"提交中…"状态
- [x] 5.7 修复 `batch_translate` 端点历史记录缺失：在创建任务后立即调用 `persist_task_if_needed(task_id)`，确保批量 arXiv 翻译任务写入 Supabase，在历史记录页面可见；同步更新前端初始状态显示（`processing` + "等待下载..."）以匹配后端实际状态
- [x] 5.8 实现持久化失败重试与降级处理：`task_manager.py` 新增 `persist_task_with_retry()` 异步方法（重试 2 次，间隔 5s）；首次失败时通过 `asyncio.create_task()` 后台重试；全部失败后注册进 `guest_tracker` 自动清除，并在内存任务中设置 `persist_failed=True`；前端 `BatchTranslation.tsx` `pollTask` 检测到该标志时弹出一次性 `toast.warning`："由于后端服务器网络问题，未能存入数据库，请注意保存翻译结果！"
- [x] 5.9 修复 `Processing.tsx` 任务 ID 读取与跳转延迟：改为优先从 URL 参数 `?taskId=` 读取（兼容 store），解决批量翻译"查看"按钮跳转后页面空白问题；同步修改 `History.tsx` `handleTaskClick` 改为 `navigate('/processing?taskId=...')`，消除依赖 store 异步更新导致的轮询延迟
- [x] 5.10 重设计 `Dashboard.tsx` 配置区域与底部按钮：恢复 Advanced Configuration 对所有 Tab（ArXiv ID / Local Upload / Batch）均可见（因 `AdvancedConfig` 直接读写 store，批量翻译通过 props 从同一 store 读取，配置本质共享）；底部按钮根据 `activeTab` 动态切换——非 Batch Tab 显示"Start Translation"，Batch Tab 显示"开始批量翻译"/"开始批量上传翻译"（依内部子 Tab 而定），提交中显示 Loader 动画，无内容时禁用
- [x] 5.11 重构 `BatchTranslation.tsx` 为 `forwardRef` 组件，修复批量翻译提交闭包陈旧 Bug：改用 `forwardRef` + `useImperativeHandle` 暴露 `submitCurrent()` 方法；新增 `onStateChange` 回调 prop，通过 `useEffect` 在 `isSubmitting`/`activeTab`/`canSubmit` 变化时通知父组件（解决 `ref.current` 不触发重渲染问题）；内部 Tab 改为受控（`activeTab` state）；用 `submitRef` 持有最新 submit 函数引用（`submitRef.current = () => { ... }`），`useImperativeHandle` 通过 `submitRef.current()` 调用，彻底消除依赖数组导致的旧闭包捕获问题（原因：`useImperativeHandle` 依赖数组为 `[activeTab]`，导致 `handleArxivSubmit` 捕获 `parsedIds` 为空时的旧闭包，点击提交时弹出"请输入至少一个 arXiv ID"错误）；移除 `BatchTranslation` 内部的两个提交按钮，改由 `Dashboard` 底部统一控制
- [x] 5.12 修复 arXiv 下载竞态条件与源路径异常：改进 `utils.py` 中的 `is_already_downloaded` 检查（确保 extracted 目录包含 .tex 文件）；在 `translate.py` 的 `run_translation` 中增加 `_ensure_source_path` 兜底逻辑，若 arXiv 源文件丢失则自动触发重新下载。
- [x] 5.13 修复文件上传输出去重（Output Reuse）漏洞：修改 `compute_config_hash` 函数，在 `arxiv_id` 为空（即本地上传）时，将 `source_path` 纳入哈希计算。解决不同上传论文因 `arxiv_id` 均为空而误判为内容相同、导致翻译结果相互覆盖的严重 Bug。
- [x] 5.14 优化批量上传 UI 体验：彻底重构 `BatchTranslation.tsx` 的 `handleUploadSubmit` 逻辑，取消预创建空 task_id 占位条目的做法；改为文件上传+启动翻译完全成功（获得真实 task_id）后再将任务展示到列表，彻底解决"上传中..."幽灵进度条卡死且无法自动消失的问题。
- [x] 5.15 完善 `upload.py` 上传目录 arxiv ID 提取与标准化：在已有 arxiv_id 推断逻辑（从文件名/目录内容正则提取）基础上，新增 `else` 分支处理"推断出 ID 但 `arxiv_XXXX.XXXXX` 目录不存在"场景——用 `shutil.move` 将 UUID 目录原位重命名为标准格式，并同步更新任务的 `source_path`/`arxiv_id`/`source_type`，重命名失败时静默回退保留 UUID 目录。效果：上传含 arXiv 文件名的压缩包后，`uploads/` 目录整洁（以 `arxiv_XXXX.XXXXX` 命名），历史记录以论文 ID 显示，后续相同论文上传可复用，下游去重哈希正确计算。
