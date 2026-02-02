LaTeXTrans-Pro: 基于检索增强与智能体协作的 LaTeX 论文翻译系统

Project Title: Design and Implementation of LaTeX Paper Translation System Based on RAG and Agent Collaboration

Status: In Development (Phase 1: MVP Skeleton)

Original Prototype: NiuTrans/LaTeXTrans

🤖 1. AI 协作者指南 (Context for AI Assistants)

如果你是协助开发本项目的 AI 模型，请在开始工作前阅读以下核心约束：

核心任务：将现有的单机 Python CLI 工具 (LaTeXTrans) 重构为一个基于 FastAPI(langchain) + React 的 Web 平台，并集成 RAG (检索增强) 和 Multi-Agent (多智能体) 架构。

开发策略：Skeleton First (骨架优先)。先打通全链路，再填充复杂逻辑。

关键约束：

AST 解析：必须使用 pylatexenc 进行抽象语法树解析，严禁使用正则表达式粗暴处理 LaTeX 结构。

编译自愈：必须在 Docker 隔离环境中运行 xelatex，使用 MiKTeX 并启用 'install on the fly'。

术语一致性：翻译必须通过 RAG 检索领域术语表，不能仅依赖模型幻觉。

技术栈锁定：

Backend: Python 3.10+, FastAPI, LangChain

Frontend: React, TailwindCSS, Vite

Database: ChromaDB (Vector), Redis (Queue)

Embedding: bge-m3

Multi-modal: Gemini-Vision

Retrieval: Hybrid (Semantic + BM25) with Cross-Encoder re-ranking

LLM: Gemini via LangChain (fallback to GPT)

LaTeX Engine: MiKTeX (via Docker, with 'install on the fly')

AI 理解项目内容辅助：

- 模块伪代码示例：
  Parser: latex_source -> pylatexenc.parse() -> AST -> extract_text_nodes() -> text_chunks
  RAG: query = extract_keywords(text_chunk); results = hybrid_search(chroma_db, query, bm25); reranked = cross_encoder_rerank(results); prompt = inject_context(reranked, text_chunk)
  Agent: agent = LangChain.Agent(tools=[TranslateTool(RAG), CiteTool(arxiv_api), ImageTool(gemini_vision), CompilerTool(docker_xelatex)]); agent.run(input=AST_chunks)

- 工作流图描述（文本ASCII）：
  User Upload (.zip) or CLI --arxiv ID --> Download (if arXiv) --> Parse AST --> Chunk Text --> RAG Retrieve --> Agent Loop (Translate + Tools) --> Reconstruct Tex --> Compile (Docker MiKTeX) --> Heal if Error --> Output PDF/Tex

- Agent 角色/示例：
  Translator Agent: 结合RAG翻译文本。示例: Input "Self-Attention mechanism"; RAG retrieves "自注意力"; Output: 一致翻译。
  Compiler Agent: 分析log修复。示例: Error "Undefined control sequence"; Agent: Add \usepackage{} and retry.

2. 项目背景与目标

本项目旨在解决科研人员阅读和撰写外文 LaTeX 论文时的痛点。不同于传统的 PDF 翻译工具，本系统直接操作 .tex 源码，保证翻译后的文档格式不乱、公式不崩、可重新编译。

核心痛点解决

术语幻觉：通过 RAG 技术引入外部术语表，解决 "Self-Attention" 被误译为 "自关注" 等问题。

上下文缺失：通过 Agent 协作，自动解析 \cite{} 引用内容和 \includegraphics{} 图片内容，辅助翻译。

编译报错：内置 Compiler Agent，自动捕获编译日志并修复 LaTeX 语法错误。

3. 系统架构

系统采用微服务架构，主要包含以下模块：

3.1 目录结构 (Directory Structure)

