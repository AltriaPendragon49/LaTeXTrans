# Backend File Index

按 `backend/` 下真实物理路径整理的后端生产侧索引，方便 AI 或人工先按路径检索，再按说明定位模块。

收录范围：Python 源码、SQL 迁移脚本、运维脚本。
不收录范围：测试代码、Markdown 文档、JSON 数据、环境示例、README。

## Usage Rules

- 当需要快速查找后端文件、理解目录分布、定位模块入口时，优先先读本文件。
- 建议检索顺序：先看 `Pure Path List` 找路径，再看 `Annotated Index` 读职责和顶层符号。
- 任何新增、删除、移动、重命名后端生产侧文件的修改，都必须同步维护本文件。
- 任何会显著改变文件职责的后端改动，也应同步更新对应说明。

## Directory Map

- `backend/app/api/routes`: FastAPI 路由入口层，负责对外 API。
- `backend/app/core`: 全局配置、认证、加密、时间等核心基础设施。
- `backend/app/db`: 数据库连接与方言适配。
- `backend/app/models`: 配置模型与数据结构定义。
- `backend/app/policies`: 权限策略与授权规则。
- `backend/app/repositories`: 持久化读写仓储层。
- `backend/app/services`: 业务服务层，是后端主要实现区域。
- `backend/app/services/agents`: LaTeX 翻译代理与编排管线。
- `backend/app/services/community_agent`: 社区智能体运行时、技能与工具。
- `backend/app/services/latex`: LaTeX 解析、重建、编译、结构守卫。
- `backend/app/services/translation`: 降级、修复、结构检查等翻译兜底逻辑。
- `backend/app/utils`: 通用异步或阻塞辅助工具。
- `backend/migrations`: 主数据库迁移脚本。
- `backend/migrations_mysql`: MySQL 迁移脚本。
- `backend/scripts`: 运维、初始化、迁移与审计脚本。

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
- `backend/app/repositories/user_settings_repository.py`
- `backend/app/services/__init__.py`
- `backend/app/services/agents/__init__.py`
- `backend/app/services/agents/base_tool_agent.py`
- `backend/app/services/agents/compilation_diagnostic_node.py`
- `backend/app/services/agents/compile_runtime.py`
- `backend/app/services/agents/controlled_repair_agent.py`
- `backend/app/services/agents/coordinator_agent.py`
- `backend/app/services/agents/generator_agent.py`
- `backend/app/services/agents/langgraph_orchestrator.py`
- `backend/app/services/agents/llm_runtime.py`
- `backend/app/services/agents/llm_token_pool.py`
- `backend/app/services/agents/parser_agent.py`
- `backend/app/services/agents/pipeline_invariants.py`
- `backend/app/services/agents/pipeline_schema.py`
- `backend/app/services/agents/structure_repair_node.py`
- `backend/app/services/agents/translation_repair_agent.py`
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
- `backend/app/services/config_capture.py`
- `backend/app/services/email_service.py`
- `backend/app/services/latex/__init__.py`
- `backend/app/services/latex/compiler.py`
- `backend/app/services/latex/parser.py`
- `backend/app/services/latex/prompts.py`
- `backend/app/services/latex/reconstruct.py`
- `backend/app/services/latex/sanitizer.py`
- `backend/app/services/latex/structure_guard.py`
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
- `backend/app/services/translation/__init__.py`
- `backend/app/services/translation/downgrade_handler.py`
- `backend/app/services/translation/repair_scheduler.py`
- `backend/app/services/translation/structure_checker.py`
- `backend/app/services/translation/ultimate_downgrade.py`
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
- `backend/scripts/apply_mysql_migrations.py`
- `backend/scripts/audit_pipeline_regression.py`
- `backend/scripts/bootstrap_local_community_papers.py`
- `backend/scripts/grant_local_admin.py`
- `backend/scripts/import_source_to_mysql.py`
- `backend/scripts/mysql_script_connection.py`

## Annotated Index

### backend
- `backend/__init__.py`: 包初始化与导出文件。

### backend/app
- `backend/app/__init__.py`: 包初始化与导出文件。
- `backend/app/main.py`: FastAPI 应用入口，负责注册中间件和路由，并处理启动与关闭时的任务收尾。 | 顶层符号: _dedupe_non_empty, get_translation_task_repository, get_community_paper_repository, reset_stale_community_tasks, fail_interrupted_translation_tasks, startup_event

### backend/app/api
- `backend/app/api/__init__.py`: 包初始化与导出文件。

