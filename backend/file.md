# Backend File Index

## Recent Responsibility Updates (2026-04-26 Community Quality Gate)

- `backend/app/api/routes/translate.py`: 社区/admin curation 生产翻译现在按 `COMMUNITY_TRANSLATION_LLM_MAX_CONCURRENT_REQUESTS` 收紧单任务 LLM 并发，默认 3，避免单篇论文内部打穿同一 API 池。
- `backend/app/models/config_models.py`: `AdvancedConfig` 增加不持久化的内部标记 `community_production_translation`，用于区分生产社区入库任务与普通交互任务。
- `backend/app/core/config.py`: 新增 `COMMUNITY_TRANSLATION_LLM_MAX_CONCURRENT_REQUESTS` 配置项，控制社区生产翻译的单任务 LLM 请求上限。

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
- `backend/app/services/translation`: 闄嶇骇銆佷慨澶嶃€佺粨鏋勬鏌ョ瓑缈昏瘧鍏滃簳閫昏緫銆?
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
- `backend/app/services/community_translation_quality.py`
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
- `backend/migrations_mysql/20260421_0008_community_paper_engagement.sql`
- `backend/migrations_mysql/20260422_0009_add_arxiv_published_at.sql`
- `backend/migrations_mysql/20260423_0010_add_login_identifier_to_users.sql`
- `backend/scripts/apply_mysql_migrations.py`
- `backend/scripts/audit_pipeline_regression.py`
- `backend/scripts/audit_community_translation_quality.py`
- `backend/scripts/bootstrap_local_community_papers.py`
- `backend/scripts/extract_core_pool_ids.py`
- `backend/scripts/grant_local_admin.py`
- `backend/scripts/import_source_to_mysql.py`
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
- `backend/app/api/routes/upload.py`: LaTeX 涓婁紶銆佹牎楠屼笌鍘嬬缉鍖呰В鍖呮帴鍙ｃ€?| 椤跺眰绗﹀彿: LatexValidationResponse, UploadResponse, extract_rar, get_file_extension, upload_file

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

