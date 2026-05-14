# Implementation Tasks

## 1. OpenSpec Alignment
- [x] 1.1 Remove stale Supabase/pgvector assumptions from this change record.
- [x] 1.2 Validate the refreshed change with `openspec validate implement-rag-terminology --strict --no-interactive`.

## 2. Storage And Review Schema
- [x] 2.1 Add MySQL migration for terminology terms, review fields, source metadata (including `provenance` JSON field), status, and keyword indexes.
  - `backend/migrations_mysql/20260513_0012_rag_terminology.sql` — 3 张表：`terminology_terms`, `terminology_evaluation_runs`, `terminology_match_log`
- [x] 2.2 Add optional embedding metadata fields for Milvus collection name, vector primary key, embedding model, and embedding status.
  - 包含在 `terminology_terms` 表：`embedding_model`, `embedding_status`(none/pending/ready/failed), `vector_collection`, `vector_term_id`
- [x] 2.3 Implement repository methods for term creation, search, approval, rejection, provenance lookup, and embedding sync state.
  - `backend/app/repositories/terminology_repository.py` — `TerminologyRepository` 提供 insert / batch insert、search、approve / reject、set_embedding_status、search_approved_terms 等完整方法

## 3. Vector Store And Embeddings
- [x] 3.1 Add Milvus configuration and connection wrapper with health/fallback behavior.
  - `backend/app/services/rag/vector_retriever.py` — `VectorRetriever` 类，支持 `ensure_collection`, `health_check`, 连接失败降级
  - 配置项在 `backend/app/core/config.py`：`RAG_TERMINOLOGY_MILVUS_URI`, `RAG_TERMINOLOGY_MILVUS_COLLECTION`
- [x] 3.2 Implement embedding client using configured provider/model.
  - `backend/app/services/rag/embedding_client.py` — `EmbeddingClient` 类，支持 `encode()`, `compute_similarity()`
  - 默认模型：`sentence-transformers/all-MiniLM-L6-v2`
- [x] 3.3 Upsert approved terms into Milvus and keep pending/rejected terms out of vector retrieval.
  - `terminology_service.py` 中审核通过时调用 `embedding_client.encode()` + `vector_retriever.upsert_term()`
  - Milvus search 仅返回已审核术语（来源为 `terminology_repository.get_all_approved_terms()`）
- [x] 3.4 Add retry-safe handling for approved terms whose embedding or Milvus upsert fails.
  - `embedding_status` 字段标记 `pending` / `ready` / `failed`，失败时仍可通过 BM25 关键词检索使用

## 4. RAG Retrieval Pipeline
- [x] 4.1 Implement query transformation from LaTeX/plain text chunks to terminology queries.
  - `pipeline.py` — `_transform_query()` 方法，提取纯文本作为查询
- [x] 4.2 **Implement BM25 keyword retrieval**: build in-memory BM25 index from approved terms using `rank_bm25`; score and rank candidates on each retrieval.
  - `bm25_retriever.py` — `Bm25Retriever` 类，`build_index()`, `search()`, `refresh()`
- [x] 4.3 Implement MySQL exact/prefix retrieval as complement to BM25.
  - `terminology_repository.py` — `search_approved_terms()` 支持短语匹配和前缀匹配
- [x] 4.4 Implement Milvus vector retrieval for approved terms.
  - `vector_retriever.py` — `search()` 执行 COSINE 相似度搜索
- [x] 4.5 Merge and deduplicate BM25, MySQL exact, and vector candidates with source/user priority.
  - `pipeline.py` — `_merge_candidates()` 按 term id 去重，用户/导入术语优先级高于系统术语
- [x] 4.6 **Implement Cross-Encoder reranking**: score (chunk_text, candidate_term) pairs using `sentence-transformers` cross-encoder model; select Top-N.
  - `cross_encoder_reranker.py` — `CrossEncoderReranker` 类，`rerank()` 方法
  - 默认模型：`cross-encoder/ms-marco-MiniLM-L-6-v2`
