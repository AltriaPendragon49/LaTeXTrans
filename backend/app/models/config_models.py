"""
高级设置的配置模型

定义翻译配置、来源类型和 LaTeX 验证的数据结构。
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Mapping
from pydantic import BaseModel, Field

from backend.app.core.config import get_default_translation_model


# 原始 CLI 兼容模式标识
ORIGIN_CLI_PARITY_MODE = "origin_cli_parity"
# 现代翻译核心模式标识
MODERN_TRANSLATION_CORE_MODE = "modern"

# 原始 CLI 兼容模式下的段落翻译最大 LLM 并发请求数
ORIGIN_CLI_PARITY_SECTION_LLM_MAX_CONCURRENT_REQUESTS = 10
# 原始 CLI 兼容模式下的错误处理最大 LLM 并发请求数
ORIGIN_CLI_PARITY_ERROR_LLM_MAX_CONCURRENT_REQUESTS = 20

def is_origin_cli_parity_config(config: Optional[Mapping[str, Any]]) -> bool:
    """判断配置是否为原始 CLI 兼容模式"""
    if not config:
        return False
    mode = str(config.get("translation_core_mode") or "").strip().lower()
    return mode == ORIGIN_CLI_PARITY_MODE or bool(config.get("enable_legacy_translation_core"))


def normalize_origin_cli_parity_agent_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    """返回当前后端交付的有效单内核配置"""
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
    # 保留用户对术语功能的选择；仅在缺失时覆盖
    normalized.setdefault("generate_terminology", False)
    normalized.setdefault("generate_terminology_table", False)
    normalized.setdefault("update_term", False)
    normalized.setdefault("user_term", "")
    return normalized


class SourceType(str, Enum):
    """输入源类型枚举"""
    UPLOAD = "upload"              # 传统文件上传
    ARXIV = "arxiv"                # ArXiv 下载
    FOLDER_UPLOAD = "folder_upload"  # 拖拽文件夹上传


class FormattingConfig(BaseModel):
    """
    LaTeX 前导区注入的排版格式配置。

    所有字段默认为 None，表示"保持原始设置"——保证向后兼容。
    在 PDF 生成时，于 add_cjk_package() 之后注入到 LaTeX 前导区。
    """
    # 行距: None=保持, 数值如 1.5, 2.0
    line_spacing: Optional[float] = Field(
        default=None,
        description="行距倍数（如 1.5）。None 表示保持原始设置"
    )

    # 全局字号: None=保持, 数值如 10, 11, 12 (单位 pt)
    font_size: Optional[float] = Field(
        default=None,
        description="全局字号（pt），如 12。None 表示保持原始设置"
    )

    # 中文字体: None=保持, \"songti\"=宋体, \"heiti\"=黑体
    cjk_font: Optional[str] = Field(
        default=None,
        description="CJK 字体预设: 'songti' 或 'heiti'。None 表示保持原始设置"
    )

    # 栏模式: None=保持, \"single\"=单栏, \"double\"=双栏
    column_mode: Optional[str] = Field(
        default=None,
        description="栏布局: 'single' 或 'double'。None 表示保持原始设置"
    )

    # 页边距: None=保持, \"narrow\"/\"normal\"/\"wide\"
    margin: Optional[str] = Field(
        default=None,
        description="页边距预设: 'narrow'、'normal' 或 'wide'。None 表示保持原始设置"
    )

    # 首行缩进: None=保持, True=启用 2em 缩进
    paragraph_indent: Optional[bool] = Field(
        default=None,
        description="启用 2em 段落缩进（CJK 惯例）。None 表示保持原始设置"
    )

    # 参考文献格式: None=保持
    bib_style: Optional[str] = Field(
        default=None,
        description="参考文献格式: 'gbt7714-numerical'、'gbt7714-author-year'、'ieeetr'、'apalike'。None 表示保持原始设置"
    )

    # 引文标记风格: None=保持
    cite_style: Optional[str] = Field(
        default=None,
        description="引文标记风格: 'numbers'、'super'、'authoryear'。None 表示保持原始设置"
    )

    # 图表标题本地化: None=保持, True=启用
    localize_captions: Optional[bool] = Field(
        default=None,
        description="本地化图表标题（如 图/表）。None 表示保持原始设置"
    )


class AdvancedConfig(BaseModel):
    """
    翻译高级配置选项。

    所有字段都有合理的默认值——用户无需任何配置即可开始翻译。
    """
    # 翻译设置
    translation_mode: str = Field(
        default="full",
        description="翻译模式: full|quick_scan（quick_scan 仅翻译摘要和结论）"
    )
    compile_strategy: str = Field(
        default="auto",
        description="LaTeX 编译策略: pdflatex|xelatex|lualatex|auto"
    )
    generate_terminology_table: bool = Field(
        default=True,
        description="生成术语对照表（CSV）"
    )
    translation_model: str = Field(
        default_factory=get_default_translation_model,
        description="翻译使用的 LLM 模型名称"
    )
    translation_core_mode: str = Field(
        default=ORIGIN_CLI_PARITY_MODE,
        description="后端执行的内部翻译核心模式"
    )
    enable_rag_terminology: bool = Field(
        default=False,
        description="为此任务启用 RAG 术语增强。需要服务端 RAG_TERMINOLOGY_ENABLED 已开启"
    )
    rag_terminology_domain: Optional[str] = Field(
        default=None,
        description="可选的 RAG 术语领域过滤器（如 'machine_learning'、'physics'）。设置后仅注入该领域的术语"
    )

    # API 配置
    use_author_api: bool = Field(
        default=True,
        description="使用官方 API（默认）。当为 True 时，忽略 custom_base_url 和 custom_api_key"
    )
    custom_base_url: Optional[str] = Field(
        default=None,
        description="自定义 API 基础 URL（如 https://aicanapi.com）。系统自动追加 /v1/chat/completions"
    )
    custom_api_key: Optional[str] = Field(
        default=None,
        description="用于该基础 URL 的自定义 API 密钥"
    )

    # 排版格式配置
    formatting: Optional[FormattingConfig] = Field(
        default=None,
        description="用于 LaTeX 前导区注入的排版格式配置。None 表示保持所有原始格式"
    )

    # 通知设置
    email_notification: bool = Field(
        default=False,
        description="任务完成或失败时发送邮件通知"
    )
    community_production_translation: bool = Field(
        default=False,
        exclude=True,
        description="内部标志，用于生产环境社区/管理员策展翻译的限额控制"
    )


class LatexValidation(BaseModel):
    """
    LaTeX 目录验证结果。

    在上传/解压文件后返回，用于指示目录是否为有效的 LaTeX 项目。
    """
    is_valid: bool = Field(description="目录是否为有效的 LaTeX 项目")
    main_file: Optional[str] = Field(
        default=None,
        description="检测到的主入口文件路径（相对于项目根目录）"
    )
    tex_files: List[str] = Field(
        default_factory=list,
        description="找到的所有 .tex 文件列表"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="非致命警告（如存在多个主文件）"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="致命错误（如未找到 .tex 文件）"
    )


# Agent 配置的翻译模式映射
# 注意：trans_mode 0/1/2 是已有模式，请勿修改其行为
TRANSLATION_MODE_MAP = {
    "full": 0,        # 全文翻译（已有模式）
    "quick_scan": 3,  # 快速扫描模式：仅翻译摘要和结论（新增）
}
