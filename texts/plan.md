# 基于检索增强与智能体协作的 LaTeX 论文翻译系统 - 可执行实施计划

> **最后更新**: 2026-01-01
> **项目状态**: Phase 0（原型完成） → Phase 1-5 逐步实施
> **原型系统**: `prototype_system/`（多智能体 CLI 工具，已完成）

---

## 0. 项目总览与核心策略

### 核心目标
将现有的 **CLI 原型工具**（LaTeXTrans）重构为一个基于 **FastAPI + React 的 Web 平台**，并集成 **RAG（检索增强）** 和 **Multi-Agent（多智能体）** 架构。

### 开发策略
**Skeleton First（骨架优先）**：先打通全链路，再填充复杂逻辑。

### 技术栈锁定

| 模块 | 技术选型 |
|------|----------|
| **Backend** | Python 3.10+, FastAPI, LangChain |
| **Frontend** | React 18+, TailwindCSS, Vite |
| **Database** | ChromaDB (向量库), Redis (任务队列) |
| **Embedding** | bge-m3 |
| **Retrieval** | Hybrid (Semantic + BM25) + Cross-Encoder re-ranking |
| **Multi-modal** | Gemini-Vision（图片识别） |
| **LLM** | Gemini via LangChain (fallback to GPT) |
| **LaTeX Engine** | MiKTeX (via Docker, with 'install on the fly') |

### 核心约束（AI 协作者必读）

1. **AST 解析**：必须使用 `pylatexenc` 进行抽象语法树解析，严禁使用正则表达式粗暴处理 LaTeX 结构
2. **编译自愈**：必须在 Docker 隔离环境中运行 xelatex，使用 MiKTeX 并启用 'install on the fly'
3. **术语一致性**：翻译必须通过 RAG 检索领域术语表，不能仅依赖模型幻觉

---

## 📅 整体时间线

根据用户实际情况（1-2 周紧急答辩 vs 正常开发），可灵活调整：

| 阶段 | 最短时间线 | 正常时间线 | 关键里程碑 | 优先级 |
|------|-----------|-----------|------------|--------|
| **Phase 1: MVP 骨架** | 3-5 天 | 2 周 | Web 端能上传、翻译、下载 PDF | 🔴 必须 |
| **Phase 2: RAG 增强** | - | 1-2 周 | 术语一致性提升 | 🟡 重要 |
| **Phase 3: Agent 协作** | - | 2 周 | LangChain 重构 + 多模态 | 🟡 重要 |
| **Phase 4: Web 交互优化** | - | 1 周 | 双栏预览 + 实时日志 | 🟢 可选 |
| **Phase 5: 测试与论文** | 2-3 天 | 1-2 周 | 评估数据 + 论文撰写 | 🔴 必须 |

**说明**：
- **紧急模式**（1-2周）：优先完成 Phase 1 + Phase 5（Web 平台 + 论文数据）
- **正常模式**（1-3月）：按顺序完成所有 Phase

---

## 第一阶段：最小可用骨架搭建（MVP Phase）

**目标**：两周内完成。抛开 RAG 和 Agent，先实现一个"Web 版的 LaTeX 翻译器"。让数据能在前端和后端之间跑通，并支持 CLI `--arxiv`。

**可交付成果**：
- ✅ 用户可通过 Web 界面上传 `.zip` 或输入 arXiv ID
- ✅ 后台自动翻译（复用现有 Agent 系统）
- ✅ 前端显示实时进度
- ✅ 翻译完成后可下载 PDF 和源码

---

### 1.1 原型代码重构与环境准备

#### [ ] 步骤 1：审计原型系统代码
**目的**：理解现有实现，确定哪些可以直接复用

**操作**：
- 阅读 `prototype_system/src/agents/coordinator_agent.py`（协调器）
- 阅读 `prototype_system/src/formats/latex/parser.py`（AST 解析）
- 阅读 `prototype_system/src/formats/latex/compile.py`（编译器）

**输出**：复用文件清单

#### [ ] 步骤 2：初始化项目结构
**目的**：创建 FastAPI + React 的目录骨架

