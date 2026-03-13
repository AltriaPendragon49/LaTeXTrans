"""
Backend Configuration Module

Loads settings from environment variables and TOML config files.
Provides configuration for LLM API, storage paths, and task status enums.
"""

import os
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path
from pydantic_settings import BaseSettings
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
        env="LLM_API_KEY"
    )
    llm_base_url: str = Field(
        env="LLM_BASE_URL"
    )
    llm_model: str = Field(
        env="LLM_MODEL"
    )
    llm_timeout: int = Field(
        default=60,
        env="LLM_TIMEOUT"
    )
    
    # Translation Settings
    target_language: str = "ch"
    source_language: str = "en"
    
    # Supabase Configuration
    supabase_url: Optional[str] = Field(
        default=None,
        env="SUPABASE_URL"
    )
    supabase_anon_key: Optional[str] = Field(
        default=None,
        env="SUPABASE_ANON_KEY",
        description="Anon key for user operations (RLS enforced)"
    )
    supabase_service_role_key: Optional[str] = Field(
        default=None,
        env="SUPABASE_SERVICE_ROLE_KEY",
        description="Service Role Key for admin operations (bypasses RLS)"
    )

    
    # Encryption Configuration
    encryption_key: Optional[str] = Field(
        default=None,
        env="ENCRYPTION_KEY",
        description="Key for encrypting sensitive data like API keys"
    )
    
    # LaTeX Compiler Settings
    latex_bin_dir: Optional[str] = Field(
        default=None,
        env="LATEX_BIN_DIR"
    )
    
    # Storage Paths (relative to project root)
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")
    uploads_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "uploads")
    outputs_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "outputs")
    terms_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "terms")
    task_configs_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "task_configs")
    failed_tasks_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "failed_tasks")
    enable_task_config_capture: bool = Field(default=True, env="ENABLE_TASK_CONFIG_CAPTURE")
    
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
        ],
        env="CORS_ORIGINS",
    )
    
    # Task Queue Settings
    max_concurrent_translations: int = Field(
        default=3,
        env="MAX_CONCURRENT_TRANSLATIONS"
    )
    max_user_active_tasks: int = Field(
        default=9,
        env="MAX_USER_ACTIVE_TASKS"
    )
    guest_task_ttl_hours: int = Field(
        default=2,
        env="GUEST_TASK_TTL_HOURS"
    )

    # SMTP / Email Notification Settings (all optional)
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    smtp_from: Optional[str] = Field(
        default=None,
        env="SMTP_FROM",
        description="Sender address; defaults to SMTP_USER if not set"
    )

    # Global LLM API concurrency limit (across all tasks and all users)
    # Set this to the max concurrent requests your LLM provider allows.
    # - NVIDIA NIM free tier: ~40 RPM → use 30
    # - OpenAI Tier 1: ~500 RPM → use 50-100
    # - Self-hosted Triton NIM: no hard limit → use 100-200
    llm_max_concurrent_requests: int = Field(
        default=30,
        env="LLM_MAX_CONCURRENT_REQUESTS",
        description="Hard ceiling on total concurrent outbound LLM API requests (global, all tasks)"
    )
    max_concurrent_compilations: int = Field(
        default=1,
        env="MAX_CONCURRENT_COMPILATIONS",
        description="Hard ceiling on concurrent LaTeX compilation subprocesses in a single worker."
    )
    async_compiler_enabled: bool = Field(
        default=True,
        env="ASYNC_COMPILER_ENABLED",
        description="Enable async subprocess-based compiler execution path."
    )
    async_blocking_wrappers_enabled: bool = Field(
        default=True,
        env="ASYNC_BLOCKING_WRAPPERS_ENABLED",
        description="Enable asyncio.to_thread wrappers for blocking operations in async paths."
    )
    db_execution_mode: str = Field(
        default="per_call_client",
        env="DB_EXECUTION_MODE",
        description="DB threaded execution strategy: per_call_client|shared_client"
    )

    # Compile-first structural fallback controls (gray rollout)
    enable_compile_first_structural_fallback: bool = Field(
        default=True,
        env="ENABLE_COMPILE_FIRST_STRUCTURAL_FALLBACK",
        description="Enable deterministic compile-first fallback for structurally broken translated parts"
    )
    structural_fallback_ratio_cap: float = Field(
        default=0.38,
        env="STRUCTURAL_FALLBACK_RATIO_CAP",
        description="Preferred fallback ratio cap (soft/hard behavior controlled by STRUCTURAL_FALLBACK_CAP_MODE)"
    )
    structural_fallback_cap_mode: str = Field(
        default="soft",
        env="STRUCTURAL_FALLBACK_CAP_MODE",
        description="Fallback ratio cap mode: soft or hard"
    )

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

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
        self.terms_dir.mkdir(parents=True, exist_ok=True)
        self.task_configs_dir.mkdir(parents=True, exist_ok=True)
        self.failed_tasks_dir.mkdir(parents=True, exist_ok=True)
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM API configuration as a dictionary"""
        return {
            "api_key": self.llm_api_key,
            "base_url": self.llm_base_url,
            "model": self.llm_model,
            "timeout": self.llm_timeout
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
