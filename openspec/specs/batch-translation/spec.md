# batch-translation Specification

## Purpose
定义批量翻译功能的 API 接口、前端界面、文件批量上传、arXiv 源码健壮性以及持久化重试机制，仅面向登录用户开放。
## Requirements
### Requirement: Batch Translation API
系统 SHALL 提供批量翻译接口，仅限登录用户使用，允许一次提交多个 arXiv 论文 ID。

#### Scenario: 登录用户提交批量翻译请求
- **WHEN** 登录用户向 `POST /api/batch-translate` 提交多个 arXiv ID
- **THEN** 系统为每个 ID 创建独立的翻译任务
- **AND** 所有任务加入翻译队列
- **AND** 返回 batch_id 和各任务的 task_id 列表

#### Scenario: Guest 用户无权使用批量翻译
- **WHEN** Guest 用户调用 `POST /api/batch-translate`
- **THEN** 系统返回 HTTP 401 Unauthorized
- **AND** 提示需要登录

#### Scenario: 批量翻译数量限制
- **WHEN** 用户提交的 arXiv ID 数量超过 9 个
- **THEN** 系统返回 HTTP 400 错误
- **AND** 提示单次批量最多 9 个

#### Scenario: 批量提交受用户配额约束
- **WHEN** 登录用户已有 K 个活跃任务
- **AND** 本次批量提交 N 个
- **AND** K + N > 9
- **THEN** 系统返回 HTTP 429 Too Many Requests
- **AND** 提示当前剩余可用配额为 9 - K

#### Scenario: 批量任务独立执行
- **WHEN** 批量中某个任务失败
- **THEN** 其他任务继续正常执行
- **AND** 每个任务状态独立可查

### Requirement: Batch Translation UI
前端 SHALL 提供批量翻译界面，仅对登录用户可用。

#### Scenario: 登录用户使用批量输入
- **WHEN** 登录用户切换到批量翻译模式
- **THEN** 显示多行输入框，可输入多个 arXiv ID（每行一个，最多 9 行）
- **AND** 显示配置选项（对所有任务统一配置）
- **AND** 显示提交按钮

#### Scenario: 查看批量任务进度
- **WHEN** 批量翻译任务提交后
- **THEN** 前端显示任务列表面板
- **AND** 每个任务显示独立的进度条和状态
- **AND** 完成的任务可直接点击预览/下载

### Requirement: Batch File Upload
前端 SHALL 提供文件批量上传模式，允许登录用户一次上传多个压缩包进行翻译。

#### Scenario: 登录用户上传多个压缩包
- **WHEN** 登录用户在文件批量上传 Tab 中选择或拖拽多个文件
- **THEN** 前端展示待上传文件队列（文件名、大小、删除按钮）
- **AND** 支持格式为 `.zip .rar .tar.gz .tex`，单文件限 50MB，最多 9 个

#### Scenario: 批量文件并行上传与翻译
- **WHEN** 用户点击"翻译 N 个文件"按钮
- **THEN** 前端清空待上传列表，进入提交状态
- **AND** 所有文件在后台并行上传
- **AND** 仅当单个文件上传成功并获得 `task_id` 后，才将其加入任务面板列表
- **AND** 直接显示"启动翻译…"并开始轮询，不再显示"上传中"的占位状态
- **NOTE** 消除中间状态旨在解决并行 setState 导致的 empty task_id 条目卡死（幽灵进度条）问题

#### Scenario: Upload Output Reuse Security
- **WHEN** 计算上传文件任务的 `config_hash` 时
- **AND** 任务无 `arxiv_id`（为本地上传）
- **THEN** 系统 MUST 将 `source_path` 纳入哈希计算
- **AND** 确保不同论文文件（即使 ID/文件名相似）不会碰撞相同的配置签名，防止翻译结果误用

#### Scenario: Output Reuse 下进度正确显示
- **WHEN** 上传的文件与已有翻译结果完全匹配（output reuse / 去重机制）
- **AND** 翻译任务在 `startTranslation` 返回前瞬间完成
- **THEN** 前端仍能正确显示"已完成"状态
- **AND** 不会卡在"上传中"或"翻译中"状态
- **NOTE** 实现方式：在调用 `startTranslation` 之前提前启动 `pollTask`，确保瞬间完成也能被捕获

### Requirement: ArXiv Source Robustness
系统 SHALL 确保 arXiv 源码在翻译前已完整就绪，并在意外丢失时提供自动恢复机制。

#### Scenario: 翻译前源码完整性检查
- **WHEN** 后端准备执行 arXiv 翻译任务
- **THEN** 系统 MUST 检查 `is_already_downloaded`
- **AND** 只有当解压目录存在且包含 `.tex` 文件时，才视为已就绪

#### Scenario: arXiv 源码丢失自动重下
- **WHEN** 任务记录存在但对应的 `source_path` 在磁盘上已失效
- **AND** 任务类型为 `arxiv`
- **THEN** 系统 SHALL 自动触发后台静默重下载
- **AND** 下载成功后更新任务路径并继续翻译，不报错中断任务

### Requirement: Batch arXiv Download Non-Blocking
系统 SHALL 在批量翻译端点中异步执行 arXiv 论文下载，不阻塞 HTTP 响应。

#### Scenario: 批量提交立即返回
- **WHEN** 登录用户向 `POST /api/batch-translate` 提交多个 arXiv ID
- **THEN** 系统在 1-2 秒内返回 `{batch_id, task_ids}`
- **AND** 每个任务的下载在后台协程 `_download_and_enqueue()` 中异步执行
- **AND** 前端初始显示任务状态为 `processing`（"等待下载..."）

