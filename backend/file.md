# Backend File Index

## Recent Responsibility Updates (2026-05-28 hot ranking curation metadata)

- `backend/migrations_mysql/20260528_0014_add_hot_ranking_curation_metadata.sql`: MySQL 迁移脚本，为 `community_curation_jobs` 增补 `source_family`、`hot_score`、`score_breakdown` 与热榜查询索引，用于保留自动入库来源和分数明细。
- `backend/app/services/hot_ranking_service.py`: 热榜自动入库改为复用现有管理员 arXiv 策展批量入口，并在 curation job 上附加热榜来源、分数和分项明细，避免预建 paper 造成失败占位与重复跳过。
- `backend/app/services/paper_service.py`: 管理员策展占位论文创建时继承 job 上的 `hot_score`，保证热榜自动入库发布后仍可参与首页 Hot 排序。
- `backend/app/repositories/community_paper_repository.py`: curation job 仓储支持读写热榜来源和分数明细字段。

## Recent Responsibility Updates (2026-05-14 RAG terminology: domain management + sharing + expanded seed data)

- `backend/app/services/rag/domain_constants.py`: 领域管理常量模块，包含 `TermDomain` 枚举（~50 个领域）、中英文标签、领域分组和标签查询函数。
- `backend/app/services/rag/seed_terminology.json`: 扩展种子数据至 ~780 条术语，新增 physics（30+）、mathematics（20+）、biology（30+）、medicine（20+）、engineering（20+）领域。
- `backend/app/models/config_models.py`: `AdvancedConfig` 新增 `rag_terminology_domain` 可选字段，用户可限制 RAG 术语注入的领域范围。
- `backend/app/services/agents/langgraph_orchestrator.py`: `node_translate()` 中 RAG 术语注入支持领域筛选参数。
- `backend/app/services/terminology_service.py`: `list_terms()` 新增 `source_type` 参数；`get_all_approved_terms_dict()` 新增 `domain` 可选筛选。
- `backend/app/api/routes/terminology.py`: 新增 `GET /api/terminology/domains` 领域列举端点；新增 `POST /terms/{id}/share` 用户术语分享端点；`GET /terms` 新增 `source_type` 查询参数。

## Recent Responsibility Updates (2026-05-14 RAG terminology test suite)

- `backend/tests/unit/test_terminology_repository.py`: 术语仓储测试，覆盖 CRUD、审核工作流（approve/reject）、多条件搜索、分页、用户隔离、批量导入、匹配日志和 embedding 状态转换。
- `backend/tests/unit/test_bm25_retriever.py`: BM25 检索器测试，覆盖索引构建、搜索排序、top_n 限制、空语料处理、自定义分词器和特殊字符。
- `backend/tests/unit/test_rag_clients.py`: RAG 客户端测试，覆盖 EmbeddingClient 编码、CrossEncoderReranker 回退排序、VectorRetriever 不可用时的安全降级和余弦相似度计算。
- `backend/tests/unit/test_pipeline.py`: RAG 流水线测试，覆盖候选去重合并、分数排序、LaTeX 查询变换、BM25/向量/仓储多源检索和组件故障降级。
- `backend/tests/unit/test_rag_integration.py`: 集成测试，覆盖 Glossary 格式化、Prompt 注入、BM25→Pipeline→Glossary 端到端链路、should_run_rag 特性门禁、TerminologyService 完整流程（get_rag_glossary 含回退、seed_official_terms 幂等、approve_term/reject_term、extract_and_store 提取流程）。

## Recent Responsibility Updates (2026-05-13 RAG terminology management)

- `backend/app/core/config.py`: 新增 RAG 术语管理配置项，包括 `RAG_TERMINOLOGY_ENABLED`、`RAG_TERMINOLOGY_MILVUS_URI`、`RAG_TERMINOLOGY_EMBEDDING_MODEL`、`RAG_TERMINOLOGY_RERANK_MODEL`、`RAG_TERMINOLOGY_BM25_REFRESH_INTERVAL` 等环境变量。
- `backend/app/models/config_models.py`: `AdvancedConfig` 新增 `enable_rag_terminology` 字段，用户可在翻译工具中显式开启 RAG 术语增强。
- `backend/app/repositories/terminology_repository.py`: 新增术语管理仓储，支持术语 CRUD、BM25 检索、审核工作流（approve/reject）、匹配日志记录和批量导入。
- `backend/app/services/rag/`: 新增 RAG 核心服务包，包含 BM25 检索器、Milvus 向量检索器、Embedding 客户端、Cross-Encoder 重排器、Glossary 格式化和多阶段流水线编排。
- `backend/app/services/rag/knowledge_base/`: 新增多源知识库摄入，支持 CSV 批量导入、BibTeX 引用解析和翻译后自动术语抽取。
- `backend/app/services/terminology_service.py`: 新增术语服务门面，协调仓储与 RAG 流水线，提供导入、检索、审核和匹配日志功能。
- `backend/app/api/routes/terminology.py`: 新增术语管理 API 路由，提供术语列表、CSV/BibTeX 上传、待审核列表、管理员审核和命中日志查询接口。
- `backend/app/services/rag/translation_hook.py`: 新增翻译流水线集成钩子，支持 RAG 术语条件判断、Glossary 注入和后置术语抽取。
- `backend/migrations_mysql/20260513_0012_rag_terminology.sql`: MySQL 迁移脚本，新增 `terminology_terms`、`terminology_evaluation_runs`、`terminology_match_log` 三张表。
- `backend/evaluation/`: 新增评估套件，包含 BLEU/ROUGE 评分、术语一致性度量和评估报告生成脚本。
- `backend/evaluation/default_key_terms.json`: 默认关键术语集，覆盖计算机科学和物理等领域。

## Recent Responsibility Updates (2026-05-09 COS PDF stable preview and fast download)

- `backend/app/api/routes/papers.py`: 社区论文 `translated-pdf` 与 `source-pdf` 预览在拿到对象存储签名 URL 时由后端代理交付并覆盖 `inline` 响应头，避免 COS 默认域名触发打开即下载；显式 PDF 下载仍保留签名 COS URL 重定向以维持下载速度。
- `backend/app/api/routes/download.py`: 普通任务 `/api/preview/{task_id}/pdf` 在 COS 模式下恢复为 2026-05-08 版本的后端代理交付，不主动转发浏览器 Range 请求；`/api/download/{task_id}/pdf` 与 arXiv raw-cache 附件下载继续重定向到签名 COS URL。

## Recent Responsibility Updates (2026-05-09 COS 回源缓存与直连交付)

- `backend/app/services/arxiv_raw_cache.py`: 新增 arXiv 原始资源 COS raw cache 帮助服务，集中生成 `pdf/<arxiv_id>` 与 `e-print/<arxiv_id>` 的对象 key 和签名 URL（PDF 下载文件名仍以 `.pdf` 呈现）；在 COS 模式且显式启用 raw cache 时，供 arXiv source/PDF 下载、社区 source_pdf 资产和 arXiv PDF 回退路径优先走 COS 回源。
- `backend/app/services/latex/utils.py`: arXiv 源码归档和原文 PDF 运行时下载现在会在 raw cache 启用时优先读取 COS 签名 URL，失败后仍保留原有 arXiv 端点回退。
- `backend/app/api/routes/download.py`: 普通任务 COS 输出的 PDF 预览现在返回签名 COS URL 重定向；arXiv PDF 回退代理会在 raw cache 可用时优先重定向到 COS，减少后端流式中转。
- `backend/app/api/routes/papers.py`: 社区论文 source/translated PDF 预览与下载在对象存储可用时返回签名 URL 重定向；缩略图路由改为复用缩略图服务的 COS 持久化交付结果。
- `backend/app/services/paper_thumbnail_service.py`: 缩略图生成服务新增 COS 持久化交付能力，生成 PNG 后写入确定性对象 key，并为浏览器返回签名 URL。
- `backend/app/services/paper_service.py`: arXiv 社区论文 `source_pdf` 在 raw cache 启用时可直接登记共享 raw-cache PDF 对象，避免发布/回填阶段强制由后端下载再上传原文 PDF。

## Recent Responsibility Updates (2026-05-09 parity kernel cleanup)

- `backend/app/models/config_models.py`: 当前翻译任务统一归一到 `origin_cli_parity` 单内核，仅保留旧 CLI 等价执行所需的配置、并发和谱系标记；已移除未参与生产路径的增强开关写入。
- `backend/app/services/agents/langgraph_orchestrator.py`: 生产图固定为 `parse -> translate -> validate_and_retry -> generate -> finalize`，审计只记录 parity 单内核谱系。
- `backend/app/services/agents/generator_agent.py`: 生成阶段只重建 parity LaTeX 并调用 `compile_with_origin_cli_parity`，保留编译队列计时和可丢弃健康分支。
- `backend/app/services/agents/translator_agent.py`: 翻译阶段保留旧 CLI 顺序、直接请求语义、重试预算、超大块源文回退和当前占位符 mask/restore；已剥离未接入 parity 生产路径的外层增强节点。
- `backend/app/services/latex/reconstruct.py`: 重建阶段保持 parity 字节语义，不再执行额外结构改写链路。
- `backend/app/services/latex/compiler.py`: 保留 `compile_with_origin_cli_parity` 及其健康分支；下载预览仍可使用同步智能编译恢复源码 PDF，已移除不再被内核调用的旧异步包装和历史参考实现。

## Recent Responsibility Updates (2026-05-09 structured insights completeness gate)

- `backend/app/services/paper_service.py`: 社区/admin 发布链路的结构化解析现在会拒绝明显截断的模块内容，包含 LLM 返回 `finish_reason=length/content_filter`、正文未以完整句子和句末标点结束等情况；失败模块会进入既有重试流程，最终仍可用兜底模板发布，并在管理员策展任务 `error` 字段保留兜底提示。

## Recent Responsibility Updates (2026-05-09 structured insights COS recovery)

- `backend/app/services/paper_service.py`: 社区/admin 发布链路的结构化解析现在会在本地任务输出缺失时，从持久化任务输出中定向恢复 `sections_map.json`、`envs_map.json`、`captions_map.json`，避免 COS 模式清理本地 `data/outputs/<task>` 后写入空源兜底内容；解析输入会跳过 LaTeX 导言区；若结构化模块最终使用兜底模板，发布仍可完成，但管理员策展任务历史会在 `error` 字段保留兜底提示。

## Recent Responsibility Updates (2026-05-08 source PDF COS cache and cleanup)