Project-Root/
├── backend/                # FastAPI 后端服务
│   ├── app/
│   │   ├── core/           # 配置与工厂模式
│   │   ├── api/            # RESTful 接口 (Upload, Translate)
│   │   ├── services/       # 核心业务逻辑
│   │   │   ├── parser/     # AST 解析器 (基于 pylatexenc)
│   │   │   ├── rag/        # 向量检索服务 (ChromaDB)
│   │   │   └── agents/     # LangChain 智能体 (Translator, Compiler)
│   │   └── utils/          # 日志与工具
│   ├── tests/              # 单元测试
│   └── requirements.txt
├── frontend/               # React 前端应用
├── docker/                 # 容器化配置
│   ├── Dockerfile.backend
│   └── Dockerfile.miktex  # 纯净的编译环境 (MiKTeX with install on the fly)
└── data/                   # 本地存储 (上传文件, 向量库, 术语表)

3.2 核心工作流 (Workflow)

Input: 用户上传 .zip (包含 .tex 和图片)，或 CLI: python main.py --arxiv <ID> (下载arXiv论文)。

Parse: LaTeXParser 将源码解析为 AST，剥离出纯文本，保留公式/宏命令骨架。

RAG:

对文本块提取关键词。

在 ChromaDB 中混合检索 (Semantic + Keyword) 术语。

Agent Loop:

TranslateTool: 结合 RAG 结果翻译文本。

CiteTool: (可选) 查询 arXiv 获取引用背景。

ImageTool: (可选) 识别图片内容。

Reconstruct: 将译文回填至 AST 骨架，还原为 .tex。

Compile & Heal: 尝试编译 -> 若失败 -> 分析 Log -> Agent 修复 -> 重试。

Output: 生成双语对照 PDF 及翻译后的源码包。

4. 功能特性 (Roadmap)

根据《项目执行规划》，开发分为五个阶段：

[ ] Phase 1: MVP 骨架 (进行中)

[ ] 实现文件上传/下载接口及 CLI --arxiv 支持。

[ ] 移植原型的 AST 解析逻辑。

[ ] 跑通 "Tex -> String -> LLM -> String -> Tex" 闭环。

[ ] Phase 2: RAG 增强

[ ] 搭建 ChromaDB 向量库。

[ ] 实现术语提取与混合检索。

[ ] Phase 3: Agent 协作

[ ] 重构为 LangChain 架构。

[ ] 实现 Docker 内的编译与错误修复循环 (MiKTeX)。

[ ] Phase 4: Web 交互

[ ] 双栏实时预览 (Source vs PDF)。

[ ] 异步任务队列 (Redis + Celery)。

5. 快速开始 (Quick Start)

环境要求

Python 3.10+

Node.js 18+

Docker & Docker Compose

MiKTeX (via Docker, install on the fly)

本地开发 (MVP阶段)

启动后端:

cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

启动前端:

cd frontend
npm install
npm run dev

CLI 示例: python main.py --arxiv 2508.18791 (下载、翻译、编译)

配置环境变量:
在 backend/.env 中配置 LLM API Key (Gemini)。

### Cloudflare 部署 (外部访问)

如需让外部用户访问系统，可使用 Cloudflare Pages + Tunnel 进行免费部署：

**1. 安装依赖工具:**
```powershell
# 安装 Wrangler CLI (Cloudflare Pages)
npm install -g wrangler

# 安装 cloudflared (Cloudflare Tunnel)
winget install Cloudflare.cloudflared
```

**2. 启动本地后端:**
```powershell
cd backend
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

**3. 启动 Tunnel 暴露后端:**
```powershell
.\scripts\start-tunnel.ps1
# 记录输出的公网 URL (如: https://xxx-xxx.trycloudflare.com)
```

**4. 部署前端:**
```powershell
.\scripts\deploy-frontend.ps1 -TunnelUrl "https://你的tunnel地址"
```

**5.地址**：https://latextrans.pages.dev


> **注意**: 每次启动 Tunnel 地址会变化，需要重新部署前端。保持 Tunnel 终端开启以维持连接。

6. 贡献指南

提交代码前请确保通过 AST 解析测试。

所有新功能必须包含对应的单元测试。

Commit Message 需遵循 Conventional Commits 规范 (e.g., feat: add rag retriever).