### backend/app/api/routes
- `backend/app/api/routes/__init__.py`: 包初始化与导出文件。
- `backend/app/api/routes/arxiv.py`: arXiv 下载与合法性校验接口。 | 顶层符号: ArxivRequest, ArxivResponse, _download_arxiv_background, download_arxiv, validate_arxiv_id
- `backend/app/api/routes/auth.py`: 认证接口，处理登录、当前用户与登出。 | 顶层符号: LoginRequest, LocalUserPayload, LoginResponse, MeResponse, get_auth_service, _error_response, login, current_user, logout
- `backend/app/api/routes/community_agent.py`: 社区智能体运行、会话与事件流接口。 | 顶层符号: CommunityAgentSkillToggles, CommunityAgentRunRequest, CommunityConversationTurnPayload, CommunityConversationRecordPayload, CommunityConversationDeleteResponse, _ensure_community_agent_authorized, _ensure_community_agent_product_enabled, create_agent_run, list_agent_conversations, upsert_agent_conversation, delete_agent_conversation
- `backend/app/api/routes/download.py`: 译文、源文件、PDF、日志与术语下载或预览接口。 | 顶层符号: _validate_pdf_with_pdfinfo, _find_translated_pdf, _candidate_output_dirs, _find_translated_pdf_in_community_library, _collect_original_pdf_candidates, _pick_best_source_pdf
- `backend/app/api/routes/history.py`: 翻译历史与任务详情接口。 | 顶层符号: TaskHistoryItem, TaskHistoryResponse, TaskDetailResponse, BatchDeleteRequest, get_translation_task_repository, _resolve_translation_task_repository, _infer_status_from_task_log, _ensure_task_authorized, _reconcile_task_snapshot, _serialize_optional_timestamp
- `backend/app/api/routes/papers.py`: 社区论文提交、列表、详情、预览、下载与管理员策展管理接口，现包含管理员任务历史查询与硬删除入口。 | 顶层符号: AssetSummary, ViewerState, PaperSummary, TaskSummary, PaperSubmitResponse, AdminCurationJobHistoryItemResponse, AdminDeleteCurationJobResponse, _ensure_paper_authorized, _ensure_local_admin, _proxy_remote_pdf_preview, _parse_single_byte_range, _serve_local_pdf_preview, _paper_thumbnail_cache_dir
- `backend/app/api/routes/settings.py`: 用户设置读取与更新接口。 | 顶层符号: UserSettingsResponse, UserSettingsUpdate, get_user_settings_repository, _resolve_user_settings_repository, _build_response, _ensure_settings_authorized, get_user_settings, update_user_settings
- `backend/app/api/routes/task.py`: 任务状态查询、删除与流式订阅接口。 | 顶层符号: TaskStatusResponse, get_translation_task_repository, _resolve_translation_task_repository, _is_guest_task, _authorize_authenticated_task, _load_authorized_task, get_task_status
- `backend/app/api/routes/translate.py`: 翻译启动、批量翻译、配置哈希与结果复用接口。 | 顶层符号: TranslateRequest, TranslateResponse, BatchTranslateRequest, BatchTranslateResponse, _schedule_community_publish_watch, get_translation_task_repository, get_user_api_config, get_user_api_config_async, build_llm_config, build_llm_config_async
- `backend/app/api/routes/upload.py`: LaTeX 上传、校验与压缩包解包接口。 | 顶层符号: LatexValidationResponse, UploadResponse, extract_rar, get_file_extension, upload_file

### backend/app/core
- `backend/app/core/__init__.py`: 包初始化与导出文件。
- `backend/app/core/auth.py`: 本地认证与权限依赖实现，处理 JWT、当前用户解析和管理员请求校验。 | 顶层符号: extract_bearer_token_from_credentials, extract_bearer_token, resolve_current_user_id, get_auth_service, optional_current_user, require_current_user
- `backend/app/core/config.py`: 全局配置中心，定义设置项、任务状态枚举以及 LLM、存储、数据库等运行参数。 | 顶层符号: TaskStatus, CompilationStage, Settings, get_settings, get_llm_config
- `backend/app/core/encryption.py`: 核心基础设施文件。 | 顶层符号: _get_fernet, encrypt_api_key, decrypt_api_key, is_encryption_configured
- `backend/app/core/timezone_utils.py`: 核心基础设施文件。 | 顶层符号: get_cst_now, get_cst_now_iso

### backend/app/db
- `backend/app/db/__init__.py`: 包初始化与导出文件。
- `backend/app/db/connection.py`: 数据库连接与辅助文件。 | 顶层符号: DatabaseUnavailableError, get_database_dialect, db_connection

### backend/app/models
- `backend/app/models/__init__.py`: 包初始化与导出文件。
- `backend/app/models/config_models.py`: 数据模型文件。 | 顶层符号: SourceType, FormattingConfig, AdvancedConfig, LatexValidation