- `backend/app/services/paper_service.py`: 社区论文资产链路新增 `source_pdf` 原文 PDF 资产类型；arXiv 论文发布完成时会将原文 PDF 持久化到当前存储后端，COS 模式下写入 `data/community_papers/<paper_id>/source_pdf/<arxiv_id>.pdf` 并登记 `paper_assets`；公开源 PDF 解析优先使用 `source_pdf` 的对象存储签名 URL，再回退到源归档、本地源目录、arXiv 和 legacy task；源归档与预览恢复会在本地目录缺失时从 COS 任务目录物化临时副本再生成 canonical 资产。
- `backend/app/api/routes/papers.py`: `/api/papers/{paper_id}/source-pdf`、`source-download`、`source-thumbnail` 支持对象存储源 PDF，通过远端 PDF 代理保留 Range 预览与下载 disposition 行为。
- `backend/scripts/backfill_community_source_pdfs_to_cos.py`: 新增 dry-run-first 运维脚本，用于发现已发布 arXiv 社区论文中缺失 `source_pdf` 的候选项，并在显式 `--execute` 时下载原文 PDF、上传到 COS、回写 `paper_assets`。
- `backend/scripts/cleanup_cos_mode_local_residue.py`: 新增 dry-run-first 本地残留清理脚本，仅在 COS 模式执行删除，限制在 `data/uploads`、`data/outputs`、`data/community_papers`、`data/failed_tasks`、`data/tmp_storage` 等安全根下，并按最小年龄阈值清理。

## Recent Responsibility Updates (2026-05-08 production asset COS migration)

- `backend/scripts/migrate_production_assets_to_cos.py`: 新增生产资产迁移运维脚本，先生成 dry-run manifest，统计本地资产、MySQL 指针与 COS 对象，支持分阶段清理 COS 孤儿对象、上传本地 durable 资产、回填历史输出 manifest、更新 MySQL 指向以及最终清理本地资产目录。

## Recent Responsibility Updates (2026-05-07 parity health branch)

- `backend/app/services/latex/compiler.py`: `origin_cli_parity` 编译新增可丢弃的健康增强分支，基线仍按旧 CLI 顺序 `pdflatex -> xelatex` 并优先保留已生成 PDF；引用/BibTeX flag、裸 `%`、旧 biblatex `.bbl`、CJK/pdfTeX 兼容、预编译包清理与图片 sanitizer 等修复仅在临时副本或受控触发路径中运行，失败时回退基线结果。
- `backend/app/services/agents/generator_agent.py`: parity 编译调用透传目标语言，用于健康增强分支判断 CJK 相关触发条件，不改变任务状态策略。

## Recent Responsibility Updates (2026-05-07 daily translation quotas)

- `backend/app/api/routes/upload.py`: 批量上传新增 `/upload/batch-translate` 认证入口，按文件数在创建任何上传/翻译任务前一次性预留每日 LaTeX 额度；单文件上传成功后复用翻译启动流程但跳过二次扣减，并对未被接受的文件释放预留额度。
- `backend/app/repositories/translation_quota_repository.py`: 新增每日 LaTeX 翻译额度与 NiuTrans PDF 直译积分快照仓储，提供按用户/额度类型/UTC+8 日期的原子预留、释放和安全快照读写。
- `backend/app/services/auth_service.py`: 登录成功后调用 NiuTrans user-info 接口，仅提取 `unusedNumIntegral` 并保存安全 PDF 直译积分快照；登录和会话自举返回独立额度快照，不暴露上游 token、apikey 或密码字段。
- `backend/app/api/routes/auth.py`: 登录、`/auth/me` 与 `/auth/quota` 响应新增 `quota_snapshot`，统一返回本地 LaTeX 每日额度和 NiuTrans PDF 直译积分状态。
- `backend/app/api/routes/translate.py`: 普通 arXiv/上传源翻译启动前预留 1 次本地 LaTeX 额度，批量 arXiv 提交按条目数原子预留；超额时返回稳定 `DAILY_LATEX_QUOTA_EXCEEDED` 结构，预接收失败时释放额度。
- `backend/app/core/config.py`: 新增 NiuTrans user-info URL、每日 LaTeX 翻译默认额度和重置时区配置。
- `backend/migrations_mysql/20260507_0011_daily_translation_quotas.sql`: 新增 `user_daily_quotas` 与 `niutrans_balance_snapshots` 表，用于持久化本地每日额度和安全的 PDF 直译积分快照。

## Recent Responsibility Updates (2026-05-06 orphan curation backfill)

- `backend/scripts/backfill_orphan_translation_curation_jobs.py`: 新增一次性管理员策展补入库脚本，用于发现已经完成但未进入 `community_curation_jobs` 的历史翻译任务，按 arXiv 去重选择具备 source、output、task_log 与译文 PDF 的最佳任务，并通过现有管理员发布链路补建策展 job、社区论文记录与公开资产；默认 dry-run，只有显式 `--execute` 才写入数据库与资产。

## Recent Responsibility Updates (2026-05-06 CLI parity timeout)

- `backend/app/core/config.py`: 新增 admin curation 等待超时环境配置，支持将 admission/execution 等待超时设为 `0` 以关闭外层等待限制。
- `backend/app/services/paper_service.py`: admin curation 等待任务终态逻辑改为读取可配置超时，并在超时值为 `0` 时持续等待，避免与 CLI parity 翻译路径产生额外半小时终止差异。

## Recent Responsibility Updates (2026-05-05 Origin CLI Parity Kernel)

- `backend/app/models/config_models.py`: 新增 `origin_cli_parity` 翻译内核模式常量、现代系统禁用清单与统一 agent 配置归一化函数，确保当前后端翻译任务默认进入旧 CLI 等价内核。
- `backend/app/api/routes/translate.py`: 共享翻译任务入口在创建 `CoordinatorAgent` 前统一应用 parity 配置，普通上传、arXiv、批量、社区与管理触发路径通过同一执行配置进入后端内核。
- `backend/app/services/paper_service.py`: 社区论文、admin 策展、content-pool 预热与 community-agent 触发的翻译桥接现在复用 translate 路由的 origin CLI parity 有效配置，确保持久化 advanced_config、config_hash 与最终内核执行保持一致。
- `backend/app/services/agents/langgraph_orchestrator.py`: 增加 parity-only LangGraph 包装图，执行路径仅保留 parse、translate、validate_and_retry、generate、finalize，并在任务日志/审计日志记录 parity 模式与未调用的现代系统。
- `backend/app/services/agents/parser_agent.py`、`backend/app/services/latex/parser.py`: 增加旧 CLI parser parity 分支，关闭后端长 section chunk 元数据、恢复旧环境抽取/need_trans 规则，并使用旧 CLI 串行环境翻译判定。
- `backend/app/services/agents/translator_agent.py`、`backend/app/services/latex/prompts.py`、`backend/app/services/latex/origin_cli_prompts.py`: parity 模式使用迁入 backend 的 `texts/origin` 旧提示词快照、旧请求 payload/retry/source fallback 语义，并恢复旧 section/error 并发上限；生产容器不再运行时依赖 repo 根目录的 `texts/origin` 文件。
- `backend/app/services/agents/validator_agent.py`: parity 模式仅执行旧 CLI command、placeholder、bracket 校验与旧 retry 目标选择，不触发后端新增结构/数学/残留英文/全局 placeholder 校验。
- `backend/app/services/agents/generator_agent.py`、`backend/app/services/latex/reconstruct.py`、`backend/app/services/latex/compiler.py`: parity 模式跳过格式化、结构 guard 与智能编译 fallback，按旧 CLI 直接重构 LaTeX，并以 pdflatex 后 xelatex 的旧顺序编译。

## Recent Responsibility Updates (2026-04-27 worker 运行时任务取消)

- `backend/app/services/task_runtime_client.py`: 新增 web 进程到 worker 进程的内部签名取消通道，用于前端删除任务或管理员删除策展任务时，同步终止 worker 内存队列中正在运行/等待运行的翻译任务。
- `backend/app/api/routes/task.py`: 删除任务前先通知 worker runtime 取消对应 task，并提供仅内部签名可调用的 `/api/internal/task/{task_id}/cancel` 入口，避免 9001 删除后 9002 继续烧 API。
- `backend/app/services/paper_service.py`: 管理员策展任务删除链路现在同样会先通知 worker runtime 取消翻译任务，再删除任务与占位论文记录。
- `backend/app/core/config.py`: 新增 worker runtime 内部取消调用地址与签名时间窗配置，默认指向 `http://127.0.0.1:9002/api`。

## Recent Responsibility Updates (2026-04-27 tiktoken 离线降级)

- `backend/app/services/latex/parser.py`: LaTeX 解析/分块阶段获取 `tiktoken` 编码失败时不再让任务失败；会退到仓库内确定性的 `estimate_tokens_v1` 估算，避免生产容器因无法访问 `openaipublic.blob.core.windows.net` 下载编码表而中断翻译。

## Recent Responsibility Updates (2026-04-27 arXiv 元数据自动修复)

- `backend/app/services/paper_service.py`: arXiv 元数据拉取现在会对临时网络请求失败执行 3 次短重试；已发布 arXiv 论文若因临时失败留下 `arXiv:<id>`、空作者、空分类、空摘要或空发布时间，可通过后台修复入口重新补齐元数据。
- `backend/app/repositories/community_paper_repository.py`: 新增已发布 arXiv 论文元数据修复候选扫描，按公开发布状态与缺失/兜底字段筛选，供 worker 周期任务小批量处理。
- `backend/app/main.py`: worker/all 运行模式新增 arXiv 元数据周期修复协程，启动后立即扫描并按配置间隔继续修复，不阻塞翻译或发布链路。
- `backend/app/core/config.py`: 新增 `COMMUNITY_ARXIV_METADATA_REPAIR_INTERVAL_SECONDS` 与 `COMMUNITY_ARXIV_METADATA_REPAIR_LIMIT`，用于控制 worker 侧元数据修复频率和批量上限。

## Recent Responsibility Updates (2026-04-27 Legacy Core Full Rollback)

- `backend/app/services/agents/llm_token_pool.py`: 系统 LLM pool 的请求级成员选择现在尊重 `reserve` 成员标记；健康主成员存在时不使用备用 key，只有主成员不可用/冷却后才进入备用成员。
- `backend/app/services/agents/langgraph_orchestrator.py`: legacy/community 翻译核心路径现在完全跳过新系统 repair、ultimate downgrade、post-compile target-language fallback 和 residual English 硬阻断；校验重翻译恢复旧系统 3 轮；校验后的 fallback report 也不再进入 legacy 状态，避免伪中文降级链路写回产物。
- `backend/app/services/agents/translator_agent.py`: legacy 翻译核心恢复旧 CLI 风格 API 调用；单 key 配置或只有一个成员的系统池走直接 `session.post(..., timeout=100)`，不再被 token pool 单成员调度串行化；legacy 校验重翻译和失败部件重试恢复为直接重试 sec/env/cap，不再使用 compile-first fallback、payload skip guard 等新内核逻辑。

