# LaTeXTrans-Pro: 基于检索增强与智能体协作的 LaTeX 论文翻译系统

Project Title: Design and Implementation of LaTeX Paper Translation System Based on RAG and Agent Collaboration

Status: In Development (Phase 1: MVP Skeleton)

Original Prototype: NiuTrans/LaTeXTrans

## 1. 项目背景与目标

本项目旨在解决科研人员阅读和撰写外文 LaTeX 论文时的痛点。不同于传统的 PDF 翻译工具，本系统直接操作 `.tex` 源码，保证翻译后的文档格式不乱、公式不崩、可重新编译。

**核心痛点解决：**

* **术语幻觉**：通过 RAG 技术引入外部术语表，解决学术名词（如 "Self-Attention" 被误译为 "自关注"）等问题。
* **上下文缺失**：通过 Agent 协作，自动解析 `\cite{}` 引用内容和 `\includegraphics{}` 图片内容，辅助翻译。
* **编译报错**：内置 Compiler Agent，自动捕获编译日志并尝试修复 LaTeX 语法错误。

## 2. 系统架构

系统采用微服务架构，主要包含以下模块：

### 2.1 目录结构

```text
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
```

### 2.2 核心工作流

1. **Input**: 用户上传 `.zip` (包含 `.tex` 和图片)，或使用 CLI 工具下载 arXiv 论文。
2. **Parse**: LaTeXParser 将源码解析为 AST，剥离出纯文本，保留公式/宏命令骨架。
3. **RAG 检索**: 对文本块提取关键词，在 ChromaDB 中混合检索 (Semantic + Keyword) 相关术语。
4. **Agent Loop**:
   * *TranslateTool*: 结合 RAG 结果翻译文本。
   * *CiteTool*: (可选) 查询 arXiv 获取引用背景。
   * *ImageTool*: (可选) 识别图片内容。
5. **Reconstruct**: 将译文回填至 AST 骨架，还原为 `.tex` 文件。
6. **Compile & Heal**: 尝试编译，若失败则分析系统日志，通过 Agent 自动修复并重试。
7. **Output**: 生成双语对照 PDF 及翻译后的源码包。

## 3. 功能特性 (Roadmap)

根据项目执行规划，开发分为以下阶段：

- [ ] **Phase 1: MVP 骨架 (进行中)**
  - [ ] 实现文件上传/下载接口及 CLI `--arxiv` 支持。
  - [ ] 移植原型的 AST 解析逻辑。
  - [ ] 跑通 "Tex -> String -> LLM -> String -> Tex" 闭环。
- [ ] **Phase 2: RAG 增强**
  - [ ] 搭建 ChromaDB 向量库。
  - [ ] 实现术语提取与混合检索。
- [ ] **Phase 3: Agent 协作**
  - [ ] 重构为 LangChain 架构。
  - [ ] 实现 Docker 内的编译与错误修复循环 (MiKTeX)。
- [ ] **Phase 4: Web 交互**
  - [ ] 双栏实时预览 (Source vs PDF)。
  - [ ] 异步任务队列 (Redis + Celery)。

## 4. 快速开始 (Quick Start)

### 环境要求
* Python 3.10+
* Node.js 18+
* Docker & Docker Compose
* MiKTeX (推荐使用 Docker 镜像，配置 `install on the fly`)

### 本地开发 (MVP阶段)

**1. 启动后端:**
```bash
cd backend
pip install -r requirements.txt
# 配置环境变量: 在 backend/.env 中配置 LLM_API_KEY 等必要参数
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**2. 启动前端:**
```bash
cd frontend
npm install
npm run dev
```

**3. CLI 示例:** 
```bash
python main.py --arxiv 2508.18791
```

### Cloudflare 部署 (外部访问)

如需让外部用户快速访问体验系统，可使用 Cloudflare Pages + Tunnel 进行免费部署：

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
# 请记录输出的公网 URL (如: https://xxx-xxx.trycloudflare.com)
```

**4. 部署前端:**
```powershell
.\scripts\deploy-frontend.ps1 -TunnelUrl "https://你的tunnel地址"
```

**5. 访问地址**: 
前端部署完成后，访问对应的 Pages 链接（如 `https://latextrans.pages.dev`）。

> **注意**: 如果使用临时 Tunnel，每次重启后端 Tunnel 地址可能会变化，需要重新部署并绑定前端。保持 Tunnel 终端开启以维持稳定的长连接。

## 5. 贡献指南

* 提交代码前请确保通过最新的 AST 解析测试。
* 所有新功能必须包含对应的单元测试覆盖。
* Commit Message 需遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/v1.0.0/) 规范 (例如: `feat: add rag retriever`).