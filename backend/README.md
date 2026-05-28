# PaperX Backend

基于 FastAPI (Python) 构建的 PaperX 后端 REST API 服务，负责 LaTeX 论文解析、翻译编排、LLM 调用、术语管理、社区服务与用户认证。

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | FastAPI, Uvicorn |
| Agent 编排 | LangChain, LangGraph |
| LaTeX 解析 | pylatexenc (AST), MiKTeX (Docker) |
| 数据库 | MySQL (主库), Redis (缓存/热榜/队列) |
| 向量检索 | Milvus + BM25 + Cross-Encoder |
| LLM | Gemini (主力) / GPT (备用), 多 Key Token Pool |
| 对象存储 | 本地磁盘 / 腾讯云 COS 双模式 |
| 认证 | 本地 JWT + NiuTrans OAuth |
| 测试 | pytest |

## 环境配置

```bash
cp .env.example .env
# 编辑 .env 配置以下必填项：
```

### 必填环境变量

```bash
# 数据库
DATABASE_URL=mysql://root:password@host.docker.internal:3306/latextrans

# JWT 认证
AUTH_PROVIDER_MODE=niutrans_local
AUTH_JWT_KEYS=v1:your-secret-key
AUTH_JWT_ISSUER=paperx
AUTH_JWT_AUDIENCE=paperx-api
AUTH_ACCESS_TOKEN_TTL_SECONDS=28800

# LLM
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-llm-endpoint/v1/chat/completions
LLM_MODEL=gpt-4.1-mini

# 加密
ENCRYPTION_KEY=your-32-byte-encryption-key
```

## 项目结构