**操作**：
```bash
# 创建后端目录
mkdir -p backend/app/{core,api/routes,services/{agents,latex}}

# 创建前端目录（使用 Vite）
npm create vite@latest frontend -- --template react
cd frontend && npm install axios tailwindcss
```

**目录结构**：
```
LaTeXTrans/
├── backend/                # FastAPI 服务
│   ├── app/
│   │   ├── core/           # 配置与工厂模式
│   │   ├── api/routes/     # RESTful 接口
│   │   ├── services/       # 核心业务逻辑
│   │   │   ├── agents/     # Agent 系统（复制自原型）
│   │   │   └── latex/      # LaTeX 处理（复制自原型）
│   │   └── utils/          # 日志与工具
│   ├── tests/              # 单元测试
│   └── requirements.txt
├── frontend/               # React 前端应用
│   ├── src/
│   │   ├── components/     # UI 组件
│   │   └── utils/          # API 封装
│   └── package.json
├── docker/                 # 容器化配置
│   ├── Dockerfile.backend
│   └── Dockerfile.miktex   # LaTeX 编译环境
├── data/                   # 本地存储
│   ├── uploads/            # 用户上传文件
│   ├── outputs/            # 翻译结果
│   └── terms/              # 术语表（CSV）
└── prototype_system/       # 原型系统（保留作为参考）
```

#### [ ] 步骤 3：封装 LaTeXParser 类
**目的**：将原型的解析逻辑适配为 Web 服务

**复用文件**：
- `prototype_system/src/formats/latex/parser.py` → `backend/app/services/latex/parser.py`
- `prototype_system/src/formats/latex/utils.py` → `backend/app/services/latex/utils.py`

**关键修改**：
- 移除所有 Streamlit 依赖（`st.progress()`, `st.text()` 等）
- 添加进度回调机制

#### [ ] 步骤 4：添加 CLI 入口支持 `--arxiv`
**目的**：保留原型的 CLI 功能，同时为 Web 接口提供复用

**操作**：
- 复用 `prototype_system/main.py` 的 `--arxiv` 参数处理逻辑
- 封装 `batch_download_arxiv_tex()` 为独立函数

---

### 1.2 基础后端服务（FastAPI）

#### [ ] 步骤 1：安装 FastAPI 和 uvicorn
```bash
cd backend
pip install fastapi uvicorn python-multipart python-dotenv aiohttp
```

#### [ ] 步骤 2：创建 FastAPI 应用骨架
**文件**：`backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LaTeXTrans API", version="1.0.0")

# 配置 CORS（允许前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "LaTeXTrans API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "latex": check_latex_available()}
```

#### [ ] 步骤 3：实现 POST `/upload` 接口
**文件**：`backend/app/api/routes/upload.py`

**功能**：
- 接收 `.zip` 或 `.tex` 文件
- 保存到 `data/uploads/{task_id}/`
- 调用 `extract_compressed_files()`（复用原型）
- 返回 `{"task_id": "uuid", "status": "pending"}`

**代码框架**：
```python
from fastapi import APIRouter, UploadFile, File
import uuid

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    # 1. 保存文件
    # 2. 解压（如果是 .zip）
    # 3. 创建任务记录
    return {"task_id": task_id, "status": "pending"}
```

#### [ ] 步骤 4：实现 POST `/translate` 接口
**文件**：`backend/app/api/routes/translate.py`

**功能**：
- 触发后台翻译任务
- 使用 `BackgroundTasks` 异步执行
- 调用 `CoordinatorAgent.workflow_latextrans()`

**代码框架**：
```python
from fastapi import APIRouter, BackgroundTasks

router = APIRouter()

@router.post("/translate/{task_id}")
async def start_translation(task_id: str, background_tasks: BackgroundTasks):
    # 1. 验证 task_id 存在
    # 2. 加载配置
    # 3. 后台任务: background_tasks.add_task(run_translation, task_id)
    return {"message": "Translation started"}

async def run_translation(task_id: str):
    # 调用 CoordinatorAgent
    pass
```

