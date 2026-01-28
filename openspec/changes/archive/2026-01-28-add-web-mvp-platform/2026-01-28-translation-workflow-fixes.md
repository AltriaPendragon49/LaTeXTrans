# 后端翻译工作流修复总结

**日期**: 2026-01-28  
**类型**: Bug 修复  
**范围**: Backend Translation Workflow  
**状态**: 已完成，等待功能测试

> [!NOTE]
> 本文档记录了第一轮修复（7个问题）。第二轮关键修复请参见：
> [`2026-01-28-critical-bugfixes.md`](./2026-01-28-critical-bugfixes.md)

## 概述

在测试后端翻译功能时，发现了一系列阻止翻译工作流正常运行的问题。本次修复解决了 7 个关键问题，使翻译工作流能够从 arXiv 下载、文件解压、LaTeX 解析一直运行到翻译任务初始化。

## OpenSpec 符合性说明

根据 `openspec/AGENTS.md` 第 36-42 行的指导原则：

> Skip proposal for:
> - Bug fixes (restore intended behavior)
> - Typos, formatting, comments
> - Dependency updates (non-breaking)
> - Configuration changes
> - Tests for existing behavior

本次修复属于 **Bug fixes (restore intended behavior)**，因此不需要创建 OpenSpec change proposal。所有修复都是为了恢复预期的系统行为，没有引入新功能或破坏性更改。

## 修复的问题

### 1. arXiv 下载目录不存在

**问题描述**:  
后端尝试下载 arXiv `.tar.gz` 文件时，因目标目录不存在而失败。

**错误信息**:
```
Failed to download arXiv paper: [Errno 2] No such file or directory
```

**根本原因**:  
`download_tex` 函数在保存文件前没有创建父目录。

**修复方案**:
- 文件: `backend/app/services/latex/utils.py`
- 行号: 774-803
- 修改: 添加 `os.makedirs(save_dir, exist_ok=True)` 在写入文件前

```python
# 在保存文件前创建目录
os.makedirs(save_dir, exist_ok=True)
tar_gz_path = os.path.join(save_dir, f'{arxiv_id}.tar.gz')
with open(tar_gz_path, 'wb') as f:
    f.write(content)
```

---

### 2. tar.gz 文件未解压

**问题描述**:  
arXiv 下载成功，但 `.tar.gz` 文件没有被解压，导致翻译阶段找不到 `.tex` 文件。

**错误信息**:
```
Translation error: No .tex files found in ...
```

**根本原因**:  
`download_tex` 函数只下载了文件，但没有解压逻辑。

**修复方案**:
- 文件: `backend/app/services/latex/utils.py`
- 行号: 774-803
- 修改: 添加 `tarfile` 解压逻辑

```python
# 解压 tar.gz 文件
with tarfile.open(tar_gz_path, 'r:gz') as tar:
    tar.extractall(path=arxiv_dir)
    logger.info(f"[SUCCESS] {arxiv_id} extracted to {arxiv_dir}")

# 删除原始 tar.gz 文件
os.remove(tar_gz_path)
```

---

### 3. CoordinatorAgent 初始化参数不匹配

**问题描述**:  
创建 `CoordinatorAgent` 时传递了错误的参数格式，导致初始化失败。

**错误信息**:
```
TypeError: CoordinatorAgent.__init__() got an unexpected keyword argument 'llm_config'
```

**根本原因**:  
`CoordinatorAgent` 构造函数期望一个统一的 `config` 字典，但代码传递了分离的 `llm_config`, `target_lang` 等参数。

**修复方案**:
- 文件: `backend/app/api/routes/translate.py`
- 行号: 79-98
- 修改: 构建统一的 `agent_config` 字典

```python
agent_config = {
    "sys_name": "LaTeXTrans",
    "target_language": target_language,
    "source_language": source_language,
    "mode": 0,
    "llm_config": llm_config  # 保持为嵌套字典
}

coordinator = CoordinatorAgent(
    config=agent_config,
    project_dir=str(source_path),
    output_dir=str(output_dir),
    on_progress=progress_callback
)
```

---

### 4. 事件循环冲突

**问题描述**:  
FastAPI 的异步环境与 `CoordinatorAgent` 尝试创建新的事件循环冲突。

**错误信息**:
```
RuntimeError: Cannot run the event loop while another loop is running
```

**根本原因**:  
`workflow_latextrans()` 方法尝试在 FastAPI 的事件循环中创建并运行新的事件循环。

**修复方案**:
- 文件: `backend/app/api/routes/translate.py`
- 行号: 36-105
- 修改: 
  1. 将 `run_translation` 改为异步函数
  2. 直接调用 `await coordinator.workflow_latextrans_async()`
  3. 使用 `asyncio.create_task()` 启动后台任务

```python
async def run_translation(task_id: str, ...):
    # ... 初始化代码 ...
    await coordinator.workflow_latextrans_async()  # 直接 await
```

---

### 5. 进度回调函数签名不匹配 (第一层)

**问题描述**:  
`TaskManager.create_progress_callback` 返回的函数签名与 `CoordinatorAgent` 期望的不匹配。

**错误信息**:
```
TypeError: on_progress() missing 1 required positional argument: 'message'
```

**根本原因**:  
- `create_progress_callback` 返回: `(stage, percentage, message)` (3 参数)
- `CoordinatorAgent` 调用: `(percentage, message)` (2 参数)

**修复方案**:
- 文件: `backend/app/services/task_manager.py`
- 行号: 166-186
- 修改: 改为 2 参数版本，自动推断 stage

```python
def on_progress(percentage: int, message: str = ""):
    # 根据进度百分比自动推断 stage
    if percentage < 10:
        stage = CompilationStage.PARSING.value
    elif percentage < 70:
        stage = CompilationStage.TRANSLATING.value
    # ... 其他阶段
    
    self.update_task(task_id=task_id, progress=percentage, stage=stage, message=message)
```