- [x] 4.7 Add graceful fallback: Cross-Encoder → BM25+vector score merge → keyword-only → skip RAG.
  - `pipeline.py` — `_safe_bm25_search()`, `_safe_vector_search()`, `_safe_repo_search()` 各自 try/except
  - Cross-Encoder 不可用时降级到 BM25+向量得分合并
- [x] 4.8 Format selected terms into a bounded `<Glossary>` prompt block.
  - `glossary_formatter.py` — `format_glossary_block()`, `estimate_token_count()`, `truncate_glossary()`

## 5. Multi-Source Knowledge Base Ingestion
- [x] 5.1 **CSV import**: implement CSV parser with row validation, duplicate detection, and batch insert as `source_type=imported`.
  - `knowledge_base/csv_importer.py` — `parse_csv_content()`, `validate_row()`, `ImporterResult`
- [x] 5.2 **BibTeX parsing**: implement BibTeX file parser to extract citation entries; use LLM to suggest term candidates with provenance metadata.
  - `knowledge_base/bibtex_parser.py` — `parse_bibtex_content()`, `extract_term_candidates()`, `format_provenance()`
- [x] 5.3 Add POST `/api/terminology/upload` endpoint accepting CSV and BibTeX files with size/content-type validation.
  - `backend/app/api/routes/terminology.py` — `POST /api/terminology/upload`
- [x] 5.4 Store all ingested candidates in MySQL with `status=pending_review` and route them through the admin review workflow.
  - 导入的术语 `source_type=imported / auto_extracted`，`status=pending_review`，走同一审核流程

## 6. Translation Tool Integration
- [x] 6.1 Add an explicit opt-in translation-tool configuration flag for RAG terminology.
  - `AdvancedConfig.enable_rag_terminology` 字段（`models/config_models.py:143`）
  - 前端 `AdvancedConfig.tsx:198-204` 有 ToggleSwitch 开关
- [x] 6.2 Ensure default `origin_cli_parity` tasks remain byte/behavior compatible when the flag is absent or false.
  - `translation_hook.should_run_rag()` 默认返回 `False`，不影响默认翻译路径
- [ ] 6.3 Inject retrieved glossary terms only for opted-in translation-tool executions.
  - **🔴 未完成**：`translation_hook.py` 的 `build_glossary_for_chunk()` + `inject_glossary_into_prompt()` 已实现，但翻译 agent（`translator_agent.py`）**从未调用它们**。
  - 现有 agent 使用自身的 `self.term_dict`（旧版 LLM 抽取/CSV 导入），不经过 RAG 管线检索。需要将 `RagTerminologyPipeline.run_pipeline()` 的输出喂给 agent 的 `self.term_dict` 或 system prompt。
- [ ] 6.4 Persist matched/injected term metadata for UI display and evaluation.
  - **🔴 未完成**：`run_post_translation_extraction()` 和 `record_match_log()` 已实现，但翻译 agent **从未调用它们**。

## 7. Admin Review
- [x] 7.1 Extract source-target terminology pairs after opted-in translations (auto-extraction).
  - `knowledge_base/extractor.py` — `extract_terms_from_translation()` 自动抽取大写短语 + 引号术语
- [x] 7.2 Store extracted pairs in MySQL as `pending_review`.
  - `terminology_service.extract_and_store()` → `repository.insert_term()` 带 `status=pending_review`
- [x] 7.3 Add admin endpoints to list, approve, reject, and inspect terminology candidates.
  - 路由：`GET /terms/pending` `PUT /terms/{id}/approve` `PUT /terms/{id}/reject` `GET /terms`
- [x] 7.4 On approval, refresh BM25 index, generate embeddings, and upsert approved terms into Milvus.
  - `terminology_service.approve_term()` 中依次执行：`refresh_bm25_index()` + `build_vector_index()`

