"""Post-translation term auto-extraction module.

Provides heuristic and LLM-assisted extraction of term pairs
from aligned source/target translation text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class TermExtractionResult:
    """Result of a term extraction operation."""

    extracted_terms: list[dict[str, Any]] = field(default_factory=list)
    extraction_method: str = "none"


def _normalise_text(text: str) -> str:
    """Lower-case, collapse whitespace."""
    return " ".join(text.lower().split())


def _extract_capitalised_phrases(text: str) -> set[str]:
    """Extract capitalised phrases that look like technical terms.

    Matches:
    - Acronyms: CNN, LSTM, BERT, etc.
    - CamelCase names: TransformerEncoder, CrossAttention
    - Capitalised multi-word phrases (2-5 words)
    """
    phrases: set[str] = set()

    # Acronyms (2+ uppercase letters, possibly with dots)
    for m in re.finditer(r'\b([A-Z]{2,}(?:\.[A-Z])*)\b', text):
        phrases.add(m.group(1))

    # CamelCase
    for m in re.finditer(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', text):
        phrases.add(m.group(1))

    # Capitalised multi-word phrases (2-5 words)
    for m in re.finditer(
        r'\b((?:[A-Z][a-z]+\s+){1,4}[A-Z][a-z]+)\b', text
    ):
        phrases.add(m.group(1))

    return phrases


def _extract_quoted_terms(text: str) -> set[str]:
    """Extract terms enclosed in double or single quotes."""
    terms: set[str] = set()
    for m in re.finditer(r'"([^"]+)"', text):
        term = m.group(1).strip()
        if term and len(term) > 1:
            terms.add(term)
    for m in re.finditer(r"'([^']+)'", text):
        term = m.group(1).strip()
        if term and len(term) > 1:
            terms.add(term)
    return terms


def _align_terms_heuristic(
    source_phrases: set[str], target_phrases: set[str]
) -> list[dict[str, str]]:
    """Simple heuristic alignment of extracted term phrases.

    Since we cannot reliably align without an LLM, we return
    source phrases with empty target (for manual review), and
    any exact-match cross-lingual terms
    (e.g. identical acronyms/camelCase names).
    """
    pairs: list[dict[str, str]] = []

    # Acronyms and CamelCase are often identical in both languages
    # For source_phrases that also appear in target_phrases, create pair
    common = source_phrases & target_phrases
    for term in common:
        pairs.append({"source_term": term, "target_term": term, "domain": ""})

    # Remaining source-only phrases → empty target (needs review)
    for term in source_phrases - common:
        pairs.append({"source_term": term, "target_term": "", "domain": ""})

    return pairs


def extract_terms_from_translation(
    source_text: str,
    target_text: str,
    llm_extract_fn: Optional[
        Callable[[str, str], list[tuple[str, str]]]
    ] = None,
) -> TermExtractionResult:
    """Extract terminology term pairs from a source/target translation pair.

    Two extraction paths:
      1. **LLM-assisted**: If *llm_extract_fn* is provided, it is called
         with ``(source_text, target_text)`` and should return a list of
         ``(source_term, target_term)`` tuples.
      2. **Heuristic fallback**: Capitalised phrases and quoted terms are
         extracted from the source text. Where the same term appears in
         the target (acronyms, CamelCase), a paired entry is created.

    Args:
        source_text: The original (source-language) text.
        target_text: The translated (target-language) text.
        llm_extract_fn: Optional callable
            ``fn(source, target) -> list[(src_term, tgt_term)]``

    Returns:
        A :class:`TermExtractionResult` with extracted term dicts.
    """
    # --- LLM-assisted extraction ---
    if llm_extract_fn is not None:
        try:
            pairs = llm_extract_fn(source_text, target_text)
            terms = [
                {"source_term": s.strip(), "target_term": t.strip(), "domain": ""}
                for s, t in pairs
                if s and s.strip()
            ]
            if terms:
                return TermExtractionResult(
                    extracted_terms=terms, extraction_method="llm"
                )
        except Exception:
            logger.exception("LLM term extraction failed, falling back to heuristic")
            # Fall through to heuristic

    # --- Heuristic extraction ---
    source_phrases = _extract_capitalised_phrases(source_text)
    source_phrases |= _extract_quoted_terms(source_text)

    target_phrases = _extract_capitalised_phrases(target_text)
    target_phrases |= _extract_quoted_terms(target_text)

    pairs = _align_terms_heuristic(source_phrases, target_phrases)

    return TermExtractionResult(
        extracted_terms=pairs,
        extraction_method="heuristic" if pairs else "none",
    )
