## Context
LaTeXTrans 当前使用 `asyncio.create_task()` 直接在事件循环中启动翻译任务。这在单用户单任务场景下可行，但存在严重的扩展性问题：
- 无并发上限 → 多任务同时编译 LaTeX 可能耗尽 16GB 内存
- Guest 文件无清理 → output 目录持续增长
- 登录用户无批量处理 → 需逐个提交翻译请求

### 约束条件
- 服务器内存仅 16GB
- LaTeX 编译引擎单次编译可能占用 500MB+
- 需保持现有单任务流程不变，向后兼容

## Goals / Non-Goals
### Goals
- 登录用户可同时提交多个翻译任务（最多 9 个活跃），互不干扰
- 登录用户可批量提交 arXiv ID（最多 9 个）
- 全局最多 3 个翻译并发执行，超出部分排队
- Guest 用户仅限单论文翻译，离开页面后不可重新访问
- 自动清理 Guest 用户的过期文件（TTL=2h）
- 多用户同时使用系统，任务间隔离

### Non-Goals
- 不引入外部消息队列（如 Redis/RabbitMQ），保持部署简单
- 不实现任务优先级
- 不实现分布式任务处理
- Guest 用户不需要配额限制（仅单论文翻译，无并发需求）

## 架构设计

### 1. 用户层级模型

```
┌─────────────────────────────────────────────────┐
│                    用户层级                       │
├─────────────────┬───────────────────────────────┤
│   Guest 用户     │   登录用户                     │
├─────────────────┼───────────────────────────────┤
│ 单论文翻译 ✅     │ 单论文翻译 ✅                   │
│ 批量翻译   ❌     │ 批量翻译 ✅（最多 9 个）         │
│ 任务历史   ❌     │ 任务历史 ✅                     │
│ 重新访问   ❌     │ 重新访问 ✅                     │
│ 配额限制   无     │ 配额限制 9 个活跃任务            │
│ 输出保留   2 小时 │ 输出保留 永久                   │
└─────────────────┴───────────────────────────────┘
```

### 2. 任务队列（TaskQueue）

```
TaskQueue (asyncio-native)
├── _semaphore: asyncio.Semaphore(3)                # 全局并发上限
├── _queue: asyncio.Queue()                         # FIFO 等待队列
├── _active_tasks: Dict[task_id, asyncio.Task]      # 运行中的任务
├── _user_task_count: Dict[user_id, int]            # 登录用户活跃任务计数
└── _worker_task: asyncio.Task                      # 队列消费者
```

**工作流程：**
1. `POST /translate/{task_id}` → 若已登录则检查配额 → 任务入队
2. Worker 循环从队列取任务 → 获取 semaphore → 运行翻译
3. 翻译完成 → 释放 semaphore → 用户计数 -1 → Worker 取下一个任务

**并发策略：**
- `MAX_CONCURRENT_TRANSLATIONS` = 3（全局并发上限）
- `MAX_USER_ACTIVE_TASKS` = 9（登录用户配额）
- Guest 用户不受配额限制（他们只能单论文翻译，自然不会形成并发压力）

### 3. Guest 输出清理（GuestCleanup）

**选择方案 B**：内存 TTL 追踪 + 定时清理任务

```
GuestTaskTracker
├── _guest_tasks: Dict[task_id, {created_at, expires_at}]
├── TTL: 2 hours
└── cleanup_interval: 30 minutes
```

**清理策略：**
1. 创建 Guest 任务时，记录 `task_id` 和 `expires_at = now + TTL`
2. 后台定时任务（每 30 分钟）扫描过期的 guest tasks
3. 对过期任务调用 `delete_task_full()` 清除 output + terms
4. TTL 窗口内，Guest 用户仍可在当前页面预览和下载（离开页面后无法再访问）

**服务重启降级：**
- Guest TTL 信息丢失 → 基于文件时间戳识别超过 TTL 的无主 output
- 比对 Supabase 中的 task_id 列表，不在其中的过期目录即为 Guest 残留

### 4. 批量翻译 API（仅登录用户）

