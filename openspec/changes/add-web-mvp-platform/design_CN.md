# 设计文档：基于Web的MVP平台

## 上下文

### 背景
LaTeXTrans 项目目前作为 CLI 原型 (`prototype_system/`) 存在，它演示了使用多代理架构的核心 LaTeX 翻译功能。然而，它：
- 需要Python环境设置和命令行熟练程度
- 翻译过程中缺乏实时反馈（某些模块依赖 Streamlit）
- 没有可访问网络的界面以实现更广泛的可用性

### 约束
- **AST解析**：必须继续使用`pylatexenc`用于 LaTeX 结构处理（无正则表达式）
- **Python环境**：后端需要Python 3.10+以及必要的依赖项
- **Docker 隔离**：LaTeX 编译必须在 Docker 中与 MiKTeX 一起进行
- **向后兼容性**：现有的 CLI 原型必须保持功能
- **时间表**：两周 MVP 交付窗口

### 利益相关者
- 最终用户：需要 LaTeX 翻译的研究人员和学生
- 开发团队：构建完整的 RAG + 多代理系统（第 2-5 阶段）
- 论文委员会：需要具有评估指标的可论证的网络平台

## 目标/非目标

### 目标
1. **端到端Web工作流程**：上传→翻译→通过浏览器下载
2. **实时进度反馈**：用户看到翻译阶段和完成百分比
3. **arXiv 集成**：支持从 arXiv 论文 ID 直接翻译
4. **代码可重用性**：改编（而不是重写）经过验证的原型逻辑
5. **未来的基础**：建立 RAG/Agent 增强架构（第 2-3 阶段）

### 非目标
1. ❌ 用户认证或多租户（单用户本地部署）
2.❌基于RAG的术语检索（推迟到第2阶段）
3.❌浪链代理编排（推迟到第三阶段）
4. ❌高级 UI 功能：双窗格预览、语法突出显示（推迟到第 4 阶段）
5. ❌ 生产部署基础设施（MVP是本地优先）
6. ❌ 数据库持久化（针对 MVP 使用内存中任务跟踪）

## 决定

### 决策 1：FastAPI 优于 Flask/Django
**选择**：FastAPI  
**理由**：
- 对后台任务处理的本机异步/等待支持
- 自动 OpenAPI 文档（对于测试和未来集成很有价值）
- 类型提示提高了代码的可维护性
- 更好的 I/O 密集型操作性能（文件上传、arXiv 下载）
- 现代Python生态系统调整（Python 3.10+）

**考虑的替代方案**：
- Flask：更简单，但缺乏原生异步；需要 OpenAPI 扩展
- Django：对于 MVP 范围来说太过分了；我们不需要更重的 ORM 框架

### 决策 2：React + Vite 而不是普通 HTML 或 Next.js
**选择**：使用 Vite 工具进行 React  
**理由**：
- React 组件模型符合 UI 要求（作为独立组件上传、进度、下载）
- Vite提供快速热重载以实现快速开发
- TailwindCSS 与 Vite 的集成非常简单
- 团队的学习曲线比 Next.js 更小
- 本地 MVP 无需 SSR

**考虑的替代方案**：
- Vanilla HTML/JS：更难管理轮询和进度更新的状态
- Next.js：对于纯客户端应用来说太过分了；本地部署不需要SSR

### 决策 3：数据库中的内存中任务状态
**选择**：基于Python字典的TaskManager  
**理由**：
- MVP 假设单用户、短会话
- 消除了设置复杂性（MVP 不依赖 PostgreSQL/Redis）
- 更快的开发迭代
- 当并发成为优先事项时，在第 4 阶段轻松迁移到 Redis/DB

**权衡**：服务器重新启动时任务状态丢失（MVP 可接受）

### 决策 4：S3/云上基于文件的存储
**选择**：本地文件系统（`data/uploads/`、`data/outputs/`）  
**理由**：
- 没有云依赖或成本
- 更简单的错误处理和调试
- 满足本地部署要求
- 稍后轻松迁移到对象存储

**权衡**：无分布式访问（单机 MVP 可接受）

### 决策 5：调整原型代码，不要重写
**选择**：复制并修改现有的`coordinator_agent.py`, `parser.py`, `utils.py`**理由**：
- 经过验证的逻辑降低了引入 LaTeX 解析错误的风险
- 删除 Streamlit 后，70% 的代码可以重用
- 比从头开始重建更快
- 保持 AST 解析合规性（`pylatexenc`用法）