#### [ ] 步骤 5：实现 GET `/task/{task_id}` 接口
**文件**：`backend/app/api/routes/task.py`

**功能**：
- 查询任务状态和进度
- 返回 `{"status": "translating", "progress": 45, "message": "..."}`

**任务状态管理**：
```python
# backend/app/services/task_manager.py
class TaskManager:
    def __init__(self):
        self._tasks = {}  # {task_id: {"status": "...", "progress": 0-100}}

    async def update_progress(self, task_id, status, progress):
        self._tasks[task_id] = {"status": status, "progress": progress}
```

#### [ ] 步骤 6：实现 GET `/download` 接口
**文件**：`backend/app/api/routes/download.py`

**功能**：
- 下载翻译后的 PDF：`/download/{task_id}/pdf`
- 下载源码包：`/download/{task_id}/source`（打包为 .zip）

#### [ ] 步骤 7：集成 CLI 到后端逻辑
**目的**：复用 arXiv 下载功能

**操作**：
- 创建 POST `/arxiv` 接口
- 接收 `{"arxiv_id": "2508.18791"}`
- 调用 `batch_download_arxiv_tex()`

---

### 1.3 基础前端界面

#### [ ] 步骤 1：初始化 React 项目（已完成）
```bash
cd frontend
npm install axios tailwindcss @headlessui/react
npx tailwindcss init
```

#### [ ] 步骤 2：实现文件拖拽上传组件
**文件**：`frontend/src/components/FileUpload.jsx`

**功能**：
- 拖拽上传 `.tex` 或 `.zip`
- 调用 `POST /upload`
- 获取 task_id

#### [ ] 步骤 3：实现进度条组件
**文件**：`frontend/src/components/ProgressTracker.jsx`

**功能**：
- 轮询 `GET /task/{task_id}`（每 2 秒）
- 显示进度条（0-100%）
- 显示当前阶段（解析 → 翻译 → 编译）

#### [ ] 步骤 4：实现下载按钮组件
**文件**：`frontend/src/components/DownloadButton.jsx`

**功能**：
- 翻译完成后显示
- 点击下载 PDF 或源码

#### [ ] 步骤 5：实现主页面布局
**文件**：`frontend/src/App.jsx`

**布局**：
- 左侧：文件上传 OR arXiv ID 输入（Tab 切换）
- 右侧：进度显示 + 下载按钮

---

### 阶段里程碑（Phase 1）

**测试场景**：
1. 用户上传一个简单的 `.tex` 文件 → 翻译成功 → 下载 PDF
2. 用户输入 arXiv ID（如 `2508.18791`）→ 自动下载 → 翻译 → 下载 PDF

**验收标准**：
- ✅ Web 界面能访问（http://localhost:5173）
- ✅ 文件上传功能正常
- ✅ 翻译进度实时更新
- ✅ PDF 能正常打开且格式正确

**如果通过，进入 Phase 2；否则，不要进入下一阶段！**

---

## 第二阶段：核心升级 —— 检索增强（RAG）模块

**目标**：解决"术语不一致"问题。在翻译流程中插入 RAG 环节。

**当前问题**：
- 原型系统使用静态 CSV 术语表，术语匹配能力弱
- "Self-Attention" 可能被误译为 "自关注"

**解决方案**：
- 构建向量数据库（ChromaDB）
- 混合检索（Semantic + BM25）
- Cross-Encoder 重排序

---

### 2.1 知识库构建（Offline Pipeline）

#### [ ] 步骤 1：准备术语数据源
**数据来源**：
- 现有术语表：`prototype_system/terms/*.csv`
- 领域文献：从 arXiv 下载论文 PDF（如 cs.AI、cs.CV 领域）
- 用户自定义术语表

**操作**：
```bash
# 将 CSV 术语表转换为向量数据
python backend/scripts/build_term_db.py --input prototype_system/terms/ --output data/chromadb/
```

#### [ ] 步骤 2：实现文档读取脚本
**文件**：`backend/scripts/build_term_db.py`