### backend/app/policies
- `backend/app/policies/__init__.py`: 包初始化与导出文件。 | 顶层符号: authorize
- `backend/app/policies/admin_policy.py`: 鉴权策略文件。 | 顶层符号: AdminPolicy
- `backend/app/policies/base.py`: 鉴权策略文件。 | 顶层符号: AuthorizationResult, BasePolicy, _normalize_roles, is_admin, is_authenticated
- `backend/app/policies/community_agent_policy.py`: 鉴权策略文件。 | 顶层符号: CommunityAgentPolicy
- `backend/app/policies/paper_policy.py`: 鉴权策略文件。 | 顶层符号: PaperPolicy
- `backend/app/policies/settings_policy.py`: 鉴权策略文件。 | 顶层符号: SettingsPolicy
- `backend/app/policies/task_policy.py`: 鉴权策略文件。 | 顶层符号: TaskPolicy

### backend/app/repositories
- `backend/app/repositories/__init__.py`: 包初始化与导出文件。
- `backend/app/repositories/auth_repository.py`: 仓储层文件，为上层服务提供持久化读写能力。 | 顶层符号: AuthRepository, _utc_now_naive, _placeholder, _placeholders, _fetchone, _fetchall
- `backend/app/repositories/community_agent_repository.py`: 仓储层文件，为上层服务提供持久化读写能力。 | 顶层符号: CommunityAgentConversationRepository, CommunityAgentRunRepository, _placeholder, _fetchone, _fetchall, _decode_turns, _decode_json_dict, _normalize_db_timestamp
- `backend/app/repositories/community_paper_repository.py`: 社区论文仓储，负责论文、资产、互动、策展、任务历史与结构化解读等数据读写。 | 顶层符号: CommunityPaperRepository, _utc_now_naive, _placeholder, _fetchone, _fetchall, _decode_json_list
- `backend/app/repositories/translation_task_repository.py`: 翻译任务仓储，负责任务状态、详情、配置哈希与历史记录的持久化。 | 顶层符号: TranslationTaskRepository, _utc_now_naive, _placeholder, _placeholders, _fetchone, _fetchall, _decode_json
- `backend/app/repositories/user_settings_repository.py`: 仓储层文件，为上层服务提供持久化读写能力。 | 顶层符号: UserSettingsRepository, _utc_now_naive, _placeholder, _fetchone, _decode_json

### backend/app/services
- `backend/app/services/__init__.py`: 包初始化与导出文件。
- `backend/app/services/auth_service.py`: 业务服务文件。 | 顶层符号: AuthServiceError, NiuTransAuthClient, LocalAuthService, _b64url_encode, _b64url_decode, _now_utc, _now_unix
- `backend/app/services/community_agent_service.py`: 社区智能体服务门面，创建运行记录、转发事件流并协调持久化。 | 顶层符号: RunNotFoundError, _RunRecord, _now_iso, _default_provider_state, _should_persist_run, _authorize_run_access, _save_run_to_repository, _save_event_to_repository
- `backend/app/services/community_content_pool_service.py`: 社区内容池服务，处理论文导入、内容池就绪度与后台构建任务。 | 顶层符号: PoolCandidate, ContentPoolDependencies, _CandidateState, CommunityContentPoolService, _utc_now_iso, _normalize_text, _default_discover_candidates, _default_admit_candidate, _default_ensure_source_ready, _default_start_translation
- `backend/app/services/config_capture.py`: 业务服务文件。 | 顶层符号: _json_safe, _mask_api_key, _sanitize_llm_config, _sanitize_agent_config, capture_task_config
- `backend/app/services/email_service.py`: 业务服务文件。 | 顶层符号: EmailService, get_email_service
- `backend/app/services/latex_validator.py`: 业务服务文件。 | 顶层符号: validate_latex_directory, find_main_tex_file
- `backend/app/services/paper_thumbnail_service.py`: 论文 PDF 缩略图缓存服务，负责首页缩略图生成、缓存命中与预热复用。 | 顶层符号: ensure_pdf_thumbnail, _thumbnail_cache_dir, _thumbnail_cache_path, _render_pdf_thumbnail_bytes_from_path, _render_pdf_thumbnail_bytes_from_url
- `backend/app/services/paper_preview_service.py`: 论文预览构建服务，生成 HTML、摘要、预览载荷并做缓存恢复。 | 顶层符号: _load_json, _build_placeholder_map, _replace_placeholders, _strip_structural_commands, _unwrap_formatting_commands, _normalize_inline_text
- `backend/app/services/paper_service.py`: 论文主服务，负责社区论文导入、翻译桥接、预览、下载、结构化解读，以及管理员策展失败留痕、任务历史与硬删除流程。 | 顶层符号: _StructuredInsightBasePreferenceTracker, _utc_now_iso, _get_curation_semaphore, _get_delete_semaphore, get_community_paper_repository, _run_local_repo, _run_db_blocking_with_retry
- `backend/app/services/runtime_pressure.py`: 运行时压力协调服务，负责区分 web/worker 角色、记录前台访问压力并让后台回填任务让步。 | 顶层符号: get_runtime_role, web_runtime_enabled, background_runtime_enabled, admin_job_execution_enabled, record_frontend_pressure, has_recent_frontend_pressure, backfill_start_blocked_by_frontend_pressure, apply_worker_process_priority
- `backend/app/services/storage_backend.py`: 对象存储抽象层，统一本地磁盘与 COS 等后端的上传/下载接口。 | 顶层符号: StoredObjectRef, StorageBackend, LocalDiskStorageBackend, CosStorageBackend, build_storage_backend, _ensure_cos_config
- `backend/app/services/task_artifact_storage.py`: 任务产物持久化服务，在本地与对象存储之间同步输出目录及清单。 | 顶层符号: _get_storage_backend, _storage_uses_object_store, _normalize_stored_path, normalize_stored_task_path, resolve_local_task_path, persist_task_directory
- `backend/app/services/task_detail.py`: 任务详情推断与标准化工具，统一 stage、detail_code、detail_message 的生成。 | 顶层符号: normalize_stage, normalize_detail_params, infer_task_detail
- `backend/app/services/task_manager.py`: 任务管理核心，维护内存态任务、异步刷库、队列执行与运行时清理。 | 顶层符号: PersistentStateFlusher, TaskManager, GuestTaskTracker, TaskQueue, get_translation_task_repository, get_auth_repository, _delete_local_cache_path, _is_within_cleanup_roots, clear_cached_runtime_artifacts, set_runtime_shutting_down

