# 后端开发 - 第一阶段实施计划

**变更 ID**: add-web-mvp-platform  
**阶段**: Phase 1 - LaTeX 处理模块改编  
**创建时间**: 2026-01-25  
**预计工作量**: 4-5 小时  

---

## 目标描述

完成 Web MVP 平台后端的第一阶段开发：改编原型系统中的 LaTeX 处理模块，使其适配 Web API 环境。这是完整后端开发的基础，必须在代理系统改编之前完成。

## 当前状态

### ✅ 已完成基础骨架 (35%)

1. **配置模块** (`backend/app/core/config.py`)
   - LLM API 配置（api_key, base_url, model, timeout）
   - 存储路径配置
   - 任务状态和编译阶段枚举

2. **任务管理器** (`backend/app/services/task_manager.py`)
   - 线程安全的内存任务存储
   - 进度回调机制
   - 任务状态管理 (CRUD)

3. **智能编译器** (`backend/app/services/latex/compiler.py`)
   - ✅ pdflatex → xelatex 回退机制
   - ✅ .log 文件错误计数和比较
   - ✅ 最优 PDF 选择逻辑

4. **简化 LaTeX 工具** (`backend/app/services/latex/utils.py`)
   - arXiv 下载功能
   - ID 验证和提取

5. **arXiv API** (`backend/app/api/routes/arxiv.py`)
   - POST /api/arxiv - 下载论文
   - GET /api/arxiv/validate/{id} - 验证 ID

6. **FastAPI 主应用** (`backend/app/main.py`)
   - 健康检查端点
   - CORS 配置
   - 基础路由注册

## 第一阶段：LaTeX 处理模块改编

### 目标

改编原型系统中的 4 个核心 LaTeX 处理文件，使其适配 Web API 环境，移除 Streamlit 依赖，添加进度回调机制。

### 任务清单

#### Task 1.1: 复制 prompts.py

**源文件**: `prototype_system/src/formats/latex/prompts.py` (48,373 字节)  
**目标文件**: `backend/app/services/latex/prompts.py`

**操作**:
- 直接复制，无需修改（纯提示词常量定义）

**验证**:
- 文件导入成功
- 提示词字符串完整

**预计时间**: 5 分钟

---

#### Task 1.2: 完善 utils.py

**源文件**: `prototype_system/src/formats/latex/utils.py` (31,329 字节)  
**当前文件**: `backend/app/services/latex/utils.py` (7,648 字节，已简化)

**修改策略**:

1. **保留现有功能**:
   - ✅ `batch_download_arxiv_tex()` - 批量下载
   - ✅ `download_tex()` - 单个下载
   - ✅ `get_tex_url()` - 获取下载链接
   - ✅ `is_already_downloaded()` - 检查已下载
   - ✅ `get_arxiv_category()` - 获取分类
   - ✅ `is_valid_arxiv_id()` - 验证 ID
   - ✅ `extract_arxiv_ids()` - 提取 ID（支持字符串或列表输入）

2. **需要添加的功能** (从原型复制):
   - `find_main_tex_file()` - 查找主 .tex 文件
   - `extract_bib_entries()` - 提取参考文献
   - `get_latex_env_content()` - 获取 LaTeX 环境内容
   - 其他 AST 辅助函数

3. **需要移除的内容**:
   - 所有 `import streamlit as st`
   - 所有 `sys.stderr` 重定向代码
   - Streamlit UI 调用

4. **需要添加的内容**:
   - Python `logging` 模块
   - 路径调整（适应 `data/` 目录结构）

**验证**:
- 所有函数可正常导入
- arXiv 下载功能正常
- 无 Streamlit 依赖

**预计时间**: 1 小时

---

#### Task 1.3: 改编 parser.py

**源文件**: `prototype_system/src/formats/latex/parser.py` (16,739 字节)  
**目标文件**: `backend/app/services/latex/parser.py`

**修改策略**:

1. **移除 Streamlit 依赖**:
   ```python
   # 删除
   import streamlit as st
   
   # 删除所有类似调用
   st.progress(0.5)
   st.text("Parsing LaTeX...")
   ```

2. **添加进度回调**:
   ```python
   def parse_latex(
       tex_file: str,
       on_progress: Optional[Callable[[str, int, str], None]] = None
   ) -> Dict:
       """
       Parse LaTeX file and extract AST structure
       
       Args:
           tex_file: Path to .tex file
           on_progress: Optional callback(stage, percentage, message)
       """
       if on_progress:
           on_progress("parsing", 10, "Loading LaTeX file...")
       
       # ... parsing logic ...
       
       if on_progress:
           on_progress("parsing", 50, "Extracting AST structure...")
       
       # ... more logic ...
       
       if on_progress:
           on_progress("parsing", 100, "Parsing complete")
   ```