### backend/app/services/agents
- `backend/app/services/agents/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?| 椤跺眰绗﹀彿: _SemaphoreProxy, _get_llm_semaphore
- `backend/app/services/agents/base_tool_agent.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: BaseToolAgent
- `backend/app/services/agents/compilation_diagnostic_node.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: DiagnosticSuggestion, DiagnosticReport, CompilationDiagnosticNode
- `backend/app/services/agents/compile_runtime.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: get_compile_semaphore
- `backend/app/services/agents/controlled_repair_agent.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: RepairRateLimitExceededError, ControlledRepairAgent
- `backend/app/services/agents/coordinator_agent.py`: 缈昏瘧娴佹按绾垮崗璋冨櫒锛岀紪鎺掕В鏋愩€佺炕璇戙€佹牎楠屻€佷慨澶嶄笌缂栬瘧姝ラ銆?| 椤跺眰绗﹀彿: CoordinatorAgent
- `backend/app/services/agents/generator_agent.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: GeneratorAgent
- `backend/app/services/agents/langgraph_orchestrator.py`: 缈昏瘧浠ｇ悊缂栨帓灞傦紝璐熻矗鑺傜偣娴佽浆銆佸璁℃棩蹇椼€佽繘搴︽洿鏂帮紝浠ュ強鍦ㄦ牎楠岄噸璇曞悗闃绘柇浠嶆畫鐣欒嫳鏂囬暱娈电殑浠诲姟瀹屾垚銆?| 椤跺眰绗﹀彿: PipelineState, _should_skip_deterministic_section_downgrade, _normalize_error_signature, _write_audit_log, _update_progress, _write_task_log, _write_stage_failed_log
- `backend/app/services/agents/llm_runtime.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: _as_mapping, extract_llm_config, _coerce_positive_int, resolve_llm_timeout, resolve_llm_max_concurrent_requests, resolve_task_llm_max_concurrent_requests
- `backend/app/services/agents/llm_token_pool.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: _MemberState, _PoolRegistry, build_pool_members_from_groups, compute_pool_routing_key, _parse_retry_after_seconds, _perform_member_request, post_chat_completion_with_pool
- `backend/app/services/agents/parser_agent.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: ParserAgent
- `backend/app/services/agents/pipeline_invariants.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: PipelineInvariantViolation, SpeculativeRepairForbiddenError, RawStructurePayloadViolation, RawContentLeakageViolation, HardFreezeProtocolViolation, assert_no_raw_structure, assert_no_long_raw_span, is_absolute_path_like
- `backend/app/services/agents/pipeline_schema.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: PipelineInput, NodeOutput, PipelineAuditEntry, FallbackReport
- `backend/app/services/agents/structure_repair_node.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: StructureRepairNode, _count_open_braces, _repair_unclosed_braces, _find_unmatched_environments, _repair_unmatched_environments, _apply_structural_repairs
- `backend/app/services/agents/translation_repair_agent.py`: 缈昏瘧浠ｇ悊绠＄嚎鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: TranslationRepairAgent, _extract_placeholders, _estimate_tokens, _count_math_delimiters, _math_delimiter_guard, _placeholder_guard, _edit_budget_check
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
- `backend/app/services/latex/structure_guard.py`: 缁撴瀯瀹堝崼锛屾牎楠岃В鏋愭垨缈昏瘧鍚庣殑鎷彿銆佺幆澧冧笌鍛戒护缁撴瀯瀹屾暣鎬с€?| 椤跺眰绗﹀彿: StructureGuardResult, _is_escaped, _strip_line_comments, _mask_verbatim_like_envs, _consume_braced_group, _consume_optional_bracket_group, _consume_command_token
- `backend/app/services/latex/token_estimator.py`: LaTeX 澶勭悊閾捐矾鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: _formula_digest, estimate_tokens_v1, safe_limit_v1
- `backend/app/services/latex/utils.py`: LaTeX 澶勭悊閾捐矾鐩稿叧鏂囦欢銆?| 椤跺眰绗﹀彿: ArxivDownloadError, ArxivNoSourceAvailableError, ArxivNetworkFailureError, ArxivArchiveCorruptedError, DownloadProgressCallback, get_pattern_command_full, extract_compressed_files, get_profect_dirs, has_appendix, remove_appendix_content, extract_latex_nodes

### backend/app/services/translation
- `backend/app/services/translation/__init__.py`: 鍖呭垵濮嬪寲涓庡鍑烘枃浠躲€?
- `backend/app/services/translation/downgrade_handler.py`: 缈昏瘧闄嶇骇涓庝慨澶嶇浉鍏虫枃浠躲€?| 椤跺眰绗﹀彿: deterministic_downgrade
- `backend/app/services/translation/repair_scheduler.py`: 缈昏瘧闄嶇骇涓庝慨澶嶇浉鍏虫枃浠躲€?| 椤跺眰绗﹀彿: QueueTimeoutError, TokenRepairScheduler
- `backend/app/services/translation/structure_checker.py`: 缈昏瘧闄嶇骇涓庝慨澶嶇浉鍏虫枃浠躲€?| 椤跺眰绗﹀彿: _has_bare_dollars, _has_leaked_env, _has_unbalanced_braces, detect_structure_invariant
- `backend/app/services/translation/ultimate_downgrade.py`: 缈昏瘧闄嶇骇涓庝慨澶嶇浉鍏虫枃浠躲€?| 椤跺眰绗﹀彿: _is_verbatim_segment, _extract_natural_language, _escape_latex_special, _strip_downgrade_comment_lines, _looks_like_downgrade_output, _split_title_and_body

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
- `backend/app/services/agents/translation_repair_agent.py`: repair agent 现已接入同一 task 级补救预算口径，避免外层 repair LLM 调用绕过主翻译预算上限。

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