### backend/app/services/agents
- `backend/app/services/agents/__init__.py`: 包初始化与导出文件。 | 顶层符号: _SemaphoreProxy, _get_llm_semaphore
- `backend/app/services/agents/base_tool_agent.py`: 翻译代理管线相关文件。 | 顶层符号: BaseToolAgent
- `backend/app/services/agents/compilation_diagnostic_node.py`: 翻译代理管线相关文件。 | 顶层符号: DiagnosticSuggestion, DiagnosticReport, CompilationDiagnosticNode
- `backend/app/services/agents/compile_runtime.py`: 翻译代理管线相关文件。 | 顶层符号: get_compile_semaphore
- `backend/app/services/agents/controlled_repair_agent.py`: 翻译代理管线相关文件。 | 顶层符号: RepairRateLimitExceededError, ControlledRepairAgent
- `backend/app/services/agents/coordinator_agent.py`: 翻译流水线协调器，编排解析、翻译、校验、修复与编译步骤。 | 顶层符号: CoordinatorAgent
- `backend/app/services/agents/generator_agent.py`: 翻译代理管线相关文件。 | 顶层符号: GeneratorAgent
- `backend/app/services/agents/langgraph_orchestrator.py`: 翻译代理管线相关文件。 | 顶层符号: PipelineState, _should_skip_deterministic_section_downgrade, _normalize_error_signature, _write_audit_log, _update_progress, _write_task_log, _write_stage_failed_log
- `backend/app/services/agents/llm_runtime.py`: 翻译代理管线相关文件。 | 顶层符号: _as_mapping, extract_llm_config, _coerce_positive_int, resolve_llm_timeout, resolve_llm_max_concurrent_requests, resolve_task_llm_max_concurrent_requests
- `backend/app/services/agents/llm_token_pool.py`: 翻译代理管线相关文件。 | 顶层符号: _MemberState, _PoolRegistry, build_pool_members_from_groups, compute_pool_routing_key, _parse_retry_after_seconds, _perform_member_request, post_chat_completion_with_pool
- `backend/app/services/agents/parser_agent.py`: 翻译代理管线相关文件。 | 顶层符号: ParserAgent
- `backend/app/services/agents/pipeline_invariants.py`: 翻译代理管线相关文件。 | 顶层符号: PipelineInvariantViolation, SpeculativeRepairForbiddenError, RawStructurePayloadViolation, RawContentLeakageViolation, HardFreezeProtocolViolation, assert_no_raw_structure, assert_no_long_raw_span, is_absolute_path_like
- `backend/app/services/agents/pipeline_schema.py`: 翻译代理管线相关文件。 | 顶层符号: PipelineInput, NodeOutput, PipelineAuditEntry, FallbackReport
- `backend/app/services/agents/structure_repair_node.py`: 翻译代理管线相关文件。 | 顶层符号: StructureRepairNode, _count_open_braces, _repair_unclosed_braces, _find_unmatched_environments, _repair_unmatched_environments, _apply_structural_repairs
- `backend/app/services/agents/translation_repair_agent.py`: 翻译代理管线相关文件。 | 顶层符号: TranslationRepairAgent, _extract_placeholders, _estimate_tokens, _count_math_delimiters, _math_delimiter_guard, _placeholder_guard, _edit_budget_check
- `backend/app/services/agents/translator_agent.py`: 核心翻译代理，负责分段翻译、术语处理、payload 守卫、降级与重试控制。 | 顶层符号: TranslatorAgent
- `backend/app/services/agents/validator_agent.py`: 翻译校验代理，检查完整性、结构风险和错误类型分类。 | 顶层符号: ValidatorAgent, find_long_english_prose_spans, classify_error

