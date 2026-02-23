# LaTeXTrans-Pro: 基于大模型的 LaTeX 论文智能翻译系统

LaTeXTrans-Pro 是一个专为科研人员打造的 LaTeX 论文翻译工具。通过直接操作 `.tex` 源码，并在隔离环境中进行编译，系统能够提供既保持原始排版格式，又符合学术规范的高质量翻译。

系统采用现代前后端分离架构，结合 Supabase 提供完善的用户认证与任务历史管理。

## ✨ 核心特性

- **直接操作 LaTeX 源码**: 彻底解决传统 PDF 翻译导致的排版错乱、公式乱码等问题。
- **多种输入源支持**:
  - **拖拽上传**: 支持直接拖拽 `.zip`、`.tar.gz` 压缩包或包含 `.tex` 文件的文件夹。
  - **arXiv 一键抓取**: 输入论文 ID，自动下载源码并准备翻译。
- **先进的翻译功能**:
  - **自动处理引用与图片**: 智能提取 LaTeX 结构，翻译时保护公式与宏命令。
  - **学术术语生成**: 翻译同时可自动生成中英文专业术语对照表。
  - **翻译模式切换**: 支持“全文翻译”与“文献快速筛查（仅摘要与结论）”两种模式。
- **智能编译与错误处理**:
  - 在 Docker 环境中隔离运行纯净的 MiKTeX，自动按需安装宏包。
  - 支持 `pdflatex`、`xelatex` 及自动协商编译策略（例如自动降级，或因含有中文等 Unicode 字符自动选择支持环境）。
- **完善的用户体验**:
  - 基于 Supabase 的账户认证体系（支持访客匿名试用）。
  - 个性化配置持久化（记录自定义 API Key、偏好模型等）。
  - 翻译历史云端留存，支持重新下载 PDF、源码、日志和术语表。
  - 前端支持 PDF 原文与译文分屏实时对比。

## 🏗️ 系统架构

整个系统包含三个核心组成部分：

- **Frontend (Web UI)**: 基于 React 19 + TypeScript + Vite 构建，使用 Tailwind CSS & shadcn/ui 提供现代化界面。用户可以在此处进行文件上传、配置调整、任务状态轮询和 PDF 阅读对比。 
  - 详情请查阅: [前端文档 (frontend/README.md)](frontend/README.md)
  
- **Backend (Web API)**: 基于 FastAPI (Python) 构建的纯 REST API。负责接收请求、解析 LaTeX 语法 (AST)、管理翻译和编译流程，以及与 LLM API 交互。
  - 详情请查阅: [后端文档 (backend/README.md)](backend/README.md)

- **Supabase (BaaS)**: 用作系统的用户中心及数据库引擎 (PostgreSQL)，负责处理 JWT 鉴权、翻译历史存储、任务状态同步等持久化需求。

### 目录结构

```text
Project-Root/
├── backend/                # FastAPI 后端服务 (REST API, LaTeX 解析, Agent 逻辑)
├── frontend/               # React 前端应用 (Web UI, 用户面板, 配置管理)
├── docker/                 # 环境编排相关 (Dockerfile.miktex, docker-compose)
├── openspec/               # OpenSpec 项目规范与需求变更追踪档案
└── data/                   # 本地存储卷 (包含用户上传文件、翻译产出)
```

## 🚀 快速开始

本项目依赖 Python 3.10+、Node.js 18+ 以及 Docker (用于提供 LaTeX 编译环境)。以下步骤假定您希望在本地运行开发服务器。

### 1. 配置必要的环境

在启动任何服务前，建议申请并配置好您的大模型 (LLM) API Key 以及 Supabase 项目参数。您可以在前端 UI 界面中直接填写并保存您的个人专属 API 密钥。

### 2. 启动后端 (Backend)

```bash
cd backend
pip install -r requirements.txt
# (可选) 复制并配置 .env 文件中的 LLM 默认参数与 Supabase 凭据
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

或者使用提供的启动脚本：
- Windows: 运行 `backend/start.bat`
- Linux/Mac: 运行 `./backend/start.sh`

### 3. 启动前端 (Frontend)

```bash
cd frontend
npm install
npm run dev
```

启动后，访问 `http://localhost:5173` 即可进入系统主界面。

### 4. Cloudflare 免费公网穿透部署

为方便团队内部测试，项目可以通过 Cloudflare Tunnel 与 Pages 快速部署至公网：

```powershell
# 1. 安装工具 (Wrangler 与 cloudflared)
npm install -g wrangler
winget install Cloudflare.cloudflared

# 2. 确保后端在运行中，并开启 Tunnel
.\scripts\start-tunnel.ps1
# (记录此时终端输出的 TryCloudflare URL)

# 3. 构建并发布前端静态文件
.\scripts\deploy-frontend.ps1 -TunnelUrl "https://您的tunnel地址"
```

> ⚠️ 注意: 临时 Tunnel 地址在每次重启后均会变化，若需要长期稳定使用，请在 Cloudflare Dashboard 中配置固定 Tunnel。

## 📖 规范与贡献

该项目采用 **OpenSpec** 驱动的纯规划开发模式，所有新功能、变更以及架构更新都必须首先在 `openspec/changes/` 目录中建立提案并经过验证后方可执行。

### 贡献流程
1. 查看已有规范: 浏览 `openspec/specs/` 了解系统当前的真实行为。
2. 提案撰写: 使用 `openspec init` 和对应指令生成修改草案，确保所有包含的需求都有明确的 Scenario 验证。
3. 执行: 只有提案完全通过 `openspec validate` 后，才可开始编写前端或后端代码。
4. 提交测试: 确保 AST 解析测试通过，并在提交中使用 Conventional Commits (例如: `feat: add guest cleanup`).

更多细节请参考 [OpenSpec 指南 (openspec/AGENTS.md)](openspec/AGENTS.md).