## Recent Responsibility Updates (2026-04-26 Community Quality Gate)

- `backend/app/api/routes/translate.py`: 社区/admin curation 生产翻译的单任务 LLM 并发恢复为原系统同级默认值 10；API 击穿保护交给每 key 任务级 token bucket，而不是压低论文内部 section 并发。
- `backend/app/api/routes/translate.py`: 社区/admin curation 生产翻译强制启用 `enable_legacy_translation_core`，让基本 section/env/caption 翻译路径回到原系统语义。
- `backend/app/services/agents/translator_agent.py`: 新增 legacy translation core 分支；启用时绕开 hard-freeze、paragraph rescue、no-op retry、target-language rescue 和结构 fallback，按原系统的 section -> env -> caption 顺序及失败原文回退逻辑执行。
- `backend/app/services/paper_service.py`: 社区发布路径不再执行翻译质量门禁阻断；翻译完成后按原系统产物直接同步 canonical PDF/preview 并发布，质量扫描逻辑仅保留为离线审计工具。
- `backend/app/core/config.py`: `COMMUNITY_TRANSLATION_LLM_MAX_CONCURRENT_REQUESTS` 默认值调整为 10，与原系统 section 并发一致。

- `backend/app/api/routes/translate.py`: 社区/admin curation 生产翻译现在走简化内核：关闭 hard-freeze transport、编译前结构门禁、编译后结构/目标语降级和诊断 LLM，减少占位符过度保护导致的慢、回退和坏译文。
- `backend/app/services/latex/utils.py`: hard-freeze 风险分层将普通 inline math 视为低风险 token，section relaxed 模式不再因相邻数学占位符重排而整段回退。

- `backend/app/api/routes/translate.py`: 社区/admin curation 生产翻译现在按 `COMMUNITY_TRANSLATION_LLM_MAX_CONCURRENT_REQUESTS` 收紧单任务 LLM 并发，默认 3，避免单篇论文内部打穿同一 API 池。
- `backend/app/models/config_models.py`: `AdvancedConfig` 增加不持久化的内部标记 `community_production_translation`，用于区分生产社区入库任务与普通交互任务。
- `backend/app/core/config.py`: 新增 `COMMUNITY_TRANSLATION_LLM_MAX_CONCURRENT_REQUESTS` 配置项，控制社区生产翻译的单任务 LLM 请求上限。
- `backend/app/services/agents/langgraph_orchestrator.py`: 残留英文验证失败现在也进入最终兜底；只有真实中文候选才做结构化降级，否则标记 source passthrough 交给发布质量门禁裁决。
- `backend/app/services/agents/base_tool_agent.py`: agent 写 JSON/YAML/TOML 前会自动重建父目录，避免运行期输出目录被清理后回写 map 文件直接失败。
- `backend/app/services/paper_service.py`: 社区策展执行阶段默认超时放宽到 2 小时；源码归档改为安全 zip 写入，钳制 1980 年前文件时间戳。
- `backend/app/services/task_artifact_storage.py`: 译文源码归档写入同样钳制 zip 条目时间戳，避免旧 mtime 文件导致归档失败。

- `backend/app/services/community_translation_quality.py`: 社区译文发布质量门禁，检查固定伪中文降级短语、多段或过长 source fallback、大段英文保留和致命 provider 状态，并输出机器可读诊断。
- `backend/app/services/paper_service.py`: canonical 社区译文资产同步前先运行质量门禁；失败时保留任务产物、写入诊断 JSON，不发布为健康社区资产。
- `backend/scripts/audit_community_translation_quality.py`: 本地扫描 `backend/data/community_papers` 的社区资产质量脚本，用于标记既有坏产物并导出 JSON 报告。

鎸?`backend/` 涓嬬湡瀹炵墿鐞嗚矾寰勬暣鐞嗙殑鍚庣鐢熶骇渚х储寮曪紝鏂逛究 AI 鎴栦汉宸ュ厛鎸夎矾寰勬绱紝鍐嶆寜璇存槑瀹氫綅妯″潡銆?

鏀跺綍鑼冨洿锛歅ython 婧愮爜銆丼QL 杩佺Щ鑴氭湰銆佽繍缁磋剼鏈€?
涓嶆敹褰曡寖鍥达細娴嬭瘯浠ｇ爜銆丮arkdown 鏂囨。銆丣SON 鏁版嵁銆佺幆澧冪ず渚嬨€丷EADME銆?

## Usage Rules

- 褰撻渶瑕佸揩閫熸煡鎵惧悗绔枃浠躲€佺悊瑙ｇ洰褰曞垎甯冦€佸畾浣嶆ā鍧楀叆鍙ｆ椂锛屼紭鍏堝厛璇绘湰鏂囦欢銆?
- 寤鸿妫€绱㈤『搴忥細鍏堢湅 `Pure Path List` 鎵捐矾寰勶紝鍐嶇湅 `Annotated Index` 璇昏亴璐ｅ拰椤跺眰绗﹀彿銆?
- 浠讳綍鏂板銆佸垹闄ゃ€佺Щ鍔ㄣ€侀噸鍛藉悕鍚庣鐢熶骇渚ф枃浠剁殑淇敼锛岄兘蹇呴』鍚屾缁存姢鏈枃浠躲€?
- 浠讳綍浼氭樉钁楁敼鍙樻枃浠惰亴璐ｇ殑鍚庣鏀瑰姩锛屼篃搴斿悓姝ユ洿鏂板搴旇鏄庛€?

## Directory Map

- `backend/app/api/routes`: FastAPI 璺敱鍏ュ彛灞傦紝璐熻矗瀵瑰 API銆?
- `backend/app/core`: 鍏ㄥ眬閰嶇疆銆佽璇併€佸姞瀵嗐€佹椂闂寸瓑鏍稿績鍩虹璁炬柦銆?
- `backend/app/db`: 鏁版嵁搴撹繛鎺ヤ笌鏂硅█閫傞厤銆?
- `backend/app/models`: 閰嶇疆妯″瀷涓庢暟鎹粨鏋勫畾涔夈€?
- `backend/app/policies`: 鏉冮檺绛栫暐涓庢巿鏉冭鍒欍€?
- `backend/app/repositories`: 鎸佷箙鍖栬鍐欎粨鍌ㄥ眰銆?
- `backend/app/services`: 涓氬姟鏈嶅姟灞傦紝鏄悗绔富瑕佸疄鐜板尯鍩熴€?
- `backend/app/services/agents`: LaTeX 缈昏瘧浠ｇ悊涓庣紪鎺掔绾裤€?
- `backend/app/services/community_agent`: 绀惧尯鏅鸿兘浣撹繍琛屾椂銆佹妧鑳戒笌宸ュ叿銆?
- `backend/app/services/latex`: LaTeX 瑙ｆ瀽銆侀噸寤恒€佺紪璇戙€佺粨鏋勫畧鍗€?
- `backend/app/utils`: 閫氱敤寮傛鎴栭樆濉炶緟鍔╁伐鍏枫€?
- `backend/migrations`: 涓绘暟鎹簱杩佺Щ鑴氭湰銆?
- `backend/migrations_mysql`: MySQL 杩佺Щ鑴氭湰銆?
- `backend/scripts`: 杩愮淮銆佸垵濮嬪寲銆佽縼绉讳笌瀹¤鑴氭湰銆?

## Pure Path List