```
POST /api/batch-translate            # 需要 Authorization header
{
  "arxiv_ids": ["2508.18791", ...],  // 最多 9 个
  "target_language": "zh",
  "source_language": "en",
  "advanced_config": { ... }
}
```

**配额示例：**
- 用户已有 3 个任务排队中 → 本次最多再批量 6 个
- 用户已有 9 个任务 → 返回 429
- Guest 调用此端点 → 返回 401

### 5. 前端 Guest 登录提示

在以下场景统一提示"请登录以使用该功能"：
- 访问批量翻译模式
- 访问历史记录 `/history`
- 访问设置 `/settings`
- （与现有 `user-auth` spec 的 Protected Features 保持一致）

### 6. 服务器重启后的队列恢复

重启后内存队列清空，但：
- 已完成的任务通过 Supabase + 文件系统恢复（现有逻辑）
- 进行中的任务标记为 `failed`（用户可重新提交）
- Guest 任务的 TTL 信息丢失 → 文件时间戳降级

## Risks / Trade-offs
- **风险**：asyncio.Semaphore 是进程内的，未来多实例需替换
  - 缓解：当前单实例部署，足够
- **风险**：Guest TTL 2 小时内用户离开页面后无法重访
  - 缓解：这是预期行为，前端明确提示
- **权衡**：不使用 Redis → 简单但仅限单实例
  - 理由：当前为单机部署，asyncio 原生队列足够

## 7. 后续迭代：UI 主题修复与文件批量上传

### 7.1 UI 主题兼容性修复

**问题**：`BatchTranslation.tsx` 和 `LoginPrompt.tsx` 使用了硬编码的暗色 Tailwind 类（`text-white`、`bg-white/5`、`border-white/10` 等），导致亮色模式下文字不可见。

**修复策略**：统一改用 shadcn/ui 的主题 CSS 变量：

| 原硬编码类 | 替换为 |
|---|---|
| `text-white` | `text-foreground` |
| `bg-white/5` | `bg-background` |
| `border-white/10` | `border-input` |
| `placeholder:text-white/25` | `placeholder:text-muted-foreground` |
| `text-white/70` | `text-muted-foreground` |

**原则**：所有颜色引用必须使用 CSS 变量，不允许在组件中硬编码 `white`/`black` 等绝对颜色。

### 7.2 批量文件上传（Batch File Upload Tab）

**新增功能**：在 `BatchTranslation.tsx` 中新增"文件批量上传"Tab，与"arXiv ID 批量"Tab 并列。

**设计要点：**

```
BatchTranslation
├── Tab: arXiv ID 批量（原有）
│   └── 多行文本框 → POST /api/batch-translate
└── Tab: 文件批量上传（新增）
    ├── 拖拽区域 / 文件选择按钮
    ├── 文件队列（FileList）：文件名 + 大小 + 删除按钮
    └── 提交按钮 → 并行 POST /api/upload × N → POST /api/translate/{task_id} × N
```

**限制：**
- 支持格式：`.zip .rar .tar.gz .tex`
- 单文件上限：50MB
- 批次上限：9 个文件

**并行处理策略（`Promise.all`）：**
- 所有文件同时开始上传，不串行等待
- 每个文件独立维护进度状态（`BatchTask[]` 按 index 更新）
- 上传完成后立即触发翻译，不等待其他文件

### 7.3 Output Reuse 下的进度竞态修复

**问题**：当系统检测到相同内容已有翻译结果（output reuse / 去重），`startTranslation` 调用会在返回前就将任务标记为 `completed`。原串行实现中 `pollTask` 在 `startTranslation` 之后才启动，导致前端永远看不到完成状态，进度卡住。

**修复**：在 `await startTranslation(...)` 之前提前调用 `pollTask(task_id, setUploadTasks)`，轮询与翻译启动并发执行。

```typescript
// 正确顺序（修复后）
pollTask(task_id, setUploadTasks)          // 先启动轮询
await startTranslation(task_id, config)    // 再触发翻译

// 错误顺序（修复前）
await startTranslation(task_id, config)    // 翻译可能瞬间完成
pollTask(task_id, setUploadTasks)          // 轮询启动时任务已结束，捕获不到
```

