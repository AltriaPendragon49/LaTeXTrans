# PaperX — 基于 RAG + Multi-Agent 的 LaTeX 论文智能翻译系统

PaperX（原名 LaTeXTrans-Pro）是一个专为科研人员打造的 LaTeX 论文翻译与社区平台。系统通过直接操作 `.tex` 源码并在 Docker 隔离环境中进行编译，提供既保持原始排版格式又符合学术规范的高质量翻译。同时，PaperX 也是一个开放的研究论文社区，支持论文发布、浏览、收藏与 AI 学术对话。

## 核心特性

### 翻译功能
- **直接操作 LaTeX 源码**：基于 `pylatexenc` 进行 AST 解析，彻底解决传统 PDF 翻译导致的排版错乱、公式乱码等问题
- **多输入源支持**：拖拽上传 `.zip`/`.tar.gz` 压缩包或 `.tex` 文件夹；输入 arXiv ID 一键抓取源码
- **智能翻译流水线**：解析 → 翻译 → 校验重试 → 重建 → 编译，完整的五阶段 Agent 编排
- **RAG 术语增强**：基于 BM25 + Milvus 向量检索 + Cross-Encoder 重排的术语管理系统，确保专业术语翻译一致性
- **翻译模式切换**：支持全文翻译与文献快速筛查（仅摘要与结论）
- **学术术语表生成**：翻译同时自动生成中英文专业术语对照表
- **PDF 直译模式**：对接 NiuTrans 引擎，支持 PDF 直接翻译

### 编译与格式
- **Docker 隔离编译**：基于 MiKTeX 的纯净编译环境，自动按需安装宏包
- **智能编译策略**：pdflatex → xelatex 自动协商，支持中文字体检测与编译环境自动切换
- **格式保持**：保护 LaTeX 公式、引用、图表、宏命令等结构元素

### 社区平台
- **论文发布与浏览**：翻译后的论文可发布到社区，支持按热度、时间排序
- **论文详情阅读**：提供原文/译文 PDF 在线预览、结构化内容解读（章节、图表、公式）
- **收藏与互动**：支持收藏文件夹、点赞、浏览计数
- **AI 学术助手**：社区智能体（Community Agent）支持论文检索、学术问答、论文导入与翻译

### 用户体验
- **本地认证体系**：支持邮箱/手机号注册登录，JWT 鉴权
- **额度管理系统**：每日 LaTeX 翻译额度 + NiuTrans 积分快照
- **翻译历史云端留存**：支持重新下载 PDF、源码、日志和术语表
- **原文/译文分屏对比**：基于 PDF 的实时对比阅读
- **国际化**：支持中/英/日/韩/德/法/俄/西多语言界面
- **暗色模式**：支持亮色/暗色主题切换

## 系统架构

```
PaperX/
├── frontend/          # React 19 + TypeScript + Vite 前端
├── backend/           # FastAPI (Python) 后端 REST API
├── Docker/            # Docker 构建文件（Backend + TeXLive 编译环境）
├── openspec/          # OpenSpec 项目规范与变更追踪
├── scripts/           # 运维脚本（部署、数据导出、分析等）
└── texts/             # 项目文档与参考资料
```

### 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React 19, TypeScript, Vite 7, TailwindCSS 4, shadcn/ui (Radix), Zustand, React Router 7 |
| **后端** | Python 3.10+, FastAPI, LangChain, LangGraph |
| **数据库** | MySQL (主库), Redis (缓存/队列/热榜) |
| **向量检索** | Milvus + BM25 + Cross-Encoder Reranker |
| **LLM** | Gemini (主力), GPT (备用), 支持多 Key Token Pool |
| **LaTeX** | MiKTeX (Docker), pylatexenc (AST 解析) |
| **存储** | 本地磁盘 / 腾讯云 COS 双模式 |
| **认证** | 本地 JWT 认证 |

## 环境要求

- **Python** 3.10+
- **Node.js** 18+
- **Docker**（用于 LaTeX 编译环境）
- **MySQL** 或 Supabase（用于数据持久化）
- **Redis**（用于缓存与队列，可选）

## 快速开始

### 1. 环境变量配置

```bash
# 后端
cp backend/.env.example backend/.env
# 编辑 backend/.env，配置 LLM API Key、数据库连接等

# 前端
cp frontend/.env.example frontend/.env
# 编辑 frontend/.env，配置后端 API 地址
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

或使用启动脚本：`backend/start.bat` (Windows) / `backend/start.sh` (Linux/Mac)

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173` 进入系统。

### 4. Docker 编译环境构建

```bash
cd Docker
docker build -t latextrans-texlive -f Dockerfile.texlive-base .
docker build -t latextrans-backend -f Dockerfile.backend .
```

## 项目文档

- [后端文档](backend/README.md) — API 接口、服务架构、文件索引
- [前端文档](frontend/README.md) — 组件结构、路由设计、状态管理
- [OpenSpec 规范](openspec/project.md) — 项目约定、架构模式、领域上下文

## 开发规范

- **禁止用正则处理 LaTeX 结构**：必须使用 `pylatexenc` 进行 AST 解析
- **提交信息**：遵循 Conventional Commits 格式（如 `feat: xxx`, `fix: xxx`）
- **OpenSpec 驱动**：新功能/架构变更需先在 `openspec/changes/` 建立提案
- **Docker 编译隔离**：LaTeX 编译必须在 Docker 环境中运行

## 许可证

本项目为学术研究用途开发。
