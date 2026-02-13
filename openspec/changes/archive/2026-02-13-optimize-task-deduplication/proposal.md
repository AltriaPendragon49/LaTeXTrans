# 任务去重与资源复用优化提案

## 变更概述

优化 Upload 和 Output 资源复用机制，避免重复下载论文和重复翻译，提升处理速度和用户体验。

## 背景

当前系统**不做去重**：
- 每次 ArXiv ID：`create_task()` → 新 UUID → `uploads/{task_id}/` → 全新下载
- 即使同一论文、配置完全一致，也会从头翻译
- 删除历史记录时清理 uploads 目录，浪费已下载的资源

**核心洞察**：
- Upload 内容与用户无关（同一论文对所有用户都一样），可跨用户共享
- 翻译结果仅与「论文源 + 翻译配置」相关，配置一致则结果一致

## 目标

### 1. Upload 共享与去重（Load 加速）

以 `arxiv_id` 为 key，将上传目录从 `uploads/{task_id}/` 改为 `uploads/arxiv_{arxiv_id}/`：
- **arXiv 下载**：检查目录是否已存在 → 存在则跳过下载，新任务 `source_path` 指向已有目录
- **文件上传**：上传后尝试从目录/文件名推断 arxiv_id → 若已存在相同 ID 的 upload，`source_path` 指向已有目录

### 2. 删除保护

删除历史记录时**禁止删除 uploads 目录**，仅删 outputs/terms。uploads 作为共享缓存保留，加速后续 Load。

### 3. 翻译结果复用（Output 加速）

启动翻译前，查询所有用户的已完成任务（跨用户），检查是否存在：
- 相同 `arxiv_id`（或相同 `source_path`）
- 相同翻译配置：`source_language`, `target_language`, `translation_mode`, `compile_strategy`, `enable_verification`

若完全一致 → **深拷贝已有 output 目录**到新任务，跳过翻译流程。

### 4. 延迟任务创建（数据库清洁）

上传/下载阶段**仅创建内存任务**，不写 Supabase 数据库记录。只有用户**点击翻译**时才首次创建数据库记录：
- 上传失败 → 不会在数据库中留下垃圾记录
- 下载失败 → 不会在数据库中留下垃圾记录
- 上传/下载成功但未翻译 → 数据库无记录

### 5. 上传失败清理（文件系统清洁）

上传处理过程中若发生失败（格式校验、LaTeX 校验等），**自动删除已创建的临时上传目录**，避免在 `uploads/` 中累积大量无效缓存。

## 关键设计原则

> [!IMPORTANT]
> **Upload ≠ Output**
> - Upload 是公共资源（论文源码），跨用户共享，不可删除
> - Output 是翻译结果，深拷贝后独立于原任务，可安全删除

> [!IMPORTANT]
> **延迟持久化**
> - 上传/下载阶段仅创建内存任务，不写数据库
> - 翻译阶段首次持久化到 Supabase
> - 保证数据库中只有真正翻译过的任务

> [!WARNING]
> **跨用户 Output 查询需要调整 RLS**
> - 当前 Supabase RLS 限制用户只能查询自己的 `translation_tasks`
> - Output 复用查询需要用 admin client 绕过 RLS，或添加新的 RLS 策略
> - 方案：后端使用 service_role key 查询，不暴露其他用户数据给前端

## 技术方案

### Upload 存储结构调整

```
data/uploads/
├── arxiv_2508.18791/      # 以 arxiv_id 为 key（arXiv 论文）
│   ├── main.tex
│   ├── 2508.18791.pdf     # 源 PDF
│   └── figures/
├── arxiv_2401.12345/      # 不同论文
│   └── ...
└── {task_id}/             # 非 arXiv 上传保持原结构
    └── ...
```

### 翻译配置签名

```python
# 用于 output 复用比对的字段
config_signature_fields = [
    "arxiv_id",           # 或 source_path
    "source_language",
    "target_language",
    "translation_mode",
    "compile_strategy",
    "enable_verification"
]
# 生成 hash 用于快速查询
config_hash = hashlib.md5(json.dumps(sorted_config).encode()).hexdigest()
```

### 流程图

```mermaid
flowchart TD
    A[用户提交 ArXiv ID] --> B{检查 uploads/arxiv_{id}/ 是否存在}
    B -->|已存在| C[跳过下载, source_path 指向已有目录]
    B -->|不存在| D[下载论文到 uploads/arxiv_{id}/]
    D --> C
    C --> E[用户点击翻译]
    E --> F{查询已完成任务: 同论文 + 同配置}
    F -->|找到匹配| G[深拷贝 output 目录到新任务]
    F -->|未找到| H[启动翻译流程]
    G --> I[标记完成]
    H --> I
```

## 受影响模块

| 模块 | 影响 |
|------|------|
| `arxiv.py` | 修改 save_dir 参数为 arxiv_id-based 路径；延迟持久化 |
| `upload.py` | 添加 arxiv_id 推断和去重逻辑；延迟持久化；失败清理 |
| `translate.py` | 添加 output 复用检查逻辑；首次持久化到数据库 |
| `task_manager.py` | 删除保护；添加 `persist_to_db` 参数和 `persist_task_if_needed()` 方法 |
| `download.py` | 调整 `source_compiled_` PDF 缓存命名（不依赖 task_id） |
| `translation_tasks` 表 | 添加 `config_hash` 字段用于快速查询 |
| Supabase RLS | 后端使用 admin client 查询跨用户 output |

## 验证计划

### 自动化测试
1. 单元测试：config_hash 生成一致性
2. 集成测试：arXiv 去重（同一 ID 第二次跳过下载）
3. 集成测试：output 复用（相同配置复制而非重翻译）

### 手动测试
1. 两次提交同一 arXiv ID → 第二次秒级完成 Load
2. 翻译后删除历史 → uploads 目录保留
3. 再次翻译同一论文同配置 → 秒级完成翻译（深拷贝）
4. 预览 source-pdf 功能正常（路径变更不影响）
5. 上传/下载但不翻译 → Supabase 无新记录
6. 点击翻译 → Supabase 首次创建记录
7. 上传失败 → uploads 目录无残留的临时目录