- `backend/__init__.py`
- `backend/app/__init__.py`
- `backend/app/api/__init__.py`
- `backend/app/api/routes/__init__.py`
- `backend/app/api/routes/arxiv.py`
- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/community_agent.py`
- `backend/app/api/routes/download.py`
- `backend/app/api/routes/history.py`
- `backend/app/api/routes/papers.py`
- `backend/app/api/routes/settings.py`
- `backend/app/api/routes/task.py`
- `backend/app/api/routes/translate.py`
- `backend/app/api/routes/upload.py`
- `backend/app/core/__init__.py`
- `backend/app/core/auth.py`
- `backend/app/core/config.py`
- `backend/app/core/encryption.py`
- `backend/app/core/timezone_utils.py`
- `backend/app/db/__init__.py`
- `backend/app/db/connection.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/config_models.py`
- `backend/app/policies/__init__.py`
- `backend/app/policies/admin_policy.py`
- `backend/app/policies/base.py`
- `backend/app/policies/community_agent_policy.py`
- `backend/app/policies/paper_policy.py`
- `backend/app/policies/settings_policy.py`
- `backend/app/policies/task_policy.py`
- `backend/app/repositories/__init__.py`
- `backend/app/repositories/auth_repository.py`
- `backend/app/repositories/community_agent_repository.py`
- `backend/app/repositories/community_paper_repository.py`
- `backend/app/repositories/translation_task_repository.py`
- `backend/app/repositories/translation_quota_repository.py`
- `backend/app/repositories/user_settings_repository.py`
- `backend/app/services/__init__.py`
- `backend/app/services/agents/__init__.py`
- `backend/app/services/agents/base_tool_agent.py`
- `backend/app/services/agents/compile_runtime.py`
- `backend/app/services/agents/coordinator_agent.py`
- `backend/app/services/agents/generator_agent.py`
- `backend/app/services/agents/langgraph_orchestrator.py`
- `backend/app/services/agents/llm_runtime.py`
- `backend/app/services/agents/llm_token_pool.py`
- `backend/app/services/agents/parser_agent.py`
- `backend/app/services/agents/pipeline_invariants.py`
- `backend/app/services/agents/translator_agent.py`
- `backend/app/services/agents/validator_agent.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/community_agent/__init__.py`
- `backend/app/services/community_agent/formatter.py`
- `backend/app/services/community_agent/language.py`
- `backend/app/services/community_agent/models.py`
- `backend/app/services/community_agent/orchestrator.py`
- `backend/app/services/community_agent/runtime.py`
- `backend/app/services/community_agent/skills/__init__.py`
- `backend/app/services/community_agent/skills/base.py`
- `backend/app/services/community_agent/skills/community_search.py`
- `backend/app/services/community_agent/skills/compose_academic_answer.py`
- `backend/app/services/community_agent/skills/contracts/__init__.py`
- `backend/app/services/community_agent/skills/contracts/community_search_papers/__init__.py`
- `backend/app/services/community_agent/skills/contracts/community_search_papers/executor.py`
- `backend/app/services/community_agent/skills/contracts/compose_academic_answer/__init__.py`
- `backend/app/services/community_agent/skills/contracts/compose_academic_answer/executor.py`
- `backend/app/services/community_agent/skills/contracts/external_tavily_search/__init__.py`
- `backend/app/services/community_agent/skills/contracts/external_tavily_search/executor.py`
- `backend/app/services/community_agent/skills/contracts/import_arxiv_paper/__init__.py`
- `backend/app/services/community_agent/skills/contracts/import_arxiv_paper/executor.py`
- `backend/app/services/community_agent/skills/contracts/read_paper_context/__init__.py`
- `backend/app/services/community_agent/skills/contracts/read_paper_context/executor.py`
- `backend/app/services/community_agent/skills/contracts/start_translation_kernel/__init__.py`
- `backend/app/services/community_agent/skills/contracts/start_translation_kernel/executor.py`
- `backend/app/services/community_agent/skills/external_tavily_search.py`
- `backend/app/services/community_agent/skills/import_arxiv_paper.py`
- `backend/app/services/community_agent/skills/read_paper_context.py`
- `backend/app/services/community_agent/skills/start_translation_kernel.py`
- `backend/app/services/community_agent/skills_runtime.py`
- `backend/app/services/community_agent/tools/__init__.py`
- `backend/app/services/community_agent/tools/base.py`
- `backend/app/services/community_agent/tools/community_search.py`
- `backend/app/services/community_agent/tools/external_tavily_search.py`
- `backend/app/services/community_agent/tools/import_arxiv_paper.py`
- `backend/app/services/community_agent/tools/read_paper_context.py`
- `backend/app/services/community_agent/tools/start_translation_kernel.py`
- `backend/app/services/community_agent/validator.py`
- `backend/app/services/community_agent_service.py`
- `backend/app/services/community_content_pool_service.py`
- `backend/app/services/community_translation_quality.py`
- `backend/app/services/config_capture.py`
- `backend/app/services/email_service.py`
- `backend/app/services/latex/__init__.py`
- `backend/app/services/latex/compiler.py`
- `backend/app/services/latex/parser.py`
- `backend/app/services/latex/prompts.py`
- `backend/app/services/latex/reconstruct.py`
- `backend/app/services/latex/sanitizer.py`
- `backend/app/services/latex/token_estimator.py`
- `backend/app/services/latex/utils.py`
- `backend/app/services/latex_validator.py`
- `backend/app/services/paper_thumbnail_service.py`
- `backend/app/services/paper_preview_service.py`
- `backend/app/services/paper_service.py`
- `backend/app/services/runtime_pressure.py`
- `backend/app/services/storage_backend.py`
- `backend/app/services/task_artifact_storage.py`
- `backend/app/services/task_detail.py`
- `backend/app/services/task_manager.py`
- `backend/app/utils/__init__.py`
- `backend/app/utils/async_blocking.py`
- `backend/migrations/20260316_add_task_detail_metadata.sql`
- `backend/migrations/20260318_add_increment_paper_download_count_fn.sql`
- `backend/migrations/20260318_add_increment_paper_view_count_fn.sql`
- `backend/migrations/20260318_add_paper_community_admission_fields.sql`
- `backend/migrations/20260318_create_interaction_tables.sql`
- `backend/migrations/20260318_create_moderation_tables.sql`
- `backend/migrations/20260318_create_papers_and_assets.sql`
- `backend/migrations/20260318_refine_day1_policy_and_index_guards.sql`
- `backend/migrations/20260323_create_community_agent_conversations.sql`
- `backend/migrations/20260326_create_community_content_pool_foundation.sql`
- `backend/migrations_mysql/20260409_0001_local_auth_mysql.sql`
- `backend/migrations_mysql/20260411_0002_community_admin_curation_flow.sql`
- `backend/migrations_mysql/20260411_0003_expand_paper_asset_id_columns.sql`
- `backend/migrations_mysql/20260411_0004_add_content_column_to_community_structured_insights.sql`
- `backend/migrations_mysql/20260412_0005_add_community_similar_recommendations.sql`
- `backend/migrations_mysql/20260419_0006_admin_curation_retention_fields.sql`
- `backend/migrations_mysql/20260421_0008_community_paper_engagement.sql`
- `backend/migrations_mysql/20260422_0009_add_arxiv_published_at.sql`
- `backend/migrations_mysql/20260423_0010_add_login_identifier_to_users.sql`
- `backend/migrations_mysql/20260507_0011_daily_translation_quotas.sql`
- `backend/scripts/apply_mysql_migrations.py`
- `backend/scripts/audit_pipeline_regression.py`
- `backend/scripts/audit_community_translation_quality.py`
- `backend/scripts/bootstrap_local_community_papers.py`
- `backend/scripts/extract_core_pool_ids.py`
- `backend/scripts/grant_local_admin.py`
- `backend/scripts/import_source_to_mysql.py`
- `backend/scripts/migrate_production_assets_to_cos.py`
- `backend/scripts/mysql_script_connection.py`
- `backend/scripts/sync_core_pool_complete_from_cos.py`

## Annotated Index

### backend
- `backend/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?

### backend/app
- `backend/app/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/main.py`: FastAPI 搴旂敤鍏ュ彛锛岃礋璐ｆ敞鍐屼腑闂翠欢鍜岃矾鐢憋紝骞跺鐞嗗惎鍔ㄤ笌鍏抽棴鏃剁殑浠诲姟鏀跺熬銆?| 椤跺眰绗﹀彿: _dedupe_non_empty, get_translation_task_repository, get_community_paper_repository, reset_stale_community_tasks, fail_interrupted_translation_tasks, startup_event

### backend/app/api
- `backend/app/api/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?

### backend/app/api/routes
- `backend/app/api/routes/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/api/routes/arxiv.py`: arXiv 涓嬭浇涓庡悎娉曟€ф牎楠屾帴鍙ｃ€?| 椤跺眰绗﹀彿: ArxivRequest, ArxivResponse, _download_arxiv_background, download_arxiv, validate_arxiv_id
- `backend/app/api/routes/auth.py`: 璁よ瘉鎺ュ彛锛屽鐞嗙櫥褰曘€佸綋鍓嶇敤鎴蜂笌鐧诲嚭銆?| 椤跺眰绗﹀彿: LoginRequest, LocalUserPayload, LoginResponse, MeResponse, get_auth_service, _error_response, login, current_user, logout
- `backend/app/api/routes/community_agent.py`: 绀惧尯鏅鸿兘浣撹繍琛屻€佷細璇濅笌浜嬩欢娴佹帴鍙ｃ€?| 椤跺眰绗﹀彿: CommunityAgentSkillToggles, CommunityAgentRunRequest, CommunityConversationTurnPayload, CommunityConversationRecordPayload, CommunityConversationDeleteResponse, _ensure_community_agent_authorized, _ensure_community_agent_product_enabled, create_agent_run, list_agent_conversations, upsert_agent_conversation, delete_agent_conversation
- `backend/app/api/routes/download.py`: 璇戞枃銆佹簮鏂囦欢銆丳DF銆佹棩蹇椾笌鏈涓嬭浇鎴栭瑙堟帴鍙ｃ€?| 椤跺眰绗﹀彿: _validate_pdf_with_pdfinfo, _find_translated_pdf, _candidate_output_dirs, _find_translated_pdf_in_community_library, _collect_original_pdf_candidates, _pick_best_source_pdf
- `backend/app/api/routes/history.py`: 缈昏瘧鍘嗗彶涓庝换鍔¤鎯呮帴鍙ｃ€?| 椤跺眰绗﹀彿: TaskHistoryItem, TaskHistoryResponse, TaskDetailResponse, BatchDeleteRequest, get_translation_task_repository, _resolve_translation_task_repository, _infer_status_from_task_log, _ensure_task_authorized, _reconcile_task_snapshot, _serialize_optional_timestamp
- `backend/app/api/routes/papers.py`: 绀惧尯璁烘枃鎻愪氦銆佸垪琛ㄣ€佽鎯呫€侀瑙堛€佷笅杞戒笌绠＄悊鍛樼瓥灞曠鐞嗘帴鍙ｏ紝鐜板寘鍚鐞嗗憳浠诲姟鍘嗗彶鏌ヨ涓庣‖鍒犻櫎鍏ュ彛銆?| 椤跺眰绗﹀彿: AssetSummary, ViewerState, PaperSummary, TaskSummary, PaperSubmitResponse, AdminCurationJobHistoryItemResponse, AdminDeleteCurationJobResponse, _ensure_paper_authorized, _ensure_local_admin, _proxy_remote_pdf_preview, _parse_single_byte_range, _serve_local_pdf_preview, _paper_thumbnail_cache_dir
- `backend/app/api/routes/settings.py`: 鐢ㄦ埛璁剧疆璇诲彇涓庢洿鏂版帴鍙ｃ€?| 椤跺眰绗﹀彿: UserSettingsResponse, UserSettingsUpdate, get_user_settings_repository, _resolve_user_settings_repository, _build_response, _ensure_settings_authorized, get_user_settings, update_user_settings
- `backend/app/api/routes/task.py`: 浠诲姟鐘舵€佹煡璇€佸垹闄や笌娴佸紡璁㈤槄鎺ュ彛銆?| 椤跺眰绗﹀彿: TaskStatusResponse, get_translation_task_repository, _resolve_translation_task_repository, _is_guest_task, _authorize_authenticated_task, _load_authorized_task, get_task_status
- `backend/app/api/routes/translate.py`: 缈昏瘧鍚姩銆佹壒閲忕炕璇戙€侀厤缃搱甯屼笌缁撴灉澶嶇敤鎺ュ彛銆?| 椤跺眰绗﹀彿: TranslateRequest, TranslateResponse, BatchTranslateRequest, BatchTranslateResponse, _schedule_community_publish_watch, get_translation_task_repository, get_user_api_config, get_user_api_config_async, build_llm_config, build_llm_config_async
- `backend/app/api/routes/upload.py`: LaTeX 上传、校验、压缩包解包与批量上传翻译入口。| 顶层符号: LatexValidationResponse, UploadResponse, _parse_advanced_config_form, _safe_upload_filename, extract_rar, get_file_extension, batch_upload_translate, upload_file

### backend/app/core
- `backend/app/core/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/core/auth.py`: 鏈湴璁よ瘉涓庢潈闄愪緷璧栧疄鐜帮紝澶勭悊 JWT銆佸綋鍓嶇敤鎴疯В鏋愬拰绠＄悊鍛樿姹傛牎楠屻€?| 椤跺眰绗﹀彿: extract_bearer_token_from_credentials, extract_bearer_token, resolve_current_user_id, get_auth_service, optional_current_user, require_current_user
- `backend/app/core/config.py`: 鍏ㄥ眬閰嶇疆涓績锛屽畾涔夎缃」銆佷换鍔＄姸鎬佹灇涓句互鍙?LLM銆佸瓨鍌ㄣ€佹暟鎹簱绛夎繍琛屽弬鏁般€?| 椤跺眰绗﹀彿: TaskStatus, CompilationStage, Settings, get_settings, get_llm_config
- `backend/app/core/encryption.py`: 鏍稿績鍩虹璁炬柦鏂囦欢銆?| 椤跺眰绗﹀彿: _get_fernet, encrypt_api_key, decrypt_api_key, is_encryption_configured
- `backend/app/core/timezone_utils.py`: 鏍稿績鍩虹璁炬柦鏂囦欢銆?| 椤跺眰绗﹀彿: get_cst_now, get_cst_now_iso

### backend/app/db
- `backend/app/db/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/db/connection.py`: 鏁版嵁搴撹繛鎺ヤ笌杈呭姪鏂囦欢銆?| 椤跺眰绗﹀彿: DatabaseUnavailableError, get_database_dialect, db_connection

### backend/app/models
- `backend/app/models/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/models/config_models.py`: 鏁版嵁妯″瀷鏂囦欢銆?| 椤跺眰绗﹀彿: SourceType, FormattingConfig, AdvancedConfig, LatexValidation

### backend/app/policies
- `backend/app/policies/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?| 椤跺眰绗﹀彿: authorize
- `backend/app/policies/admin_policy.py`: 閴存潈绛栫暐鏂囦欢銆?| 椤跺眰绗﹀彿: AdminPolicy
- `backend/app/policies/base.py`: 閴存潈绛栫暐鏂囦欢銆?| 椤跺眰绗﹀彿: AuthorizationResult, BasePolicy, _normalize_roles, is_admin, is_authenticated
- `backend/app/policies/community_agent_policy.py`: 閴存潈绛栫暐鏂囦欢銆?| 椤跺眰绗﹀彿: CommunityAgentPolicy
- `backend/app/policies/paper_policy.py`: 閴存潈绛栫暐鏂囦欢銆?| 椤跺眰绗﹀彿: PaperPolicy
- `backend/app/policies/settings_policy.py`: 閴存潈绛栫暐鏂囦欢銆?| 椤跺眰绗﹀彿: SettingsPolicy
- `backend/app/policies/task_policy.py`: 閴存潈绛栫暐鏂囦欢銆?| 椤跺眰绗﹀彿: TaskPolicy