**功能**：
- 读取 PDF 文献（使用 `PyPDF2` 或 `unstructured`）
- 读取 CSV 术语表
- 提取术语对（英文 → 中文）

#### [ ] 步骤 3：实现 Intelligent Chunking
**目的**：按语义或 LaTeX 段落切分文本

**策略**：
- 使用 `pylatexenc` 解析 LaTeX 结构
- 按 section/paragraph 切分
- 每个 chunk 保持上下文完整性

#### [ ] 步骤 4：部署 ChromaDB
**安装**：
```bash
pip install chromadb sentence-transformers
```

**初始化数据库**：
```python
import chromadb
client = chromadb.Client()
collection = client.create_collection(name="latex_terms")
```

#### [ ] 步骤 5：使用 bge-m3 Embedding 存入向量库
**文件**：`backend/services/rag/embedder.py`

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-m3')

def embed_terms(terms):
    return model.encode(terms)
```

---

### 2.2 检索与注入（Online Pipeline）

#### [ ] 步骤 1：实现混合检索
**文件**：`backend/services/rag/retriever.py`

**功能**：
- Vector Search（语义相似度）
- BM25（精确匹配）
- 混合得分：`score = α * semantic + (1-α) * bm25`

#### [ ] 步骤 2：引入 Cross-Encoder 重排序
**安装**：
```bash
pip install sentence-transformers
```

**代码**：
```python
from sentence_transformers import CrossEncoder

cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank(query, candidates):
    scores = cross_encoder.predict([(query, c) for c in candidates])
    return sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
```

#### [ ] 步骤 3：修改翻译 Prompt，增加 `{context}` 槽位
**原 Prompt**：
```
Translate the following LaTeX text to Chinese: {text}
```

**新 Prompt（RAG 增强）**：
```
You are a professional LaTeX translator. Use the following glossary for consistent terminology:

<Glossary>
{retrieved_terms}
</Glossary>

Translate the following LaTeX text to Chinese: {text}
```

#### [ ] 步骤 4：逻辑变更
**原流程**：
```
Parse AST → Extract text → LLM translate → Reconstruct
```

**新流程（RAG）**：
```
Parse AST → Extract text → Extract keywords → RAG retrieve → Assemble prompt → LLM translate → Reconstruct
```

**文件**：`backend/services/agents/translator.py`

**修改点**：
```python
# 在翻译前调用 RAG
retrieved_terms = rag_retriever.search(text_chunk, top_k=5)
prompt = build_prompt_with_context(text_chunk, retrieved_terms)
```

---

### 阶段里程碑（Phase 2）

**测试场景**：
上传一篇包含生僻术语（如 "Self-Attention"）的论文 → 系统能根据预设的术语表将其准确翻译为 "自注意力"，而不是直译。

**验收标准**：
- ✅ ChromaDB 向量库正常运行
- ✅ 术语检索准确率 > 90%（手动抽查 10 个术语）
- ✅ 翻译质量主观评分提升（对比 Phase 1）

---

## 第三阶段：核心升级 —— 智能体协作（Agent）模块

**目标**：解决"上下文缺失"和"编译报错"问题。用 LangChain 重构业务逻辑。

**当前问题**：
- 翻译时缺少引用上下文（`\cite{}`）
- 图片内容无法理解（`\includegraphics{}`）
- 编译失败时缺少自动修复

**解决方案**：
- 引入 LangChain Agent 框架
- 实现 CiteTool、ImageTool、CompilerTool

---

### 3.1 智能体架构重构

#### [ ] 步骤 1：安装 LangChain
```bash
pip install langchain langchain-google-genai
```

#### [ ] 步骤 2：将线性代码重构为 LangChain Chain
**原逻辑**（线性）：
```python
text = parser.extract_text()
translated = llm.translate(text)
result = reconstructor.build(translated)
```

**新逻辑**（LangChain）：
```python
from langchain.chains import SequentialChain

chain = SequentialChain([
    ParserChain(),
    RAGChain(),
    TranslateChain(),
    ValidateChain(),
    CompileChain()
])