3. **保留核心逻辑**:
   - ✅ 所有 `pylatexenc` AST 解析逻辑
   - ✅ JSON 生成逻辑
   - ✅ 环境提取逻辑

4. **添加日志**:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   
   logger.info("Starting LaTeX parsing...")
   logger.debug(f"Processing file: {tex_file}")
   ```

**验证**:
- 能成功解析示例 .tex 文件
- 生成正确的 JSON AST 结构
- 进度回调正常触发

**预计时间**: 2 小时

---

#### Task 1.4: 改编 reconstruct.py

**源文件**: `prototype_system/src/formats/latex/reconstruct.py` (7,268 字节)  
**目标文件**: `backend/app/services/latex/reconstruct.py`

**修改策略**:

1. **移除 Streamlit 依赖**:
   - 删除 `import streamlit as st`
   - 删除所有 UI 调用

2. **添加日志记录**:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   
   logger.info("Reconstructing LaTeX from JSON...")
   ```

3. **保留重构逻辑**:
   - ✅ JSON 到 LaTeX 的转换逻辑
   - ✅ 格式化和缩进逻辑

4. **添加进度回调** (如果需要):
   ```python
   def reconstruct_latex(
       json_data: Dict,
       on_progress: Optional[Callable] = None
   ) -> str:
       if on_progress:
           on_progress("reconstructing", 50, "Converting JSON to LaTeX...")
       # ... logic ...
   ```

**验证**:
- 能从 JSON 重构出有效的 LaTeX
- 输出格式正确

**预计时间**: 1 小时

---

## 实施顺序

按依赖关系顺序执行：

1. **prompts.py** - 最简单，直接复制
2. **utils.py** - 添加辅助函数
3. **parser.py** - 依赖 utils.py
4. **reconstruct.py** - 独立，可并行

## 验证计划

### 单元测试

为每个模块创建测试：

```python
# backend/tests/test_latex_parser.py
import pytest
from backend.app.services.latex.parser import parse_latex

def test_parse_simple_tex():
    """测试简单 LaTeX 文件解析"""
    tex_content = r"""
    \documentclass{article}
    \begin{document}
    Hello World
    \end{document}
    """
    result = parse_latex(tex_content)
    assert result is not None
    assert "document" in result

def test_parse_with_progress_callback():
    """测试进度回调"""
    progress_calls = []
    
    def on_progress(stage, pct, msg):
        progress_calls.append((stage, pct, msg))
    
    parse_latex(test_file, on_progress=on_progress)
    
    assert len(progress_calls) > 0
    assert progress_calls[0][0] == "parsing"
```

### 集成测试

```bash
# 测试完整流程
cd d:\future\antigravity\LaTexTrans
pytest backend/tests/test_latex_module.py -v
```

### 手动测试

```python
# 测试脚本: test_latex_modules.py
from backend.app.services.latex import parser, utils, prompts

# 1. 测试 prompts
print("Prompts loaded:", len(prompts.TRANSLATION_PROMPT) > 0)

# 2. 测试 utils
arxiv_id = "2508.18791"
is_valid = utils.is_valid_arxiv_id(arxiv_id)
print(f"arXiv ID {arxiv_id} valid:", is_valid)

# 3. 测试 parser
tex_file = "data/uploads/test/main.tex"
result = parser.parse_latex(tex_file)
print("Parse result:", result is not None)
```

## 风险和缓解

### 风险 1: parser.py 文件较大

**问题**: 16KB 文件，可能有多处 Streamlit 调用  
**缓解**: 使用全局搜索替换，仔细检查每处修改

### 风险 2: pylatexenc 版本兼容性

**问题**: 依赖可能与原型不同  
**缓解**: 确保使用相同的 pylatexenc 版本

### 风险 3: 进度回调集成复杂

**问题**: 需要在多个位置添加回调  
**缓解**: 使用统一的回调模式，先在一个函数中测试

## 完成标准

第一阶段完成后，应满足：

- ✅ 所有 4 个 LaTeX 模块文件已创建
- ✅ 无 Streamlit 依赖
- ✅ 所有模块可正常导入
- ✅ 进度回调机制正常工作
- ✅ 单元测试通过
- ✅ 能成功解析示例 LaTeX 文件

## 下一阶段

完成第一阶段后，将进入第二阶段：代理系统改编（6 个代理文件）。
