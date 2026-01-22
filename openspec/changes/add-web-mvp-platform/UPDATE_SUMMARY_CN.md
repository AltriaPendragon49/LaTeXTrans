# OpenSpec 提案更新 - 编译失败处理 & API配置

## ✅ 更新完成

根据您的两个新需求，我已成功更新 OpenSpec 提案的所有相关文件。

---

## 📋 需求1：编译失败时的源码下载

### 核心策略更新

**完美编译定义**：
- ✅ **只有当编译生成的 PDF 日志 log 中无错误时，才认为是完美编译**
- ⚠️ 如果两个编译器都有错误，选择错误较少的作为"瑕疵PDF"输出
- ❌ 如果两个都无法生成PDF，提供翻译后的源码下载

### 新增任务状态

| 状态 | 含义 | PDF可用 | 源码可用 | UI显示 |
|------|------|---------|----------|--------|
| `completed` | 完美编译（0错误） | ✅ | ✅ | ✅ 翻译完成！|
| `completed_with_warnings` | 瑕疵编译（有错误但有PDF） | ✅ | ✅ | ⚠️ 翻译完成但有警告 |
| `failed_compilation` | 编译失败（无PDF） | ❌ | ✅ | ❌ 编译失败，下载源码 |
| `failed` | 翻译失败（其他错误） | ❌ | 可能 | ❌ 翻译失败 |

### UI 行为变化

**情况1：完美编译 (status = "completed")**
```
显示: ✅ Translation complete!
按钮: [Download PDF]
```

**情况2：瑕疵编译 (status = "completed_with_warnings")**
```
显示: ⚠️ Translation completed with compilation warnings
按钮: [Download PDF] [Download Source]
提示: ⚠️ 警告图标，表示PDF可能有问题
```

**情况3：编译失败 (status = "failed_compilation")**
```
显示: ❌ PDF compilation failed
按钮: [Download Source] (突出显示)
提示: Download translated LaTeX source for manual compilation
可选: [Retry] 按钮
```

---

## 📋 需求2：LLM API配置更新

### 新API参数

```python
LLM_CONFIG = {
    "api_key": "sk-SVd4dIKfuIwhQ9kUlgCr9ZMpoIWp7PEzZxpVStjSRqeqNBLu",
    "base_url": "https://aicanapi.com/v1",
    "model": "gpt-4.1-mini",
    "timeout": 60
}
```

### 安全实践

⚠️ **重要**：
- API 密钥应通过环境变量 `LLM_API_KEY` 加载
- 不应在源码中硬编码
- 可以在 `config/default.toml` 中配置默认值（开发环境）

### 配置文件示例

**backend/app/core/config.py**:
```python
import os
from typing import Optional

class Settings:
    # LLM API配置
    LLM_API_KEY: str = os.getenv(
        "LLM_API_KEY", 
        "sk-SVd4dIKfuIwhQ9kUlgCr9ZMpoIWp7PEzZxpVStjSRqeqNBLu"
    )
    LLM_BASE_URL: str = "https://aicanapi.com/v1"
    LLM_MODEL: str = "gpt-4.1-mini"
    LLM_TIMEOUT: int = 60
    
    # 任务状态枚举
    class TaskStatus:
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        COMPLETED_WITH_WARNINGS = "completed_with_warnings"
        FAILED_COMPILATION = "failed_compilation"
        FAILED = "failed"

settings = Settings()
```

---

## 📝 更新的文件清单

### 1. **specs/latex-translation-core/spec.md**
   - ✅ 添加 "Perfect compilation (zero errors)" 场景
   - ✅ 区分完美编译和瑕疵编译
   - ✅ "Total compilation failure with source preservation" 场景
   - ✅ 明确失败时保留源码供下载

### 2. **specs/web-ui/spec.md**
   - ✅ 添加 "Completion with warnings notification" 场景
   - ✅ 添加 "Compilation failure notification" 场景
   - ✅ 添加 "Download source only (compilation failed)" 场景
   - ✅ 更新下载按钮的显示逻辑

### 3. **specs/web-api/spec.md**
   - ✅ 添加 "Query completed task status (perfect compilation)" 场景
   - ✅ 添加 "Query completed task status (with warnings)" 场景
   - ✅ 添加 "Query failed compilation task status" 场景
   - ✅ 更新任务状态返回值

### 4. **design.md**
   - ✅ 更新 Task Object 数据模型，添加新状态
   - ✅ 添加 `warnings` 和 `source_available` 字段
   - ✅ 新增 "LLM API Configuration" 章节
   - ✅ 明确 API 密钥和 base_url

### 5. **tasks.md**
   - ✅ 更新 Task 5.1，添加具体 API 配置参数
   - ✅ 添加任务状态枚举定义的实现要求