**`startTranslation` 返回后的状态保护**：仅在任务未处于终态（`completed`/`failed` 等）时才更新消息，避免覆盖已由轮询写入的完成状态。

### 7.4 `batch_translate` 端点 ImportError 修复

**问题**：`translate.py` 的 `batch_translate` 端点在函数体内动态导入了不存在的函数：
```python
from backend.app.api.routes.arxiv import download_arxiv_source  # ❌ 不存在
```

**根因**：`arxiv.py` 中没有 `download_arxiv_source` 函数，实际下载逻辑封装在 `_download_arxiv_background`（私有）和 `batch_download_arxiv_tex`（工具函数）中。

**修复**：
1. 在 `translate.py` 顶部静态导入正确的工具函数：
   ```python
   from backend.app.services.latex.utils import batch_download_arxiv_tex, extract_arxiv_ids
   ```
2. 在 `batch_translate` 端点内直接调用 `batch_download_arxiv_tex`，复用与 `arxiv.py` 相同的下载逻辑
3. arXiv ID 规范化：通过 `extract_arxiv_ids` 支持 URL 格式输入（如 `https://arxiv.org/abs/2401.00001`）

### 7.5 文件上传输出去重（Output Reuse）漏洞修复

**问题**：后端 `compute_config_hash` 原逻辑在 `arxiv_id` 为空时（本地上传）未将 `source_path` 纳入哈希计算。由于同用户的所有上传任务在 `config` 相同、且 `arxiv_id` 均为空时计算出的哈希完全一致，导致不同论文的翻译输出被误认为相同而相互覆盖。

**修复**：修改哈希计算逻辑，当 `arxiv_id` 不存在时，显式将 `source_path` 纳入哈希输入，确保每个独立上传任务拥有唯一的缓存标识。

## 8. 后续迭代：批量翻译可靠性增强

### 8.1 `batch_translate` 端点异步化（HTTP 阻塞修复）

**问题**：原实现在 HTTP 请求期间同步 `await asyncio.to_thread(batch_download_arxiv_tex, ...)` 下载每个 arXiv 论文，导致请求挂起数分钟，前端"提交中…"按钮长时间无响应。

**修复设计**：将下载与入队逻辑提取为独立的后台协程 `_download_and_enqueue()`，通过 `asyncio.create_task()` 在 HTTP 请求返回后异步执行。

```
POST /api/batch-translate
│
├── 循环 arxiv_ids
│   ├── create_task()                                  # 内存任务创建
│   ├── persist_task_if_needed()                       # 立即写入 Supabase（同步，快速）
│   └── asyncio.create_task(_download_and_enqueue())  # 后台异步下载
│
└── 立即返回 {batch_id, task_ids}                      # 1-2 秒内响应

_download_and_enqueue() [后台运行]
├── update_task(status=processing, "正在下载...")
├── asyncio.to_thread(batch_download_arxiv_tex)        # 阻塞 I/O 在线程池
├── update_task(status=pending, source_available=True)
└── task_queue.enqueue(run_translation)
```

**前端适配**：`handleArxivSubmit` 初始任务状态改为 `processing` + "等待下载..."，与后端实际状态对齐。

### 8.2 持久化失败重试与降级处理

**问题**：Supabase 网络不可用时，`persist_task_if_needed()` 静默失败，任务仅存在于内存中，服务重启后丢失，历史记录不可见。

**设计目标**：
- 网络抖动时自动重试，无需用户感知
- 持续不可用时：任务仍可正常翻译，但用户需知晓无法持久化
- 失败任务自动纳入 Guest 清理机制，避免文件泄漏

**重试机制**（`persist_task_with_retry`）：

```
persist_task_with_retry(task_id, retries=2, delay=5.0)
│
├── attempt 0: persist_task_if_needed()
│   ├── 成功 → return True
│   └── 失败 → sleep(5s)
├── attempt 1: persist_task_if_needed()
│   ├── 成功 → return True
│   └── 失败 → sleep(5s)
├── attempt 2: persist_task_if_needed()
│   ├── 成功 → return True
│   └── 失败 → 降级处理
└── 降级处理
    ├── guest_tracker.register(task_id)   # 纳入 TTL 清理
    └── task["persist_failed"] = True     # 内存标志，供前端检测
```

