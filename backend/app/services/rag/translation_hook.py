"""Translation pipeline integration hooks for RAG terminology.

Provides lightweight adapter functions that connect the existing
translator agent with the RAG terminology pipeline:
  1. Feature-gate check (server-level + user config).
  2. Glossary injection into the system/user prompt.
  3. Post-translation term auto-extraction.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from backend.app.core.config import get_settings
from backend.app.services.rag.glossary_formatter import format_glossary_block

logger = logging.getLogger(__name__)


def should_run_rag(config: dict) -> bool:
    """Check whether RAG terminology should run for a translation task.

    Requires both:
      1. Server-level ``RAG_TERMINOLOGY_ENABLED = true``.
      2. User/task-level ``enable_rag_terminology = true`` (from the task
         configuration sent by the frontend).

    Args:
        config: The task configuration dict (usually from the frontend
            or stored task config).  Expected to have a top-level or
            nested ``enable_rag_terminology`` boolean key.

    Returns:
        ``True`` when RAG terminology is enabled at both levels.
    """
    settings = get_settings()
    if not bool(getattr(settings, "rag_terminology_enabled", False)):
        return False

    # Check the user/task-level opt-in.
    user_enabled = bool(config.get("enable_rag_terminology", False))
    return user_enabled


def inject_glossary_into_prompt(
    original_prompt: str,
    glossary_block: str,
) -> str:
    """Inject a glossary block into a translation prompt.

    If *glossary_block* is non-empty it is prepended before the
    original prompt content, separated by a blank line.  This
    ensures the model sees the terminology mapping before the
    text to translate.

    Args:
        original_prompt: The existing system or user prompt string.
        glossary_block: The formatted glossary block (or empty string).

    Returns:
        The augmented prompt with the glossary injected, or the
        original prompt unchanged if *glossary_block* is empty.
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
    """Build a glossary block for a single translation chunk.

    This is the primary entry point used by the translator agent to
    obtain glossary terms for a chunk.  It uses the simplified
    substring-matching implementation in TerminologyService.

    Args:
        chunk_text: The source-language text chunk.
        source_lang: Source language code.
        target_lang: Target language code.
        top_n: Maximum number of terms (defaults to server setting).

    Returns:
        A dict with keys ``glossary_block``, ``selected_terms``, and
        ``match_count``.
    """
    settings = get_settings()
    effective_top_n = (
        top_n if top_n is not None
        else getattr(settings, "rag_terminology_top_n", 10)
    )

    from backend.app.services.terminology_service import TerminologyService  # lazy: avoid circular import
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
    """Build a glossary block string from a list of term dicts.

    Delegates to the shared ``format_glossary_block`` helper from
    ``glossary_formatter`` so the output format is consistent
    between the pipeline and hand-crafted term lists.

    Args:
        terms: List of dicts with ``source_term`` and ``target_term`` keys.

    Returns:
        A formatted ``<Glossary>...</Glossary>`` block (empty string if
        *terms* is empty).
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
    """Run auto-extraction after a translation task completes.

    Aligns source and target chunks (by index) and extracts term pairs
    from each aligned pair.  Extracted terms are inserted into the
    terminology database as ``pending_review``.

    Args:
        task_id: The translation task ID for provenance.
        source_chunks: List of source-language chunk texts.
        target_chunks: List of translated (target-language) chunk texts.
        llm_extract_fn: Optional LLM-based extraction callable.
            ``fn(source_text, target_text) -> list[(src, tgt)]``.
        user_id: Optional user ID (defaults to ``"system"``).

    Returns:
        List of inserted term IDs (may be empty if no terms extracted).
    """
    from backend.app.services.terminology_service import TerminologyService  # lazy: avoid circular import
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
