"""
Configuration Models for Advanced Settings

Defines data structures for translation configuration, source types, and LaTeX validation.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Input source type enumeration"""
    UPLOAD = "upload"              # Traditional file upload
    ARXIV = "arxiv"                # ArXiv download
    FOLDER_UPLOAD = "folder_upload"  # Drag-and-drop directory upload


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
    enable_verification: bool = Field(
        default=True, 
        description="Enable dual-model verification"
    )
    generate_terminology_table: bool = Field(
        default=True, 
        description="Generate terminology reference table (CSV)"
    )
    translation_model: str = Field(
        default="qwen/qwen3-235b-a22b", 
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