### backend/app/repositories
- `backend/app/repositories/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/repositories/auth_repository.py`: 浠撳偍灞傛枃浠讹紝涓轰笂灞傛湇鍔℃彁渚涙寔涔呭寲璇诲啓鑳藉姏銆?| 椤跺眰绗﹀彿: AuthRepository, _utc_now_naive, _placeholder, _placeholders, _fetchone, _fetchall
- `backend/app/repositories/community_agent_repository.py`: 浠撳偍灞傛枃浠讹紝涓轰笂灞傛湇鍔℃彁渚涙寔涔呭寲璇诲啓鑳藉姏銆?| 椤跺眰绗﹀彿: CommunityAgentConversationRepository, CommunityAgentRunRepository, _placeholder, _fetchone, _fetchall, _decode_turns, _decode_json_dict, _normalize_db_timestamp
- `backend/app/repositories/community_paper_repository.py`: 绀惧尯璁烘枃浠撳偍锛岃礋璐ｈ鏂囥€佽祫浜с€佷簰鍔ㄣ€佺瓥灞曘€佷换鍔″巻鍙蹭笌缁撴瀯鍖栬В璇荤瓑鏁版嵁璇诲啓銆?| 椤跺眰绗﹀彿: CommunityPaperRepository, _utc_now_naive, _placeholder, _fetchone, _fetchall, _decode_json_list
- `backend/app/repositories/translation_task_repository.py`: 缈昏瘧浠诲姟浠撳偍锛岃礋璐ｄ换鍔＄姸鎬併€佽鎯呫€侀厤缃搱甯屼笌鍘嗗彶璁板綍鐨勬寔涔呭寲銆?| 椤跺眰绗﹀彿: TranslationTaskRepository, _utc_now_naive, _placeholder, _placeholders, _fetchone, _fetchall, _decode_json
- `backend/app/repositories/user_settings_repository.py`: 浠撳偍灞傛枃浠讹紝涓轰笂灞傛湇鍔℃彁渚涙寔涔呭寲璇诲啓鑳藉姏銆?| 椤跺眰绗﹀彿: UserSettingsRepository, _utc_now_naive, _placeholder, _fetchone, _decode_json

#### backend/app/repositories daily quota additions
- `backend/app/repositories/translation_quota_repository.py`: 每日翻译额度仓储，兼容 SQLite/MySQL，负责 `user_daily_quotas` 原子预留/释放与 `niutrans_balance_snapshots` 安全快照读写。| 顶层符号: TranslationQuotaRepository

### backend/app/services
- `backend/app/services/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/services/auth_service.py`: 涓氬姟鏈嶅姟鏂囦欢銆?| 椤跺眰绗﹀彿: AuthServiceError, NiuTransAuthClient, LocalAuthService, _b64url_encode, _b64url_decode, _now_utc, _now_unix
- `backend/app/services/community_agent_service.py`: 绀惧尯鏅鸿兘浣撴湇鍔￠棬闈紝鍒涘缓杩愯璁板綍銆佽浆鍙戜簨浠舵祦骞跺崗璋冩寔涔呭寲銆?| 椤跺眰绗﹀彿: RunNotFoundError, _RunRecord, _now_iso, _default_provider_state, _should_persist_run, _authorize_run_access, _save_run_to_repository, _save_event_to_repository
- `backend/app/services/community_content_pool_service.py`: 绀惧尯鍐呭姹犳湇鍔★紝澶勭悊璁烘枃瀵煎叆銆佸唴瀹规睜灏辩华搴︿笌鍚庡彴鏋勫缓浠诲姟銆?| 椤跺眰绗﹀彿: PoolCandidate, ContentPoolDependencies, _CandidateState, CommunityContentPoolService, _utc_now_iso, _normalize_text, _default_discover_candidates, _default_admit_candidate, _default_ensure_source_ready, _default_start_translation
- `backend/app/services/config_capture.py`: 涓氬姟鏈嶅姟鏂囦欢銆?| 椤跺眰绗﹀彿: _json_safe, _mask_api_key, _sanitize_llm_config, _sanitize_agent_config, capture_task_config
- `backend/app/services/email_service.py`: 涓氬姟鏈嶅姟鏂囦欢銆?| 椤跺眰绗﹀彿: EmailService, get_email_service
- `backend/app/services/latex_validator.py`: 涓氬姟鏈嶅姟鏂囦欢銆?| 椤跺眰绗﹀彿: validate_latex_directory, find_main_tex_file
- `backend/app/services/paper_thumbnail_service.py`: 璁烘枃 PDF 缂╃暐鍥剧紦瀛樻湇鍔★紝璐熻矗棣栭〉缂╃暐鍥剧敓鎴愩€佺紦瀛樺懡涓笌棰勭儹澶嶇敤銆?| 椤跺眰绗﹀彿: ensure_pdf_thumbnail, _thumbnail_cache_dir, _thumbnail_cache_path, _render_pdf_thumbnail_bytes_from_path, _render_pdf_thumbnail_bytes_from_url
- `backend/app/services/paper_preview_service.py`: 璁烘枃棰勮鏋勫缓鏈嶅姟锛岀敓鎴?HTML銆佹憳瑕併€侀瑙堣浇鑽峰苟鍋氱紦瀛樻仮澶嶃€?| 椤跺眰绗﹀彿: _load_json, _build_placeholder_map, _replace_placeholders, _strip_structural_commands, _unwrap_formatting_commands, _normalize_inline_text
- `backend/app/services/paper_service.py`: 璁烘枃涓绘湇鍔★紝璐熻矗绀惧尯璁烘枃瀵煎叆銆佺炕璇戞ˉ鎺ャ€侀瑙堛€佷笅杞姐€佺粨鏋勫寲瑙ｈ锛屼互鍙婄鐞嗗憳绛栧睍澶辫触鐣欑棔銆佷换鍔″巻鍙蹭笌纭垹闄ゆ祦绋嬨€?| 椤跺眰绗﹀彿: _StructuredInsightBasePreferenceTracker, _utc_now_iso, _get_curation_semaphore, _get_delete_semaphore, get_community_paper_repository, _run_local_repo, _run_db_blocking_with_retry
- `backend/app/services/runtime_pressure.py`: 杩愯鏃跺帇鍔涘崗璋冩湇鍔★紝璐熻矗鍖哄垎 web/worker 瑙掕壊銆佽褰曞墠鍙拌闂帇鍔涘苟璁╁悗鍙板洖濉换鍔¤姝ャ€?| 椤跺眰绗﹀彿: get_runtime_role, web_runtime_enabled, background_runtime_enabled, admin_job_execution_enabled, record_frontend_pressure, has_recent_frontend_pressure, backfill_start_blocked_by_frontend_pressure, apply_worker_process_priority
- `backend/app/services/storage_backend.py`: 瀵硅薄瀛樺偍鎶借薄灞傦紝缁熶竴鏈湴纾佺洏涓?COS 绛夊悗绔殑涓婁紶/涓嬭浇鎺ュ彛銆?| 椤跺眰绗﹀彿: StoredObjectRef, StorageBackend, LocalDiskStorageBackend, CosStorageBackend, build_storage_backend, _ensure_cos_config
- `backend/app/services/task_artifact_storage.py`: 浠诲姟浜х墿鎸佷箙鍖栨湇鍔★紝鍦ㄦ湰鍦颁笌瀵硅薄瀛樺偍涔嬮棿鍚屾杈撳嚭鐩綍鍙婃竻鍗曘€?| 椤跺眰绗﹀彿: _get_storage_backend, _storage_uses_object_store, _normalize_stored_path, normalize_stored_task_path, resolve_local_task_path, persist_task_directory
- `backend/app/services/task_detail.py`: 浠诲姟璇︽儏鎺ㄦ柇涓庢爣鍑嗗寲宸ュ叿锛岀粺涓€ stage銆乨etail_code銆乨etail_message 鐨勭敓鎴愩€?| 椤跺眰绗﹀彿: normalize_stage, normalize_detail_params, infer_task_detail
- `backend/app/services/task_manager.py`: 浠诲姟绠＄悊鏍稿績锛岀淮鎶ゅ唴瀛樻€佷换鍔°€佸紓姝ュ埛搴撱€侀槦鍒楁墽琛屼笌杩愯鏃舵竻鐞嗐€?| 椤跺眰绗﹀彿: PersistentStateFlusher, TaskManager, GuestTaskTracker, TaskQueue, get_translation_task_repository, get_auth_repository, _delete_local_cache_path, _is_within_cleanup_roots, clear_cached_runtime_artifacts, set_runtime_shutting_down

#### backend/app/services daily quota additions