```
backend/
├── app/
│   ├── main.py                      # FastAPI 入口，启动/关闭事件
│   ├── api/routes/                  # API 路由层
│   │   ├── arxiv.py                 # arXiv 下载与校验
│   │   ├── auth.py                  # 登录/注册/会话/登出
│   │   ├── community_agent.py       # 社区智能体运行与会话
│   │   ├── download.py              # PDF/源码/日志/术语表下载与预览
│   │   ├── history.py               # 翻译历史查询与删除
│   │   ├── papers.py                # 社区论文 CRUD、策展、互动、收藏
│   │   ├── pdf_direct.py            # NiuTrans PDF 直译
│   │   ├── settings.py              # 用户设置读写
│   │   ├── task.py                  # 任务状态、SSE 流、运行时取消
│   │   ├── terminology.py           # RAG 术语管理（CRUD/审核/匹配/领域）
│   │   ├── translate.py             # 翻译启动、批量、配置哈希
│   │   └── upload.py                # 文件上传、批量翻译
│   ├── core/                        # 核心基础设施
│   │   ├── auth.py                  # JWT 解析、当前用户、管理员校验
│   │   ├── config.py                # 全局配置（Settings、TaskStatus、LLM）
│   │   ├── encryption.py            # API Key AES 加密
│   │   └── timezone_utils.py        # UTC+8 时区工具
│   ├── db/
│   │   └── connection.py            # MySQL 连接与方言适配
│   ├── models/
│   │   └── config_models.py         # SourceType, AdvancedConfig, FormattingConfig
│   ├── policies/                    # 权限策略
│   │   ├── base.py                  # AuthorizationResult, BasePolicy
│   │   ├── admin_policy.py          # 管理员
│   │   ├── community_agent_policy.py # 社区智能体
│   │   ├── paper_policy.py          # 论文
│   │   ├── settings_policy.py       # 设置
│   │   └── task_policy.py           # 任务
│   ├── repositories/                # 持久化仓储层
│   │   ├── auth_repository.py       # 用户认证读写
│   │   ├── community_agent_repository.py # 对话与运行记录
│   │   ├── community_paper_repository.py # 论文、资产、互动、策展、推荐、元数据
│   │   ├── terminology_repository.py # 术语 CRUD、BM25、审核
│   │   ├── translation_quota_repository.py # 每日额度与积分快照
│   │   ├── translation_task_repository.py  # 翻译任务状态与历史
│   │   └── user_settings_repository.py     # 用户设置
│   ├── services/                    # 业务服务层（核心实现）
│   │   ├── agents/                  # 翻译 Agent 管线
│   │   │   ├── base_tool_agent.py   # Agent 基类
│   │   │   ├── compile_runtime.py   # 编译信号量
│   │   │   ├── coordinator_agent.py # 流水线协调器
│   │   │   ├── generator_agent.py   # LaTeX 重建与编译
│   │   │   ├── langgraph_orchestrator.py # LangGraph 编排层（审计/进度/日志）
│   │   │   ├── llm_runtime.py       # LLM 配置解析
│   │   │   ├── llm_token_pool.py    # 多 Key Token Pool
│   │   │   ├── parser_agent.py      # LaTeX 解析代理
│   │   │   ├── pipeline_invariants.py # 流水线安全约束
│   │   │   ├── translator_agent.py  # 核心翻译代理（分块/重试/降级）
│   │   │   └── validator_agent.py   # 翻译质量校验
│   │   ├── community_agent/         # 社区智能体
│   │   │   ├── orchestrator.py      # ReAct 编排（规划/搜索/技能/回答）
│   │   │   ├── runtime.py           # 运行时上下文/事件循环
│   │   │   ├── formatter.py         # 输出格式化
│   │   │   ├── language.py          # 语言检测与标准化
│   │   │   ├── models.py            # 数据模型
│   │   │   ├── skills_runtime.py    # 技能运行时
│   │   │   ├── validator.py         # 查询校验
│   │   │   ├── skills/              # 技能定义（社区搜索、回答、Tavily、导入、阅读、翻译）
│   │   │   └── tools/               # 工具实现（同上 6 个工具）
│   │   ├── latex/                   # LaTeX 处理
│   │   │   ├── compiler.py          # Docker/Host LaTeX 编译器（智能切换/健康分支）
│   │   │   ├── parser.py            # AST 解析器（章节/环境/占位符切分）
│   │   │   ├── prompts.py           # LLM 提示词管理
│   │   │   ├── reconstruct.py       # 译文 LaTeX 重建
│   │   │   ├── sanitizer.py         # 预编译清洗（修复危险命令/PDF 修复）
│   │   │   ├── token_estimator.py   # Token 估算（tiktoken + 回退）
│   │   │   └── utils.py             # arXiv 下载、解压、路径等工具
│   │   ├── rag/                     # RAG 检索增强
│   │   │   ├── bm25_retriever.py    # BM25 检索器
│   │   │   ├── vector_retriever.py  # Milvus 向量检索器
│   │   │   ├── embedding_client.py  # Embedding 客户端
│   │   │   ├── cross_encoder_reranker.py # Cross-Encoder 重排
│   │   │   ├── glossary_formatter.py # 术语表格式化
│   │   │   ├── pipeline.py          # 多阶段检索流水线
│   │   │   ├── domain_constants.py  # 领域常量（~50 个领域）
│   │   │   ├── translation_hook.py  # 翻译集成钩子
│   │   │   └── knowledge_base/      # 知识库摄入（CSV/BibTeX/自动抽取）
│   │   ├── auth_service.py          # 本地认证 + NiuTrans 积分同步
│   │   ├── community_agent_service.py # 智能体运行管理
│   │   ├── community_content_pool_service.py # 内容池服务
│   │   ├── community_translation_quality.py  # 社区翻译质量门禁
│   │   ├── config_capture.py        # 配置快照
│   │   ├── email_service.py         # 邮件通知
│   │   ├── hot_ranking_service.py   # 热榜排序
│   │   ├── latex_validator.py       # LaTeX 目录校验
│   │   ├── paper_preview_service.py # 论文预览构建（HTML/摘要/占位符替换）
│   │   ├── paper_service.py         # 论文主服务（导入/翻译/预览/下载/策展/发布）
│   │   ├── paper_thumbnail_service.py # PDF 缩略图生成（本地+COS）
│   │   ├── runtime_pressure.py      # 运行时压力协调（web/worker 角色）
│   │   ├── storage_backend.py       # 对象存储抽象层（本地/COS）
│   │   ├── task_artifact_storage.py # 任务产物持久化
│   │   ├── task_detail.py           # 任务详情标准化
│   │   ├── task_manager.py          # 任务管理核心（队列/调度/清理）
│   │   └── task_runtime_client.py   # Worker 运行时取消通道
│   └── utils/
│       └── async_blocking.py        # 阻塞调用异步包装
├── migrations/                      # Supabase PostgreSQL 迁移
├── migrations_mysql/                # MySQL 迁移脚本（0001~0015，含异步取消/额度/热榜）
├── scripts/                         # 运维脚本
│   ├── apply_mysql_migrations.py    # MySQL 迁移执行
│   ├── grant_local_admin.py         # 管理员授权
│   ├── bootstrap_local_community_papers.py # 本地论文导入
│   ├── sync_core_pool_complete_from_cos.py # COS 资产同步
│   ├── migrate_production_assets_to_cos.py # 资产迁移
│   └── ...                          # 更多运维/审计脚本
├── evaluation/                      # 评估套件（BLEU/ROUGE/术语一致性）
├── arxiv_id/core_pool/              # arXiv ID 核心池状态文件
├── requirements.txt                 # Python 依赖
├── start.sh / start.bat / start.ps1 # 启动脚本
└── .env.example                     # 环境变量示例
```