## 8. Frontend
- [x] 8.1 Add translation-tool UI control for optional RAG terminology.
  - `AdvancedConfig.tsx:198-204` — ToggleSwitch 绑定 `enable_rag_terminology`
  - **注意**：开关存在但后端未接线，打开后实际无效果
- [x] 8.2 Display matched/injected terms for completed RAG-enabled tasks.
  - `TerminologyMatchLog.tsx` — 匹配日志展示组件
  - 调用 `GET /api/terminology/terms/task/{task_id}/match-logs`
- [x] 8.3 Add or extend admin UI for pending terminology review.
  - `TerminologyReviewPanel.tsx` — 审核面板（列表、通过/拒绝、CSV/BibTeX 拖拽上传）
  - `RagTerminologyAdminPage` — 管理后台页面
  - 国际化 key 完整：`zh/common.json` 和 `en/common.json`

## 9. Evaluation And Artifacts
- [x] 9.1 **BLEU/ROUGE evaluation script**: implement script that computes sentence-level and document-level BLEU/ROUGE scores comparing baseline vs RAG-enabled outputs on the same source paper.
  - `evaluation/bleu_rouge.py` — `BleuRougeEvaluator` 类，支持 `compute_bleu()`, `compute_rouge()`, `evaluate_pair()`, `evaluate_corpus()`
- [x] 9.2 **Terminology consistency metric**: implement metric measuring the proportion of predefined key terms translated identically across all occurrences; per-term and aggregate rates.
  - `evaluation/term_consistency.py` — `TermConsistencyEvaluator`，支持 `evaluate_output()`, `compare_runs()`
- [x] 9.3 **Evaluation report export**: generate structured JSON/CSV report with BLEU, ROUGE, and terminology consistency scores.
  - `evaluation/run_evaluation.py` — `run_full_evaluation()`, `generate_report()`, 支持 single-paper 和 corpus 评估模式
- [x] 9.4 Prepare graduation-design evaluation artifacts: matched-term logs, score deltas, and qualitative comparison notes.
  - 报告结构包含 metadata、inputs、bleu_rouge（含 delta）、terminology_consistency（含 per-term 和 aggregate）

## 10. Tests
- [ ] 10.1 Add unit tests for repository status transitions and permission boundaries.
  - **🔴 未完成**：无 `test_terminology_repository.py` 或类似文件
- [ ] 10.2 Add unit tests for BM25 index build, scoring, and refresh behavior.
  - **🔴 未完成**：无 `test_bm25_retriever.py` 或类似文件
- [ ] 10.3 Add unit tests for hybrid retrieval merge/deduplication and fallback behavior.
  - **🔴 未完成**：无 `test_pipeline.py` 或类似文件
- [ ] 10.4 Add mocked tests for embedding, Milvus, Cross-Encoder reranking clients.
  - **🔴 未完成**：无对应测试文件
- [ ] 10.5 Add integration coverage for an opted-in translation-tool run that records matched terms.
  - **🔴 未完成**：无集成测试

---

## 11. ❗ 额外缺失项（超出原 tasks.md 范围）

以下缺失项在原始 tasks.md 中未明确列出，但根据 spec/design 和实际需求应当存在：

### 11.1 预置官方术语种子库
- [ ] 11.1.1 将 `backend/evaluation/default_key_terms.json`（含 computer_science, physics 领域术语）作为种子数据导入 RAG 术语库
- [ ] 11.1.2 在 `main.py` 的 `startup_event()` 中添加首次运行时初始化官方术语的逻辑（检查表是否为空，若空则自动插入 `source_type=system` 的预置术语）
- [ ] 11.1.3 官方术语标记为 `source_type=system`，`status=approved`，开箱即用
- [ ] 11.1.4 支持通过管理接口更新/扩充官方术语库