---

### 6. 进度回调函数签名不匹配 (第二层)

**问题描述**:  
`CoordinatorAgent` 传递给子 agent 的 lambda 函数签名不匹配。

**错误信息**:
```
TypeError: <lambda>() takes 2 positional arguments but 3 were given
```

**根本原因**:  
- Lambda 定义: `lambda p, m: ...` (2 参数)
- `base_tool_agent.update_progress` 调用: `(stage, percentage, message)` (3 参数)

**修复方案**:
- 文件: `backend/app/services/agents/coordinator_agent.py`
- 行号: 67-133 (多处)
- 修改: 所有 lambda 改为接受 3 个参数

```python
# ParserAgent
on_progress=lambda s, p, m: self.update_progress(5 + int(p * 0.05), m)

# TranslatorAgent
on_progress=lambda s, p, m: self.update_progress(10 + int(p * 0.6), m)

# ValidatorAgent  
on_progress=lambda s, p, m: self.update_progress(70 + int(p * 0.05), m)

# GeneratorAgent
on_progress=lambda s, p, m: self.update_progress(85 + int(p * 0.15), m)
```

---

### 7. TranslatorAgent category 空值检查缺失

**问题描述**:  
`TranslatorAgent` 尝试对 `None` 对象调用 `.get()` 方法。

**错误信息**:
```
AttributeError: 'NoneType' object has no attribute 'get'
```

**根本原因**:  
`self.category` 从 config 获取时可能为 `None`，但代码直接调用 `self.category.get(arxiv_id)` 而没有空值检查。

**修复方案**:
- 文件: `backend/app/services/agents/translator_agent.py`
- 行号: 865-896
- 修改: 添加空值检查

```python
# 检查 category 是否为 None
if self.category and self.category.get(arxiv_id):
    # ... 使用 category
```

---

## 修改的文件清单

| 文件路径 | 修改行数 | 修改类型 | 说明 |
|---------|---------|---------|------|
| `backend/app/services/latex/utils.py` | 774-803, 834-841 | 功能增强 | 添加目录创建和文件解压逻辑 |
| `backend/app/api/routes/translate.py` | 1-11, 36-105, 145-200 | 架构修复 | 异步化 + 配置结构修复 |
| `backend/app/services/task_manager.py` | 166-195 | 接口调整 | 进度回调签名修复 |
| `backend/app/services/agents/coordinator_agent.py` | 67-133 | 接口调整 | Lambda 签名修复 |
| `backend/app/services/agents/translator_agent.py` | 865-896 | 防御性编程 | 空值检查 |
| `test.py` | 10-116 | 测试改进 | 添加健康检查和错误处理 |

## 验证步骤

### 自动化验证
```bash
# 1. 健康检查
GET /health
# 期望: 200 OK, 返回应用信息

# 2. arXiv 下载
POST /api/arxiv
{
  "arxiv_ids": ["2601.16172"],
  "target_language": "ch"
}
# 期望: 200 OK, 文件下载并解压成功

# 3. 启动翻译
POST /api/translate/{task_id}
{
  "target_language": "ch",
  "source_language": "en"
}
# 期望: 200 OK, 翻译任务在后台启动

# 4. 查询任务状态
GET /api/task/{task_id}
# 期望: 状态从 parsing -> translating 正常推进
```

### 手动测试
运行 `test.py` 脚本：
```bash
python test.py
```

**预期结果**:
- ✅ 健康检查通过
- ✅ arXiv 下载成功并解压
- ✅ 翻译任务启动
- ✅ 进度从 0% -> 10% (parsing) -> 10%+ (translating)
- ⏳ 等待 LLM API 响应完成翻译（需要几分钟）

## 潜在风险和注意事项

### 1. LLM API 调用可能失败
**风险**: ParserAgent 中 LLM 请求有时返回 "Expecting value: line 1 column 1"  
**影响**: 解析阶段部分环境的 `need_trans` 判断失败，默认为 True  
**缓解**: 系统会重试 2 次，最终使用默认值继续执行

### 2. 长时间运行任务
**风险**: 翻译任务可能需要几分钟到十几分钟  
**影响**: 用户体验，超时风险  
**建议**: 
- 考虑添加任务超时设置
- 提供更详细的进度反馈
- 添加任务取消功能

### 3. 内存中的任务管理
**风险**: 当前 TaskManager 使用内存存储，服务重启会丢失任务状态  
**影响**: 长时间运行的任务在服务重启后无法恢复  
**建议**: 在后续版本中考虑持久化任务状态

## 下一步行动

1. **运行完整测试**: 使用 `test.py` 验证端到端流程
2. **监控 LLM API**: 观察 TranslatorAgent 的 LLM 调用是否成功
3. **检查 PDF 生成**: 验证翻译完成后能否成功生成 PDF
4. **性能测试**: 测量完整翻译流程的耗时

## 总结

本次修复解决了翻译工作流从启动到运行的所有阻塞问题：

| 阶段 | 状态 | 说明 |
|------|------|------|
| arXiv 下载 | ✅ 已修复 | 目录创建、文件解压 |
| 工作流启动 | ✅ 已修复 | 异步化、配置结构 |
| 进度报告 | ✅ 已修复 | 回调函数签名统一 |
| 翻译初始化 | ✅ 已修复 | 空值检查 |
| 实际翻译 | ⏳ 待测试 | 需要 LLM API 响应 |
| PDF 生成 | ⏳ 待测试 | 依赖翻译完成 |

所有代码修复符合 OpenSpec "Bug fixes" 原则，没有引入新功能或破坏性更改，仅恢复了预期的系统行为。