## API 端点总览

所有端点前缀：`/api`

### 认证与用户 (auth.py)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/login` | 用户登录（NiuTrans OAuth） |
| GET | `/auth/me` | 当前用户信息 |
| GET | `/auth/quota` | 用户额度快照 |
| POST | `/auth/logout` | 登出 |

### 翻译工作流 (arxiv.py, upload.py, translate.py, task.py, download.py)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/arxiv` | 下载 arXiv 论文源码 |
| GET | `/arxiv/validate/{arxiv_id}` | 校验 arXiv ID |
| POST | `/upload` | 上传 LaTeX 文件 |
| POST | `/upload/batch-translate` | 批量上传并翻译 |
| POST | `/translate/{task_id}` | 启动翻译任务 |
| POST | `/batch-translate` | 批量 arXiv 翻译 |
| GET | `/queue/status` | 队列状态 |
| GET | `/task/{task_id}` | 查询任务状态 |
| GET | `/task/{task_id}/stream` | SSE 流式状态推送 |
| GET | `/tasks` | 列出全部任务 |
| DELETE | `/task/{task_id}` | 删除任务 |
| GET | `/download/{task_id}/pdf` | 下载译文 PDF |
| GET | `/download/{task_id}/source` | 下载译文源码 |
| GET | `/download/{task_id}/logs` | 下载编译日志 |
| GET | `/download/{task_id}/terminology` | 下载术语表 CSV |
| GET | `/preview/{task_id}/pdf` | 预览译文 PDF |
| GET | `/preview/{task_id}/source-pdf` | 预览原文 PDF |

### 翻译历史与设置 (history.py, settings.py)
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/history` | 翻译历史列表（分页） |
| GET | `/history/{task_id}` | 任务详情 |
| DELETE | `/history/{task_id}` | 删除单条历史 |
| DELETE | `/history` | 批量删除历史 |
| GET | `/settings` | 获取用户设置 |
| PUT | `/settings` | 更新用户设置 |

### 社区论文 (papers.py)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/papers/submit` | 提交论文 |
| POST | `/papers/import` | 导入论文 |
| GET | `/papers` | 论文列表（排序/筛选/分页） |
| GET | `/papers/{paper_id}` | 论文详情 |
| GET | `/papers/{paper_id}/preview` | 论文预览 |
| POST | `/papers/{paper_id}/translate` | 翻译论文 |
| GET | `/papers/{paper_id}/translated-pdf` | 译文 PDF |
| GET | `/papers/{paper_id}/translated-thumbnail` | 译文缩略图 |
| GET | `/papers/{paper_id}/source-pdf` | 原文 PDF 预览 |
| GET | `/papers/{paper_id}/source-download` | 原文 PDF 下载 |
| GET | `/papers/{paper_id}/source-thumbnail` | 原文缩略图 |
| POST | `/papers/{paper_id}/view` | 记录浏览 |
| POST | `/papers/{paper_id}/download-session` | 下载会话 |
| GET | `/papers/{paper_id}/download` | 下载 |
| GET/POST/PATCH/DELETE | `/papers/favorites*` | 收藏夹管理 |
| POST/DELETE | `/papers/{paper_id}/like` | 点赞/取消 |
| GET | `/papers/content-pool/readiness` | 内容池就绪度 |
| GET | `/papers/content-pool/jobs` | 内容池任务 |
| GET/POST/PATCH/DELETE | `/papers/admin/curation/*` | 管理员策展管理 |
| GET/DELETE | `/papers/admin/curation/history/*` | 管理员策展历史 |