#### Scenario: 后台下载完成后自动入队翻译
- **WHEN** `_download_and_enqueue()` 后台协程完成 arXiv 源码下载
- **THEN** 任务状态更新为 `pending`（source_available=True）
- **AND** 翻译任务自动加入 `TaskQueue` 等待执行

### Requirement: Batch Translation Persistence Retry
系统 SHALL 在 Supabase 写入失败时自动重试，并在全部失败时降级处理，确保用户得到明确提示。

#### Scenario: 持久化首次失败时后台重试
- **WHEN** `batch_translate` 端点调用 `persist_task_if_needed()` 失败
- **THEN** 系统通过 `asyncio.create_task()` 在后台启动 `persist_task_with_retry()`
- **AND** 重试最多 2 次，每次间隔 5 秒
- **AND** HTTP 响应不受影响，正常返回 task_ids

#### Scenario: 重试成功后任务正常持久化
- **WHEN** 后台重试期间 Supabase 网络恢复
- **THEN** 任务成功写入数据库
- **AND** 任务在历史记录中可见

#### Scenario: 全部重试失败后降级处理
- **WHEN** `persist_task_with_retry()` 所有重试均失败
- **THEN** 系统将该任务注册进 `GuestTaskTracker`（纳入 TTL 自动清理）
- **AND** 在内存任务中设置 `persist_failed=True` 标志
- **AND** 翻译任务仍正常执行，不受影响

#### Scenario: 前端检测到持久化失败并警告用户
- **WHEN** `BatchTranslation.tsx` 的 `pollTask` 轮询到 `persist_failed=True`
- **AND** 该 task_id 尚未弹出过警告
- **THEN** 前端弹出一次性警告 toast："由于后端服务器网络问题，未能存入数据库，请注意保存翻译结果！"
- **AND** 同一任务不重复弹出警告

### Requirement: Dashboard Configuration Sharing
Advanced Configuration SHALL 对所有翻译 Tab 均可见，配置在单论文翻译与批量翻译之间共享。

#### Scenario: 切换到 Batch Tab 时配置仍可访问
- **WHEN** 用户切换到 Batch Tab
- **THEN** Advanced Configuration 折叠面板仍然显示
- **AND** 用户可展开并修改语言、翻译模式、编译策略、API 等配置
- **AND** 修改后的配置对批量翻译任务生效

#### Scenario: 底部按钮根据 Tab 动态切换
- **WHEN** 用户处于 ArXiv ID 或 Local Upload Tab
- **THEN** 底部显示"Start Translation"按钮，触发单论文翻译
- **WHEN** 用户处于 Batch Tab
- **THEN** 底部显示批量提交按钮
- **AND** 按钮文案根据批量内部子 Tab 变化（arXiv ID 批量 → "开始批量翻译"，文件批量上传 → "开始批量上传翻译"）
- **AND** 无内容时按钮禁用，提交中显示 Loader 动画

### Requirement: BatchTranslation Component Interface
`BatchTranslation` 组件 SHALL 通过标准化接口与父组件通信，支持外部触发提交和状态感知。

#### Scenario: 父组件触发批量提交
- **WHEN** Dashboard 底部按钮被点击（activeTab = 'batch'）
- **THEN** 通过 `batchRef.current.submitCurrent()` 触发 `BatchTranslation` 内部当前激活子 Tab 的提交逻辑
- **AND** 提交使用最新的输入内容（无闭包陈旧问题）

#### Scenario: 批量翻译状态同步到父组件
- **WHEN** `BatchTranslation` 内部的 `isSubmitting`/`activeTab`/`canSubmit` 任一发生变化
- **THEN** 通过 `onStateChange` 回调通知父组件
- **AND** 父组件的 `batchState` state 更新，触发重渲染
- **AND** 底部按钮的禁用状态、文案、图标随之更新
- **NOTE** 实现方式：`useEffect` 监听相关状态变化并调用 `onStateChange`，而非通过 `ref.current` 属性读取（后者不触发重渲染）

### Requirement: ArXiv ID Extraction for Uploads
系统 SHALL 自动从上传的文件夹/压缩包中推断 arXiv ID，并标准化存储路径。

#### Scenario: 从文件名推断 ArXiv ID 并标准化
- **WHEN** 用户上传一个包含 arXiv ID 格式文件名的压缩包（如 `arXiv-2602.17665.tar.gz`）
- **THEN** 系统 MUST 提取该 ID
- **AND** 若对应标准化目录 `arxiv_{id}` 尚不存在，使用 `shutil.move` 将解压后的 UUID 目录重命名为 `arxiv_{id}`
- **AND** 更新任务的 `source_type` 为 `arxiv`
- **AND** 记录任务的 `arxiv_id`
- **AND** 历史记录标题应显示论文 ID 以便识别

#### Scenario: 从目录内容推断 ArXiv ID
- **WHEN** 上传文件名不带 ID，但解压后的目录包含识别度高的 arXiv 文件（如 `2602.17665.tex`）
- **THEN** 系统 SHALL 尝试从中推断 ID 并执行相同的标准化重命名逻辑

#### Scenario: 标准化目录已存在时复用
- **WHEN** 提取出 arXiv ID 后发现 `arxiv_{id}` 目录已存在
- **THEN** 系统 MUST 复用已有目录并删除新上传的内容
- **AND** 更新新任务的 `source_path` 指向已有目录
- **AND** 确保 `compute_config_hash` 能正确命中已有翻译结果（Output Reuse）

#### Scenario: 推断失败时的健壮性
- **WHEN** 无法推断 arXiv ID 或重命名操作失败
- **THEN** 系统 SHALL 保留原始 UUID 目录方案
- **AND** 任务保持 `folder_upload` 类型
- **AND** 整个流程不应因为重命名失败而中断