### backend/app/services/agents
- `backend/app/services/agents/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?| 椤跺眰绗﹀彿: _SemaphoreProxy, _get_llm_semaphore
- `backend/app/services/agents/base_tool_agent.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: BaseToolAgent
- `backend/app/services/agents/compile_runtime.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: get_compile_semaphore
- `backend/app/services/agents/coordinator_agent.py`: 缈昏瘧娴佹按绾垮崗璋冨櫒锛岀紪鎺掕В鏋愩€佺炕璇戙€佹牎楠屻€佷慨澶嶄笌缂栬瘧姝ラ銆?| 椤跺眰绗﹀彿: CoordinatorAgent
- `backend/app/services/agents/generator_agent.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: GeneratorAgent
- `backend/app/services/agents/langgraph_orchestrator.py`: 缈昏瘧浠ｇ悊缂栨帓灞傦紝璐熻矗鑺傜偣娴佽浆銆佸璁℃棩蹇椼€佽繘搴︽洿鏂帮紝浠ュ強鍦ㄦ牎楠岄噸璇曞悗闃绘柇浠嶆畫鐣欒嫳鏂囬暱娈电殑浠诲姟瀹屾垚銆?| 椤跺眰绗﹀彿: PipelineState, _should_skip_deterministic_section_downgrade, _normalize_error_signature, _write_audit_log, _update_progress, _write_task_log, _write_stage_failed_log
- `backend/app/services/agents/llm_runtime.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: _as_mapping, extract_llm_config, _coerce_positive_int, resolve_llm_timeout, resolve_llm_max_concurrent_requests, resolve_task_llm_max_concurrent_requests
- `backend/app/services/agents/llm_token_pool.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: _MemberState, _PoolRegistry, build_pool_members_from_groups, compute_pool_routing_key, _parse_retry_after_seconds, _perform_member_request, post_chat_completion_with_pool
- `backend/app/services/agents/parser_agent.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: ParserAgent
- `backend/app/services/agents/pipeline_invariants.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: PipelineInvariantViolation, SpeculativeRepairForbiddenError, RawStructurePayloadViolation, RawContentLeakageViolation, HardFreezeProtocolViolation, assert_no_raw_structure, assert_no_long_raw_span, is_absolute_path_like
- `backend/app/services/agents/translator_agent.py`: 鏍稿績缈昏瘧浠ｇ悊锛岃礋璐ｅ垎娈电炕璇戙€佹湳璇鐞嗐€乸ayload 瀹堝崼銆侀檷绾т笌閲嶈瘯鎺у埗锛屽苟鎵挎媴娈嬬暀鑻辨枃闀挎鐨勪繚瀹堜腑鏂囪ˉ鏁戜笌璇垽 immutable 鍒嗘鐨勫厹搴曠炕璇戙€?| 椤跺眰绗﹀彿: TranslatorAgent
- `backend/app/services/agents/validator_agent.py`: 缈昏瘧鏍￠獙浠ｇ悊锛屾鏌ュ畬鏁存€с€佺粨鏋勯闄╁拰閿欒绫诲瀷鍒嗙被銆?| 椤跺眰绗﹀彿: ValidatorAgent, find_long_english_prose_spans, classify_error

### backend/app/services/community_agent
- `backend/app/services/community_agent/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/services/community_agent/formatter.py`: 涓氬姟鏈嶅姟鏂囦欢銆?| 椤跺眰绗﹀彿: format_summary
- `backend/app/services/community_agent/language.py`: 涓氬姟鏈嶅姟鏂囦欢銆?| 椤跺眰绗﹀彿: normalize_response_language, is_chinese_language, detect_response_language, summary_labels
- `backend/app/services/community_agent/models.py`: 涓氬姟鏈嶅姟鏂囦欢銆?| 椤跺眰绗﹀彿: AnswerSlots, PlannerStep
- `backend/app/services/community_agent/orchestrator.py`: 绀惧尯鏅鸿兘浣撶紪鎺掑眰锛岃礋璐ｈ鍒掋€佹绱€佹妧鑳芥墽琛屼笌绛旀缁勭粐銆?| 椤跺眰绗﹀彿: CommunityReactAgent, _normalize_text, _normalize_history, _normalize_reader_selection, _extract_arxiv_id, _normalized_title_tokens, _title_similarity_score
- `backend/app/services/community_agent/runtime.py`: 绀惧尯鏅鸿兘浣撹繍琛屾椂涓婁笅鏂囦笌浜嬩欢寰幆灏佽銆?| 椤跺眰绗﹀彿: AgentRuntimeState
- `backend/app/services/community_agent/skills_runtime.py`: 绀惧尯鏅鸿兘浣撴妧鑳借繍琛屾椂锛岃礋璐ｈ閰嶃€佸惎鍋滃拰璋冪敤鎶€鑳姐€?| 椤跺眰绗﹀彿: PromptSkillPack, PromptSkillBundle, _extract_frontmatter, _extract_json_block, load_prompt_skill_packs, _is_pack_visible, build_skill_prompt_bundle
- `backend/app/services/community_agent/validator.py`: 涓氬姟鏈嶅姟鏂囦欢銆?| 椤跺眰绗﹀彿: ValidationError, _normalize_text, _extract_domains, _mentions_time_constraint, _looks_like_paper_title_query, validate_search_query, _collect_known_paper_ids

### backend/app/services/community_agent/skills
- `backend/app/services/community_agent/skills/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?| 椤跺眰绗﹀彿: discover_skill_types, instantiate_discovered_skills
- `backend/app/services/community_agent/skills/base.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉畾涔夋枃浠躲€?| 椤跺眰绗﹀彿: SkillContract, AgentSkill, _extract_frontmatter, _extract_section_body, _extract_json_block, _extract_text_block, load_skill_contract
- `backend/app/services/community_agent/skills/community_search.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉畾涔夋枃浠躲€?| 椤跺眰绗﹀彿: CommunitySearchPapersSkill, _normalize_text, _citation_from_paper
- `backend/app/services/community_agent/skills/compose_academic_answer.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉畾涔夋枃浠躲€?| 椤跺眰绗﹀彿: ComposeAcademicAnswerSkill, _normalize_text, _normalize_string_list, _resolve_chat_completions_url, _extract_json_object
- `backend/app/services/community_agent/skills/external_tavily_search.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉畾涔夋枃浠躲€?| 椤跺眰绗﹀彿: ExternalTavilySearchSkill, _normalize_text
- `backend/app/services/community_agent/skills/import_arxiv_paper.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉畾涔夋枃浠躲€?| 椤跺眰绗﹀彿: ImportArxivPaperSkill
- `backend/app/services/community_agent/skills/read_paper_context.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉畾涔夋枃浠躲€?| 椤跺眰绗﹀彿: ReadPaperContextSkill, _normalize_text, _extract_anchor_ids
- `backend/app/services/community_agent/skills/start_translation_kernel.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉畾涔夋枃浠躲€?| 椤跺眰绗﹀彿: StartTranslationKernelSkill

### backend/app/services/community_agent/skills/contracts
- `backend/app/services/community_agent/skills/contracts/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?

### backend/app/services/community_agent/skills/contracts/community_search_papers
- `backend/app/services/community_agent/skills/contracts/community_search_papers/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/services/community_agent/skills/contracts/community_search_papers/executor.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉悎绾︽垨鎵ц鍣ㄦ枃浠躲€?| 椤跺眰绗﹀彿: CommunitySearchPapersSkill

### backend/app/services/community_agent/skills/contracts/compose_academic_answer
- `backend/app/services/community_agent/skills/contracts/compose_academic_answer/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/services/community_agent/skills/contracts/compose_academic_answer/executor.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉悎绾︽垨鎵ц鍣ㄦ枃浠躲€?| 椤跺眰绗﹀彿: ComposeAcademicAnswerSkill

### backend/app/services/community_agent/skills/contracts/external_tavily_search
- `backend/app/services/community_agent/skills/contracts/external_tavily_search/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/services/community_agent/skills/contracts/external_tavily_search/executor.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉悎绾︽垨鎵ц鍣ㄦ枃浠躲€?| 椤跺眰绗﹀彿: ExternalTavilySearchSkill

### backend/app/services/community_agent/skills/contracts/import_arxiv_paper
- `backend/app/services/community_agent/skills/contracts/import_arxiv_paper/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/services/community_agent/skills/contracts/import_arxiv_paper/executor.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉悎绾︽垨鎵ц鍣ㄦ枃浠躲€?| 椤跺眰绗﹀彿: ImportArxivPaperSkill

### backend/app/services/community_agent/skills/contracts/read_paper_context
- `backend/app/services/community_agent/skills/contracts/read_paper_context/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/services/community_agent/skills/contracts/read_paper_context/executor.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉悎绾︽垨鎵ц鍣ㄦ枃浠躲€?| 椤跺眰绗﹀彿: ReadPaperContextSkill

### backend/app/services/community_agent/skills/contracts/start_translation_kernel
- `backend/app/services/community_agent/skills/contracts/start_translation_kernel/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/services/community_agent/skills/contracts/start_translation_kernel/executor.py`: 绀惧尯鏅鸿兘浣撴妧鑳藉悎绾︽垨鎵ц鍣ㄦ枃浠躲€?| 椤跺眰绗﹀彿: StartTranslationKernelSkill