### 社区智能体 (community_agent.py)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/agent/runs` | 创建智能体运行 |
| GET | `/agent/runs/{run_id}` | 查询运行状态 |
| GET | `/agent/runs/{run_id}/events` | 运行事件流 |
| GET | `/agent/conversations` | 对话列表 |
| PUT | `/agent/conversations/{id}` | 更新/创建对话 |
| DELETE | `/agent/conversations/{id}` | 删除对话 |

### RAG 术语管理 (terminology.py)
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/terminology/domains` | 领域列表 |
| POST | `/terminology/terms` | 创建术语 |
| PUT | `/terminology/terms/{id}` | 更新术语 |
| DELETE | `/terminology/terms/{id}` | 删除术语 |
| POST | `/terminology/terms/{id}/share` | 分享术语 |
| POST | `/terminology/terms/batch` | 批量操作 |
| GET | `/terminology/my-terms` | 我的术语 |
| GET | `/terminology/terms` | 术语搜索 |
| GET | `/terminology/pending` | 待审核术语 |
| POST | `/terminology/upload` | CSV/BibTeX 上传 |
| POST | `/terminology/{id}/approve` | 批准术语 |
| POST | `/terminology/{id}/reject` | 拒绝术语 |
| GET | `/terminology/tasks/{id}/matches` | 翻译匹配日志 |
| POST | `/terminology/glossary/lookup` | 术语查询 |
| POST | `/terminology/index/refresh-bm25` | 重建 BM25 索引 |
| POST | `/terminology/index/build-vector` | 构建向量索引 |

### PDF 直译 (pdf_direct.py)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/pdf-direct/upload` | 上传 PDF |
| POST | `/pdf-direct/{task_id}/start` | 启动直译 |
| GET | `/pdf-direct/{task_id}` | 查询状态 |
| POST | `/pdf-direct/{task_id}/poll` | 轮询状态 |
| POST | `/pdf-direct/{task_id}/cancel` | 取消任务 |
| GET | `/pdf-direct/{task_id}/download` | 下载结果 |
| GET | `/pdf-direct` | 任务列表 |

## 翻译流水线

```
parse ──→ translate ──→ validate_and_retry ──→ generate ──→ finalize
  │            │               │                    │             │
AST 解析    分段翻译      质量校验+重试         LaTeX 重建    PDF 编译
  │            │          (最多 3 轮)              │          (pdflatex→xelatex)
  └── parity 内核 (origin CLI 等价) ────────────────┘
```

## 运行模式

后端支持双进程模式：

- **web** (`--runtime-role web`)：处理 HTTP 请求，记录前台压力
- **worker** (`--runtime-role worker`)：执行翻译任务，周期修复（arXiv 元数据/热榜 Redis）

```bash
# 启动 web
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动 worker（另开一个终端）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
# Worker 角色通过环境变量 RUNTIME_ROLE=worker 设置
```

## 测试

```bash
# 运行全部测试
pytest backend/tests/

# 按模块测试
pytest backend/tests/unit/test_pdf_direct_service.py
pytest backend/tests/unit/test_terminology_repository.py
pytest backend/tests/unit/test_rag_integration.py
```