---

## 🔍 关键变更对比

### 编译逻辑流程

**之前**:
```
pdflatex尝试
  ↓ 失败
xelatex回退
  ↓ 比较错误
选择较好的PDF
  ↓ 都失败
抛出异常 ❌
```

**现在**:
```
pdflatex尝试
  ↓ 检查log
有错误? → xelatex回退
  ↓ 比较错误
都无错误? → completed ✅
有错误但有PDF? → completed_with_warnings ⚠️
都无PDF? → failed_compilation + 保留源码 📄
```

### 任务状态变化

**之前** (4种状态):
- `pending`
- `processing`
- `completed`
- `failed`

**现在** (6种状态):
- `pending`
- `processing`
- `completed` ← 仅限0错误
- `completed_with_warnings` ← **新增**（有错误但有PDF）
- `failed_compilation` ← **新增**（无PDF但有源码）
- `failed`

---

## ✅ 验证结果

```bash
$ openspec validate add-web-mvp-platform --strict --no-interactive
✓ Change 'add-web-mvp-platform' is valid

$ openspec list
Changes:
  add-web-mvp-platform     0/42 tasks    just now
```

**所有场景格式正确** ✅  
**需求完整覆盖** ✅  
**验证通过** ✅

---

## 🎯 实现要点

### 编译器实现伪代码

```python
def compile_with_fallback(tex_file: Path) -> CompilationResult:
    """智能编译策略"""
    
    # 1. 尝试 pdflatex
    pdf1, log1, exit1 = run_compiler("pdflatex", tex_file)
    errors1 = count_errors(log1)
    
    # 完美编译？
    if exit1 == 0 and errors1 == 0:
        return CompilationResult(
            status="completed",
            pdf_path=pdf1,
            log=log1,
            error_count=0
        )
    
    # 2. 尝试 xelatex
    pdf2, log2, exit2 = run_compiler("xelatex", tex_file)
    errors2 = count_errors(log2)
    
    # 完美编译？
    if exit2 == 0 and errors2 == 0:
        return CompilationResult(
            status="completed",
            pdf_path=pdf2,
            log=log2,
            error_count=0
        )
    
    # 3. 都有PDF，选择错误少的
    if pdf1.exists() and pdf2.exists():
        best_pdf = pdf1 if errors1 < errors2 else pdf2
        return CompilationResult(
            status="completed_with_warnings",
            pdf_path=best_pdf,
            log=log1 if errors1 < errors2 else log2,
            error_count=min(errors1, errors2)
        )
    
    # 4. 只有一个PDF
    if pdf1.exists():
        return CompilationResult(
            status="completed_with_warnings",
            pdf_path=pdf1,
            log=log1,
            error_count=errors1
        )
    
    if pdf2.exists():
        return CompilationResult(
            status="completed_with_warnings",
            pdf_path=pdf2,
            log=log2,
            error_count=errors2
        )
    
    # 5. 都失败，保留源码
    raise CompilationFailedError(
        status="failed_compilation",
        combined_errors=f"{log1}\n\n{log2}",
        source_preserved=True
    )

def count_errors(log_content: str) -> int:
    """统计LaTeX错误"""
    patterns = [
        r'^! LaTeX Error',
        r'^! Undefined control sequence',
        r'^! Missing'
    ]
    return sum(
        1 for line in log_content.split('\n')
        if any(re.match(p, line.strip()) for p in patterns)
    )
```

### UI组件更新

**DownloadButton.jsx**:
```jsx
function DownloadButton({ task }) {
  if (task.status === "completed") {
    return <Button onClick={downloadPDF}>Download PDF</Button>;
  }
  
  if (task.status === "completed_with_warnings") {
    return (
      <>
        <WarningIcon /> Compilation had warnings
        <Button onClick={downloadPDF}>Download PDF</Button>
        <Button onClick={downloadSource}>Download Source</Button>
      </>
    );
  }
  
  if (task.status === "failed_compilation") {
    return (
      <>
        <ErrorIcon /> PDF compilation failed
        <Button primary onClick={downloadSource}>
          Download Source for Manual Compilation
        </Button>
        <Button secondary onClick={retry}>Retry</Button>
      </>
    );
  }
  
  return null;
}
```

---

## 📌 下一步

1. **审查更新**：
   - ✅ 确认编译失败处理逻辑符合预期
   - ✅ 确认 API 配置信息正确

2. **批准提案**：
   - 所有规范文件已更新
   - 任务清单已更新
   - 设计文档已包含新配置

3. **开始实施**：
   - 按照 42 个任务逐步实施
   - 优先实现 Task 3.3（编译器回退）
   - Task 5.1 配置新的 API 密钥

---

**状态**: ✅ **提案已完整更新并验证，等待批准后开始实施**
