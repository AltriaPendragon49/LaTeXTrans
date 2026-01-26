# 第一和第二阶段功能测试指南

**测试日期**: 2026-01-25  
**测试范围**: LaTeX 处理模块（第一阶段）+ 代理系统（第二阶段）  
**版本**: v1.2 - 包含已修复bug的说明

---

## ⚠️ 已修复的Bug（重要）

> **在开始测试前，请注意以下bug已被修复，测试步骤已相应更新**

### Bug #1: [get_llm_config()](file:///d:/future/antigravity/LaTexTrans/backend/app/core/config.py#136-139) 导入错误 ✅ 已修复

**问题**: [parser_agent.py](file:///d:/future/antigravity/LaTexTrans/backend/app/services/agents/parser_agent.py) 等模块无法导入 [get_llm_config](file:///d:/future/antigravity/LaTexTrans/backend/app/core/config.py#136-139)  
**修复**: 在 [backend/app/core/config.py](file:///d:/future/antigravity/LaTexTrans/backend/app/core/config.py) 中新增了便捷函数 [get_llm_config()](file:///d:/future/antigravity/LaTexTrans/backend/app/core/config.py#136-139)  
**影响**: 现在可以直接从配置模块导入使用

```python
# 现在可以正常使用
from backend.app.core.config import get_llm_config
llm_config = get_llm_config()  # 返回字典
```

### Bug #2: [extract_arxiv_ids()](file:///d:/future/antigravity/LaTexTrans/backend/app/services/latex/utils.py#886-919) 增强 ✅ 已修复

**问题**: 函数只接受列表，传入字符串返回空列表  
**修复**: 函数现在同时支持字符串和列表输入  
**影响**: 可以更方便地使用

```python
# 新增功能：支持单个字符串
extract_arxiv_ids("2508.18791")  # ✅ 返回 ['2508.18791']
extract_arxiv_ids("https://arxiv.org/abs/2508.18791")  # ✅ 返回 ['2508.18791']

# 原有功能：继续支持列表
extract_arxiv_ids(["2508.18791", "1234.56789"])  # ✅ 返回 ['2508.18791', '1234.56789']
```

### Bug #3: 编译器返回字典而非对象 ✅ 已说明

**问题**: [compile_with_fallback()](file:///d:/future/antigravity/LaTexTrans/backend/app/services/latex/compiler.py#179-308) 返回字典，但测试代码期望对象属性  
**这不是Bug**: 函数设计文档规定返回字典（第179-201行）  
**影响**: 测试代码需要使用字典访问方式

```python
# ✅ 正确用法（使用字典访问）
result = compile_with_fallback(tex_file, output_dir)
status = result['status']          # 正确
engine = result['engine']          # 正确 - 字段名是 "engine"
pdf_path = result['pdf_path']      # 正确

# ❌ 错误用法（期望对象属性）
status = result.status             # 错误 - 字典没有属性
engine = result.engine_used        # 错误 - 字段名不对
```

### Bug #4: BaseToolAgent 抽象类不能直接实例化 ✅ 已修复

**问题**: 原测试脚本直接实例化 `BaseToolAgent` 抽象类  
**错误**: `TypeError: Can't instantiate abstract class BaseToolAgent with abstract method execute`  
**原因**: `BaseToolAgent` 是抽象类（ABC），包含抽象方法 `execute()`，不能直接实例化  
**修复**: 创建具体子类 `TestAgent` 实现 `execute()` 方法进行测试

```python
# ❌ 错误用法（直接实例化抽象类）
agent = BaseToolAgent(agent_name="TestAgent", config=test_config)
# TypeError: Can't instantiate abstract class BaseToolAgent with abstract method execute

# ✅ 正确用法（创建具体子类）
class TestAgent(BaseToolAgent):
    def execute(self, data: Any = None, **kwargs: Any) -> Any:
        """实现抽象方法"""
        return {"status": "success", "data": data}

agent = TestAgent(agent_name="TestAgent", config=test_config)
```

**重要**: 进度回调函数接受 **3个参数** `(stage, percentage, message)`，这是设计文档明确规定的（见 [base_tool_agent.py:33](file:///d:/future/antigravity/LaTexTrans/openspec/changes/add-web-mvp-platform/base_tool_agent.py#L33) 和 [spec_CN.md:16](file:///d:/future/antigravity/LaTexTrans/openspec/changes/add-web-mvp-platform/specs/latex-translation-core/spec_CN.md#L16)）

---

## 📋 测试清单概览

### ✅ 第一阶段：LaTeX 处理模块
- [ ] 1. 配置模块测试
- [ ] 2. LaTeX 工具函数测试
- [ ] 3. LaTeX 解析器测试
- [ ] 4. LaTeX 重构器测试
- [ ] 5. 智能编译器测试
- [ ] 6. Prompts 模块测试

### ✅ 第二阶段：代理系统
- [ ] 7. 基础代理测试
- [ ] 8. 解析代理测试
- [ ] 9. 生成代理测试
- [ ] 10. 验证代理测试
- [ ] 11. 翻译代理测试（最复杂）
- [ ] 12. 协调代理测试

### ✅ 集成功能
- [ ] 13. 任务管理器测试
- [ ] 14. 进度回调机制测试
- [ ] 15. Logging 系统测试

---

## 👨‍💻 手动测试指南

### 前置准备

#### 1. 确认 Python 环境

```bash
# 检查 Python 版本（需要 3.8+）
python --version

# 激活虚拟环境
conda activate latex_rag_agent  # 或你的环境名称
```

#### 2. 安装依赖

```bash
cd d:\future\antigravity\LaTexTrans\backend
pip install -r requirements.txt
```

**注意事项**:
- `tiktoken==0.5.1` 可能需要 Rust 编译器，如果安装失败可以暂时跳过
- 确保安装了 `pylatexenc`, `aiohttp`, `fastapi`, `pandas` 等核心依赖

---

### 第一阶段测试：LaTeX 处理模块

#### 测试 A1: 配置模块测试 🔧 已更新

**文件**: [backend/app/core/config.py](file:///d:/future/antigravity/LaTexTrans/backend/app/core/config.py)

**测试步骤**:
```bash
cd d:\future\antigravity\LaTexTrans
conda activate latex_rag_agent
python
```

```python
# 在 Python 交互式环境中
import sys
import os
sys.path.insert(0, os.getcwd())

from backend.app.core.config import Settings, get_settings, get_llm_config

# 测试 1: 检查配置加载
settings = get_settings()
print(f"✅ Settings loaded: {settings.app_name}")
print(f"✅ LLM Model: {settings.llm_model}")
print(f"✅ Uploads dir: {settings.uploads_dir}")

# 测试 2: 检查 LLM 配置（使用新增的便捷函数）
llm_config = get_llm_config()
print(f"✅ LLM Config keys: {list(llm_config.keys())}")
print(f"✅ LLM Model: {llm_config['model']}")
print(f"✅ LLM Base URL: {llm_config['base_url']}")

# 测试 3: 检查任务状态枚举
from backend.app.core.config import TaskStatus, CompilationStage
print(f"✅ Task statuses: {[s.value for s in TaskStatus]}")
print(f"✅ Compilation stages: {[s.value for s in CompilationStage]}")
```

**预期输出**:
```
✅ Settings loaded: LaTeXTrans Backend
✅ LLM Model: gpt-4.1-mini
✅ Uploads dir: d:\future\antigravity\LaTexTrans\data\uploads
✅ LLM Config keys: ['api_key', 'base_url', 'model', 'timeout']
✅ LLM Model: gpt-4.1-mini
✅ LLM Base URL: https://aicanapi.com
✅ Task statuses: ['pending', 'processing', 'completed', 'completed_with_warnings', 'failed_compilation', 'failed']
✅ Compilation stages: ['idle', 'parsing', 'translating', 'compiling', 'compilation_failed', 'done']
```

---

#### 测试 A2: LaTeX 工具函数测试 🔧 已更新

**文件**: [backend/app/services/latex/utils.py](file:///d:/future/antigravity/LaTexTrans/backend/app/services/latex/utils.py)

**测试步骤**:
```python
from backend.app.services.latex.utils import (
    is_valid_arxiv_id,
    extract_arxiv_ids
)

print("\n=== 开始测试 LaTeX 工具函数 ===")

# 测试 1: arXiv ID 验证
print("\n--- 测试 1: ID 格式验证 ---")
test_ids = [
    "2508.18791",    # 预期: True (有效)
    "1234.56789",    # 预期: True (有效)
    "invalid_id",    # 预期: False
    "12345",         # 预期: False (位数不对)
]

for arxiv_id in test_ids:
    is_valid = is_valid_arxiv_id(arxiv_id)
    icon = "✅" if is_valid else "❌"
    print(f"ID: {arxiv_id:<12} -> {icon} (结果: {is_valid})")

# 测试 2: 从 URL 提取 ID（测试新增的字符串支持）
print("\n--- 测试 2: 从 URL 提取 ID（支持字符串和列表）---")
test_cases = [
    "2508.18791",                                      # 直接ID
    "https://arxiv.org/abs/2508.18791",               # 标准摘要页
    "http://arxiv.org/pdf/1234.56789.pdf",            # PDF 链接
    ["2508.18791", "https://arxiv.org/pdf/1234.56789.pdf"]  # 列表（原有功能）
]

for item in test_cases:
    ids = extract_arxiv_ids(item)
    input_type = type(item).__name__
    print(f"输入类型: {input_type:6} -> 提取结果: {ids}")

print("\n✅ 工具函数测试结束")
```

**预期输出**:
```
=== 开始测试 LaTeX 工具函数 ===

--- 测试 1: ID 格式验证 ---
ID: 2508.18791   -> ✅ (结果: True)
ID: 1234.56789   -> ✅ (结果: True)
ID: invalid_id   -> ❌ (结果: False)
ID: 12345        -> ❌ (结果: False)

--- 测试 2: 从 URL 提取 ID（支持字符串和列表）---
输入类型: str    -> 提取结果: ['2508.18791']
输入类型: str    -> 提取结果: ['2508.18791']
输入类型: str    -> 提取结果: ['1234.56789']
输入类型: list   -> 提取结果: ['2508.18791', '1234.56789']

✅ 工具函数测试结束
```

---

#### 测试 A3: 智能编译器测试（核心功能）

**文件**: [backend/app/services/latex/compiler.py](file:///d:/future/antigravity/LaTexTrans/backend/app/services/latex/compiler.py)

**准备工作**:
1. 确保系统已安装 LaTeX（MiKTeX 或 TeX Live）
2. 准备一个简单的 `.tex` 测试文件

**创建测试文件**:
在 `d:\future\antigravity\LaTexTrans\` 创建 `test_simple.tex`:

```latex
\documentclass{article}
\usepackage[utf8]{inputenc}
\begin{document}
\title{Test Document}
\author{Test}
\date{2026-01-25}
\maketitle
\section{Introduction}
This is a test document.
\end{document}
```

**测试步骤**:
```python
from backend.app.services.latex.compiler import compile_with_fallback
from pathlib import Path

# 测试简单编译
tex_file = Path("test_simple.tex")
output_dir = Path("test_output")
output_dir.mkdir(exist_ok=True)

print("开始测试智能编译器...")
result = compile_with_fallback(str(tex_file), str(output_dir))

print(f"\n编译结果:")
print(f"  状态: {result['status']}")
print(f"  使用引擎: {result['engine']}")
print(f"  PDF路径: {result['pdf_path']}")
print(f"  错误数量: {result['error_count']}")

# 检查PDF文件是否存在
pdf_path = Path(result['pdf_path']) if result['pdf_path'] else None
if pdf_path and pdf_path.exists():
    print(f"\n✅ 成功生成 PDF: {pdf_path} ({pdf_path.stat().st_size} bytes)")
else:
    print(f"\n❌ 编译失败")
    if result.get('errors'):
        print(f"错误详情: {result['errors'][:200]}...")
```

**预期输出**:
```
开始测试智能编译器...

编译结果:
  状态: completed
  使用引擎: pdflatex
  PDF路径: test_output\test_simple.pdf
  错误数量: 0

✅ 成功生成 PDF: test_output\test_simple.pdf (44534 bytes)
```

---

### 第二阶段测试：代理系统

#### 测试 B1: 基础代理测试 🔧 已修复

**文件**: [backend/app/services/agents/base_tool_agent.py](file:///d:/future/antigravity/LaTexTrans/backend/app/services/agents/base_tool_agent.py)

**⚠️ 重要**: `BaseToolAgent` 是抽象类，不能直接实例化。必须创建具体子类实现 `execute()` 方法。进度回调函数需要 **3个参数** `(stage, percentage, message)`。

```python
from backend.app.services.agents.base_tool_agent import BaseToolAgent
from pathlib import Path
from typing import Any
import json


# 创建一个简单的测试子类，实现 execute() 方法
class TestAgent(BaseToolAgent):
    """用于测试的具体代理类"""
    
    def execute(self, data: Any = None, **kwargs: Any) -> Any:
        """实现抽象方法 execute()"""
        self.log("TestAgent executing...")
        return {"status": "success", "data": data}


# 创建测试配置
test_config = {
    "llm_config": {
        "model": "gpt-4.1-mini",
        "api_key": "test_key",
        "base_url": "https://aicanapi.com"
    },
    "source_language": "en",
    "target_language": "zh"
}

# 测试进度回调
progress_log = []
def test_progress_callback(stage, percentage, message):
    """
    进度回调函数
    注意：根据设计文档，回调函数接受3个参数 (stage, percentage, message)
    """
    progress_log.append((stage, percentage, message))
    print(f"[{stage}] 进度: {percentage}% - {message}")


print("\n=== 开始测试 BaseToolAgent ===\n")

# 创建代理实例（使用具体子类）
agent = TestAgent(
    agent_name="TestAgent",
    config=test_config,
    on_progress=test_progress_callback
)

# 测试 1: 日志功能
print("--- 测试 1: 日志功能 ---")
agent.log("这是一条测试日志")
agent.log("这是警告日志", level="warning")
print("✅ 日志功能正常\n")

# 测试 2: 进度更新
print("--- 测试 2: 进度回调 ---")
agent.update_progress(50, "测试进度更新")
assert len(progress_log) == 1
assert progress_log[0] == ("testagent", 50, "测试进度更新")
print("✅ 进度回调正常\n")

# 测试 3: 文件读写
print("--- 测试 3: 文件读写 ---")
test_data = {"test": "data", "number": 42}
test_file = Path("test_output/test.json")
test_file.parent.mkdir(exist_ok=True)

agent.save_file(test_file, "json", test_data)
loaded_data = agent.read_file(test_file, "json")

assert loaded_data == test_data
print(f"✅ 文件读写正常 (保存并读取: {test_file})\n")

# 测试 4: execute() 方法
print("--- 测试 4: execute() 方法 ---")
result = agent.execute({"input": "test_data"})
assert result["status"] == "success"
print(f"✅ execute() 方法正常 (返回: {result})\n")

# 测试 5: 配置读取
print("--- 测试 5: 配置读取 ---")
model = agent.get_config("llm_config", {}).get("model")
assert model == "gpt-4.1-mini"
print(f"✅ 配置读取正常 (LLM模型: {model})\n")

print("=" * 50)
print("✅ BaseToolAgent 所有测试通过!")
print("=" * 50)
```

**预期输出**:
```
=== 开始测试 BaseToolAgent ===

--- 测试 1: 日志功能 ---
✅ 日志功能正常

--- 测试 2: 进度回调 ---
[testagent] 进度: 50% - 测试进度更新
✅ 进度回调正常

--- 测试 3: 文件读写 ---
✅ 文件读写正常 (保存并读取: test_output\test.json)

--- 测试 4: execute() 方法 ---
✅ execute() 方法正常 (返回: {'status': 'success', 'data': {'input': 'test_data'}})

--- 测试 5: 配置读取 ---
✅ 配置读取正常 (LLM模型: gpt-4.1-mini)

==================================================
✅ BaseToolAgent 所有测试通过!
==================================================
```

---

#### 测试 B2: 任务管理器测试

**文件**: [backend/app/services/task_manager.py](file:///d:/future/antigravity/LaTexTrans/backend/app/services/task_manager.py)

```python
from backend.app.services.task_manager import TaskManager
from backend.app.core.config import TaskStatus

# 创建任务管理器
tm = TaskManager()

# 测试 1: 创建任务
task_id = tm.create_task(source_type="arxiv")
print(f"✅ 创建任务: {task_id}")

# 测试 2: 获取任务
task = tm.get_task(task_id)
print(f"✅ 任务状态: {task['status']}")
print(f"✅ 任务进度: {task['progress']}%")

# 测试 3: 更新任务
tm.update_task(task_id, status=TaskStatus.PROCESSING, progress=50, message="正在翻译")
task = tm.get_task(task_id)
assert task['status'] == TaskStatus.PROCESSING.value
assert task['progress'] == 50
print("✅ 任务更新正常")

# 测试 4: 进度回调工厂
callback = tm.create_progress_callback(task_id)
callback("compiling", 75, "即将完成")
task = tm.get_task(task_id)
assert task['progress'] == 75
print("✅ 进度回调工厂正常")

# 测试 5: 删除任务
tm.delete_task(task_id)
task = tm.get_task(task_id)
assert task is None
print("✅ 任务删除正常")

print("\n✅ TaskManager 所有测试通过!")
```

---

## 🧪 集成测试（需要完整环境）

### 测试 C1: 端到端 LaTeX 处理测试

**前提条件**:
- 已安装 LaTeX 环境
- 已安装所有 Python 依赖
- 已配置 LLM API 密钥

**测试脚本**: 创建 `test_e2e_latex.py`

```python
"""
端到端 LaTeX 处理测试
"""
import asyncio
from pathlib import Path
from backend.app.services.agents.parser_agent import ParserAgent
from backend.app.services.agents.generator_agent import GeneratorAgent

# 配置
config = {
    "llm_config": {
        "model": "gpt-4.1-mini",
        "api_key": "sk-SVd4dIKfuIwhQ9kUlgCr9ZMpoIWp7PEzZxpVStjSRqeqNBLu",
        "base_url": "https://aicanapi.com",
        "timeout": 60
    },
    "source_language": "en",
    "target_language": "zh"
}

# ⚠️ 重要：测试项目目录应该指向具体的 LaTeX 项目，而不是整个项目根目录
# 如果使用 Path(".")，GeneratorAgent 会复制整个项目目录到 output_dir，
# 导致递归嵌套问题（test_output/latex_processing/test_output/...）
#
# 建议使用真实的 arXiv 论文作为测试样例，确保测试的真实性
project_dir = Path("test_files/arXiv-2601.16172v1")  # 使用真实arXiv论文
output_dir = Path("test_output/latex_processing")

# 确保输出目录存在
output_dir.mkdir(parents=True, exist_ok=True)

def test_latex_parsing():
    """测试 LaTeX 解析"""
    print("\n=== 测试 LaTeX 解析 ===")
    
    parser = ParserAgent(
        config=config,
        project_dir=str(project_dir),
        output_dir=str(output_dir)
    )
    
    try:
        parser.execute()
        print("✅ LaTeX 解析成功")
        
        # 检查输出文件
        expected_files = [
            "sections_map.json",
            "captions_map.json",
            "envs_map.json"
        ]
        
        for file in expected_files:
            filepath = output_dir / file
            if filepath.exists():
                print(f"  ✅ 生成文件: {file}")
            else:
                print(f"  ❌ 缺少文件: {file}")
                
    except Exception as e:
        print(f"❌ 解析失败: {e}")

def test_latex_generation():
    """测试 LaTeX 生成和编译"""
    print("\n=== 测试 LaTeX 生成 ===")
    
    generator = GeneratorAgent(
        config=config,
        project_dir=str(project_dir),
        output_dir=str(output_dir)
    )
    
    try:
        pdf_path = generator.execute()
        if pdf_path:
            print(f"✅ PDF 生成成功: {pdf_path}")
        else:
            print("❌ PDF 生成失败")
    except Exception as e:
        print(f"❌ 生成失败: {e}")

if __name__ == "__main__":
    test_latex_parsing()
    # test_latex_generation()  # 取消注释以测试编译
```

**运行测试**:
```bash
python test_e2e_latex.py
```

---

## 📊 测试结果记录

### 手动测试结果

请在执行手动测试后填写：

#### 第一阶段 - LaTeX 处理模块
- [√ ] A1: 配置模块测试
- [√ ] A2: LaTeX 工具函数测试
- [√ ] A3: 智能编译器测试

#### 第二阶段 - 代理系统
- [√ ] B1: 基础代理测试
- [√ ] B2: 任务管理器测试

#### 集成测试
- [× ] C1: 端到端测试



## 🎯 下一步

测试完成后，请根据结果：

1. **如果所有测试通过**: 可以继续第三阶段（API 路由集成）
2. **如果有失败**: 记录失败的测试，我会帮你修复
3. **如果需要帮助**: 把测试输出发给我，我会协助排查

---

**测试记录人**: _________  
**测试完成日期**: _________  
**版本**: v1.2 (包含Bug修复)
