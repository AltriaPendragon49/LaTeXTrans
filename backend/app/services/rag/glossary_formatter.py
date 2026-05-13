from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Glossary block formatting
# ---------------------------------------------------------------------------

_GLOSSARY_OPEN = "<Glossary>"
_GLOSSARY_CLOSE = "</Glossary>"
_GLOSSARY_LINE_TPL = "{source_term} -> {target_term}"


def format_glossary_block(terms: list[dict]) -> str:
    """Format a list of term dicts into a compact ``<Glossary>`` block.

    Parameters
    ----------
    terms : list[dict]
        Each dict must have ``"source_term"`` and ``"target_term"`` keys.

    Returns
    -------
    str
        Formatted block::

            <Glossary>
            source_term_1 -> target_term_1
            source_term_2 -> target_term_2
            </Glossary>

        If *terms* is empty, returns an empty string (no block).
    """
    if not terms:
        return ""

    lines = [_GLOSSARY_OPEN]
    for t in terms:
        source = str(t.get("source_term", "") or "")
        target = str(t.get("target_term", "") or "")
        if source and target:
            lines.append(_GLOSSARY_LINE_TPL.format(source_term=source, target_term=target))
    lines.append(_GLOSSARY_CLOSE)

    # If all entries were empty, return empty string.
    if len(lines) <= 2:
        return ""

    return "\n".join(lines)


def estimate_token_count(glossary_block: str) -> int:
    """Roughly estimate the token count of a glossary block.

    Uses ``len(text) // 4`` as a coarse heuristic suitable for context
    budget checks.

    Parameters
    ----------
    glossary_block : str
        The formatted glossary block (or empty string).

    Returns
    -------
    int
        Estimated token count (``0`` for empty input).
    """
    if not glossary_block:
        return 0
    return max(1, len(glossary_block) // 4)


def truncate_glossary(glossary_block: str, max_tokens: int) -> str:
    """Truncate a glossary block to fit within a token budget.

    Keeps as many complete term lines as possible while staying within
    ``max_tokens``.  The ``<Glossary>`` and ``</Glossary>`` delimiters
    are always included when at least one term line fits the budget.

    Parameters
    ----------
    glossary_block : str
        The formatted glossary block.
    max_tokens : int
        Maximum allowed token count.

    Returns
    -------
    str
        Possibly truncated glossary block, or an empty string if the
        delimiters alone exceed the budget.
    """
    if not glossary_block or max_tokens <= 0:
        return ""

    lines = glossary_block.splitlines()
    if len(lines) < 2:
        return ""

    # Start with just the delimiters.
    kept = [_GLOSSARY_OPEN, _GLOSSARY_CLOSE]
    delimiters_block = "\n".join(kept)
    if estimate_token_count(delimiters_block) > max_tokens:
        return ""

    # Add content lines one by one while staying within budget.
    content_lines = lines[1:-1]  # everything between open and close
    for line in content_lines:
        candidate_block = "\n".join(kept[:-1] + [line, _GLOSSARY_CLOSE])
        if estimate_token_count(candidate_block) > max_tokens:
            break
        kept.insert(-1, line)

    return "\n".join(kept)
