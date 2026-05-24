"""
Backend Configuration Module

Loads settings from environment variables and TOML config files.
Provides configuration for LLM API, storage paths, and task status enums.
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
    """Task status enumeration"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED_COMPILATION = "failed_compilation"
    STRUCTURE_INVALID = "structure_invalid"
    FAILED = "failed"


class CompilationStage(str, Enum):
    """Compilation stage enumeration"""
    IDLE = "idle"
    PARSING = "parsing"
    TRANSLATING = "translating"
    COMPILING = "compiling"
    COMPILATION_FAILED = "compilation_failed"
    DONE = "done"


class Settings(BaseSettings):
    """Application settings"""
    
    # Application Info
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
        description="Optional JSON array describing system-managed LLM pool groups: [{base_url, api_keys: []}, ...]",
    )
    llm_members_json: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_MEMBERS_JSON", "llm_members_json"),
        description="Optional JSON array describing LLM members: [{member_id, base_url, api_key, account_id, quota_scope, concurrency, reserve}, ...]",
    )
    llm_pool_reserve_count: int = Field(
        default=1,
        validation_alias=AliasChoices("LLM_POOL_RESERVE_COUNT", "llm_pool_reserve_count"),
        description="Healthy LLM members to reserve for failover/spikes when computing community task capacity.",
    )
    llm_member_default_concurrency: int = Field(
        default=1,
        validation_alias=AliasChoices("LLM_MEMBER_DEFAULT_CONCURRENCY", "llm_member_default_concurrency"),
        description="Default per-member outbound LLM request concurrency.",
    )
    llm_shared_pool_concurrency: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("LLM_SHARED_POOL_CONCURRENCY", "llm_shared_pool_concurrency"),
        description="Optional shared pool concurrency limit across configured LLM members.",
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
    
    # Translation Settings
    target_language: str = "ch"
    source_language: str = "en"
    
    # Legacy import-source configuration
    migration_source_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("MIGRATION_SOURCE_URL", "IMPORT_SOURCE_URL"),
    )
    migration_source_anon_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("MIGRATION_SOURCE_ANON_KEY", "IMPORT_SOURCE_ANON_KEY"),
        description="Legacy import-source public key retained only for migration tooling.",
    )
    migration_source_service_role_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("MIGRATION_SOURCE_SERVICE_ROLE_KEY", "IMPORT_SOURCE_SERVICE_ROLE_KEY"),
        description="Legacy import-source privileged key retained only for migration tooling.",
    )

    # Local auth / MySQL configuration
    database_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "MYSQL_DATABASE_URL"),
        description="Business database URL. MySQL is the target for runtime migration.",
    )
    mysql_host: Optional[str] = Field(
        default=None,
        validation_alias="MYSQL_HOST",
        description="Optional dedicated host-side MySQL host for migration scripts.",
    )
    mysql_port: int = Field(
        default=3306,
        validation_alias="MYSQL_PORT",
        description="Optional dedicated host-side MySQL port for migration scripts.",
    )
    mysql_user: Optional[str] = Field(
        default=None,
        validation_alias="MYSQL_USER",
        description="Optional dedicated host-side MySQL user for migration scripts.",
    )
    mysql_password: Optional[str] = Field(
        default=None,
        validation_alias="MYSQL_PASSWORD",
        description="Optional dedicated host-side MySQL password for migration scripts.",
    )
    mysql_database: Optional[str] = Field(
        default=None,
        validation_alias="MYSQL_DATABASE",
        description="Optional dedicated host-side MySQL database for migration scripts.",
    )
    mysql_connect_timeout: int = Field(
        default=10,
        validation_alias="MYSQL_CONNECT_TIMEOUT",
        description="Optional dedicated host-side MySQL connect timeout in seconds for migration scripts.",
    )
    auth_provider_mode: str = Field(
        default="niutrans_local",
        validation_alias="AUTH_PROVIDER_MODE",
    )
    auth_jwt_keys: str = Field(
        default="v1:change-me-local-dev-secret",
        validation_alias="AUTH_JWT_KEYS",
        description="Comma-separated versioned signing keys, e.g. v3:secret3,v2:secret2",
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
        description="NiuTrans account user-info endpoint used only for safe PDF direct credit snapshots.",
    )
    daily_latex_translation_quota_limit: int = Field(
        default=3,
        validation_alias="DAILY_LATEX_TRANSLATION_QUOTA_LIMIT",
        description="Daily local LaTeX translation items per authenticated user.",
    )
    daily_latex_translation_quota_timezone: str = Field(
        default="Asia/Shanghai",
        validation_alias="DAILY_LATEX_TRANSLATION_QUOTA_TIMEZONE",
        description="Natural-day timezone for local daily LaTeX translation quota reset.",
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

    
    # Encryption Configuration
    encryption_key: Optional[str] = Field(
        default=None,
        validation_alias="ENCRYPTION_KEY",
        description="Key for encrypting sensitive data like API keys"
    )
    community_download_token_secret: Optional[str] = Field(
        default=None,
        validation_alias="COMMUNITY_DOWNLOAD_TOKEN_SECRET",
        description="Signing secret for short-lived community paper download tokens",
    )
    community_agent_tavily_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("COMMUNITY_AGENT_TAVILY_API_KEY", "COMMUNITY_AGENT_SEARCH_API_KEY"),
        description="API key for Tavily-backed external search in the community agent runtime.",
    )
    community_agent_tavily_base_url: str = Field(
        default="https://api.tavily.com",
        validation_alias=AliasChoices("COMMUNITY_AGENT_TAVILY_BASE_URL", "COMMUNITY_AGENT_SEARCH_API_URL"),
        description="Base URL for Tavily-backed external search in the community agent runtime.",
    )
    community_baseline_seed_path: Optional[Path] = Field(
        default=None,
        validation_alias="COMMUNITY_BASELINE_SEED_PATH",
        description="Optional JSON seed file used as a baseline public community feed when no public papers exist.",
    )
    community_feed_redis_url: Optional[str] = Field(
        default=None,
        validation_alias="COMMUNITY_FEED_REDIS_URL",
        description="Optional Redis URL used for shared public community feed indexes and cache.",
    )
    community_feed_redis_prefix: str = Field(
        default="feed",
        validation_alias="COMMUNITY_FEED_REDIS_PREFIX",
        description="Key prefix for shared public community feed Redis state.",
    )
    community_feed_cache_ttl_seconds: int = Field(
        default=60,
        validation_alias="COMMUNITY_FEED_CACHE_TTL_SECONDS",
        description="TTL in seconds for shared anonymous public feed response cache entries.",
    )
    community_feed_rebuild_lock_ttl_seconds: int = Field(
        default=30,
        validation_alias="COMMUNITY_FEED_REBUILD_LOCK_TTL_SECONDS",
        description="TTL in seconds for the shared Redis rebuild lock guarding public feed index refreshes.",
    )
    community_feed_rebuild_interval_seconds: float = Field(
        default=300.0,
        validation_alias="COMMUNITY_FEED_REBUILD_INTERVAL_SECONDS",
        description="Periodic worker-side interval for full Redis public feed index repair/rebuild runs; set to 0 to disable.",
    )
    community_arxiv_metadata_repair_interval_seconds: float = Field(
        default=1800.0,
        validation_alias="COMMUNITY_ARXIV_METADATA_REPAIR_INTERVAL_SECONDS",
        description="Periodic worker-side interval for repairing published arXiv papers whose metadata fell back after a transient fetch failure; set to 0 to disable.",
    )
    community_arxiv_metadata_repair_limit: int = Field(
        default=20,
        validation_alias="COMMUNITY_ARXIV_METADATA_REPAIR_LIMIT",
        description="Maximum published arXiv papers to scan per metadata repair pass.",
    )
    pipeline_timeout_seconds: float = Field(
        default=1800.0,
        validation_alias="PIPELINE_TIMEOUT_SECONDS",
        description="Global translation pipeline timeout in seconds; set to 0 to disable.",
    )
    admin_curation_task_wait_timeout_seconds: int = Field(
        default=1800,
        validation_alias="ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS",
        description="Legacy admin curation task wait timeout in seconds; set to 0 to disable stage wait timeouts.",
    )
    admin_curation_admission_timeout_seconds: int = Field(
        default=1800,
        validation_alias="ADMIN_CURATION_ADMISSION_TIMEOUT_SECONDS",
        description="Admin curation queued/admission-stage wait timeout in seconds; set to 0 to disable.",
    )
    admin_curation_execution_timeout_seconds: int = Field(
        default=7200,
        validation_alias="ADMIN_CURATION_EXECUTION_TIMEOUT_SECONDS",
        description="Admin curation processing/execution-stage wait timeout in seconds; set to 0 to disable.",
    )
    community_agent_product_enabled: bool = Field(
        default=False,
        validation_alias="COMMUNITY_AGENT_PRODUCT_ENABLED",
        description="Whether the retained community-agent product routes are directly usable in the current product mode.",
    )
    community_curation_max_concurrent: int = Field(
        default=2,
        validation_alias="COMMUNITY_CURATION_MAX_CONCURRENT",
        description="Maximum concurrent admin community curation jobs.",
    )
    backend_runtime_role: str = Field(
        default="all",
        validation_alias="BACKEND_RUNTIME_ROLE",
        description="Runtime role for the current backend process: all|web|worker.",
    )
    worker_runtime_api_base_url: str = Field(
        default="http://127.0.0.1:9002/api",
        validation_alias=AliasChoices("WORKER_RUNTIME_API_BASE_URL", "worker_runtime_api_base_url"),
        description="Loopback API base URL used by the web runtime to signal worker runtime task cancellation.",
    )
    internal_runtime_request_max_age_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "INTERNAL_RUNTIME_REQUEST_MAX_AGE_SECONDS",
            "internal_runtime_request_max_age_seconds",
        ),
        description="Maximum clock skew accepted for signed internal runtime control requests.",
    )
    admin_job_poll_interval_seconds: float = Field(
        default=5.0,
        validation_alias="ADMIN_JOB_POLL_INTERVAL_SECONDS",
        description="Polling interval used by worker/background runtimes to claim queued admin jobs.",
    )
    frontend_pressure_grace_seconds: float = Field(
        default=15.0,
        validation_alias="FRONTEND_PRESSURE_GRACE_SECONDS",
        description="How long worker backfill admission should defer after recent frontend traffic.",
    )
    frontend_pressure_write_interval_seconds: float = Field(
        default=1.0,
        validation_alias="FRONTEND_PRESSURE_WRITE_INTERVAL_SECONDS",
        description="Minimum interval between persisted frontend-pressure heartbeats from the web runtime.",
    )
    worker_process_nice_increment: int = Field(
        default=10,
        validation_alias="WORKER_PROCESS_NICE_INCREMENT",
        description="Additional niceness applied to worker runtimes where the platform supports it.",
    )
    
    # LaTeX Compiler Settings
    latex_bin_dir: Optional[str] = Field(
        default=None,
        validation_alias="LATEX_BIN_DIR"
    )
    
    # Storage Paths (relative to project root)
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
        description="Temporary staging directory for storage-backed workflows such as COS uploads.",
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
    
    # File Upload Settings
    max_upload_size: int = 50 * 1024 * 1024  # 50MB in bytes
    allowed_extensions: set = {".zip", ".tex", ".tar", ".tar.gz", ".tgz", ".rar"}
    
    # CORS Settings
    # Supports comma-separated CORS_ORIGINS env.
    # Wildcard is intentionally disallowed for production safety.
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

    
    # Task Queue Settings
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

    # SMTP / Email Notification Settings (all optional)
    smtp_host: Optional[str] = Field(default=None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, validation_alias="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, validation_alias="SMTP_PASSWORD")
    smtp_from: Optional[str] = Field(
        default=None,
        validation_alias="SMTP_FROM",
        description="Sender address; defaults to SMTP_USER if not set"
    )

    # Global LLM API concurrency limit (across all tasks and all users)
    # Set this to the max concurrent requests your LLM provider allows.
    # - NVIDIA NIM free tier: ~40 RPM → use 30
    # - OpenAI Tier 1: ~500 RPM → use 50-100
    # - Self-hosted Triton NIM: no hard limit → use 100-200
    llm_max_concurrent_requests: int = Field(
        default=10,
        validation_alias="LLM_MAX_CONCURRENT_REQUESTS",
        description="Hard ceiling on total concurrent outbound LLM API requests (global, all tasks)"
    )
    community_translation_llm_max_concurrent_requests: int = Field(
        default=10,
        validation_alias="COMMUNITY_TRANSLATION_LLM_MAX_CONCURRENT_REQUESTS",
        description="Per-task outbound LLM request cap for production community/admin curation translations.",
    )
    max_concurrent_compilations: int = Field(
        default=1,
        validation_alias="MAX_CONCURRENT_COMPILATIONS",
        description="Hard ceiling on concurrent LaTeX compilation subprocesses in a single worker."
    )
    async_blocking_wrappers_enabled: bool = Field(
        default=True,
        validation_alias="ASYNC_BLOCKING_WRAPPERS_ENABLED",
        description="Enable asyncio.to_thread wrappers for blocking operations in async paths."
    )
    db_execution_mode: str = Field(
        default="per_call_client",
        validation_alias="DB_EXECUTION_MODE",
        description="DB threaded execution strategy: per_call_client|shared_client"
    )

    # RAG Terminology Settings
    rag_terminology_enabled: bool = Field(
        default=False,
        validation_alias="RAG_TERMINOLOGY_ENABLED",
        description="Enable the RAG terminology pipeline globally. When disabled, user opt-in is ignored."
    )
    rag_terminology_top_n: int = Field(
        default=10,
        validation_alias="RAG_TERMINOLOGY_TOP_N",
        description="Maximum number of glossary terms to inject per chunk."
    )
    rag_terminology_milvus_uri: str | None = Field(
        default=None,
        validation_alias="RAG_TERMINOLOGY_MILVUS_URI",
        description="Milvus server URI (e.g. http://localhost:19530). Required for vector retrieval."
    )
    rag_terminology_milvus_collection: str = Field(
        default="terminology_terms",
        validation_alias="RAG_TERMINOLOGY_MILVUS_COLLECTION",
        description="Milvus collection name for approved term embeddings."
    )
    rag_terminology_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="RAG_TERMINOLOGY_EMBEDDING_MODEL",
        description="Embedding model for generating term and query vectors."
    )
    rag_terminology_rerank_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        validation_alias="RAG_TERMINOLOGY_RERANK_MODEL",
        description="Cross-Encoder model for reranking retrieved terms."
    )
    rag_terminology_bm25_refresh_interval: int = Field(
        default=60,
        validation_alias="RAG_TERMINOLOGY_BM25_REFRESH_INTERVAL",
        description="BM25 index refresh interval in seconds."
    )
    rag_terminology_max_upload_size_mb: int = Field(
        default=5,
        validation_alias="RAG_TERMINOLOGY_MAX_UPLOAD_SIZE_MB",
        description="Maximum upload file size in MB for CSV/BibTeX terminology files."
    )

    # Server Settings
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
        mode = str(value or "per_call_client").strip().lower()
        if mode not in {"per_call_client", "shared_client"}:
            return "per_call_client"
        return mode

    @field_validator("backend_runtime_role", mode="before")
    @classmethod
    def _parse_backend_runtime_role(cls, value):
        role = str(value or "all").strip().lower()
        if role not in {"all", "web", "worker"}:
            return "all"
        return role

    @field_validator("local_admin_external_user_ids", mode="before")
    @classmethod
    def _parse_local_admin_external_user_ids(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return []
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure all directories exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.community_papers_dir.mkdir(parents=True, exist_ok=True)
        self.terms_dir.mkdir(parents=True, exist_ok=True)
        self.task_configs_dir.mkdir(parents=True, exist_ok=True)
        self.failed_tasks_dir.mkdir(parents=True, exist_ok=True)
        self.storage_temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def local_storage_root(self) -> Path:
        """Expose the durable root the local disk backend uses for dev/local fallback."""
        return self.base_dir
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM API configuration as a dictionary"""
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
        normalized = str(value or "").strip().rstrip("/")
        if not normalized:
            return ""
        if normalized.endswith("/chat/completions"):
            return normalized
        if normalized.endswith("/v1"):
            return f"{normalized}/chat/completions"
        return f"{normalized}/v1/chat/completions"

    def get_llm_system_pool_groups(self) -> list[dict[str, Any]]:
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
        Load additional configuration from TOML file
        
        Args:
            config_path: Path to TOML config file. Defaults to 'config/default.toml'
        
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            config_path = self.base_dir / "prototype_system" / "config" / "default.toml"
        
        if Path(config_path).exists():
            return toml.load(config_path)
        else:
            return {}


# Global settings instance
settings = Settings()


# Helper function to get settings
def get_settings() -> Settings:
    """Get application settings"""
    return settings


# Helper function to get LLM config
def get_llm_config() -> Dict[str, Any]:
    """Get LLM API configuration as a dictionary"""
    return settings.get_llm_config()


def get_default_translation_model() -> str:
    """Get the default translation model from the runtime LLM config."""
    return settings.llm_model
