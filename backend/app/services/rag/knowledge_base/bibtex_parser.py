"""BibTeX parser for RAG terminology knowledge base.

Parses .bib file entries, extracts citation metadata, and produces
term candidates from titles using heuristic or LLM-based extraction.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def _clean_bibtex_value(value: str) -> str:
    """Strip enclosing braces/quotes and normalise whitespace."""
    value = value.strip()
    if len(value) >= 2:
        if (value.startswith("{") and value.endswith("}")) or (
            value.startswith('"') and value.endswith('"')
        ):
            value = value[1:-1]
    return value.strip()


# RE for BibTeX field lines:  key  =  {value}
_FIELD_RE = re.compile(r'^\s*(\w+)\s*=\s*\{(.*)\}\s*[,]?\s*$')

# RE for entry start:  @type{citation_key,
_ENTRY_START_RE = re.compile(r'^\s*@(\w+)\s*\{\s*([^,]+)\s*,\s*$', re.IGNORECASE)


def parse_bibtex_content(content: str) -> list[dict]:
    """Parse a .bib file string into a list of entry dicts.

    Each entry dict contains:
        citation_key, entry_type, title, author, year, journal, abstract
    (only fields that were present in the source).

    Args:
        content: Raw .bib file content as a string.

    Returns:
        A list of parsed entry dicts.
    """
    entries: list[dict] = []
    current_entry: dict[str, Any] | None = None
    current_key: str | None = None
    brace_depth = 0
    field_buffer: list[str] = []

    lines = content.splitlines()

    for line in lines:
        # --- Detect entry start ---
        match = _ENTRY_START_RE.match(line)
        if match:
            # Flush any previous unterminated entry
            if current_entry is not None:
                logger.warning("Unterminated BibTeX entry found: %s", current_entry.get("citation_key"))
                current_entry = None
                current_key = None
                field_buffer = []
                brace_depth = 0

            entry_type = match.group(1).lower()
            citation_key = match.group(2).strip()
            current_entry = {
                "citation_key": citation_key,
                "entry_type": entry_type,
            }
            current_key = None
            field_buffer = []
            brace_depth = 1
            continue

        if current_entry is None:
            # Check for @string, @preamble, @comment which may use braces
            if re.match(r'^\s*@(string|preamble|comment)\s*\{', line, re.IGNORECASE):
                brace_depth = 1
            continue

        # Track brace depth inside entry
        for ch in line:
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1

        if brace_depth <= 0:
            # Entry closed — flush remaining field buffer
            _flush_field_buffer(current_entry, current_key, field_buffer)
            entries.append(current_entry)
            current_entry = None
            current_key = None
            field_buffer = []
            brace_depth = 0
            continue

        # --- Parse field lines ---
        field_match = _FIELD_RE.match(line)
        if field_match:
            # Flush previous field
            _flush_field_buffer(current_entry, current_key, field_buffer)
            field_key = field_match.group(1).lower()
            field_value = _clean_bibtex_value(field_match.group(2))
            current_entry[field_key] = field_value
            current_key = None
            field_buffer = []
        elif "=" in line and current_key is None:
            # Multi-line field value start
            parts = line.split("=", 1)
            current_key = parts[0].strip().lower()
            remainder = parts[1].strip()
            # Remove trailing comma
            if remainder.endswith(","):
                remainder = remainder[:-1].strip()
            field_buffer = [remainder] if remainder else []
        elif current_key is not None:
            field_buffer.append(line)

    # Flush last entry if still open
    if current_entry is not None:
        _flush_field_buffer(current_entry, current_key, field_buffer)
        entries.append(current_entry)

    return entries


def _flush_field_buffer(entry: dict, current_key: str | None, field_buffer: list[str]) -> None:
    """Append multi-line field buffer to the entry under *current_key*."""
    if current_key is None or not field_buffer:
        return
    raw = " ".join(field_buffer)
    raw = _clean_bibtex_value(raw)
    if raw:
        entry[current_key] = raw


# ---- Term candidate extraction ----


def extract_term_candidates(
    entries: list[dict],
    llm_helper: Optional[Callable[[str], list[tuple[str, str]]]] = None,
) -> list[dict]:
    """Extract term-candidate dicts from parsed BibTeX entries.

    Uses heuristics to mine key phrases from titles:
      - Looks for quoted terms or obvious technical phrases.
      - If *llm_helper* is provided it is called with the title text and
        should return a list of ``(source_term, target_term)`` tuples.

    Args:
        entries: Parsed BibTeX entry dicts from :func:`parse_bibtex_content`.
        llm_helper: Optional callable ``fn(title: str) -> list[(str, str)]``
            that returns (source, target) term pairs extracted from the title.

    Returns:
        A list of candidate dicts with keys:
            source_term, target_term, domain, provenance
    """
    candidates: list[dict] = []

    for entry in entries:
        title = entry.get("title", "")
        if not title:
            continue

        provenance = format_provenance(entry)
        domain = _infer_domain(entry)

        # --- LLM-assisted extraction ---
        if llm_helper is not None:
            try:
                pairs = llm_helper(title)
                for source_term, target_term in pairs:
                    if source_term and source_term.strip():
                        candidates.append(
                            {
                                "source_term": source_term.strip(),
                                "target_term": (target_term or "").strip(),
                                "domain": domain,
                                "provenance": provenance,
                            }
                        )
            except Exception:
                logger.exception("LLM term extraction from BibTeX title failed for entry %s", entry.get("citation_key"))
                # Fall through to heuristic extraction
                pass

        # --- Heuristic extraction: quoted terms ---
        quoted_terms = re.findall(r'"([^"]+)"', title)
        for term in quoted_terms:
            term = term.strip()
            if term and len(term) > 1:
                candidates.append(
                    {
                        "source_term": term,
                        "target_term": "",
                        "domain": domain,
                        "provenance": provenance,
                    }
                )

        # --- Heuristic extraction: potential technical phrases (2-4 word capitalized) ---
        tech_phrases = re.findall(
            r'\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*){1,3})', title
        )
        for phrase in tech_phrases:
            phrase = phrase.strip()
            if phrase and len(phrase) > 3 and phrase not in {q for q in quoted_terms}:
                candidates.append(
                    {
                        "source_term": phrase,
                        "target_term": "",
                        "domain": domain,
                        "provenance": provenance,
                    }
                )

    return candidates


def _infer_domain(entry: dict) -> str:
    """Infer academic domain from BibTeX entry metadata."""
    keywords = entry.get("keywords", "")
    if keywords:
        kw = keywords.strip().lower()
        # Use first keyword as domain hint
        return kw.split(",")[0].strip()[:64]

    # Fallback: try to infer from entry type or journal
    entry_type = entry.get("entry_type", "")
    journal = entry.get("journal", "")
    if not journal and entry_type in ("inproceedings", "conference"):
        return "computer_science"
    if entry_type in ("article",):
        return "general"

    return ""


def format_provenance(entry: dict) -> dict:
    """Format a provenance dict for a BibTeX entry.

    The result is suitable for storing in the ``provenance`` column
    of the terminology_terms table.
    """
    return {
        "source": "bibtex",
        "citation_key": entry.get("citation_key", ""),
        "entry_type": entry.get("entry_type", ""),
    }
