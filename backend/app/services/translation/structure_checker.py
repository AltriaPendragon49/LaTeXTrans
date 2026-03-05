"""
Phase 0: Structure Invariant Checker
======================================
Lightweight classifier that detects structural unsafe patterns in a LaTeX env.

This function:
  - ONLY classifies (sets is_structure_safe = True/False)
  - NEVER raises, blocks, or triggers any downgrade
  - Returns a copy of the env dict with the classification added
"""
from __future__ import annotations
import re
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# Detect raw \\begin{...} or \\end{...} in content — structure token leaks
_LEAKED_ENV_RE = re.compile(r"\\(?:begin|end)\{[^}]*\}")

# Detect unbalanced curly braces
_OPEN_BRACE_RE = re.compile(r"(?<!\\)\{")
_CLOSE_BRACE_RE = re.compile(r"(?<!\\)\}")

# Pattern for a tight math pair: $<non-whitespace content>$
# A valid inline math pair must not have a space immediately after the opening $
# and not have a space immediately before the closing $.
# Examples: $x$, $E=mc^2$, $\frac{a}{b}$ → all safe
# NOT safe: "$5 ... $10" because it spans across words
_MATH_PAIR_RE = re.compile(r"\$\S(?:[^$]*\S)?\$")


def _has_bare_dollars(text: str) -> bool:
    """Return True if there are un-escaped dollar signs that are NOT tight math pairs.

    A tight math pair: $<content>$ where content does not begin or end with a
    space. This distinguishes $E=mc^2$ (math) from $5 (text-mode dollar).

    Strategy:
      1. Replace escaped dollar signs with placeholder to ignore them.
      2. Iteratively remove all tight $...$ math pairs from the text.
      3. If any $ remains, it is a bare dollar → unsafe.
    """
    # Step 1: blank out escaped dollars
    working = text.replace(r"\$", "\x00")

    # Step 2: remove tight math pairs repeatedly (handles adjacent pairs)
    prev = None
    while prev != working:
        prev = working
        working = _MATH_PAIR_RE.sub("", working)

    # Step 3: any remaining $ is bare
    return "$" in working


def _has_leaked_env(text: str) -> bool:
    return bool(_LEAKED_ENV_RE.search(text))


def _has_unbalanced_braces(text: str) -> bool:
    open_count = len(_OPEN_BRACE_RE.findall(text))
    close_count = len(_CLOSE_BRACE_RE.findall(text))
    return open_count != close_count


def detect_structure_invariant(env: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 0 classification: determine whether an env is structurally safe.

    Args:
        env: A dict with at least a 'content' key (LaTeX text).

    Returns:
        A new dict equal to `env` plus the key `is_structure_safe` (bool).
        If `content` is missing or not a string, defaults to safe=True.
    """
    result = dict(env)  # shallow copy, preserving all original keys

    try:
        content = env.get("content", "")
        if not isinstance(content, str):
            content = ""

        if not content:
            result["is_structure_safe"] = True
            return result

        unsafe = (
            _has_bare_dollars(content)
            or _has_leaked_env(content)
            or _has_unbalanced_braces(content)
        )
        result["is_structure_safe"] = not unsafe

    except Exception as exc:  # noqa: BLE001
        # Phase 0 must NEVER crash the pipeline — default to safe
        logger.warning("detect_structure_invariant: unexpected error: %s", exc)
        result["is_structure_safe"] = True

    return result
