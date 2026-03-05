"""
Configuration Models for Advanced Settings

Defines data structures for translation configuration, source types, and LaTeX validation.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


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
        default="deepseek-ai/deepseek-v3.2", 
        description="Translation LLM model name"
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
