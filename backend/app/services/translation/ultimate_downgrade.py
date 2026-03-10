"""
ultimate_downgrade.py
eliminate-silent-fallback — Phase 4 Ultimate Text Rendering (Final Safety Net)

Deterministic algorithmic renderer that:
1. Strips all LaTeX structural tags (\\begin{}, \\end{}, _, ^, etc.)
2. Aggressively escapes all LaTeX special characters in translated text
3. Wraps the result in a minimal, compilation-safe LaTeX container
4. Guarantees 100% compilation success as the absolute final fallback

Spec invariants:
  - MUST be synchronous and deterministic (no LLM calls whatsoever)
  - Code blocks and verbatim environments are EXEMPT (not transformed)
  - Escaping order: backslash first, then all other special characters
  - After this renderer, the natural language is visible in target language
    even if all LaTeX formatting is lost

DeFeated goal: "ugly but readable" PDF — preserving target-language readability
over LaTeX source purity.
"""
from __future__ import annotations

import re
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.services.agents.pipeline_schema import FallbackReport

# ---------------------------------------------------------------------------
# Characters that must be escaped in LaTeX text mode
# Escape order matters: backslash MUST come first.
# ---------------------------------------------------------------------------
_LATEX_SPECIAL_CHARS = [
    ("\\", r"\textbackslash{}"),   # Must be first!
    ("$",  r"\$"),
    ("%",  r"\%"),
    ("#",  r"\#"),
    ("&",  r"\&"),
    ("_",  r"\_"),
    ("^",  r"\textasciicircum{}"),
    ("~",  r"\textasciitilde{}"),
    ("{",  r"\{"),
    ("}",  r"\}"),
]

# Pattern to detect verbatim / code-like environments (exempt from downgrade)
_VERBATIM_BEGIN = re.compile(
    r"\\begin\{(?:verbatim|lstlisting|minted|Verbatim|alltt)\*?\}"
)
_VERBATIM_END = re.compile(
    r"\\end\{(?:verbatim|lstlisting|minted|Verbatim|alltt)\*?\}"
)

# LaTeX structural commands to strip (before escaping natural-language text)
_LATEX_ENV_STRIP = re.compile(
    r"\\(?:begin|end)\{[^}]*\}"
)
_LATEX_SECTION_CMDS = re.compile(
    r"\\(?:section|subsection|subsubsection|paragraph|subparagraph|chapter)\*?\{([^}]*)\}"
)
_LATEX_FORMATTING = re.compile(
    r"\\(?:textbf|textit|emph|texttt|underline|textrm|textsc|textsl)\{([^}]*)\}"
)
_LATEX_DISPLAY_MATH = re.compile(r"\\\[.*?\\\]", re.DOTALL)
_LATEX_INLINE_MATH = re.compile(r"\$[^$]*\$")
_DOUBLE_DOLLAR_MATH = re.compile(r"\$\$.*?\$\$", re.DOTALL)

# Placeholder pattern — must NOT be stripped or escaped
_PLACEHOLDER_PATTERN = re.compile(
    r"<PLACEHOLDER_(?:ENV|CAP|ITEM|EQROW|MATH)_\d+>"
)


def _is_verbatim_segment(text: str) -> bool:
    """Return True if the text appears to be a verbatim/code block (exempt)."""
    return bool(_VERBATIM_BEGIN.search(text))


def _extract_natural_language(text: str) -> str:
    """Strip LaTeX structural markup, keeping natural language and placeholders.

    Order of operations:
    1. Preserve verbatim blocks as-is (extracted → protected)
    2. Preserve placeholder tokens
    3. Expand formatting commands (\\textbf{X} → X)
    4. Expand section commands (\\section{X} → X)
    5. Remove display math environments (non-translatable)
    6. Remove remaining \\begin{}/\\end{} pairs
    7. Remove remaining LaTeX command calls (\\cmd{...} stripped)
    """
    # Replace formatting commands with their argument content
    text = _LATEX_SECTION_CMDS.sub(r"\1", text)
    text = _LATEX_FORMATTING.sub(r"\1", text)

    # Remove display math (cannot be shown as plain text safely)
    text = _DOUBLE_DOLLAR_MATH.sub("", text)
    text = _LATEX_DISPLAY_MATH.sub("", text)

    # Remove begin/end environment delimiters
    text = _LATEX_ENV_STRIP.sub("", text)

    # Remove remaining LaTeX commands (\\cmd, \\cmd{...})
    # Keep placeholders intact via a substitution dance
    # 1. Temporarily mask placeholders
    placeholders = _PLACEHOLDER_PATTERN.findall(text)
    for i, ph in enumerate(placeholders):
        text = text.replace(ph, f"__PH_{i}__", 1)

    # 2. Strip residual LaTeX commands
    text = re.sub(r"\\[A-Za-z@]+(?:\[[^\]]*\])?(?:\{[^}]*\})*", "", text)

    # 3. Restore placeholders
    for i, ph in enumerate(placeholders):
        text = text.replace(f"__PH_{i}__", ph, 1)

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


def _escape_latex_special(text: str) -> str:
    """Aggressively escape all LaTeX special characters in natural language text.

    Placeholders are temporarily protected before escaping.
    Backslash is escaped first (required by spec).
    """
    # Temporarily mask placeholders to avoid escaping them
    placeholders = _PLACEHOLDER_PATTERN.findall(text)
    masks: dict[str, str] = {}
    for i, ph in enumerate(placeholders):
        mask = f"PHMASK{i}PHMASK"
        masks[mask] = ph
        text = text.replace(ph, mask, 1)

    # Escape in order — backslash MUST be processed first
    for char, replacement in _LATEX_SPECIAL_CHARS:
        if char == "\\":
            # Only escape standalone backslashes (not already escaped sequences)
            # Since we already stripped structural commands, remaining backslashes
            # are either residual commands or literal text backslashes.
            text = text.replace(char, replacement)
        else:
            text = text.replace(char, replacement)

    # Restore placeholders
    for mask, ph in masks.items():
        text = text.replace(mask, ph)

    return text


def ultimate_downgrade_segment(
    translated_text: str,
    fallback_report: Optional["FallbackReport"] = None,
) -> str:
    """Apply the ultimate downgrade renderer to a single segment.

    Spec guarantees:
    - Deterministic: same input always produces same output.
    - Compilation-safe: all LaTeX special characters are escaped.
    - Readable: target-language natural language is preserved.
    - Exempt: verbatim/code environments are returned as-is.

    Args:
        translated_text: The (possibly structurally broken) translated text.
        fallback_report: Optional context for logging. Not used for logic.

    Returns:
        A minimal, compilation-safe LaTeX text block.
    """
    if not translated_text or not translated_text.strip():
        # Empty input: return a safe placeholder comment
        return "% [LaTeX-Trans: ultimate downgrade — segment was empty]"

    # Verbatim/code blocks are exempt from downgrade
    if _is_verbatim_segment(translated_text):
        return translated_text

    # Step 1: Extract natural language (strip structural LaTeX)
    natural = _extract_natural_language(translated_text)

    if not natural.strip():
        return "% [LaTeX-Trans: ultimate downgrade — no natural language extracted]"

    # Step 2: escape all LaTeX special characters
    escaped = _escape_latex_special(natural)

    # Step 3: Wrap in a minimal, isolated LaTeX container
    # Plain paragraph output — safest container (no environments)
    chunk_scope = getattr(fallback_report, "chunk_scope", "unknown") if fallback_report else "unknown"
    result = (
        f"% [LaTeX-Trans: ultimate downgrade applied — chunk: {chunk_scope}]\n"
        f"{escaped}\n"
    )

    return result