### backend/app/services/community_agent
- `backend/app/services/community_agent/__init__.py`: 包初始化与导出文件。
- `backend/app/services/community_agent/formatter.py`: 业务服务文件。 | 顶层符号: format_summary
- `backend/app/services/community_agent/language.py`: 业务服务文件。 | 顶层符号: normalize_response_language, is_chinese_language, detect_response_language, summary_labels
- `backend/app/services/community_agent/models.py`: 业务服务文件。 | 顶层符号: AnswerSlots, PlannerStep
- `backend/app/services/community_agent/orchestrator.py`: 社区智能体编排层，负责计划、检索、技能执行与答案组织。 | 顶层符号: CommunityReactAgent, _normalize_text, _normalize_history, _normalize_reader_selection, _extract_arxiv_id, _normalized_title_tokens, _title_similarity_score
- `backend/app/services/community_agent/runtime.py`: 社区智能体运行时上下文与事件循环封装。 | 顶层符号: AgentRuntimeState
- `backend/app/services/community_agent/skills_runtime.py`: 社区智能体技能运行时，负责装配、启停和调用技能。 | 顶层符号: PromptSkillPack, PromptSkillBundle, _extract_frontmatter, _extract_json_block, load_prompt_skill_packs, _is_pack_visible, build_skill_prompt_bundle
- `backend/app/services/community_agent/validator.py`: 业务服务文件。 | 顶层符号: ValidationError, _normalize_text, _extract_domains, _mentions_time_constraint, _looks_like_paper_title_query, validate_search_query, _collect_known_paper_ids

### backend/app/services/community_agent/skills
- `backend/app/services/community_agent/skills/__init__.py`: 包初始化与导出文件。 | 顶层符号: discover_skill_types, instantiate_discovered_skills
- `backend/app/services/community_agent/skills/base.py`: 社区智能体技能定义文件。 | 顶层符号: SkillContract, AgentSkill, _extract_frontmatter, _extract_section_body, _extract_json_block, _extract_text_block, load_skill_contract
- `backend/app/services/community_agent/skills/community_search.py`: 社区智能体技能定义文件。 | 顶层符号: CommunitySearchPapersSkill, _normalize_text, _citation_from_paper
- `backend/app/services/community_agent/skills/compose_academic_answer.py`: 社区智能体技能定义文件。 | 顶层符号: ComposeAcademicAnswerSkill, _normalize_text, _normalize_string_list, _resolve_chat_completions_url, _extract_json_object
- `backend/app/services/community_agent/skills/external_tavily_search.py`: 社区智能体技能定义文件。 | 顶层符号: ExternalTavilySearchSkill, _normalize_text
- `backend/app/services/community_agent/skills/import_arxiv_paper.py`: 社区智能体技能定义文件。 | 顶层符号: ImportArxivPaperSkill
- `backend/app/services/community_agent/skills/read_paper_context.py`: 社区智能体技能定义文件。 | 顶层符号: ReadPaperContextSkill, _normalize_text, _extract_anchor_ids
- `backend/app/services/community_agent/skills/start_translation_kernel.py`: 社区智能体技能定义文件。 | 顶层符号: StartTranslationKernelSkill

### backend/app/services/community_agent/skills/contracts
- `backend/app/services/community_agent/skills/contracts/__init__.py`: 包初始化与导出文件。

### backend/app/services/community_agent/skills/contracts/community_search_papers
- `backend/app/services/community_agent/skills/contracts/community_search_papers/__init__.py`: 包初始化与导出文件。
- `backend/app/services/community_agent/skills/contracts/community_search_papers/executor.py`: 社区智能体技能合约或执行器文件。 | 顶层符号: CommunitySearchPapersSkill

### backend/app/services/community_agent/skills/contracts/compose_academic_answer
- `backend/app/services/community_agent/skills/contracts/compose_academic_answer/__init__.py`: 包初始化与导出文件。
- `backend/app/services/community_agent/skills/contracts/compose_academic_answer/executor.py`: 社区智能体技能合约或执行器文件。 | 顶层符号: ComposeAcademicAnswerSkill

