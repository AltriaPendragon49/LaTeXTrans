"""
后端配置模块

从环境变量和 TOML 配置文件中加载设置。
提供 LLM API、存储路径和任务状态枚举等配置。
"""

import json
import os
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field, field_validator
import toml


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED_COMPILATION = "failed_compilation"
    STRUCTURE_INVALID = "structure_invalid"
    FAILED = "failed"


class CompilationStage(str, Enum):
    """编译阶段枚举"""
    IDLE = "idle"
    PARSING = "parsing"
    TRANSLATING = "translating"
    COMPILING = "compiling"
    COMPILATION_FAILED = "compilation_failed"
    DONE = "done"


class Settings(BaseSettings):
    """应用程序全局设置"""

    # 应用基本信息
    app_name: str = "PaperX Backend"
    version: str = "0.1.0"
    
    llm_api_key: str = Field(
        validation_alias="LLM_API_KEY"
    )
    llm_base_url: str = Field(
        validation_alias="LLM_BASE_URL"
    )
    llm_model: str = Field(
        validation_alias="LLM_MODEL"
    )
    llm_system_pool_groups_json: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_SYSTEM_POOL_GROUPS_JSON", "llm_system_pool_groups_json"),
        description="可选的 JSON 数组，描述系统管理的 LLM 池组: [{base_url, api_keys: []}, ...]",
    )
    llm_members_json: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_MEMBERS_JSON", "llm_members_json"),
        description="可选的 JSON 数组，描述 LLM 成员: [{member_id, base_url, api_key, account_id, quota_scope, concurrency, reserve}, ...]",
    )
    llm_pool_reserve_count: int = Field(
        default=1,
        validation_alias=AliasChoices("LLM_POOL_RESERVE_COUNT", "llm_pool_reserve_count"),
        description="计算社区任务容量时保留的健康 LLM 成员数量，用于故障转移/流量突增",
    )
    llm_member_default_concurrency: int = Field(
        default=1,
        validation_alias=AliasChoices("LLM_MEMBER_DEFAULT_CONCURRENCY", "llm_member_default_concurrency"),
        description="每个成员的默认出站 LLM 请求并发数",
    )
    llm_shared_pool_concurrency: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_SHARED_POOL_CONCURRENCY", "llm_shared_pool_concurrency"),
        description="可选的所有 LLM 成员共享池并发限制",
    )
    llm_timeout: int = Field(
        default=120,
        validation_alias="LLM_TIMEOUT"
    )
    model_context_tokens: int = Field(
        default=32000,
        validation_alias="MODEL_CONTEXT_TOKENS"
    )
    prompt_reserve_tokens: int = Field(
        default=4096,
        validation_alias="PROMPT_RESERVE_TOKENS"
    )
    
    # 翻译设置
    target_language: str = "ch"
    source_language: str = "en"

    # 遗留导入源配置
    migration_source_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("MIGRATION_SOURCE_URL", "IMPORT_SOURCE_URL"),
    )
    migration_source_anon_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("MIGRATION_SOURCE_ANON_KEY", "IMPORT_SOURCE_ANON_KEY"),
        description="仅用于迁移工具的遗留导入源公钥",
    )
    migration_source_service_role_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("MIGRATION_SOURCE_SERVICE_ROLE_KEY", "IMPORT_SOURCE_SERVICE_ROLE_KEY"),
        description="仅用于迁移工具的遗留导入源特权密钥",
    )

    # 本地认证 / MySQL 配置
    database_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "MYSQL_DATABASE_URL"),
        description="业务数据库 URL，MySQL 是运行时迁移的目标",
    )
    mysql_host: Optional[str] = Field(
        default=None,
        validation_alias="MYSQL_HOST",
        description="可选的专用主机端 MySQL 主机地址，用于迁移脚本",
    )
    mysql_port: int = Field(
        default=3306,
        validation_alias="MYSQL_PORT",
        description="可选的专用主机端 MySQL 端口，用于迁移脚本",
    )
    mysql_user: Optional[str] = Field(
        default=None,
        validation_alias="MYSQL_USER",
        description="可选的专用主机端 MySQL 用户名，用于迁移脚本",
    )
    mysql_password: Optional[str] = Field(
        default=None,
        validation_alias="MYSQL_PASSWORD",
        description="可选的专用主机端 MySQL 密码，用于迁移脚本",
    )
    mysql_database: Optional[str] = Field(
        default=None,
        validation_alias="MYSQL_DATABASE",
        description="可选的专用主机端 MySQL 数据库名，用于迁移脚本",
    )
    mysql_connect_timeout: int = Field(
        default=10,
        validation_alias="MYSQL_CONNECT_TIMEOUT",
        description="可选的专用主机端 MySQL 连接超时时间（秒），用于迁移脚本",
    )
    auth_provider_mode: str = Field(
        default="niutrans_local",
        validation_alias="AUTH_PROVIDER_MODE",
    )
    auth_jwt_keys: str = Field(
        default="v1:change-me-local-dev-secret",
        validation_alias="AUTH_JWT_KEYS",
        description="逗号分隔的版本化签名密钥，格式如 v3:secret3,v2:secret2",
    )
    auth_jwt_issuer: str = Field(
        default="latextrans-local",
        validation_alias="AUTH_JWT_ISSUER",
    )
    auth_jwt_audience: str = Field(
        default="latextrans-api",
        validation_alias="AUTH_JWT_AUDIENCE",
    )
    auth_access_token_ttl_seconds: int = Field(
        default=28800,
        validation_alias="AUTH_ACCESS_TOKEN_TTL_SECONDS",
    )
    niutrans_auth_url: str = Field(
        default="https://niutrans.com/niutrans-auth/auth/login",
        validation_alias="NIUTRANS_AUTH_URL",
    )
    niutrans_login_url: str = Field(
        default="https://niutrans.com/login?active=0",
        validation_alias="NIUTRANS_LOGIN_URL",
    )
    niutrans_register_url: str = Field(
        default="https://niutrans.com/login?active=3",
        validation_alias="NIUTRANS_REGISTER_URL",
    )
    niutrans_account_url: str = Field(
        default="https://niutrans.com/login?active=0",
        validation_alias="NIUTRANS_ACCOUNT_URL",
    )
    niutrans_user_info_url: str = Field(
        default="https://niutrans.com/NiuTransConsole/user/getUserInfo",
        validation_alias="NIUTRANS_USER_INFO_URL",
        description="NiuTrans 账户用户信息端点，仅用于安全的 PDF 直译积分快照",
    )
    pdf_direct_translation_enabled: bool = Field(
        default=False,
        validation_alias="PDF_DIRECT_TRANSLATION_ENABLED",
        description="启用 PDF 直译工作区和 API 路由",
    )
    niutrans_doc_api_base_url: str = Field(
        default="https://api-doc.niutrans.com/documentTransApi",
        validation_alias="NIUTRANS_DOC_API_BASE_URL",
        description="NiuTrans 文档翻译 API 基础 URL，用于论文翻译端点",
    )
    niutrans_doc_api_app_id: Optional[str] = Field(
        default=None,
        validation_alias="NIUTRANS_DOC_API_APP_ID",
        description="产品级文档翻译 API 应用 ID，用于 NiuTrans 请求签名",
    )
    pdf_direct_poll_interval_seconds: float = Field(
        default=2.0,
        validation_alias="PDF_DIRECT_POLL_INTERVAL_SECONDS",
        description="PDF 直译任务状态检查的轮询间隔（秒）",
    )
    daily_latex_translation_quota_limit: int = Field(
        default=3,
        validation_alias="DAILY_LATEX_TRANSLATION_QUOTA_LIMIT",
        description="每位认证用户每日本地 LaTeX 翻译限额",
    )
    daily_latex_translation_quota_timezone: str = Field(
        default="Asia/Shanghai",
        validation_alias="DAILY_LATEX_TRANSLATION_QUOTA_TIMEZONE",
        description="本地每日 LaTeX 翻译配额重置的自然日时区",
    )
    local_admin_external_user_ids: list[str] = Field(
        default_factory=list,
        validation_alias="LOCAL_ADMIN_EXTERNAL_USER_IDS",
    )
    enable_legacy_import_readonly: bool = Field(
        default=False,
        validation_alias=AliasChoices("ENABLE_LEGACY_IMPORT_READONLY", "ENABLE_IMPORT_SOURCE_READONLY"),
    )
    migration_dry_run: bool = Field(
        default=False,
        validation_alias="MIGRATION_DRY_RUN",
    )

    
    # 加密配置
    encryption_key: Optional[str] = Field(
        default=None,
        validation_alias="ENCRYPTION_KEY",
        description="用于加密 API 密钥等敏感数据的密钥"
    )
    community_download_token_secret: Optional[str] = Field(
        default=None,
        validation_alias="COMMUNITY_DOWNLOAD_TOKEN_SECRET",
        description="用于短期社区论文下载令牌的签名密钥",
    )
    community_agent_tavily_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("COMMUNITY_AGENT_TAVILY_API_KEY", "COMMUNITY_AGENT_SEARCH_API_KEY"),
        description="社区 Agent 运行时基于 Tavily 的外部搜索 API 密钥",
    )
    community_agent_tavily_base_url: str = Field(
        default="https://api.tavily.com",
        validation_alias=AliasChoices("COMMUNITY_AGENT_TAVILY_BASE_URL", "COMMUNITY_AGENT_SEARCH_API_URL"),
        description="社区 Agent 运行时基于 Tavily 的外部搜索基础 URL",
    )
    community_baseline_seed_path: Optional[Path] = Field(
        default=None,
        validation_alias="COMMUNITY_BASELINE_SEED_PATH",
        description="可选的 JSON 种子文件，在没有公开论文时作为基准公共社区信息流",
    )
    community_feed_redis_url: Optional[str] = Field(
        default=None,
        validation_alias="COMMUNITY_FEED_REDIS_URL",
        description="可选的 Redis URL，用于共享公共社区信息流索引和缓存",
    )
    community_feed_redis_prefix: str = Field(
        default="feed",
        validation_alias="COMMUNITY_FEED_REDIS_PREFIX",
        description="共享公共社区信息流 Redis 状态的键前缀",
    )
    community_feed_cache_ttl_seconds: int = Field(
        default=60,
        validation_alias="COMMUNITY_FEED_CACHE_TTL_SECONDS",
        description="共享匿名公共信息流响应缓存条目的 TTL（秒）",
    )
    community_feed_rebuild_lock_ttl_seconds: int = Field(
        default=30,
        validation_alias="COMMUNITY_FEED_REBUILD_LOCK_TTL_SECONDS",
        description="保护公共信息流索引刷新的共享 Redis 重建锁 TTL（秒）",
    )
    community_feed_rebuild_interval_seconds: float = Field(
        default=300.0,
        validation_alias="COMMUNITY_FEED_REBUILD_INTERVAL_SECONDS",
        description="定期 Worker 端全量 Redis 公共信息流索引修复/重建运行的间隔；设为 0 禁用",
    )
    community_arxiv_metadata_repair_interval_seconds: float = Field(
        default=1800.0,
        validation_alias="COMMUNITY_ARXIV_METADATA_REPAIR_INTERVAL_SECONDS",
        description="定期 Worker 端修复已发布 arXiv 论文元数据的间隔，用于元数据因临时获取失败而回退的情况；设为 0 禁用",
    )
    community_arxiv_metadata_repair_limit: int = Field(
        default=20,
        validation_alias="COMMUNITY_ARXIV_METADATA_REPAIR_LIMIT",
        description="每次元数据修复扫描的已发布 arXiv 论文最大数量",
    )
    pipeline_timeout_seconds: float = Field(
        default=1800.0,
        validation_alias="PIPELINE_TIMEOUT_SECONDS",
        description="全局翻译流水线超时时间（秒）；设为 0 禁用",
    )
    admin_curation_task_wait_timeout_seconds: int = Field(
        default=1800,
        validation_alias="ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS",
        description="遗留管理员策展任务等待超时时间（秒）；设为 0 禁用阶段等待超时",
    )
    admin_curation_admission_timeout_seconds: int = Field(
        default=1800,
        validation_alias="ADMIN_CURATION_ADMISSION_TIMEOUT_SECONDS",
        description="管理员策展排队/准入阶段等待超时时间（秒）；设为 0 禁用",
    )
    admin_curation_execution_timeout_seconds: int = Field(
        default=7200,
        validation_alias="ADMIN_CURATION_EXECUTION_TIMEOUT_SECONDS",
        description="管理员策展处理/执行阶段等待超时时间（秒）；设为 0 禁用",
    )
    community_agent_product_enabled: bool = Field(
        default=False,
        validation_alias="COMMUNITY_AGENT_PRODUCT_ENABLED",
        description="当前产品模式中是否可直接使用保留的社区 Agent 产品路由",
    )
    community_curation_max_concurrent: int = Field(
        default=2,
        validation_alias="COMMUNITY_CURATION_MAX_CONCURRENT",
        description="最大并发的管理员社区策展任务数",
    )

    # 热门排行定时任务
    hot_ranking_cron_enabled: bool = Field(
        default=True,
        validation_alias="HOT_RANKING_CRON_ENABLED",
    )
    hot_ranking_cron_hour: int = Field(
        default=3,
        validation_alias="HOT_RANKING_CRON_HOUR",
    )
    hot_ranking_cron_minute: int = Field(
        default=7,
        validation_alias="HOT_RANKING_CRON_MINUTE",
    )
    hot_ranking_cron_lock_ttl_seconds: int = Field(
        default=43200,
        validation_alias="HOT_RANKING_CRON_LOCK_TTL_SECONDS",
    )

    # 自动收录
    hot_ranking_auto_intake_enabled: bool = Field(
        default=True,
        validation_alias="HOT_RANKING_AUTO_INTAKE_ENABLED",
    )
    hot_ranking_auto_intake_top_n: int = Field(
        default=20,
        validation_alias="HOT_RANKING_AUTO_INTAKE_TOP_N",
    )
    hot_ranking_auto_intake_min_score: float = Field(
        default=3.0,
        validation_alias="HOT_RANKING_AUTO_INTAKE_MIN_SCORE",
    )
    hot_ranking_auto_intake_default_window: str = Field(
        default="3d",
        validation_alias="HOT_RANKING_AUTO_INTAKE_DEFAULT_WINDOW",
    )
    hot_ranking_system_user_id: str = Field(
        default="",
        validation_alias="HOT_RANKING_SYSTEM_USER_ID",
    )
    hot_ranking_arxiv_id_dir: str = Field(
        default="",
        validation_alias="HOT_RANKING_ARXIV_ID_DIR",
    )

    backend_runtime_role: str = Field(
        default="all",
        validation_alias="BACKEND_RUNTIME_ROLE",
        description="当前后端进程的运行时角色: all|web|worker",
    )
    worker_runtime_api_base_url: str = Field(
        default="http://127.0.0.1:9002/api",
        validation_alias=AliasChoices("WORKER_RUNTIME_API_BASE_URL", "worker_runtime_api_base_url"),
        description="Web 运行时用于通知 Worker 运行时取消任务的回环 API 基础 URL",
    )
    internal_runtime_request_max_age_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "INTERNAL_RUNTIME_REQUEST_MAX_AGE_SECONDS",
            "internal_runtime_request_max_age_seconds",
        ),
        description="签名内部运行时控制请求所接受的最大时钟偏差",
    )
    admin_job_poll_interval_seconds: float = Field(
        default=5.0,
        validation_alias="ADMIN_JOB_POLL_INTERVAL_SECONDS",
        description="Worker/后台运行时用于认领排队管理任务的轮询间隔",
    )
    frontend_pressure_grace_seconds: float = Field(
        default=15.0,
        validation_alias="FRONTEND_PRESSURE_GRACE_SECONDS",
        description="在最近前端流量之后，Worker 回填准入应推迟的时长",
    )
    frontend_pressure_write_interval_seconds: float = Field(
        default=1.0,
        validation_alias="FRONTEND_PRESSURE_WRITE_INTERVAL_SECONDS",
        description="Web 运行时持久化前端压力心跳的最小间隔",
    )
    worker_process_nice_increment: int = Field(
        default=10,
        validation_alias="WORKER_PROCESS_NICE_INCREMENT",
        description="在支持该功能的平台上应用于 Worker 运行时的额外 nice 增量",
    )

    # LaTeX 编译器设置
    latex_bin_dir: Optional[str] = Field(
        default=None,
        validation_alias="LATEX_BIN_DIR"
    )

    # 存储路径（相对于项目根目录）
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")
    uploads_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "uploads")
    outputs_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "outputs")
    community_papers_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "community_papers")
    terms_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "terms")
    task_configs_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "task_configs")
    failed_tasks_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "failed_tasks")
    storage_backend_mode: str = Field(default="local_disk", validation_alias="STORAGE_BACKEND_MODE")
    storage_temp_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "tmp_storage",
        validation_alias="STORAGE_TEMP_DIR",
        description="用于 COS 上传等存储驱动工作流的临时暂存目录",
    )
    cos_bucket: Optional[str] = Field(default=None, validation_alias="COS_BUCKET")
    cos_region: Optional[str] = Field(default=None, validation_alias="COS_REGION")
    cos_secret_id: Optional[str] = Field(default=None, validation_alias="COS_SECRET_ID")
    cos_secret_key: Optional[str] = Field(default=None, validation_alias="COS_SECRET_KEY")
    cos_base_prefix: str = Field(default="latextrans-prod", validation_alias="COS_BASE_PREFIX")
    arxiv_raw_cache_enabled: bool = Field(default=False, validation_alias="ARXIV_RAW_CACHE_ENABLED")
    arxiv_raw_cache_prefix: str = Field(default="", validation_alias="ARXIV_RAW_CACHE_PREFIX")
    arxiv_raw_cache_signed_url_expires_seconds: int = Field(
        default=600,
        validation_alias="ARXIV_RAW_CACHE_SIGNED_URL_EXPIRES_SECONDS",
    )
    enable_task_config_capture: bool = Field(default=True, validation_alias="ENABLE_TASK_CONFIG_CAPTURE")

    # 文件上传设置
    max_upload_size: int = 50 * 1024 * 1024  # 50MB（以字节为单位）
    allowed_extensions: set = {".zip", ".tex", ".tar", ".tar.gz", ".tgz", ".rar"}

    # CORS 设置
    # 支持逗号分隔的 CORS_ORIGINS 环境变量。
    # 出于生产环境安全考虑，通配符被有意禁止。
    cors_origins: list[str] = Field(
    default_factory=lambda: [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://latextrans.pages.dev",
        "https://latextrans.online",
        "https://latextrans.niutrans.com",
        "https://paperx.niutrans.com",
    ],
    validation_alias="CORS_ORIGINS",
)


    # 任务队列设置
    max_concurrent_translations: int = Field(
        default=3,
        validation_alias="MAX_CONCURRENT_TRANSLATIONS"
    )
    max_user_active_tasks: int = Field(
        default=9,
        validation_alias="MAX_USER_ACTIVE_TASKS"
    )
    guest_task_ttl_hours: int = Field(
        default=2,
        validation_alias="GUEST_TASK_TTL_HOURS"
    )

    # SMTP / 邮件通知设置（全部可选）
    smtp_host: Optional[str] = Field(default=None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, validation_alias="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, validation_alias="SMTP_PASSWORD")
    smtp_from: Optional[str] = Field(
        default=None,
        validation_alias="SMTP_FROM",
        description="发件人地址；未设置时默认使用 SMTP_USER"
    )

    # 全局 LLM API 并发限制（跨所有任务和所有用户）
    # 将此值设置为 LLM 提供商允许的最大并发请求数。
    # - NVIDIA NIM 免费层：~40 RPM → 使用 30
    # - OpenAI Tier 1：~500 RPM → 使用 50-100
    # - 自托管 Triton NIM：无硬限制 → 使用 100-200
    llm_max_concurrent_requests: int = Field(
        default=10,
        validation_alias="LLM_MAX_CONCURRENT_REQUESTS",
        description="总并发出站 LLM API 请求的硬上限（全局，所有任务）"
    )
    community_translation_llm_max_concurrent_requests: int = Field(
        default=10,
        validation_alias="COMMUNITY_TRANSLATION_LLM_MAX_CONCURRENT_REQUESTS",
        description="生产环境社区/管理员策展翻译的每任务出站 LLM 请求上限",
    )
    max_concurrent_compilations: int = Field(
        default=1,
        validation_alias="MAX_CONCURRENT_COMPILATIONS",
        description="单个 Worker 中并发的 LaTeX 编译子进程硬上限"
    )
    async_blocking_wrappers_enabled: bool = Field(
        default=True,
        validation_alias="ASYNC_BLOCKING_WRAPPERS_ENABLED",
        description="在异步路径中为阻塞操作启用 asyncio.to_thread 包装器"
    )
    db_execution_mode: str = Field(
        default="per_call_client",
        validation_alias="DB_EXECUTION_MODE",
        description="数据库线程执行策略: per_call_client|shared_client"
    )

    # RAG 术语设置
    rag_terminology_enabled: bool = Field(
        default=False,
        validation_alias="RAG_TERMINOLOGY_ENABLED",
        description="全局启用 RAG 术语流水线。禁用时，用户的选择加入将被忽略"
    )
    rag_terminology_top_n: int = Field(
        default=10,
        validation_alias="RAG_TERMINOLOGY_TOP_N",
        description="每个分块注入的术语表最大数量"
    )
    rag_terminology_milvus_uri: str | None = Field(
        default=None,
        validation_alias="RAG_TERMINOLOGY_MILVUS_URI",
        description="Milvus 服务器 URI（如 http://localhost:19530）。向量检索必需"
    )
    rag_terminology_milvus_collection: str = Field(
        default="terminology_terms",
        validation_alias="RAG_TERMINOLOGY_MILVUS_COLLECTION",
        description="用于存储已审核术语嵌入向量的 Milvus 集合名"
    )
    rag_terminology_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="RAG_TERMINOLOGY_EMBEDDING_MODEL",
        description="生成术语和查询向量的嵌入模型"
    )
    rag_terminology_rerank_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        validation_alias="RAG_TERMINOLOGY_RERANK_MODEL",
        description="对检索到的术语进行重排序的 Cross-Encoder 模型"
    )
    rag_terminology_bm25_refresh_interval: int = Field(
        default=60,
        validation_alias="RAG_TERMINOLOGY_BM25_REFRESH_INTERVAL",
        description="BM25 索引刷新间隔（秒）"
    )
    rag_terminology_max_upload_size_mb: int = Field(
        default=5,
        validation_alias="RAG_TERMINOLOGY_MAX_UPLOAD_SIZE_MB",
        description="CSV/BibTeX 术语文件的最大上传大小（MB）"
    )

    # 服务器设置
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=("settings_",),
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        """解析 CORS 来源配置，支持字符串、列表、元组和集合格式"""
        if value is None:
            return value

        if isinstance(value, str):
            normalized = value.strip()
            if normalized.startswith("["):
                try:
                    parsed = json.loads(normalized)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    origins = [str(item).strip() for item in parsed if str(item).strip()]
                else:
                    origins = [item.strip().strip("\"'") for item in normalized.split(",") if item.strip()]
            else:
                origins = [item.strip().strip("\"'") for item in normalized.split(",") if item.strip()]
        elif isinstance(value, (list, tuple, set)):
            origins = [str(item).strip() for item in value if str(item).strip()]
        else:
            return value

        if any(origin == "*" for origin in origins):
            raise ValueError("CORS_ORIGINS cannot include wildcard '*'.")

        return origins

    @field_validator("db_execution_mode", mode="before")
    @classmethod
    def _parse_db_execution_mode(cls, value):
        """解析数据库执行模式，仅支持 per_call_client 和 shared_client"""
        mode = str(value or "per_call_client").strip().lower()
        if mode not in {"per_call_client", "shared_client"}:
            return "per_call_client"
        return mode

    @field_validator("backend_runtime_role", mode="before")
    @classmethod
    def _parse_backend_runtime_role(cls, value):
        """解析后端运行时角色，仅支持 all、web 和 worker"""
        role = str(value or "all").strip().lower()
        if role not in {"all", "web", "worker"}:
            return "all"
        return role

    @field_validator("local_admin_external_user_ids", mode="before")
    @classmethod
    def _parse_local_admin_external_user_ids(cls, value):
        """解析本地管理员外部用户 ID 列表，支持逗号分隔字符串、列表、元组和集合格式"""
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return []
    
    def __init__(self, **kwargs):
        """初始化设置并确保所有必要目录存在"""
        super().__init__(**kwargs)
        # 确保所有目录存在
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.community_papers_dir.mkdir(parents=True, exist_ok=True)
        self.terms_dir.mkdir(parents=True, exist_ok=True)
        self.task_configs_dir.mkdir(parents=True, exist_ok=True)
        self.failed_tasks_dir.mkdir(parents=True, exist_ok=True)
        self.storage_temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def local_storage_root(self) -> Path:
        """暴露本地磁盘后端用于开发/本地回退的持久化根路径"""
        return self.base_dir

    def get_llm_config(self) -> Dict[str, Any]:
        """获取 LLM API 配置，以字典形式返回"""
        config: Dict[str, Any] = {
            "api_key": self.llm_api_key,
            "base_url": self.llm_base_url,
            "model": self.llm_model,
            "timeout": self.llm_timeout,
            "model_context_tokens": self.model_context_tokens,
            "prompt_reserve_tokens": self.prompt_reserve_tokens,
            "reserve_count": self.llm_pool_reserve_count,
            "default_member_concurrency": self.llm_member_default_concurrency,
        }
        if self.llm_shared_pool_concurrency:
            config["shared_pool_concurrency"] = self.llm_shared_pool_concurrency

        members = self.get_llm_system_pool_members()
        if members:
            primary = members[0]
            config.update(
                {
                    "api_key": primary["api_key"],
                    "base_url": primary["base_url"],
                    "pool_mode": "system_managed",
                    "pool_members": members,
                    "pool_routing_key": self._compute_llm_pool_routing_key(members),
                }
            )
        return config

    @staticmethod
    def _normalize_chat_completions_url(value: Optional[str]) -> str:
        """将给定的 URL 标准化为完整的 /chat/completions 端点路径"""
        normalized = str(value or "").strip().rstrip("/")
        if not normalized:
            return ""
        if normalized.endswith("/chat/completions"):
            return normalized
        if normalized.endswith("/v1"):
            return f"{normalized}/chat/completions"
        return f"{normalized}/v1/chat/completions"

    def get_llm_system_pool_groups(self) -> list[dict[str, Any]]:
        """从配置中解析 LLM 系统池组列表"""
        raw = str(self.llm_system_pool_groups_json or "").strip()
        if not raw:
            return []

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []

        if not isinstance(parsed, list):
            return []

        groups: list[dict[str, Any]] = []
        for index, item in enumerate(parsed):
            if not isinstance(item, dict):
                continue
            base_url = self._normalize_chat_completions_url(item.get("base_url"))
            api_keys = [
                str(key).strip()
                for key in (item.get("api_keys") or [])
                if str(key).strip()
            ]
            if not base_url or not api_keys:
                continue
            groups.append(
                {
                    "group_id": str(item.get("group_id") or f"group-{index}"),
                    "base_url": base_url,
                    "api_keys": api_keys,
                    "account_id": str(item.get("account_id") or ""),
                    "quota_scope": str(item.get("quota_scope") or "shared"),
                    "concurrency": int(item.get("concurrency") or self.llm_member_default_concurrency),
                }
            )
        return groups

    def get_llm_system_pool_members(self) -> list[dict[str, Any]]:
        """从配置中解析 LLM 系统池成员列表，优先使用直接成员配置，回退到池组配置"""
        raw_members = str(self.llm_members_json or "").strip()
        if raw_members:
            try:
                parsed_members = json.loads(raw_members)
            except json.JSONDecodeError:
                parsed_members = None
            if isinstance(parsed_members, list):
                members: list[dict[str, Any]] = []
                for index, item in enumerate(parsed_members):
                    if not isinstance(item, dict):
                        continue
                    base_url = self._normalize_chat_completions_url(item.get("base_url"))
                    api_key = str(item.get("api_key") or "").strip()
                    if not base_url or not api_key:
                        continue
                    members.append(
                        {
                            "member_id": str(item.get("member_id") or f"member-{index}"),
                            "base_url": base_url,
                            "api_key": api_key,
                            "account_id": str(item.get("account_id") or ""),
                            "quota_scope": str(item.get("quota_scope") or "shared"),
                            "concurrency": int(item.get("concurrency") or self.llm_member_default_concurrency),
                            "reserve": bool(item.get("reserve") or False),
                        }
                    )
                if members:
                    return members

        members: list[dict[str, Any]] = []
        for group_index, group in enumerate(self.get_llm_system_pool_groups()):
            group_id = str(group.get("group_id") or f"group-{group_index}")
            for key_index, api_key in enumerate(group.get("api_keys") or []):
                members.append(
                    {
                        "member_id": f"{group_id}-member-{key_index}",
                        "base_url": group["base_url"],
                        "api_key": api_key,
                        "account_id": str(group.get("account_id") or ""),
                        "quota_scope": str(group.get("quota_scope") or "shared"),
                        "concurrency": int(group.get("concurrency") or self.llm_member_default_concurrency),
                    }
                )
        return members

    @staticmethod
    def _compute_llm_pool_routing_key(members: list[dict[str, Any]]) -> str:
        """基于成员列表的归一化哈希值计算 LLM 池路由键"""
        normalized = [
            (
                str(member.get("member_id") or "").strip(),
                str(member.get("base_url") or "").strip(),
                str(member.get("api_key") or "").strip(),
                str(member.get("account_id") or "").strip(),
                str(member.get("quota_scope") or "").strip(),
            )
            for member in members
        ]
        import hashlib

        digest = hashlib.md5(repr(sorted(normalized)).encode("utf-8")).hexdigest()
        return f"system-pool:{digest}"
    
    def load_toml_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        从 TOML 文件中加载额外的配置

        参数：
            config_path: TOML 配置文件的路径，默认为 'config/default.toml'

        返回：
            配置字典
        """
        if config_path is None:
            config_path = self.base_dir / "prototype_system" / "config" / "default.toml"
        
        if Path(config_path).exists():
            return toml.load(config_path)
        else:
            return {}


# 全局设置实例
settings = Settings()


def get_settings() -> Settings:
    """获取应用程序全局设置"""
    return settings


def get_llm_config() -> Dict[str, Any]:
    """获取 LLM API 配置字典"""
    return settings.get_llm_config()


def get_default_translation_model() -> str:
    """从运行时 LLM 配置中获取默认翻译模型名称"""
    return settings.llm_model