**调用时机**：`batch_translate` 端点首次 `persist_task_if_needed()` 失败时，立即通过 `asyncio.create_task()` 启动后台重试，不阻塞 HTTP 响应，与下载/翻译并发进行。

**前端警告机制**：
- `BatchTranslation.tsx` 的 `pollTask` 轮询时检测 `persist_failed` 字段（由 `GET /api/tasks/{task_id}` 返回）
- 首次检测到时弹出一次性 `toast.warning`（8 秒）："由于后端服务器网络问题，未能存入数据库，请注意保存翻译结果！"
- 使用 `warnedPersistFailed` ref（`Set<string>`）确保每个 task_id 只弹出一次

**降级后的清理保证**：
- 持久化失败的认证用户任务被注册进 `GuestTaskTracker`
- 现有的 `periodic_cleanup`（每 30 分钟）会自动清除其 output 和 terms 目录
- TTL 与 Guest 任务相同（默认 2 小时，可通过 `GUEST_TASK_TTL_HOURS` 配置）

## 9. 后续迭代：Dashboard 配置区域重设计与 BatchTranslation 组件化

### 9.1 Dashboard 配置区域重设计

**背景**：原实现在 Batch Tab 激活时隐藏 Advanced Configuration 和全局 Start 按钮，但这与实际架构不符——`AdvancedConfig` 组件直接读写 Zustand store，`BatchTranslation` 通过 props 从同一 store 读取 `advancedConfig`/`targetLanguage`/`sourceLanguage`，配置本质上是共享的。

**重设计方案**：

```
Dashboard 布局（所有 Tab 共享）
├── Tabs（ArXiv ID / Local Upload / Batch）
│   └── TabsContent（各 Tab 的输入区域）
├── Advanced Configuration（Collapsible，对所有 Tab 均显示）
│   └── AdvancedConfig 组件（直接读写 store）
└── 底部按钮区（根据 activeTab 动态切换）
    ├── activeTab ≠ 'batch' → <Button onClick={handleStart}>Start Translation</Button>
    └── activeTab = 'batch' → <Button onClick={batchRef.current?.submitCurrent()}>
                                  开始批量翻译 / 开始批量上传翻译（依内部子 Tab）
                              </Button>
```

**配置共享原则**：Advanced Configuration 中的语言设置、翻译模式、编译策略、API 配置等，对单论文翻译和批量翻译均生效，无需分别配置。

### 9.2 BatchTranslation 组件化（forwardRef + onStateChange）

**问题**：Dashboard 需要从外部触发 `BatchTranslation` 内部的提交逻辑，同时需要感知内部状态（是否可提交、是否提交中、当前子 Tab）以控制底部按钮的显示。

**方案选型**：

| 方案 | 优点 | 缺点 |
|---|---|---|
| `forwardRef` + `useImperativeHandle` | 命令式触发，接口清晰 | 需要额外机制同步状态 |
| 提升状态到 Dashboard | 状态集中管理 | 大量 props 下钻，耦合度高 |
| 事件总线 / Context | 解耦 | 过度设计 |

**选择方案**：`forwardRef` + `useImperativeHandle`（触发）+ `onStateChange` 回调（状态同步）

**接口设计**：

```typescript
// 暴露给父组件的命令式接口（仅触发，不读取状态）
export interface BatchTranslationHandle {
    submitCurrent: () => void  // 触发当前激活内部 Tab 的提交
}

// 通过回调同步给父组件的状态（触发重渲染）
export interface BatchTranslationState {
    isSubmitting: boolean
    activeTab: 'arxiv' | 'upload'
    canSubmit: boolean
}

// Props 新增
interface BatchTranslationProps {
    // ...原有 props
    onStateChange?: (state: BatchTranslationState) => void
}
```

**关键实现细节**：

1. **`onStateChange` 通过 `useEffect` 触发**（而非在 `useImperativeHandle` 中读取）：
   ```typescript
   useEffect(() => {
       onStateChange?.({ isSubmitting, activeTab, canSubmit })
   }, [activeTab, isArxivSubmitting, isUploadSubmitting, parsedIds.length, queuedFiles.length])
   ```
   原因：`ref.current` 的属性变化不触发 React 重渲染，必须通过回调将状态提升到父组件的 `useState`。