### 11.2 术语管理增强功能
- [ ] 11.2.1 **创建术语 API**：`POST /api/terminology/terms` — 管理员可手动创建新术语（不经过上传流程）
- [ ] 11.2.2 **编辑术语 API**：`PUT /api/terminology/terms/{id}` — 管理员可编辑已有术语
- [ ] 11.2.3 **删除术语 API**：`DELETE /api/terminology/terms/{id}` — 管理员可删除术语
- [ ] 11.2.4 **批量操作 API**：`POST /api/terminology/terms/batch` — 批量批准/拒绝/删除
- [ ] 11.2.5 **前端术语浏览页面**：完整的术语库页面（非仅待审核），支持按状态/领域/语言对筛选、分页浏览全部术语
- [ ] 11.2.6 **前端创建/编辑术语**：管理员可从 UI 直接创建和编辑术语
- [ ] 11.2.7 **前端领域筛选控件**：在术语列表和审核页面添加 domain/source_lang 筛选下拉框

### 11.3 用户个人术语库
- [ ] 11.3.1 **用户个人术语表**：`/workspace/glossary` 页面从占位符改造为实际功能页面
- [ ] 11.3.2 **用户级别的数据隔离**：Repository 查询方法增加 `owner_user_id` 筛选，用户只能看到自己的术语
- [ ] 11.3.3 **用户个人上传入口**：用户可在自己的工作区上传 CSV/BibTeX 导入个人术语
- [ ] 11.3.4 用户术语 `source_type=user`，仅自己可见；可分享给管理员审核成为共享术语

### 11.4 领域管理
- [ ] 11.4.1 建立预定义领域枚举（computer_science, physics, mathematics, biology, medicine, engineering 等）
- [ ] 11.4.2 每个领域配套预置术语集（作为 seed data）
- [ ] 11.4.3 按领域浏览/管理术语的界面
- [ ] 11.4.4 翻译任务中按论文领域自动选择术语库

### 11.5 多语料前端入口
- [ ] 11.5.1 **工具中心入口**：`tools-hub` 中为 RAG 术语库添加独立的非管理员入口（目前仅在 admin 链接中）
- [ ] 11.5.2 **独立术语库页面**：从审核面板中拆出独立的"术语库"浏览页面
- [ ] 11.5.3 **上传功能独立化**：上传界面从审核面板标签页升级为独立页面或对话框
- [ ] 11.5.4 **多语料切换**：支持在多个术语库/领域集合之间切换（个人库 vs 官方库 vs 共享库）

---

## 状态汇总

| 类别 | 总计 | 已完成 | 未完成 |
|------|------|--------|--------|
| 1-5. 核心功能 | 22 | 22 | 0 |
| 6. 翻译管线集成 | 4 | 2 | **2 🔴 P0** |
| 7. 管理审核 | 4 | 4 | 0 |
| 8. 前端 | 3 | 3 | 0 |
| 9. 评估 | 4 | 4 | 0 |
| 10. 测试 | 5 | 0 | **5 🔴 P1** |
| 11. 额外缺失 | 20 | 0 | **20 🔴 P0-P3** |
| **合计** | **62** | **35 (56%)** | **27 (44%)** |

### 优先级建议

| 优先级 | 项数 | 说明 |
|--------|------|------|
| **P0 🔥** | 2 | 翻译管线集成（6.3, 6.4）— 不接上整个功能是死的 |
| **P0 🔥** | 2 | 预置官方术语种子（11.1.1, 11.1.2）— 没数据术语库是空的 |
| **P1** | 5 | 测试覆盖（10.1-10.5） |
| **P1** | 4 | 术语管理增强（11.2.1-11.2.4 API）— 管理员手动增删改 |
| **P1** | 4 | 用户个人术语库（11.3.1-11.3.4）— 你的截图里缺少的功能 |
| **P2** | 5 | 前端 UI 增强（11.2.5-11.2.7, 11.5.1-11.5.2） |
| **P2-P3** | 5 | 领域管理、多语料、上传独立化（11.4, 11.5.3-11.5.4） |
