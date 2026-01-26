# 代码重用映射文档

## 审计总结

已审查原型系统的核心代码,识别出需要改编和重用的组件。主要需要移除 Streamlit 依赖并添加 Web API 集成。

## 需要移除的依赖

### Streamlit 相关
所有文件中包含的以下代码需要移除或替换:
- `import streamlit as st`
-`st.progress()`- 进度条显示
-`st.text()`
[翻译失败保留原文: Empty response]
/ `st.status_text`- 状态文本显示  
-`st.spinner()`- 加载动画
-`st.success()`
[翻译失败保留原文: Empty response]
/ `st.error()`- 成功/错误消息
-`sys.stderr = open(os.devnull, 'w')`
[翻译失败保留原文: Empty response]
/ `sys.stderr = sys.__stderr__`- 用于抑制 Streamlit 输出

### 替换方案
- 使用 Python`logging`模块记录日志
- 添加进度回调函数 `on_progress(stage, percentage, message)`
- 通过 TaskManager 更新任务状态

## 文件重用映射

### 1. 核心代理系统

#### 源文件 → 目标文件

**协调代理:**
-`prototype_system/src/agents/coordinator_agent.py`→ `backend/app/services/agents/coordinator_agent.py`
- **需要修改:**
  - 删除 Streamlit 依赖
  - 添加进度回调机制
  - 添加错误处理和异常传播
  - 保留异步工作流逻辑

**解析代理:**
- `prototype_system/src/agents/tool_agents/parser_agent.py`
  → `backend/app/services/agents/parser_agent.py`
- **需要修改:**
  - 删除 Streamlit 进度显示
  - 添加进度回调 `on_progress()`
  - LLM 请求保持不变

**翻译代理:**
- `prototype_system/src/agents/tool_agents/translator_agent.py`
  → `backend/app/services/agents/translator_agent.py`
- **需要修改:**
  - 删除 Streamlit UI 调用
  - 添加进度回调
  - 保留异步翻译逻辑
  - 保留术语提取和重试机制

**生成代理:**
- `prototype_system/src/agents/tool_agents/generator_agent.py`
  → `backend/app/services/agents/generator_agent.py`
- **需要修改:**
  - 删除所有 Streamlit 进度显示代码
  - 调用新的智能编译器 `compile_with_fallback()`
  - 添加进度回调
  - 保留文件重构逻辑

**验证代理:**
- `prototype_system/src/agents/tool_agents/validator_agent.py`
  → `backend/app/services/agents/validator_agent.py`
- **需要修改:**
  - 删除 Streamlit 依赖
  - 添加日志记录
  - 保留验证逻辑

**基础代理:**
- `prototype_system/src/agents/tool_agents/base_tool_agent.py`
  → `backend/app/services/agents/base_tool_agent.py`
- **需要修改:**
  - 更新日志方法使用 Python logging
  - 保留文件读写工具方法

### 2. LaTeX 处理模块

**解析器:**
- `prototype_system/src/formats/latex/parser.py`
  → `backend/app/services/latex/parser.py`
- **需要修改:**
  - 删除 `import streamlit as st`
  - 所有`st.progress()`调用替换为进度回调
  - 保留所有 AST 解析逻辑 (pylatexenc)
  - 保留 JSON 生成逻辑

**编译器 (已完成重构):**
- ✅`backend/app/services/latex/compiler.py`- 新实现
  - 实现了`compile_with_fallback()`函数
  - pdflatex → xelatex 回退机制
  - .log 文件错误计数
  - 错误对比和 PDF 选择逻辑

**工具函数:**
- `prototype_system/src/formats/latex/utils.py`
  → `backend/app/services/latex/utils.py`
- **需要修改:**
  - 删除 `import streamlit as st`
  - 保留所有 LaTeX 处理函数
  - 保留`batch_download_arxiv_tex()`函数 (修改 Streamlit 调用)
  - 保留`get_arxiv_category()`函数
  - 保留所有正则表达式和 AST 工具
  - 调整文件路径以适应 Web 环境

**重构器:**
- `prototype_system/src/formats/latex/reconstruct.py`
  → `backend/app/services/latex/reconstruct.py`
- **需要修改:**
  - 删除 Streamlit 依赖
  - 保留所有重构逻辑

**提示词:**
- `prototype_system/src/formats/latex/prompts.py`
  → `backend/app/services/latex/prompts.py`
- **无需修改** - 直接复制

### 3. 配置管理

**已完成:**
- ✅`backend/app/core/config.py`- Python 配置类
  - 从环境变量或 TOML 加载设置
  - LLM API 配置
  - 存储路径配置
  - 任务状态枚举

### 4. 任务管理

**已完成:**
- ✅`backend/app/services/task_manager.py`- 任务管理器
  - 线程安全的内存任务状态跟踪
  - 进度更新机制
  - 状态查询

## 关键差异

| 原型系统 | Web 后端 |
|---------|----------|
| Streamlit UI | FastAPI + 回调 |
| 同步执行 | FastAPI BackgroundTasks |
| 控制台输出 | Logging + TaskManager |
| 单编译器 | 智能回退编译器 ✅ |
|`tex source/`
[翻译失败保留原文: Empty response]
| `data/uploads/{task_id}/`
[翻译失败保留原文: Empty response]
|
| `outputs/`
[翻译失败保留原文: Empty response]
| `data/outputs/{task_id}/`|

## 实施状态

**已完成:**
- ✅ 配置模块
- ✅ 任务管理器
- ✅ 智能编译器

**进行中:**
- ⏳ LaTeX 工具函数
- ⏳ LaTeX 解析器

**待完成:**
- ⏸️ 代理系统 (6个文件)
- ⏸️ API 端点 (7个)