### backend/app/services/community_agent/skills/contracts/external_tavily_search
- `backend/app/services/community_agent/skills/contracts/external_tavily_search/__init__.py`: 包初始化与导出文件。
- `backend/app/services/community_agent/skills/contracts/external_tavily_search/executor.py`: 社区智能体技能合约或执行器文件。 | 顶层符号: ExternalTavilySearchSkill

### backend/app/services/community_agent/skills/contracts/import_arxiv_paper
- `backend/app/services/community_agent/skills/contracts/import_arxiv_paper/__init__.py`: 包初始化与导出文件。
- `backend/app/services/community_agent/skills/contracts/import_arxiv_paper/executor.py`: 社区智能体技能合约或执行器文件。 | 顶层符号: ImportArxivPaperSkill

### backend/app/services/community_agent/skills/contracts/read_paper_context
- `backend/app/services/community_agent/skills/contracts/read_paper_context/__init__.py`: 包初始化与导出文件。
- `backend/app/services/community_agent/skills/contracts/read_paper_context/executor.py`: 社区智能体技能合约或执行器文件。 | 顶层符号: ReadPaperContextSkill

### backend/app/services/community_agent/skills/contracts/start_translation_kernel
- `backend/app/services/community_agent/skills/contracts/start_translation_kernel/__init__.py`: 包初始化与导出文件。
- `backend/app/services/community_agent/skills/contracts/start_translation_kernel/executor.py`: 社区智能体技能合约或执行器文件。 | 顶层符号: StartTranslationKernelSkill

### backend/app/services/community_agent/tools
- `backend/app/services/community_agent/tools/__init__.py`: 包初始化与导出文件。 | 顶层符号: ToolRegistry, instantiate_tools
- `backend/app/services/community_agent/tools/base.py`: 社区智能体工具实现文件。 | 顶层符号: CommunityAgentTool
- `backend/app/services/community_agent/tools/community_search.py`: 社区智能体工具实现文件。 | 顶层符号: CommunitySearchPapersTool
- `backend/app/services/community_agent/tools/external_tavily_search.py`: 社区智能体工具实现文件。 | 顶层符号: ExternalTavilySearchTool
- `backend/app/services/community_agent/tools/import_arxiv_paper.py`: 社区智能体工具实现文件。 | 顶层符号: ImportArxivPaperTool
- `backend/app/services/community_agent/tools/read_paper_context.py`: 社区智能体工具实现文件。 | 顶层符号: ReadPaperContextTool
- `backend/app/services/community_agent/tools/start_translation_kernel.py`: 社区智能体工具实现文件。 | 顶层符号: StartTranslationKernelTool

### backend/app/services/latex
- `backend/app/services/latex/__init__.py`: 包初始化与导出文件。
- `backend/app/services/latex/compiler.py`: LaTeX 编译服务，负责分阶段编译、驱动切换、日志收集与智能回退。 | 顶层符号: LatexExecutor, HostLatexExecutor, DockerLatexExecutor, CompilationResult, LaTeXCompiler, _get_latex_executor, _has_real_bib_files, _iter_manual_bbl_inputs, _has_bibliography_driver, _prepare_bibliography_inputs, _validate_generated_pdf_structure
- `backend/app/services/latex/parser.py`: LaTeX 解析服务，负责切分章节、环境、占位符与可翻译片段。 | 顶层符号: LatexParser
- `backend/app/services/latex/prompts.py`: LaTeX 处理链路相关文件。 | 顶层符号: init_prompts, create_prompts
- `backend/app/services/latex/reconstruct.py`: LaTeX 重建服务，将翻译后的片段按原结构回填并重组输出。 | 顶层符号: LatexConstructor
- `backend/app/services/latex/sanitizer.py`: LaTeX 清洗器，预处理危险或不兼容命令并修正文档驱动细节。 | 顶层符号: apply_precompile_sanitization, _find_ghostscript, extract_failed_pdf_paths, check_pdf_syntax_error, sanitize_pdf, patch_tex_includegraphics
- `backend/app/services/latex/structure_guard.py`: 结构守卫，校验解析或翻译后的括号、环境与命令结构完整性。 | 顶层符号: StructureGuardResult, _is_escaped, _strip_line_comments, _mask_verbatim_like_envs, _consume_braced_group, _consume_optional_bracket_group, _consume_command_token
- `backend/app/services/latex/token_estimator.py`: LaTeX 处理链路相关文件。 | 顶层符号: _formula_digest, estimate_tokens_v1, safe_limit_v1
- `backend/app/services/latex/utils.py`: LaTeX 处理链路相关文件。 | 顶层符号: ArxivDownloadError, ArxivNoSourceAvailableError, ArxivNetworkFailureError, ArxivArchiveCorruptedError, DownloadProgressCallback, get_pattern_command_full, extract_compressed_files, get_profect_dirs, has_appendix, remove_appendix_content, extract_latex_nodes

