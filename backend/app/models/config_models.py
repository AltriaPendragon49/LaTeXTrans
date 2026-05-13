"""
Configuration Models for Advanced Settings

Defines data structures for translation configuration, source types, and LaTeX validation.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Mapping
from pydantic import BaseModel, Field


ORIGIN_CLI_PARITY_MODE = "origin_cli_parity"
MODERN_TRANSLATION_CORE_MODE = "modern"

ORIGIN_CLI_PARITY_SECTION_LLM_MAX_CONCURRENT_REQUESTS = 10
ORIGIN_CLI_PARITY_ERROR_LLM_MAX_CONCURRENT_REQUESTS = 20

def is_origin_cli_parity_config(config: Optional[Mapping[str, Any]]) -> bool:
    if not config:
        return False
    mode = str(config.get("translation_core_mode") or "").strip().lower()
    return mode == ORIGIN_CLI_PARITY_MODE or bool(config.get("enable_legacy_translation_core"))


def normalize_origin_cli_parity_agent_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the effective single-kernel config for current backend delivery."""
    normalized = dict(config or {})
    normalized["translation_core_mode"] = ORIGIN_CLI_PARITY_MODE
    normalized["enable_legacy_translation_core"] = True
    normalized["mode"] = 0
    normalized["translation_mode"] = "full"
    normalized["enable_parser_env_llm_judgment"] = True
    normalized["origin_cli_parity_legacy_parser_env_judgment"] = True
    normalized["origin_cli_parity_single_kernel_lineage"] = True
    normalized["llm_max_concurrent_requests"] = ORIGIN_CLI_PARITY_SECTION_LLM_MAX_CONCURRENT_REQUESTS
    normalized["llm_error_max_concurrent_requests"] = (
        ORIGIN_CLI_PARITY_ERROR_LLM_MAX_CONCURRENT_REQUESTS
    )
    normalized["generate_terminology"] = False
    normalized["generate_terminology_table"] = False
    normalized["update_term"] = False
    normalized["user_term"] = ""
    return normalized


class SourceType(str, Enum):
    """Input source type enumeration"""
    UPLOAD = "upload"              # Traditional file upload
    ARXIV = "arxiv"                # ArXiv download
    FOLDER_UPLOAD = "folder_upload"  # Drag-and-drop directory upload


class FormattingConfig(BaseModel):
    """
    Typography formatting configuration for LaTeX preamble injection.
    
    All fields default to None, meaning 'keep original' - safe for backward compatibility.
    Injected into the LaTeX preamble after add_cjk_package() during PDF generation.
    """
    # 行距: None=保持, 数值如 1.5, 2.0
    line_spacing: Optional[float] = Field(
        default=None,
        description="Line spacing multiplier (e.g. 1.5). None means keep original."
    )
    
    # 全局字号: None=保持, 数值如 10, 11, 12 (单位 pt)
    font_size: Optional[float] = Field(
        default=None,
        description="Global font size in pt (e.g. 12). None means keep original."
    )
    
    # 中文字体: None=保持, \"songti\"=宋体, \"heiti\"=黑体
    cjk_font: Optional[str] = Field(
        default=None,
        description="CJK font preset: 'songti' or 'heiti'. None means keep original."
    )
    
    # 栏模式: None=保持, \"single\"=单栏, \"double\"=双栏
    column_mode: Optional[str] = Field(
        default=None,
        description="Column layout: 'single' or 'double'. None means keep original."
    )
    
    # 页边距: None=保持, \"narrow\"/\"normal\"/\"wide\"
    margin: Optional[str] = Field(
        default=None,
        description="Page margin preset: 'narrow', 'normal', or 'wide'. None means keep original."
    )
    
    # 首行缩进: None=保持, True=启用 2em 缩进
    paragraph_indent: Optional[bool] = Field(
        default=None,
        description="Enable 2em paragraph indent (CJK convention). None means keep original."
    )
    
    # 参考文献格式: None=保持
    bib_style: Optional[str] = Field(
        default=None,
        description="Bibliography style: 'gbt7714-numerical', 'gbt7714-author-year', 'ieeetr', 'apalike'. None means keep original."
    )
    
    # 引文标记风格: None=保持
    cite_style: Optional[str] = Field(
        default=None,
        description="Citation style: 'numbers', 'super', 'authoryear'. None means keep original."
    )
    
    # 图表标题本地化: None=保持, True=启用
    localize_captions: Optional[bool] = Field(
        default=None,
        description="Localize figure/table captions (e.g. 图/表). None means keep original."
    )


class AdvancedConfig(BaseModel):
    """
    Advanced configuration options for translation.
    
    All fields have sensible defaults - users can start translating without 
    configuring anything.
    """
    # Translation settings
    translation_mode: str = Field(
        default="full", 
        description="Translation mode: full|quick_scan (quick_scan translates abstract+conclusion only)"
    )
    compile_strategy: str = Field(
        default="auto", 
        description="LaTeX compile strategy: pdflatex|xelatex|lualatex|auto"
    )
    generate_terminology_table: bool = Field(
        default=True, 
        description="Generate terminology reference table (CSV)"
    )
    translation_model: str = Field(
        default="gemini-2.5-flash",
        description="Translation LLM model name"
    )
    translation_core_mode: str = Field(
        default=ORIGIN_CLI_PARITY_MODE,
        description="Internal translation core mode for backend execution."
    )
    enable_rag_terminology: bool = Field(
        default=False,
        description="Enable RAG terminology enhancement for this task. Requires server-side RAG_TERMINOLOGY_ENABLED."
    )

    # API configuration
    use_author_api: bool = Field(
        default=True, 
        description="Use author's API (default). When True, custom_base_url and custom_api_key are ignored."
    )
    custom_base_url: Optional[str] = Field(
        default=None, 
        description="Custom API base URL (e.g., https://aicanapi.com). System auto-appends /v1/chat/completions"
    )
    custom_api_key: Optional[str] = Field(
        default=None, 
        description="Custom API key for the base URL"
    )
    
    # Typography formatting configuration
    formatting: Optional[FormattingConfig] = Field(
        default=None,
        description="Typography formatting config for LaTeX preamble injection. None means keep all original formatting."
    )

    # Notification
    email_notification: bool = Field(
        default=False,
        description="Send email notification when task completes or fails."
    )
    community_production_translation: bool = Field(
        default=False,
        exclude=True,
        description="Internal flag for production community/admin curation translation limits.",
    )


class LatexValidation(BaseModel):
    """
    LaTeX directory validation result.
    
    Returned after uploading/extracting files to indicate whether 
    the directory is a valid LaTeX project.
    """
    is_valid: bool = Field(description="Whether the directory is a valid LaTeX project")
    main_file: Optional[str] = Field(
        default=None, 
        description="Detected main entry file path (relative to project root)"
    )
    tex_files: List[str] = Field(
        default_factory=list, 
        description="List of all .tex files found"
    )
    warnings: List[str] = Field(
        default_factory=list, 
        description="Non-fatal warnings (e.g., multiple main files)"
    )
    errors: List[str] = Field(
        default_factory=list, 
        description="Fatal errors (e.g., no .tex files found)"
    )


# Translation mode mapping for agent config
# NOTE: trans_mode 0/1/2 are existing modes, DO NOT modify their behavior
TRANSLATION_MODE_MAP = {
    "full": 0,        # Full document translation (existing)
    "quick_scan": 3,  # Quick scan mode: translate abstract + conclusion only (NEW)
}