result = chain.run(input_file)
```

#### [ ] 步骤 3：定义工具（Tools）
**文件**：`backend/services/agents/tools.py`

**工具清单**：
1. **TranslateTool**：封装 Phase 2 的 RAG 翻译逻辑
2. **CiteTool**：输入 `\cite{xxx}`，调用 ArXiv API 获取摘要
3. **ImageTool**：输入图片路径，调用 Gemini-Vision 生成描述

**代码示例（CiteTool）**：
```python
from langchain.tools import Tool
import arxiv

def cite_tool(cite_key: str) -> str:
    """查询 arXiv 引用的摘要"""
    search = arxiv.Search(id_list=[cite_key])
    result = next(search.results())
    return result.summary

cite_tool = Tool(
    name="CiteTool",
    func=cite_tool,
    description="Get abstract of cited paper from arXiv"
)
```

**ImageTool（Gemini-Vision）**：
```python
from langchain_google_genai import ChatGoogleGenerativeAI

def image_tool(image_path: str) -> str:
    """识别图片内容"""
    llm = ChatGoogleGenerativeAI(model="gemini-pro-vision")
    response = llm.invoke([{"type": "image", "path": image_path}])
    return response.content

image_tool = Tool(
    name="ImageTool",
    func=image_tool,
    description="Describe image content using Gemini-Vision"
)
```

---



### 阶段里程碑（Phase 3）

**测试场景**：
故意上传一个有人为语法错误的 LaTeX 文件（如缺少 `\usepackage{amsmath}`），系统能自动修复并生成 PDF。

**验收标准**：
- ✅ LangChain Agent 正常运行
- ✅ CiteTool 能正确获取引用摘要
- ✅ ImageTool 能识别图片内容
- ✅ Compiler Agent 能自动修复 80% 的常见错误

---

## 第四阶段：交互体验与工程化（Web & Ops）

**目标**：达到任务书中"交互式"、"可视化"的要求。

---

### 4.1 高级前端交互

#### [ ] 步骤 1：实现双栏对照预览
**组件**：`frontend/src/components/DualPaneViewer.jsx`

**功能**：
- 左侧：LaTeX 源码（CodeMirror 编辑器 + 语法高亮）
- 右侧：PDF 预览（pdf.js）

**技术选型**：
```bash
npm install @uiw/react-codemirror pdfjs-dist
```

#### [ ] 步骤 2：使用 WebSocket 实时推送 Log
**后端**：
```python
from fastapi import WebSocket

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    while True:
        log_message = await get_task_log(task_id)
        await websocket.send_text(log_message)
        await asyncio.sleep(1)
```

**前端**：
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${taskId}`);
ws.onmessage = (event) => {
    console.log("Log:", event.data);
};
```

---

### 4.2 任务队列与并发

#### [ ] 步骤 1：安装 Redis + Celery
```bash
pip install redis celery
```

#### [ ] 步骤 2：将翻译任务放入队列
**文件**：`backend/celery_app.py`

```python
from celery import Celery

app = Celery('latextrans', broker='redis://localhost:6379')

@app.task
def translate_task(task_id):
    run_translation(task_id)
```

**触发任务**：
```python
from celery_app import translate_task

@router.post("/translate/{task_id}")
async def start_translation(task_id: str):
    translate_task.delay(task_id)
    return {"message": "Task queued"}
```

#### [ ] 步骤 3：基于 Session ID 隔离用户文件和知识库
**策略**：
- 每个用户创建独立的向量库集合
- 文件存储路径：`data/uploads/{user_id}/{task_id}/`

---

### 阶段里程碑（Phase 4）

**测试场景**：
- 双栏预览能同步滚动
- WebSocket 日志实时更新
- 多个用户同时翻译互不干扰

---

## 第五阶段：测试、论文与答辩准备

**目标**：产出学术成果。

---

### 5.1 评估与测试

#### [ ] 步骤 1：准备测试集
**数据来源**：
- 从 arXiv 下载 10-20 篇论文（覆盖多个领域）
- 手动标注"黄金翻译"（Gold Reference）

**文件**：`evaluation/test_papers.txt`
```
2508.18791  # cs.AI
2412.13736  # cs.CV
...
```

#### [ ] 步骤 2：计算 BLEU/ROUGE
**文件**：`evaluation/scripts/compute_metrics.py`

```python
from nltk.translate.bleu_score import sentence_bleu

