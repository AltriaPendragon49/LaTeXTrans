"""翻译流水线 RAG 术语集成钩子

提供轻量级适配器函数，将现有翻译 Agent 与 RAG 术语流水线连接：
  1. 功能门禁检查（服务端 + 用户配置）。
  2. 将术语表注入系统/用户提示。
  3. 翻译后术语自动提取。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from backend.app.core.config import get_settings
from backend.app.services.rag.glossary_formatter import format_glossary_block

logger = logging.getLogger(__name__)


def should_run_rag(config: dict) -> bool:
    """检查翻译任务是否应启用 RAG 术语功能。

    同时要求:
      1. 服务端 ``RAG_TERMINOLOGY_ENABLED = true``。
      2. 用户/任务级 ``enable_rag_terminology = true``（来自前端发送的任务配置）。

    参数:
        config: 任务配置字典（通常来自前端或已存储的任务配置）。
            期望包含顶层或嵌套的 ``enable_rag_terminology`` 布尔键。

    返回:
        当 RAG 术语在两个级别均已启用时返回 ``True``。
    """
    settings = get_settings()
    if not bool(getattr(settings, "rag_terminology_enabled", False)):
        return False

    # 检查用户/任务级开关。
    user_enabled = bool(config.get("enable_rag_terminology", False))
    return user_enabled


def inject_glossary_into_prompt(
    original_prompt: str,
    glossary_block: str,
) -> str:
    """将术语表块注入翻译提示。

    如果 *glossary_block* 非空，则将其前置到原始提示内容之前，用空行分隔。
    这确保模型在翻译文本之前先看到术语映射。

    参数:
        original_prompt: 现有的系统或用户提示字符串。
        glossary_block: 已格式化的术语表块（或空字符串）。

    返回:
        注入了术语表的增强提示，如果 *glossary_block* 为空则返回原始提示。
    """
    if not glossary_block or not glossary_block.strip():
        return original_prompt

    return f"{glossary_block}\n\n{original_prompt}"


def build_glossary_for_chunk(
    chunk_text: str,
    *,
    source_lang: str = "en",
    target_lang: str = "zh",
    top_n: Optional[int] = None,
) -> dict[str, Any]:
    """为单个翻译文本块构建术语表。

    这是翻译 Agent 使用的主入口点，用于获取文本块的术语表。
    使用术语服务中的简化子串匹配实现。

    参数:
        chunk_text: 源语言文本块。
        source_lang: 源语言代码。
        target_lang: 目标语言代码。
        top_n: 最大术语数量（默认取自服务端设置）。

    返回:
        包含 ``glossary_block``, ``selected_terms``, ``match_count`` 的字典。
    """
    settings = get_settings()
    effective_top_n = (
        top_n if top_n is not None
        else getattr(settings, "rag_terminology_top_n", 10)
    )

    from backend.app.services.terminology_service import TerminologyService  # 延迟导入: 避免循环依赖
    service = TerminologyService()
    result = service.get_rag_glossary(
        chunk_text,
        source_lang=source_lang,
        target_lang=target_lang,
        top_n=effective_top_n,
    )

    return {
        "glossary_block": result.get("glossary_block", ""),
        "selected_terms": result.get("terms", []),
        "match_count": result.get("match_count", 0),
    }


def build_glossary_from_terms(terms: list[dict]) -> str:
    """从术语字典列表构建术语表字符串。

    委托给共享的 ``format_glossary_block`` 辅助函数，
    确保流水线和手工构建的术语列表输出格式一致。

    参数:
        terms: 包含 ``source_term`` 和 ``target_term`` 键的字典列表。

    返回:
        已格式化的 ``<Glossary>...</Glossary>`` 块（*terms* 为空时返回空字符串）。
    """
    return format_glossary_block(terms)


def run_post_translation_extraction(
    task_id: str,
    source_chunks: list[str],
    target_chunks: list[str],
    llm_extract_fn: Optional[
        Callable[[str, str], list[tuple[str, str]]]
    ] = None,
    user_id: Optional[str] = None,
) -> list[str]:
    """翻译任务完成后运行自动术语提取。

    按索引对齐源语言和目标语言文本块，从每个对齐的配对中提取术语对。
    提取的术语以 ``pending_review`` 状态插入术语数据库。

    参数:
        task_id: 翻译任务 ID（用于溯源）。
        source_chunks: 源语言文本块列表。
        target_chunks: 翻译后（目标语言）文本块列表。
        llm_extract_fn: 可选的基于 LLM 的提取回调。
            ``fn(source_text, target_text) -> list[(src, tgt)]``。
        user_id: 可选用户 ID（默认 ``"system"``）。

    返回:
        已插入的术语 ID 列表（未提取时可能为空）。
    """
    from backend.app.services.terminology_service import TerminologyService  # 延迟导入: 避免循环依赖
    service = TerminologyService()
    all_ids: list[str] = []

    min_len = min(len(source_chunks), len(target_chunks))
    for idx in range(min_len):
        src = source_chunks[idx]
        tgt = target_chunks[idx]
        if not src or not tgt:
            continue

        try:
            ids = service.extract_and_store(
                task_id=task_id,
                source_text=src,
                target_text=tgt,
                llm_extract_fn=llm_extract_fn,
                user_id=user_id,
            )
            all_ids.extend(ids)
        except Exception:
            logger.exception(
                "Post-translation extraction failed for task %s chunk %d",
                task_id,
                idx,
            )

    return all_ids