**方法**：
- 删除：`st.progress()`, `st.text()`, `st.spinner()`来电
- 添加：TaskManager 消耗的进度回调（`on_progress(stage,%)`）
- 保留：所有 AST 逻辑、编译器逻辑、代理编排

### 决策 6：通过 WebSocket 轮询进度
**选择**：前端民意调查`GET /task/{task_id}`每 2 秒  
**理由**：
- 更简单的实现（无需设置 WebSocket 服务器）
- 2-10 分钟翻译的足够用户体验（WebSocket 过度杀伤力）
- 使用标准 HTTP 请求更轻松地进行调试
- WebSocket 升级推迟到第 4 阶段（实时日志）

**权衡**：延迟稍高（约 2 秒 vs 即时），对于 MVP 来说可以接受

### 决策 7：单一回购结构
**选择**：单个存储库`backend/`, `frontend/`, `prototype_system/`目录  
**理由**：
- 原型适应期间更容易交叉引用
- 简化论文交付的依赖关系管理
- 与 OpenSpec 工作流程保持一致（单个项目.md）

**文件结构**：
````
LaTeXTrans/
├── backend/ # FastAPI + 适配原型逻辑
├── 前端/ # React + Vite
├──prototype_system/ # 原始CLI（保留作为参考）
├── data/ # 运行时存储（gitignored）
├── openspec/ # 这个提案和未来的规范
└── docker/ # 未来：MiKTeX 容器
````

## 架构概述

### 请求流程
````
用户浏览器
    ↓（上传 .zip 或 arXiv ID）
反应前端（本地主机：5173）
    ↓（POST /上传或/arxiv→task_id）
    ↓ (POST /translate/{task_id})
FastAPI 后端（本地主机：8000）
    ↓（后台任务）
CoordinatorAgent（改编自原型）
    ├─ ParserAgent → AST 提取（pylatexenc）
    ├─ TranslatorAgent → LLM翻译（双子座）
    └─ GeneratorAgent → xelatex 编译（未来：Docker）
    ↓（写入数据/输出/）
TaskManager（更新{task_id：{status，progress}}）
    ↑ （前端通过 GET /task/{task_id} 轮询）
反应前端
    ↓（通过 GET /download/{task_id}/pdf 下载）
用户浏览器（接收翻译后的 PDF）
````

### 关键组件

**后端服务**：
- `TaskManager`：任务状态/进度的内存状态存储
- `LaTeXParser`：改编自 `prototype_system/src/formats/latex/parser.py`
- `ArxivUtils`：改编自`prototype_system/src/formats/latex/utils.py`
- `CoordinatorAgent`：改编自`prototype_system/src/agents/coordinator_agent.py`

**API 路线**：
-`POST /upload`→ 接收文件，返回task_id
-`POST /arxiv`→ 接收arXiv ID，下载源码，返回task_id
-`POST /translate/{task_id}`→ 触发后台翻译
-`GET /task/{task_id}`→ 返回{状态、进度、消息}
-`GET /download/{task_id}/pdf`→ 流 PDF 文件
-`GET /download/{task_id}/source`→ Streams 压缩源

**前端组件**：
- `FileUpload.jsx`：拖放+文件选择
- `ArxivInput.jsx`：带有验证的 arXiv ID 输入
- `ProgressTracker.jsx`：轮询+进度条+状态显示
- `DownloadButton.jsx`：完成时的条件渲染
- `App.jsx`：带有选项卡切换器的布局编排

## 数据模型

### 任务对象（内存中）
````蟒蛇
{
    "task_id": "uuid-字符串",
    “状态”：“待处理”| 「处理」| “已完成” | “已完成并带有警告”| “编译失败”| “失败”，
    "progress": 0-100, # 百分比
    "stage": "解析" | 「翻译」| “编译” | “完成”| “编译失败”，
    "message": "当前操作说明",
    “错误”：空 | “错误消息”，
    “警告”：空| “编译警告摘要”，
    “source_available”：true | false, # LaTeX源可以下载
    "created_at": "ISO 时间戳",
    “completed_at”：空 | “ISO时间戳”，
    "source_type": "上传" | “arxiv”，
    "source_path": "数据/上传/{task_id}/",
    “output_path”：“数据/输出/ch_{project_name}/”
}
````

