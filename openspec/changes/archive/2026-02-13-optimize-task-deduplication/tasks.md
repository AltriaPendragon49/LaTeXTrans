# 任务去重与资源复用 - 任务列表

## Phase 1: Upload 共享与去重

### 1.1 arXiv 下载路径变更
- [x] 修改 `arxiv.py`: save_dir 从 `uploads/{task_id}/` 改为 `uploads/arxiv_{arxiv_id}/`
- [x] 修改 `arxiv.py`: source_path 指向 `uploads/arxiv_{arxiv_id}/{arxiv_id}/`
- [x] 验证 `is_already_downloaded()` 自动跳过已下载论文

### 1.2 上传文件去重
- [x] 在 `upload.py` 中添加 arxiv_id 推断逻辑（复用 `_infer_arxiv_id` 模式）
- [x] 若推断到 arxiv_id 且已有对应 uploads 目录，source_path 指向已有目录
- [x] 清理多余的临时上传目录

### 1.3 预览兼容性
- [x] 修改 `download.py`: `source_compiled_` PDF 缓存命名去掉 task_id
- [x] 验证 `preview_source_pdf` 在新路径结构下正常工作

---

## Phase 2: 删除保护

### 2.1 跳过 uploads 删除
- [x] 修改 `task_manager.py` `delete_task_full()`: 移除 uploads 目录删除逻辑
- [x] 验证删除历史后 uploads 内容保留

---

## Phase 3: 翻译结果复用

### 3.1 配置签名
- [x] 实现 `compute_config_hash()` 函数
- [x] 在启动翻译时计算并存储 config_hash

### 3.2 数据库变更
- [x] 添加 `config_hash` 列到 `translation_tasks` 表
- [x] 创建索引加速查询

### 3.3 Output 复用逻辑
- [x] 在 `translate.py` 翻译前查询匹配的已完成任务（admin client 跨用户）
- [x] 实现深拷贝 output 目录逻辑
- [x] 复用成功时更新 task 状态为 completed

---

## Phase 4: 延迟任务创建

### 4.1 TaskManager 延迟持久化
- [x] 修改 `create_task()`: 添加 `persist_to_db` 参数（默认 `False`）
- [x] 新增 `persist_task_if_needed()` 方法

### 4.2 上传/下载流程调整
- [x] 修改 `upload.py`: `create_task(persist_to_db=False)`
- [x] 修改 `arxiv.py`: `create_task(persist_to_db=False)`

### 4.3 翻译流程调整
- [x] 修改 `translate.py`: 翻译前调用 `persist_task_if_needed(task_id)`

---

## Phase 5: 上传失败清理

### 5.1 上传失败自动清理
- [x] 修改 `upload.py`: 添加 `upload_success` 标志
- [x] 在 `finally` 块中清理失败时创建的临时目录

---

## 测试验证

### 基础功能测试（Phase 1-3）
- [x] 手动测试：同一 arXiv ID 第二次 Load 秒级完成
- [x] 手动测试：删除历史后 uploads 保留
- [x] 手动测试：相同配置翻译秒级完成（深拷贝）
- [x] 手动测试：source-pdf 预览正常

### 延迟创建与清理测试（Phase 4-5）
- [x] 手动测试：上传/下载但不翻译 → Supabase 无新记录
- [x] 手动测试：点击翻译 → Supabase 首次创建记录
- [x] 手动测试：上传失败 → uploads 目录无残留临时目录