def evaluate(reference, hypothesis):
    bleu = sentence_bleu([reference.split()], hypothesis.split())
    return {"BLEU": bleu}
```

#### [ ] 步骤 3：统计编译成功率
**指标**：
- 编译成功率 = 成功编译的论文数 / 总论文数
- 平均重试次数

#### [ ] 步骤 4：术语一致性评估
**方法**：
- 从翻译结果中提取术语对
- 对比术语表，计算准确率

#### [ ] 步骤 5：消融实验
**对比组**：
- Baseline：关闭 RAG 和 Agent
- RAG Only：仅启用 RAG
- Full System：RAG + Agent

---

### 5.2 论文撰写

#### [ ] 步骤 1：第三章：系统设计（架构图）
**内容**：
- 系统总体架构图（Frontend + Backend + Agent + RAG）
- 数据流图（上传 → 解析 → 翻译 → 编译）
- ER 图（任务、文件、术语表）

**工具**：draw.io, PlantUML

#### [ ] 步骤 2：第四章：关键技术（RAG、Agent）
**内容**：
- RAG 检索流程（混合检索 + 重排序）
- Agent 工具设计（CiteTool, ImageTool, CompilerTool）
- 编译自愈算法

#### [ ] 步骤 3：第五章：实验分析
**内容**：
- 测试集描述
- BLEU/ROUGE 得分对比表
- 编译成功率对比图
- 术语一致性热力图
- 消融实验结果

**示例表格**：
| 方法 | BLEU | 编译成功率 | 术语一致性 |
|------|------|-----------|----------|
| Baseline | 0.45 | 75% | 60% |
| RAG Only | 0.58 | 75% | 85% |
| Full System | 0.62 | 92% | 90% |

---

### 阶段里程碑（Phase 5）

**验收标准**：
- ✅ 论文草稿完成（包含所有章节）
- ✅ 实验数据完整（至少 10 篇测试论文）
- ✅ 演示 PPT 制作完成

---

## 风险管理（Plan B）

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|---------|
| **AST 解析崩溃**（pylatexenc 对复杂宏支持不好） | 中 | 高 | 设置"降级模式"：AST 失败 → 回退到纯文本行切分 |
| **编译自愈失败**（总是修不好） | 高 | 中 | Web 端提供"手动修复"框，Agent 修不好时抛给用户 |
| **RAG 检索慢**（向量搜索耗时） | 中 | 中 | 仅对"摘要"和"引言"做深层 RAG，正文仅关键词匹配 |
| **MiKTeX Docker 兼容性**（Windows 兼容问题） | 低 | 高 | Fallback to TeX Live；文档清晰安装步骤 |
| **时间不足**（1-2周无法完成所有功能） | 高 | 高 | 优先完成 Phase 1 + Phase 5（Web 平台 + 论文数据） |

---

## 附录：关键文件路径速查

### 原型系统（复用源）
- `prototype_system/main.py` - CLI 入口
- `prototype_system/src/agents/coordinator_agent.py` - 协调器
- `prototype_system/src/agents/tool_agents/*.py` - 子 Agent
- `prototype_system/src/formats/latex/*.py` - LaTeX 处理
- `prototype_system/config/default.toml` - 配置文件
- `prototype_system/terms/*.csv` - 术语表

### 新系统（需创建）
- `backend/app/main.py` - FastAPI 入口
- `backend/app/services/rag/retriever.py` - RAG 检索器
- `backend/app/services/agents/tools.py` - LangChain Tools
- `frontend/src/App.jsx` - React 主应用
- `docker/Dockerfile.miktex` - LaTeX 编译环境
- `evaluation/scripts/compute_metrics.py` - 评估脚本

---

**本计划由 Claude Code 生成 - 2026-01-01**
**基于原型系统：NiuTrans/LaTeXTrans**