### backend/app/services/translation
- `backend/app/services/translation/__init__.py`: 包初始化与导出文件。
- `backend/app/services/translation/downgrade_handler.py`: 翻译降级与修复相关文件。 | 顶层符号: deterministic_downgrade
- `backend/app/services/translation/repair_scheduler.py`: 翻译降级与修复相关文件。 | 顶层符号: QueueTimeoutError, TokenRepairScheduler
- `backend/app/services/translation/structure_checker.py`: 翻译降级与修复相关文件。 | 顶层符号: _has_bare_dollars, _has_leaked_env, _has_unbalanced_braces, detect_structure_invariant
- `backend/app/services/translation/ultimate_downgrade.py`: 翻译降级与修复相关文件。 | 顶层符号: _is_verbatim_segment, _extract_natural_language, _escape_latex_special, _strip_downgrade_comment_lines, _looks_like_downgrade_output, _split_title_and_body

### backend/app/utils
- `backend/app/utils/__init__.py`: 包初始化与导出文件。
- `backend/app/utils/async_blocking.py`: 通用工具文件。 | 顶层符号: _wrappers_enabled, _db_mode, run_blocking, run_db_blocking

### backend/migrations
- `backend/migrations/20260316_add_task_detail_metadata.sql`: 数据库迁移脚本：20260316 add task detail metadata。 | SQL 片段: ALTER TABLE public.translation_tasks ADD COLUMN IF NOT EXISTS detail_code TEXT; ALTER TABLE public.translation_tasks ADD
- `backend/migrations/20260318_add_increment_paper_download_count_fn.sql`: 数据库迁移脚本：20260318 add increment paper download count fn。 | SQL 片段: create or replace function public.increment_paper_download_count(target_paper_id uuid) returns table (download_count int
- `backend/migrations/20260318_add_increment_paper_view_count_fn.sql`: 数据库迁移脚本：20260318 add increment paper view count fn。 | SQL 片段: create or replace function public.increment_paper_view_count(target_paper_id uuid) returns table (view_count integer) la
- `backend/migrations/20260318_add_paper_community_admission_fields.sql`: 数据库迁移脚本：20260318 add paper community admission fields。 | SQL 片段: alter table public.papers add column if not exists community_status text not null default 'user_fallback' check (communi
- `backend/migrations/20260318_create_interaction_tables.sql`: 数据库迁移脚本：20260318 create interaction tables。 | SQL 片段: create table if not exists public.paper_likes ( paper_id uuid not null references public.papers (id) on delete cascade, 
- `backend/migrations/20260318_create_moderation_tables.sql`: 数据库迁移脚本：20260318 create moderation tables。 | SQL 片段: create table if not exists public.reports ( id uuid primary key default gen_random_uuid(), target_type text not null che
- `backend/migrations/20260318_create_papers_and_assets.sql`: 数据库迁移脚本：20260318 create papers and assets。 | SQL 片段: create table if not exists public.papers ( id uuid primary key default gen_random_uuid(), source text not null check (so
- `backend/migrations/20260318_refine_day1_policy_and_index_guards.sql`: 数据库迁移脚本：20260318 refine day1 policy and index guards。 | SQL 片段: create index if not exists comments_parent_id_idx on public.comments (parent_id) where parent_id is not null; create ind
- `backend/migrations/20260323_create_community_agent_conversations.sql`: 数据库迁移脚本：20260323 create community agent conversations。 | SQL 片段: create table if not exists public.community_agent_conversations ( user_id uuid not null default auth.uid() references au
- `backend/migrations/20260326_create_community_content_pool_foundation.sql`: 数据库迁移脚本：20260326 create community content pool foundation。 | SQL 片段: create table if not exists public.community_content_pool_candidates ( id uuid primary key default gen_random_uuid(), arx

### backend/migrations_mysql
- `backend/migrations_mysql/20260409_0001_local_auth_mysql.sql`: MySQL 迁移脚本：local auth mysql。 | SQL 片段: create table if not exists users ( id varchar(64) not null, external_provider varchar(32) not null, external_user_id var
- `backend/migrations_mysql/20260411_0002_community_admin_curation_flow.sql`: MySQL 迁移脚本：community admin curation flow。 | SQL 片段: create table if not exists community_structured_insights ( paper_id varchar(64) not null, section_key varchar(64) not nu
- `backend/migrations_mysql/20260411_0003_expand_paper_asset_id_columns.sql`: MySQL 迁移脚本：expand paper asset id columns。 | SQL 片段: alter table papers modify column trans_latest_asset_pdf_id varchar(255) null, modify column community_selected_asset_id 
- `backend/migrations_mysql/20260411_0004_add_content_column_to_community_structured_insights.sql`: MySQL 迁移脚本：add content column to community structured insights。 | SQL 片段: set @community_structured_insights_has_content := ( select count(*) from information_schema.columns where table_schema =
- `backend/migrations_mysql/20260412_0005_add_community_similar_recommendations.sql`: MySQL 迁移脚本：add community similar recommendations。 | SQL 片段: create table if not exists community_similar_recommendations ( paper_id varchar(64) not null, position int not null, arx
- `backend/migrations_mysql/20260419_0006_admin_curation_retention_fields.sql`: MySQL 迁移脚本：为管理员策展任务补充失败留痕字段与已发布论文关联字段。 | SQL 片段: alter table community_curation_jobs add column terminal_task_status varchar(32) null after status

### backend/scripts
- `backend/scripts/apply_mysql_migrations.py`: 运维或迁移脚本。 | 顶层符号: _load_sql_files, apply_migrations, main
- `backend/scripts/audit_pipeline_regression.py`: 运维或迁移脚本。 | 顶层符号: _load_json, _find_main_tex, _placeholder_only_chunks, _count_status, _invariant_fallback_sections, _status_sections
- `backend/scripts/bootstrap_local_community_papers.py`: 运维或迁移脚本。 | 顶层符号: LocalPaperCandidate, _iso_utc_from_path, _iter_candidate_dirs, _match_arxiv_id, _infer_arxiv_id, _find_preview_html, _find_translated_pdf
- `backend/scripts/grant_local_admin.py`: 运维或迁移脚本。 | 顶层符号: _utc_now_naive, _fetch_target_user, grant_local_admin, main
- `backend/scripts/import_source_to_mysql.py`: 运维或迁移脚本。 | 顶层符号: _utc_now, _first, _as_str, _as_bool, _as_int, _as_timestamp
- `backend/scripts/mysql_script_connection.py`: 运维或迁移脚本。 | 顶层符号: resolve_mysql_script_config, describe_mysql_script_target, mysql_script_connection
## Recent Responsibility Updates (2026-04-19)

- `backend/app/services/task_manager.py`: 任务管理器现已负责执行尝试编号、同尝试终态单调保护、持久层异常状态对账，以及队列级未捕获异常的终态封口，避免状态漂移长期占用并发槽位。
- `backend/app/api/routes/translate.py`: 翻译执行入口现已在每次运行前开启新的 attempt，并将进度与终态更新绑定到该 attempt；同时兼容旧测试桩缺少 attempt 接口或旧版 progress callback 签名的场景。
- `backend/app/services/paper_service.py`: 管理员策展等待逻辑现已增加“持久层短超时 + 熔断退避”兜底，并在发现不可能状态时合成失败终态，避免数据库抖动反向卡死管理任务。
- `backend/app/api/routes/papers.py`: 管理员策展历史接口现已负责规范化 `all` / `processing` 筛选语义，并提供选中任务的批量硬删除入口。
- `backend/app/repositories/community_paper_repository.py`: 策展任务列表查询现已支持将 `processing` 扩展匹配到 `processing`、`translating`、`publishing` 三类在途状态。

## Recent Responsibility Updates

- `backend/app/api/routes/papers.py`: 管理员策展历史接口现已负责规范化 `all` / `processing` 筛选语义，并提供选中任务批量硬删除入口。
- `backend/app/services/paper_service.py`: 管理员策展历史服务现已负责处理中状态聚合查询与批量硬删除编排，并返回逐任务成功/失败结果。
- `backend/app/repositories/community_paper_repository.py`: 策展任务列表查询现已支持将 `processing` 扩展匹配到 `processing`、`translating`、`publishing` 三类在途状态。

## Recent Responsibility Updates (2026-04-20)

- `backend/app/api/routes/papers.py`: ���������б��뿨Ƭ���·�������ṩ `source-download` ��ڣ����� paper summary �б�¶ `arxiv_url` �� `github_url` ���о�����Ԫ���ݡ�
- `backend/app/api/routes/download.py`: Դ�� PDF Ԥ���߼����ѳ�ȡΪ�ɸ��õ� `_serve_source_pdf`��ͬʱ֧�� inline Ԥ���� attachment �������ַ��ط�ʽ��
- `backend/app/services/paper_service.py`: �������Ļ��ܷ������Ѹ���� preview HTML ����ȡ GitHub �ⲿ���ӣ�Ϊ��ҳ���Ŀ�Ƭ��ֱ���о������ṩ���ݡ�
