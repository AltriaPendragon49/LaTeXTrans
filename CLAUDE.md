# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

LaTeXTrans-Pro 是一个基于 AI 的 LaTeX 论文翻译系统，旨在重构为 FastAPI + React 的 Web 平台，并集成 RAG（检索增强）和 Multi-Agent（多智能体）架构。

**当前阶段**: Phase 1 (MVP 骨架) - 原型系统已实现，正在向 Web 平台迁移

**原型系统位置**: `prototype_system/` 目录包含完整的 CLI 工具原型

## 常用命令

### 原型系统 (Prototype System)

```bash
# 基础运行（使用配置文件）
python prototype_system/main.py --config config/default.toml

# 从 arXiv 下载并翻译论文
python prototype_system/main.py --arxiv <arxiv_id>

# 指定模型和 API 配置
python prototype_system/main.py --model <model_name> --key <api_key> --url <base_url>

# 指定输入和输出目录
python prototype_system/main.py --source <tex_source_dir> --output <output_dir>
```

### 环境配置

```bash
# 安装依赖
pip install -r prototype_system/requirements.txt

# 确保系统已安装 LaTeX 编译器（latexmk, pdflatex, xelatex）
# Windows: 安装 MiKTeX
# Linux: apt-get install texlive-full latexmk
# macOS: brew install mactex
```

## 核心架构约束

### 1. LaTeX 解析规则（CRITICAL）

**必须使用 `pylatexenc` 进行 AST 解析，严禁使用正则表达式粗暴处理 LaTeX 结构**

- 解析器位置: `prototype_system/src/formats/latex/parser.py`
- 核心类: `LatexParser`
- 解析流程:
  1. 合并 `\input{}` 和 `\include{}` 文件
  2. 提取 `\newcommand` 定义
  3. 按 section/subsection 分割文档
  4. 提取 caption（标题、摘要、关键词等）
  5. 提取环境（equation, figure, table 等）

**占位符系统**:
- 输入文件: `<PLACEHOLDER_{filename}_begin/end>`
- 环境: `<PLACEHOLDER_ENV_{count}>`
- Caption: `<PLACEHOLDER_CAP_{count}>`
- 新命令: `<PLACEHOLDER_NEWCOMMAND_{count}>`

### 2. 多智能体工作流

位置: `prototype_system/src/agents/`

**CoordinatorAgent** 负责协调以下子 Agent:

1. **ParserAgent**: 解析 LaTeX 文档，生成 JSON 映射文件
   - 输出: `sections_map.json`, `captions_map.json`, `envs_map.json`, `newcommands_map.json`, `inputs_map.json`

2. **TranslatorAgent**: 使用 LLM 翻译文本块
   - 支持两种模式:
     - Mode 0: 完整翻译
     - Mode 1: 错误修复模式
   - 异步执行以提高效率

3. **ValidatorAgent**: 验证翻译后的 LaTeX 语法
   - 检测未闭合的括号、环境等
   - 生成 `errors_report.json`

4. **GeneratorAgent**: 重建 LaTeX 并编译
   - 使用 `latexmk` 编译
   - 先尝试 `pdflatex`，失败后使用 `xelatex`
   - 日文翻译使用 `lualatex`

**重试机制**: 最多重试 3 次编译错误修复

### 3. LaTeX 编译流程

位置: `prototype_system/src/formats/latex/compile.py`

编译顺序:
1. 首先使用 `latexmk -pdflatex`
2. 失败则尝试 `latexmk -xelatex`
3. 日文目标语言使用 `latexmk -lualatex`

编译参数:
```bash
latexmk -pdflatex -interaction=nonstopmode -outdir=<build_dir> -file-line-error -synctex=1 -f <main.tex>
```

### 4. 配置文件结构

`prototype_system/config/default.toml`:

```toml
sys_name = "LaTeXTrans"
version = "0.1.0"
target_language = "ch"  # ch (中文), ja (日文), en (英文)
source_language = "en"
paper_list = []  # arXiv IDs 列表
tex_sources_dir = "tex source"
output_dir = "outputs"

[llm_config]
model = ""        # 模型名称
api_key = ""      # API 密钥
base_url = ""     # API 基础 URL
```

## 重要实现细节

### 不需翻译的环境 (No-Translate Environments)

以下 LaTeX 环境会被原样保留:
- 数学环境: `equation`, `align`, `gather`, `cases`, `split`, `multline`, `subequations`
- 图表: `figure`, `table`, `tabular`, `tikzpicture`
- 代码: `lstlisting`, `minted`, `verbatim`
- 算法: `algorithm`, `algorithmic`, `algorithmicx`
- 引用: `thebibliography`, `bibitem`

这些环境会被替换为占位符，翻译完成后再还原。

### Section 合并策略

- 使用 `tiktoken` 计算 token 数
- 小于 50 tokens 的 section 会与相邻 section 合并
- 减少 API 调用次数，提高效率

### 异步事件循环管理

`CoordinatorAgent` 使用自定义事件循环:
- Windows 平台需要特殊处理 `shutdown_asyncgens()`
- 每次工作流结束后关闭并重新创建事件循环
- 避免事件循环冲突

## 输出文件结构

```
outputs/
└── ch_arXiv-2412.13736v1/           # 翻译后的项目目录
    ├── arXiv-2412.13736v1/          # 重建的 LaTeX 源码
    │   ├── main.tex
    │   ├── main.bib
    │   ├── image/
    │   └── build_pdflatex/          # 编译输出
    │       └── main.pdf
    ├── ch_arXiv-2412.13736v1.pdf    # 最终翻译的 PDF
    ├── sections_map.json            # 分段映射
    ├── captions_map.json            # 标题映射
    ├── envs_map.json                # 环境映射
    ├── newcommands_map.json         # 命令定义映射
    ├── inputs_map.json              # 输入文件映射
    └── errors_report.json           # 错误报告（如有）
```

## 开发路线图（待实现）

### Phase 2: RAG 增强
- 搭建 ChromaDB 向量库
- 实现术语提取与混合检索（Semantic + BM25）
- 使用 Cross-Encoder 重排序

### Phase 3: Agent 协作
- 重构为 LangChain 架构
- 实现 Docker 内的编译与错误修复循环
- 集成 Gemini-Vision 进行图片内容识别

### Phase 4: Web 交互
- FastAPI 后端 + React 前端
- 双栏实时预览（Source vs PDF）
- 异步任务队列（Redis + Celery）

## 技术栈锁定（未来架构）

- **Backend**: Python 3.10+, FastAPI, LangChain
- **Frontend**: React, TailwindCSS, Vite
- **Database**: ChromaDB (Vector), Redis (Queue)
- **Embedding**: bge-m3
- **Multi-modal**: Gemini-Vision
- **Retrieval**: Hybrid (Semantic + BM25) with Cross-Encoder re-ranking
- **LLM**: Gemini via LangChain (fallback to GPT)
- **LaTeX Engine**: MiKTeX (via Docker, with 'install on the fly')

## 代码修改注意事项

1. **AST 解析**: 任何对 LaTeX 结构的解析必须基于 `pylatexenc`，不得使用简单的字符串匹配
2. **占位符格式**: 保持占位符命名一致性，确保解析和重建过程配对
3. **异步函数**: 翻译 Agent 使用异步 I/O，修改时注意事件循环管理
4. **编译顺序**: 不要改变 pdflatex → xelatex → lualatex 的回退顺序
5. **JSON 映射文件**: 这些文件用于调试和中间状态保存，不要省略生成步骤
6. **错误重试**: 最大重试次数为 3 次，避免无限循环

## 常见问题

### 编译失败
- 检查系统是否安装 `latexmk`
- 查看 `build_pdflatex/main.log` 日志文件
- 确认所有引用的图片和 `.bib` 文件存在

### 翻译质量问题
- 当前阶段未实现 RAG，术语翻译依赖 LLM 能力
- 可通过修改 `prompts.py` 调整 prompt

### 内存占用
- 大型文档会产生较多 JSON 映射文件
- 可通过增大 `_merge_short_sections` 的 `min_tokens` 参数减少分段数量

## 术语翻译

**关键术语（一致性要求）**:
- Self-Attention → 自注意力
- Transformer → Transformer（保持英文）
- Fine-tuning → 微调
- RAG (Retrieval-Augmented Generation) → 检索增强生成