2. **`submitRef` 解决闭包陈旧问题**：
   ```typescript
   const submitRef = useRef<() => void>(() => {})
   submitRef.current = () => {
       if (activeTab === 'arxiv') handleArxivSubmit()
       else handleUploadSubmit()
   }
   useImperativeHandle(ref, () => ({
       submitCurrent: () => submitRef.current(),
   }), [])  // 依赖数组为空，避免旧闭包
   ```
   根因：若 `useImperativeHandle` 依赖数组为 `[activeTab]`，`handleArxivSubmit` 会被旧闭包捕获（`parsedIds` 为空时的版本），导致有内容时点击提交仍报"请输入至少一个 arXiv ID"。`submitRef` 每次渲染都更新为最新函数引用，彻底规避此问题。

3. **内部 Tab 改为受控**：`activeTab` 由 `useState` 管理，`Tabs` 组件使用 `value={activeTab}` + `onValueChange`，父组件可通过 `BatchTranslationState.activeTab` 感知当前子 Tab，从而动态调整底部按钮文案。

## 10. 后续迭代：上传目录 ArXiv ID 提取与标准化

### 10.1 问题背景

上传含 arXiv 文件名的压缩包（如 `arXiv-2602.17665v1.tar.gz`）时，解压后目录以随机 UUID 命名，导致：
- `uploads/` 目录混乱（`8f49429b-e4d7-4...`、`1039b72d-5fec-4...` 等 UUID 文件夹）
- 历史记录中任务标题仅显示 UUID 前 8 位，无法一眼识别论文
- 相同论文重复上传无法去重，每次都创建新的 UUID 目录
- 下游 `compute_config_hash` 无 `arxiv_id`，以 `source_path` 作为内容键，不同任务无法复用输出

### 10.2 现有逻辑（修改前）

`upload.py` 已有 arxiv_id 推断逻辑（正则 `(\d{4}\.\d{4,5})(v\d+)?`），从以下两处提取：
1. 上传的文件名（如 `arXiv-2602.17665v1.tar.gz`）
2. 解压后目录内的文件名

**已有行为**：仅在推断出 ID 且对应 `arxiv_XXXX.XXXXX` 目录**已存在**时复用旧目录、删除新上传。**不处理目录不存在的情况。**

### 10.3 修复方案

在现有 `if shared_upload_dir.exists()` 分支后新增 `else` 分支：

```
/api/upload 处理流程（修复后）
│
├── 解压文件到 UUID 目录
├── 正则提取 arxiv_id（文件名 → 目录内容）
│
└── if arxiv_id 推断成功:
    │
    ├── if arxiv_XXXX.XXXXX 已存在:
    │   └── 复用旧目录，删除 UUID 目录，更新 source_path/arxiv_id/source_type
    │
    └── else (新增):
        ├── shutil.move(UUID目录 → arxiv_XXXX.XXXXX)  # 原地重命名
        ├── 更新 source_path/arxiv_id/source_type="arxiv"
        └── 失败时静默回退（保留 UUID 目录，不影响后续流程）
```

### 10.4 连锁效果

| 场景 | 修复前 | 修复后 |
|---|---|---|
| 上传 `arXiv-2602.17665v1.tar.gz` | 目录为 `8f49429b-...` | 目录为 `arxiv_2602.17665` |
| 历史记录显示 | `8f49429b`（UUID 前8位） | `2602.17665`（论文 ID） |
| 再次上传同 ID 文件 | 创建新 UUID 目录 | 复用 `arxiv_2602.17665` |
| 下游翻译去重 | 以 `source_path` 计算哈希（每次不同） | 以 `arxiv_id` 计算哈希（相同논文一致） |
| 无 arXiv ID 的上传 | UUID 目录（不变） | UUID 目录（不变） |

**修改范围**：仅 `upload.py`，单文件单逻辑分支，单个上传和批量上传（均走 `/api/upload` 端点）统一覆盖。
