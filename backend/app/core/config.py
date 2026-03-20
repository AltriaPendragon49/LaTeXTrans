"""
Backend Configuration Module

Loads settings from environment variables and TOML config files.
Provides configuration for LLM API, storage paths, and task status enums.
"""

import os
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
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
    app_name: str = "LaTeXTrans Backend"
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
    
    # Supabase Configuration
    supabase_url: Optional[str] = Field(
        default=None,
        validation_alias="SUPABASE_URL"
    )
    supabase_anon_key: Optional[str] = Field(
        default=None,
        validation_alias="SUPABASE_ANON_KEY",
        description="Anon key for user operations (RLS enforced)"
    )
    supabase_service_role_key: Optional[str] = Field(
        default=None,
        validation_alias="SUPABASE_SERVICE_ROLE_KEY",
        description="Service Role Key for admin operations (bypasses RLS)"
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
    community_baseline_seed_path: Optional[Path] = Field(
        default=None,
        validation_alias="COMMUNITY_BASELINE_SEED_PATH",
        description="Optional JSON seed file used as a baseline public community feed when no public papers exist.",
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
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://latextrans.pages.dev",
        "https://latextrans.online",
        "https://latextrans.niutrans.com",
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
    max_concurrent_compilations: int = Field(
        default=1,
        validation_alias="MAX_CONCURRENT_COMPILATIONS",
        description="Hard ceiling on concurrent LaTeX compilation subprocesses in a single worker."
    )
    async_compiler_enabled: bool = Field(
        default=True,
        validation_alias="ASYNC_COMPILER_ENABLED",
        description="Enable async subprocess-based compiler execution path."
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

    # Compile-first structural fallback controls (deprecated runtime semantics)
    enable_compile_first_structural_fallback: bool = Field(
        default=True,
        validation_alias="ENABLE_COMPILE_FIRST_STRUCTURAL_FALLBACK",
        description="Deprecated compatibility flag. Structural candidates are no longer rolled back during validation."
    )
    enable_post_compile_target_language_fallback: bool = Field(
        default=True,
        validation_alias="ENABLE_POST_COMPILE_TARGET_LANGUAGE_FALLBACK",
        description="Enable deterministic target-language fallback after an initial compile failure."
    )
    structural_fallback_ratio_cap: float = Field(
        default=0.38,
        validation_alias="STRUCTURAL_FALLBACK_RATIO_CAP",
        description="Preferred fallback ratio cap (soft/hard behavior controlled by STRUCTURAL_FALLBACK_CAP_MODE)"
    )
    structural_fallback_cap_mode: str = Field(
        default="soft",
        validation_alias="STRUCTURAL_FALLBACK_CAP_MODE",
        description="Fallback ratio cap mode: soft or hard"
    )

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=("settings_",),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        if value is None:
            return value

        if isinstance(value, str):
            origins = [item.strip() for item in value.split(",") if item.strip()]
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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure all directories exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.community_papers_dir.mkdir(parents=True, exist_ok=True)
        self.terms_dir.mkdir(parents=True, exist_ok=True)
        self.task_configs_dir.mkdir(parents=True, exist_ok=True)
        self.failed_tasks_dir.mkdir(parents=True, exist_ok=True)
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM API configuration as a dictionary"""
        return {
            "api_key": self.llm_api_key,
            "base_url": self.llm_base_url,
            "model": self.llm_model,
            "timeout": self.llm_timeout,
            "model_context_tokens": self.model_context_tokens,
            "prompt_reserve_tokens": self.prompt_reserve_tokens,
        }
    
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