### LLM API 配置
后端应使用以下 LLM API 配置（改编自原型的“config/default.toml”）：

````蟒蛇
LLM_配置 = {
    "api_key": "sk-SVd4dIKfuIwhQ9kUlgCr9ZMpoIWp7PEzZxpVStjSRqeqNBLu",
    "base_url": "https://aicanapi.com/v1/chat/completions",
    "model": "gpt-4.1-mini", # 或按照配置中指定
    "timeout": 60 # 每个请求秒
}
````

**注意**：API 密钥应从环境变量加载`LLM_API_KEY`或配置文件，未硬编码在源代码中。

### 文件存储布局
````
数据/
├── 上传/
│ └── {task_id}/
│ ├── 原始.zip（如果已上传）
│ └── 摘录/
│ └── main.tex
├── 输出/
│ └── ch_{项目名称}/
│ ├── 翻译.tex
│ ├── 译.pdf
│ └── ...（支持文件）
└── 条款/
    └── *.csv（术语词汇表，MVP 中未使用）
````

## 风险/权衡

### 风险 1：翻译超时
**问题**：长论文（>50 页）可能需要 >10 分钟  
**缓解措施**：
- 使用FastAPI`BackgroundTasks`以避免 HTTP 超时
- 前端显示取消按钮（未来：POST /task/{task_id}/cancel）
- 在 LLM 调用中设置合理的超时（每个块 60 秒）

### 风险 2：Latex 编译失败
**问题**：MiKTeX Docker 尚未在 MVP 中实现  
**缓解措施**：
- 第 1 阶段：在主机系统上运行 xelatex（需要本地 MiKTeX 安装）
- 将 Docker 设置记录为 MVP 后的增强
- 在任务错误字段中包含编译错误日志

### 风险 3：并发用户请求
**问题**：内存中的 TaskManager 不是线程安全的  
**缓解措施**：
- 使用Python`threading.Lock()`用于任务字典更新
- 在自述文件中记录单用户限制
- 规划第 4 阶段的 Redis 迁移

### 风险 4：大文件上传
**问题**：100MB+`.zip`文件可能会耗尽内存  
**缓解措施**：
- FastAPI 流式上传（`UploadFile`）
- 设置最大上传大小限制（MVP 为 50MB）
- 处理前验证文件大小

### 风险 5：Streamlit 依赖删除
**问题**：删除 UI 调用时原型代码可能会失败  
**缓解措施**：
- 改编前进行彻底的代码审核（任务 1.x）
- 用 Python 替换日志记录调用`logging`模块
- 添加核心功能的单元测试（解析器、翻译器）

## 迁移计划

### 阶段 0 → 阶段 1（此更改）
1. 新建`backend/`和`frontend/`目录（非破坏性）
2. 将原型代码复制到`backend/app/services/`
3. 调整复制的代码（原始原型保持不变）
4. 构建Web UI和API层
5. 运行并行测试：CLI 与 Web 工作流程

### 回滚策略
- 删除`backend/`和`frontend/`目录
- 原型系统保持完整功能
- 不迁移现有用户（尚不存在）

### 合并前测试
- [ ] CLI 工作流程不受影响：`python prototype_system/main.py --arxiv 2508.18791`成功
- [ ] Web工作流程功能：上传→翻译→下载成功
- [ ] 比较输出：通过 CLI 和 Web 翻译的相同 arXiv 论文生成相同的 PDF

## 开放问题

1. **问**：我们是否应该支持批量上传（一次多篇论文）？  
   **A**：没有 MVP。每个请求单个任务。批量功能推迟到第 4 阶段。

2. **问**：我们是否需要用户会话或者可以通过 ID 全局访问任务吗？  
   **A**：全局任务 ID (UUID) 对于单用户 MVP 来说已经足够了。会话隔离被推迟。

3. **问**：前端构建应该由 FastAPI 提供服务还是单独运行？  
   **A**：在开发中单独运行（Vite 开发服务器）。生产版本稍后由 FastAPI 提供服务。

4. **问**：编译时缺少LaTeX包如何处理？  
   **A**：对于 MVP，假设主机上启用了 MiKTeX 自动安装。 Docker 在第 3 阶段将其隔离。

5. **问**：我们是否应该记录所有 API 请求以进行调试？  
   **答**：是的。使用 FastAPI 中间件记录请求/响应。存储在`backend/logs/`中。