### backend/app/services/community_agent/tools
- `backend/app/services/community_agent/tools/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?| 椤跺眰绗﹀彿: ToolRegistry, instantiate_tools
- `backend/app/services/community_agent/tools/base.py`: 绀惧尯鏅鸿兘浣撳伐鍏峰疄鐜版枃浠躲€?| 椤跺眰绗﹀彿: CommunityAgentTool
- `backend/app/services/community_agent/tools/community_search.py`: 绀惧尯鏅鸿兘浣撳伐鍏峰疄鐜版枃浠躲€?| 椤跺眰绗﹀彿: CommunitySearchPapersTool
- `backend/app/services/community_agent/tools/external_tavily_search.py`: 绀惧尯鏅鸿兘浣撳伐鍏峰疄鐜版枃浠躲€?| 椤跺眰绗﹀彿: ExternalTavilySearchTool
- `backend/app/services/community_agent/tools/import_arxiv_paper.py`: 绀惧尯鏅鸿兘浣撳伐鍏峰疄鐜版枃浠躲€?| 椤跺眰绗﹀彿: ImportArxivPaperTool
- `backend/app/services/community_agent/tools/read_paper_context.py`: 绀惧尯鏅鸿兘浣撳伐鍏峰疄鐜版枃浠躲€?| 椤跺眰绗﹀彿: ReadPaperContextTool
- `backend/app/services/community_agent/tools/start_translation_kernel.py`: 绀惧尯鏅鸿兘浣撳伐鍏峰疄鐜版枃浠躲€?| 椤跺眰绗﹀彿: StartTranslationKernelTool

### backend/app/services/latex
- `backend/app/services/latex/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/services/latex/compiler.py`: LaTeX 缂栬瘧鏈嶅姟锛岃礋璐ｅ垎闃舵缂栬瘧銆侀┍鍔ㄥ垏鎹€佹棩蹇楁敹闆嗕笌鏅鸿兘鍥為€€銆?| 椤跺眰绗﹀彿: LatexExecutor, HostLatexExecutor, DockerLatexExecutor, CompilationResult, LaTeXCompiler, _get_latex_executor, _has_real_bib_files, _iter_manual_bbl_inputs, _has_bibliography_driver, _prepare_bibliography_inputs, _validate_generated_pdf_structure
- `backend/app/services/latex/parser.py`: LaTeX 瑙ｆ瀽鏈嶅姟锛岃礋璐ｅ垏鍒嗙珷鑺傘€佺幆澧冦€佸崰浣嶇涓庡彲缈昏瘧鐗囨銆?| 椤跺眰绗﹀彿: LatexParser
- `backend/app/services/latex/prompts.py`: LaTeX 澶勭悊閾捐矾鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: init_prompts, create_prompts
- `backend/app/services/latex/reconstruct.py`: LaTeX 閲嶅缓鏈嶅姟锛屽皢缈昏瘧鍚庣殑鐗囨鎸夊師缁撴瀯鍥炲～骞堕噸缁勮緭鍑恒€?| 椤跺眰绗﹀彿: LatexConstructor
- `backend/app/services/latex/sanitizer.py`: LaTeX 娓呮礂鍣紝棰勫鐞嗗嵄闄╂垨涓嶅吋瀹瑰懡浠ゅ苟淇鏂囨。椹卞姩缁嗚妭銆?| 椤跺眰绗﹀彿: apply_precompile_sanitization, _find_ghostscript, extract_failed_pdf_paths, check_pdf_syntax_error, sanitize_pdf, patch_tex_includegraphics
- `backend/app/services/latex/token_estimator.py`: LaTeX 澶勭悊閾捐矾鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: _formula_digest, estimate_tokens_v1, safe_limit_v1
- `backend/app/services/latex/utils.py`: LaTeX 澶勭悊閾捐矾鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: ArxivDownloadError, ArxivNoSourceAvailableError, ArxivNetworkFailureError, ArxivArchiveCorruptedError, DownloadProgressCallback, get_pattern_command_full, extract_compressed_files, get_profect_dirs, has_appendix, remove_appendix_content, extract_latex_nodes


### backend/app/utils
- `backend/app/utils/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/utils/async_blocking.py`: 閫氱敤宸ュ叿鏂囦欢銆?| 椤跺眰绗﹀彿: _wrappers_enabled, _db_mode, run_blocking, run_db_blocking

### backend/migrations
- `backend/migrations/20260316_add_task_detail_metadata.sql`: 鏁版嵁搴撹縼绉昏剼鏈細20260316 add task detail metadata銆?| SQL 鐗囨: ALTER TABLE public.translation_tasks ADD COLUMN IF NOT EXISTS detail_code TEXT; ALTER TABLE public.translation_tasks ADD
- `backend/migrations/20260318_add_increment_paper_download_count_fn.sql`: 鏁版嵁搴撹縼绉昏剼鏈細20260318 add increment paper download count fn銆?| SQL 鐗囨: create or replace function public.increment_paper_download_count(target_paper_id uuid) returns table (download_count int
- `backend/migrations/20260318_add_increment_paper_view_count_fn.sql`: 鏁版嵁搴撹縼绉昏剼鏈細20260318 add increment paper view count fn銆?| SQL 鐗囨: create or replace function public.increment_paper_view_count(target_paper_id uuid) returns table (view_count integer) la
- `backend/migrations/20260318_add_paper_community_admission_fields.sql`: 鏁版嵁搴撹縼绉昏剼鏈細20260318 add paper community admission fields銆?| SQL 鐗囨: alter table public.papers add column if not exists community_status text not null default 'user_fallback' check (communi
- `backend/migrations/20260318_create_interaction_tables.sql`: 鏁版嵁搴撹縼绉昏剼鏈細20260318 create interaction tables銆?| SQL 鐗囨: create table if not exists public.paper_likes ( paper_id uuid not null references public.papers (id) on delete cascade, 
- `backend/migrations/20260318_create_moderation_tables.sql`: 鏁版嵁搴撹縼绉昏剼鏈細20260318 create moderation tables銆?| SQL 鐗囨: create table if not exists public.reports ( id uuid primary key default gen_random_uuid(), target_type text not null che
- `backend/migrations/20260318_create_papers_and_assets.sql`: 鏁版嵁搴撹縼绉昏剼鏈細20260318 create papers and assets銆?| SQL 鐗囨: create table if not exists public.papers ( id uuid primary key default gen_random_uuid(), source text not null check (so
- `backend/migrations/20260318_refine_day1_policy_and_index_guards.sql`: 鏁版嵁搴撹縼绉昏剼鏈細20260318 refine day1 policy and index guards銆?| SQL 鐗囨: create index if not exists comments_parent_id_idx on public.comments (parent_id) where parent_id is not null; create ind
- `backend/migrations/20260323_create_community_agent_conversations.sql`: 鏁版嵁搴撹縼绉昏剼鏈細20260323 create community agent conversations銆?| SQL 鐗囨: create table if not exists public.community_agent_conversations ( user_id uuid not null default auth.uid() references au
- `backend/migrations/20260326_create_community_content_pool_foundation.sql`: 鏁版嵁搴撹縼绉昏剼鏈細20260326 create community content pool foundation銆?| SQL 鐗囨: create table if not exists public.community_content_pool_candidates ( id uuid primary key default gen_random_uuid(), arx

### backend/migrations_mysql
- `backend/migrations_mysql/20260409_0001_local_auth_mysql.sql`: MySQL 杩佺Щ鑴氭湰锛歭ocal auth mysql銆?| SQL 鐗囨: create table if not exists users ( id varchar(64) not null, external_provider varchar(32) not null, external_user_id var
- `backend/migrations_mysql/20260411_0002_community_admin_curation_flow.sql`: MySQL 杩佺Щ鑴氭湰锛歝ommunity admin curation flow銆?| SQL 鐗囨: create table if not exists community_structured_insights ( paper_id varchar(64) not null, section_key varchar(64) not nu
- `backend/migrations_mysql/20260411_0003_expand_paper_asset_id_columns.sql`: MySQL 杩佺Щ鑴氭湰锛歟xpand paper asset id columns銆?| SQL 鐗囨: alter table papers modify column trans_latest_asset_pdf_id varchar(255) null, modify column community_selected_asset_id 
- `backend/migrations_mysql/20260411_0004_add_content_column_to_community_structured_insights.sql`: MySQL 杩佺Щ鑴氭湰锛歛dd content column to community structured insights銆?| SQL 鐗囨: set @community_structured_insights_has_content := ( select count(*) from information_schema.columns where table_schema =
- `backend/migrations_mysql/20260412_0005_add_community_similar_recommendations.sql`: MySQL 杩佺Щ鑴氭湰锛歛dd community similar recommendations銆?| SQL 鐗囨: create table if not exists community_similar_recommendations ( paper_id varchar(64) not null, position int not null, arx
- `backend/migrations_mysql/20260419_0006_admin_curation_retention_fields.sql`: MySQL 杩佺Щ鑴氭湰锛氫负绠＄悊鍛樼瓥灞曚换鍔¤ˉ鍏呭け璐ョ暀鐥曞瓧娈典笌宸插彂甯冭鏂囧叧鑱斿瓧娈点€?| SQL 鐗囨: alter table community_curation_jobs add column terminal_task_status varchar(32) null after status

 - `backend/migrations_mysql/20260423_0010_add_login_identifier_to_users.sql`: MySQL 迁移脚本，为 `users` 表补充 `login_identifier` 字段并兼容重复执行。| SQL 片段: alter table users add column login_identifier varchar(255) null after external_user_id

 - `backend/migrations_mysql/20260507_0011_daily_translation_quotas.sql`: MySQL 迁移脚本，新增 `user_daily_quotas` 与 `niutrans_balance_snapshots`，用于每日本地 LaTeX 翻译额度和 NiuTrans PDF 直译积分安全快照。

### backend/scripts
- `backend/scripts/apply_mysql_migrations.py`: 杩愮淮鎴栬縼绉昏剼鏈€?| 椤跺眰绗﹀彿: _load_sql_files, apply_migrations, main
- `backend/scripts/audit_pipeline_regression.py`: 杩愮淮鎴栬縼绉昏剼鏈€?| 椤跺眰绗﹀彿: _load_json, _find_main_tex, _placeholder_only_chunks, _count_status, _invariant_fallback_sections, _status_sections
- `backend/scripts/bootstrap_local_community_papers.py`: 杩愮淮鎴栬縼绉昏剼鏈€?| 椤跺眰绗﹀彿: LocalPaperCandidate, _iso_utc_from_path, _iter_candidate_dirs, _match_arxiv_id, _infer_arxiv_id, _find_preview_html, _find_translated_pdf
- `backend/scripts/extract_core_pool_ids.py`: 浠?`core_pool/latest.md` 鎻愬彇 arXiv ID 椤哄簭鍒楄〃骞跺啓鍏ュ悓绾?`id.md` 鐨勮緟鍔╄剼鏈€?| 椤跺眰绗﹀彿: ID_LINE_PATTERN, DEFAULT_INPUT_PATH, extract_arxiv_ids, write_id_file, build_argument_parser, main
- `backend/scripts/grant_local_admin.py`: 杩愮淮鎴栬縼绉昏剼鏈€?| 椤跺眰绗﹀彿: _utc_now_naive, _fetch_target_user, grant_local_admin, main
- `backend/scripts/import_source_to_mysql.py`: 杩愮淮鎴栬縼绉昏剼鏈€?| 椤跺眰绗﹀彿: _utc_now, _first, _as_str, _as_bool, _as_int, _as_timestamp
- `backend/scripts/mysql_script_connection.py`: 杩愮淮鎴栬縼绉昏剼鏈€?| 椤跺眰绗﹀彿: resolve_mysql_script_config, describe_mysql_script_target, mysql_script_connection
- `backend/scripts/sync_core_pool_complete_from_cos.py`: 从后端 `papers` 与 `paper_assets` 记录发现完整的 local-disk 或 object-storage 论文资产集合，按已记录路径同步到 `data/community_papers/<arxiv_id>/...`，并支持本地发起服务器同步、打包拉回、清理服务器 arXiv ID 输出目录。| 顶层符号: ARXIV_ID_PATTERN, DEFAULT_COMPLETE_PATH, DEFAULT_DESTINATION_ROOT, parse_complete_arxiv_ids, read_complete_arxiv_ids, load_latest_backend_asset_records, discover_complete_asset_candidates, write_complete_arxiv_ids, parse_remote_server_credentials, build_remote_sync_command, safe_extract_tar, remote_pull_core_pool_complete_assets, sync_core_pool_complete_assets, build_argument_parser, main
## Recent Responsibility Updates (2026-04-19)

- `backend/app/services/task_manager.py`: 浠诲姟绠＄悊鍣ㄧ幇宸茶礋璐ｆ墽琛屽皾璇曠紪鍙枫€佸悓灏濊瘯缁堟€佸崟璋冧繚鎶ゃ€佹寔涔呭眰寮傚父鐘舵€佸璐︼紝浠ュ強闃熷垪绾ф湭鎹曡幏寮傚父鐨勭粓鎬佸皝鍙ｏ紝閬垮厤鐘舵€佹紓绉婚暱鏈熷崰鐢ㄥ苟鍙戞Ы浣嶃€?
- `backend/app/api/routes/translate.py`: 缈昏瘧鎵ц鍏ュ彛鐜板凡鍦ㄦ瘡娆¤繍琛屽墠寮€鍚柊鐨?attempt锛屽苟灏嗚繘搴︿笌缁堟€佹洿鏂扮粦瀹氬埌璇?attempt锛涘悓鏃跺吋瀹规棫娴嬭瘯妗╃己灏?attempt 鎺ュ彛鎴栨棫鐗?progress callback 绛惧悕鐨勫満鏅€?
- `backend/app/services/paper_service.py`: 绠＄悊鍛樼瓥灞曠瓑寰呴€昏緫鐜板凡澧炲姞鈥滄寔涔呭眰鐭秴鏃?+ 鐔旀柇閫€閬库€濆厹搴曪紝骞跺湪鍙戠幇涓嶅彲鑳界姸鎬佹椂鍚堟垚澶辫触缁堟€侊紝閬垮厤鏁版嵁搴撴姈鍔ㄥ弽鍚戝崱姝荤鐞嗕换鍔°€?
- `backend/app/services/paper_service.py`: 绀惧尯璁烘枃鍏紑閾捐矾鐜板凡闃绘缂哄け鏍囬/浣滆€呯殑 arXiv 绛栧睍缁撴灉鍙戝竷锛屽苟浼氬湪棣栭〉鍒楄〃璇诲彇鏃惰嚜鍔ㄤ慨澶嶄粛甯﹀崰浣嶆爣棰樼殑鍘嗗彶璁烘枃鍏冩暟鎹€?
- `backend/app/api/routes/papers.py`: 绠＄悊鍛樼瓥灞曞巻鍙叉帴鍙ｇ幇宸茶礋璐ｈ鑼冨寲 `all` / `processing` 绛涢€夎涔夛紝骞舵彁渚涢€変腑浠诲姟鐨勬壒閲忕‖鍒犻櫎鍏ュ彛銆?
- `backend/app/repositories/community_paper_repository.py`: 绛栧睍浠诲姟鍒楄〃鏌ヨ鐜板凡鏀寔灏?`processing` 鎵╁睍鍖归厤鍒?`processing`銆乣translating`銆乣publishing` 涓夌被鍦ㄩ€旂姸鎬併€?

## Recent Responsibility Updates

- `backend/app/api/routes/papers.py`: 绠＄悊鍛樼瓥灞曞巻鍙叉帴鍙ｇ幇宸茶礋璐ｈ鑼冨寲 `all` / `processing` 绛涢€夎涔夛紝骞舵彁渚涢€変腑浠诲姟鎵归噺纭垹闄ゅ叆鍙ｃ€?
- `backend/app/services/paper_service.py`: 绠＄悊鍛樼瓥灞曞巻鍙叉湇鍔＄幇宸茶礋璐ｅ鐞嗕腑鐘舵€佽仛鍚堟煡璇笌鎵归噺纭垹闄ょ紪鎺掞紝骞惰繑鍥為€愪换鍔℃垚鍔?澶辫触缁撴灉銆?
- `backend/app/repositories/community_paper_repository.py`: 绛栧睍浠诲姟鍒楄〃鏌ヨ鐜板凡鏀寔灏?`processing` 鎵╁睍鍖归厤鍒?`processing`銆乣translating`銆乣publishing` 涓夌被鍦ㄩ€旂姸鎬併€?

## Recent Responsibility Updates (2026-04-20)

- `backend/app/api/routes/papers.py`: 社区论文列表与卡片相关路由现已提供 `source-download` 入口，并在 paper summary 中暴露 `arxiv_url` 与 `github_url` 等研究动作元数据。
- `backend/app/api/routes/download.py`: 源文 PDF 预览逻辑现已抽取为可复用的 `_serve_source_pdf`，同时支持 inline 预览与 attachment 下载两种返回方式。
- `backend/app/services/paper_service.py`: 社区论文汇总服务现已负责从 preview HTML 中提取 GitHub 外部链接，为首页论文卡片的直达研究动作提供数据。
## Recent Responsibility Updates (2026-04-20 Admin Reset)

- `backend/app/services/paper_service.py`: 管理员策展任务现已区分 `admission` / `execution` 两段超时，失败时会写入 `terminal_reason` 与 `timeout_reason`，并在管理员入库链路默认关闭术语表生成。
- `backend/app/services/task_manager.py`: 任务取消现已同时写入终态、触发运行时取消，并尝试终止活跃编译进程，避免超时或预算取消后残留 `processing`。
- `backend/app/api/routes/task.py`: 任务状态查询与 SSE 推送现已返回稳定的 `terminal_reason`。
- `backend/app/api/routes/papers.py`: 管理员策展历史接口现已返回 `terminal_reason` 与 `timeout_reason`。
- `backend/app/repositories/community_paper_repository.py`: 策展任务仓储现已持久化 `terminal_reason` 与 `timeout_reason` 字段。
- `backend/app/services/agents/translator_agent.py`: 翻译代理现已收紧 nested rescue 的 per-part / per-task 预算，并将外部 API 致命失败视为外层重试跳过信号。
- `backend/app/services/agents/langgraph_orchestrator.py`: 外层 validate/retranslate 轮次现已收紧到 `2` 轮。
- `backend/migrations_mysql/20260421_0007_admin_curation_terminal_reasons.sql`: 为 `community_curation_jobs` 增补 `terminal_reason` 与 `timeout_reason` 列。

- ackend/app/services/paper_service.py: 管理员 arXiv 重复入库现已在提交前枚举同 rxiv_id 的旧 curation job，先取消仍在运行的策展协程并执行全流程硬删除，再创建新的 curation job 与全新 paper_id。
- ackend/app/repositories/community_paper_repository.py: 社区策展仓储现已提供按 rxiv_id 顺序枚举 curation jobs 的查询，供重复入库预删除编排复用。
- `backend/scripts/backfill_translated_pdf_delivery.py`: 社区译文 PDF 交付回填脚本，现已负责批量将现有论文的译文 PDF 升级为已完成首页空白裁剪的最终交付资产。
- `backend/app/services/agents/translator_agent.py`: 翻译代理现已补充 task 级补救 LLM 调用预算、`HARD_FREEZE_PROTOCOL_VIOLATION` 预算，以及预算耗尽后的稳定 fallback reason，确保补救调用不会无限放大。
- `backend/app/services/agents/langgraph_orchestrator.py`: 编排层现已按 `2` 次 validate 重翻预算执行，并在补救预算耗尽时停止继续进入 repair 环，直接转入有界降级路径。

## Recent Responsibility Updates (2026-04-21 Community Engagement)

## Recent Responsibility Updates (2026-04-22 Feed Rebuild Safety)
## Recent Responsibility Updates (2026-04-23 Local Auth Identifier)

- `backend/scripts/sync_core_pool_complete_from_cos.py`：从后端 `papers` 与 `paper_assets` 记录发现完整 local-disk 或 object-storage 资产集合，按已记录路径下载或复制，避免依赖 COS 列桶权限；新增 `--remote-pull-and-clean`，可在本地触发服务器容器同步、下载 arXiv ID 目录归档并清理服务器输出目录。顶层符号新增 `load_latest_backend_asset_records`、`discover_complete_asset_candidates`、`write_complete_arxiv_ids`、`remote_pull_core_pool_complete_assets`。

- `backend/app/api/routes/auth.py`: 登录与会话自举响应现在显式返回 `login_identifier`，供前端展示真实登录方式而不是内部用户 ID。
- `backend/app/services/auth_service.py`: 本地鉴权服务现在会持久化用户本次输入的登录标识，并在登录与验会话时统一回传。
- `backend/app/repositories/auth_repository.py`: 鉴权仓储现在负责读写 `users.login_identifier`，确保邮箱缺失时仍可恢复手机号或其他登录标识。
- `backend/migrations_mysql/20260423_0010_add_login_identifier_to_users.sql`: 为 `users` 表新增 `login_identifier` 列，并兼容重复执行场景。

- `backend/app/core/config.py`: 新增公开 feed 周期重建间隔配置，统一控制 Worker 侧 Redis 排名修复任务是否启用及其执行频率。
- `backend/app/services/paper_service.py`: 公开 feed 索引全量重建现已改为写入临时 ZSET 后再通过 Redis `RENAME` 原子替换正式键，并在重建后统一清理匿名列表响应缓存。
- `backend/app/main.py`: Worker 启动流程现已挂载公开 feed Redis 索引的周期修复协程，复用现有后台运行位而不额外引入 MQ 或独立 Cron 形态。

- `backend/migrations_mysql/20260421_0008_community_paper_engagement.sql`: 新增社区论文收藏文件夹、文件夹论文关联、按天去重浏览记录三组持久化表，并补齐唯一约束与查询索引。
- `backend/app/api/routes/papers.py`: 社区论文路由现已提供收藏文件夹管理、论文收藏夹同步、点赞切换与真实浏览计数接口，并支持匿名浏览标识请求头与 cookie 回写。
- `backend/app/services/paper_service.py`: 社区论文服务现已负责收藏夹关系同步、派生收藏态聚合、点赞一人一票切换、UTC+8 自然日浏览去重以及最新/浏览量/点赞量排序编排。
- `backend/app/repositories/community_paper_repository.py`: 社区论文仓储现已持久化收藏文件夹、文件夹论文关联、点赞切换、浏览去重记录与聚合计数维护，供首页列表、详情页与收藏页共享。
- `backend/app/core/config.py`: 新增社区公开 feed 的 Redis 配置项，统一声明共享排序索引、响应缓存 TTL 与重建锁参数，供 Web/Worker 进程复用。
- `backend/app/services/paper_service.py`: 社区论文服务现已接管公开 feed 的 Redis 共享排序索引、匿名响应缓存、按 paper 单点刷新与 MySQL 元数据回源组装，搜索请求仍直接走数据库路径。
- `backend/app/repositories/community_paper_repository.py`: 社区论文公开列表查询已移除 `community_status` 的 official-first 排序假设，统一按发布时间/浏览量/点赞量与发布时间回退规则返回稳定顺序。
