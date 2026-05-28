from __future__ import annotations

import base64
import html
import json
import mimetypes
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote_plus


"""论文预览 HTML 生成服务

将翻译后的 LaTeX 内容渲染为结构化 HTML 预览页面，
支持图表内联、数学公式、参考文献链接和读者交互。
"""

PREVIEW_READER_VERSION = "reader-v13"

HEADING_COMMAND_PATTERN = re.compile(
    r"\\(?P<kind>section|subsection|subsubsection)\*?\{(?P<title>[^}]*)\}",
    re.DOTALL,
)
PLACEHOLDER_PATTERN = re.compile(r"<(?:PLACEHOLDER|PROTECTED)_[^>]+>")
CAPTION_PATTERN = re.compile(r"\\caption\{(?P<caption>.*?)\}", re.DOTALL)
BLOCK_PLACEHOLDER_PATTERN = re.compile(r"__PAPER_PREVIEW_BLOCK_\d+__")
SPECIAL_ENV_PATTERN = re.compile(
    r"\\begin\{(?P<kind>figure\*?|table\*?|itemize|enumerate|thebibliography|algorithm\*?|tabular\*?|equation\*?|align\*?|alignat\*?|gather\*?|multline\*?|eqnarray\*?|split|CD|center|quote|snugshade\*?)\}"
    r"(?P<options>(?:\[[^\]]*\])?(?:\{[^{}]*\})?)"
    r"(?P<body>.*?)"
    r"\\end\{(?P=kind)\}",
    re.DOTALL,
)
FORMAT_COMMAND_PATTERN = re.compile(
    r"\\(?:textbf|textit|textup|emph|underline|textrm|textsc|mathrm|mathbf|mathit|bd)\{([^{}]*)\}"
)
HREF_PATTERN = re.compile(r"\\href\{[^}]*\}\{([^}]*)\}")
HREF_COMMAND_PATTERN = re.compile(r"\\href\{(?P<url>[^}]*)\}\{(?P<label>[^}]*)\}")
URL_PATTERN = re.compile(r"\\url\{([^}]*)\}")
URL_COMMAND_PATTERN = re.compile(r"\\url\{(?P<url>[^}]*)\}")
ANGLE_BRACKET_URL_PATTERN = re.compile(r"\[<(?P<url>https?://[^>\s]+)>\]")
BARE_URL_PATTERN = re.compile(r"(?P<url>https?://[^\s<>\])]+)")
REFERENCE_PATTERN = re.compile(r"\\(?:eqref|autoref|cref|Cref|ref)\{[^}]*\}")
CITATION_PATTERN = re.compile(r"~?\\cite[a-zA-Z*]*(?:\s*\[[^\]]*\])*\s*\{[^}]*\}")
LABEL_PATTERN = re.compile(r"\\label\{[^}]*\}")
FOOTNOTE_PATTERN = re.compile(r"\\footnote\{.*?\}", re.DOTALL)
REFERENCE_COMMAND_PATTERN = re.compile(r"\\(?P<command>eqref|autoref|cref|Cref|ref)\{(?P<labels>[^}]*)\}")
CITATION_COMMAND_PATTERN = re.compile(r"~?\\cite[a-zA-Z*]*(?:\s*\[[^\]]*\])*\s*\{(?P<keys>[^}]*)\}")
BIBITEM_ENTRY_PATTERN = re.compile(
    r"\\bibitem(?:\[[^\]]*\])?\{(?P<key>[^}]*)\}\s*(?P<body>.*?)(?=(?:\\bibitem(?:\[[^\]]*\])?\{)|\Z)",
    re.DOTALL,
)
DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
ARXIV_REFERENCE_PATTERN = re.compile(r"\b(?:arXiv:)?(?P<id>\d{4}\.\d{4,5}(?:v\d+)?)\b", re.IGNORECASE)
CUSTOM_SUBHEADING_OPEN_PATTERN = re.compile(
    r"^\s*\\(?P<kind>subsubsection|subsection|PARR|PAR|paragraph)\s*",
    re.DOTALL,
)
INCLUDE_GRAPHICS_PATTERN = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{(?P<path>[^}]+)\}", re.DOTALL)
TABULAR_PATTERN = re.compile(
    r"\\begin\{tabular\*?\}(?:\[[^\]]*\])?(?:\{[^{}]*\}){1,2}(?P<body>.*?)\\end\{tabular\*?\}",
    re.DOTALL,
)
LIST_ITEM_PATTERN = re.compile(r"\\item(?:\[[^\]]*\])?\s*")
BIBITEM_PATTERN = re.compile(r"\\bibitem(?:\[[^\]]*\])?\{[^}]*\}\s*", re.DOTALL)
CJK_WRAPPER_PATTERN = re.compile(
    r"\\begin\{CJK\}\{[^}]*\}\{[^}]*\}(?P<body>.*?)\\end\{CJK\}",
    re.DOTALL,
)
DISPLAY_MATH_ENVIRONMENTS = (
    "equation",
    "equation*",
    "align",
    "align*",
    "alignat",
    "alignat*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "eqnarray",
    "eqnarray*",
    "split",
    "CD",
)
STRUCTURAL_LINE_PATTERN = re.compile(
    r"^\s*\\(?:begin\{document\}|end\{document\}|maketitle|clearpage|newpage|pagebreak|par|noindent|centering|raggedright|raggedleft|small|footnotesize|scriptsize|normalsize|hfill)\s*$"
)
FORMULA_NOISE_PATTERN = re.compile(r"[\u200b\s]+")
SIMPLE_SYMBOL_MATH_PATTERN = re.compile(r"(?<!\\)\$\s*([↑↓✓])\s*(?<!\\)\$")
DISPLAY_MATH_INLINE_PATTERN = re.compile(
    r"(?P<block>\$\$(?P<dollar>.*?)\$\$|\\\[(?P<bracket>.*?)\\\]|\\begin\{(?P<env>equation\*?|align\*?|alignat\*?|gather\*?|multline\*?|eqnarray\*?|split|CD)\}(?P<env_body>.*?)\\end\{(?P=env)\})",
    re.DOTALL,
)
DISPLAY_MATH_ENV_BLOCK_PATTERN = re.compile(
    r"\\begin\{(?P<env>equation\*?|align\*?|alignat\*?|gather\*?|multline\*?|eqnarray\*?|split|CD)\}(?P<body>[\s\S]*?)\\end\{(?P=env)\}",
    re.DOTALL,
)
INLINE_MATH_SEGMENT_PATTERN = re.compile(
    r"(?P<block>(?<!\\)\$\$(?:[\s\S]*?)(?<!\\)\$\$|(?<!\\)\$(?:[^$\n]|\\\$)+(?<!\\)\$|\\\((?:[\s\S]*?)\\\)|\\\[(?:[\s\S]*?)\\\])",
    re.DOTALL,
)
LATEX_SYMBOL_REPLACEMENTS = {
    r"\uparrow": "↑",
    r"\downarrow": "↓",
    r"\checkmark": "✓",
}
FORMATTING_PREFIX_RESIDUE_PATTERN = re.compile(
    r"\\(?:textbf|textit|textup|emph|underline|textrm|textsc|mathrm|mathbf|mathit|bf|it|rm|tt)(?=[A-Za-z0-9])"
)
ORPHAN_DELIMITER_COMMAND_PATTERN = re.compile(
    r"\\(?:left|right|big|Big|bigg|Bigg|bigl|bigr|Bigl|Bigr|biggl|biggr|Biggl|Biggr)\b"
)


def _load_json(path: Path) -> List[Dict[str, Any]]:
    """安全地从路径加载 JSON 数组"""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _build_placeholder_map(output_dir: Path) -> Dict[str, str]:
    """构建占位符 -> 翻译内容的映射表"""
    placeholder_map: Dict[str, str] = {}
    for filename in ("envs_map.json", "captions_map.json", "newcommands_map.json"):
        for row in _load_json(output_dir / filename):
            placeholder = str(row.get("placeholder") or "").strip()
            if not placeholder:
                continue
            content = row.get("trans_content") or row.get("content") or ""
            placeholder_map[placeholder] = str(content)

    for row in _load_json(output_dir / "inputs_map.json"):
        begin = str(row.get("begin") or "").strip()
        end = str(row.get("end") or "").strip()
        if begin:
            placeholder_map[begin] = ""
        if end:
            placeholder_map[end] = ""

    return placeholder_map


def _replace_placeholders(text: str, placeholder_map: Dict[str, str]) -> str:
    def _replace(match: re.Match[str]) -> str:
        placeholder = match.group(0)
        replacement = placeholder_map.get(placeholder, "")
        if placeholder and placeholder in replacement:
            replacement = replacement.replace(placeholder, "")
        return replacement

    current = text
    seen_payloads = {current}
    max_rounds = max(1, len(placeholder_map) + 2)
    for _ in range(max_rounds):
        if not PLACEHOLDER_PATTERN.search(current):
            return current
        updated = PLACEHOLDER_PATTERN.sub(_replace, current)
        if updated == current:
            break
        if updated in seen_payloads:
            logger.warning("Preview placeholder expansion detected a cycle; dropping unresolved placeholders")
            current = updated
            break
        seen_payloads.add(updated)
        current = updated

    if PLACEHOLDER_PATTERN.search(current):
        logger.warning("Preview placeholder expansion exceeded safe rounds; dropping unresolved placeholders")
        current = PLACEHOLDER_PATTERN.sub("", current)
    return current


def _strip_structural_commands(text: str, *, preserve_references: bool = False) -> str:
    cleaned = text
    cleaned = re.sub(r"\\begin\{document\}", " ", cleaned)
    cleaned = re.sub(r"\\end\{document\}", " ", cleaned)
    cleaned = re.sub(r"\\maketitle\b", " ", cleaned)
    cleaned = re.sub(r"\\clearpage\b", "\n", cleaned)
    cleaned = re.sub(r"\\newpage\b", "\n", cleaned)
    cleaned = re.sub(r"\\pagebreak\b", "\n", cleaned)
    cleaned = re.sub(r"\\par\b", "\n", cleaned)
    cleaned = re.sub(r"\\noindent\b", " ", cleaned)
    cleaned = re.sub(r"\\appendix\b", "\n", cleaned)
    cleaned = re.sub(r"\\bibliography\{[^}]*\}", " ", cleaned)
    cleaned = re.sub(r"\\bibliographystyle\{[^}]*\}", " ", cleaned)
    cleaned = re.sub(r"\\(?:vspace|vskip|hspace|hskip)\*?\{[^}]*\}", " ", cleaned)
    cleaned = re.sub(r"\\(?:smallskip|medskip|bigskip)\b", " ", cleaned)
    cleaned = re.sub(r"\\hfill\b", " ", cleaned)
    cleaned = re.sub(r"\\begin\{(?:quote|snugshade\*?)\}", "\n", cleaned)
    cleaned = re.sub(r"\\end\{(?:quote|snugshade\*?)\}", "\n", cleaned)
    cleaned = _replace_braced_command(cleaned, "flushright", lambda body: body)
    cleaned = _normalize_lettrine_commands(cleaned)
    if not preserve_references:
        cleaned = LABEL_PATTERN.sub(" ", cleaned)
        cleaned = CITATION_PATTERN.sub("", cleaned)
        cleaned = REFERENCE_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"\\textasciitilde(?:\{\}|\\\{\\\})?", " ", cleaned)
    cleaned = cleaned.replace("\\\\", "\n")
    cleaned = cleaned.replace("~", " ")
    return cleaned


def _unwrap_formatting_commands(text: str) -> str:
    current = text
    command_names = ("textbf", "textit", "textup", "emph", "underline", "textrm", "textsc", "mathrm", "mathbf", "mathit", "bd")
    previous = None
    while current != previous:
        previous = current
        current = FORMAT_COMMAND_PATTERN.sub(r"\1", current)
        for command_name in command_names:
            current = _replace_braced_command(current, command_name, lambda body: body)
    current = HREF_PATTERN.sub(r"\1", current)
    current = URL_PATTERN.sub(r"\1", current)
    return current


def _normalize_inline_text(text: str, *, preserve_references: bool = False) -> str:
    """规范化内联文本：去除 LaTeX 结构命令、引用、格式化命令等"""
    cleaned = _strip_structural_commands(text, preserve_references=preserve_references)
    cleaned = _replace_display_math_environments_with_dollars(cleaned)
    cleaned = _strip_control_command_residue(cleaned)
    cleaned = _strip_latex_reference_noise(cleaned, preserve_references=preserve_references)
    cleaned = _replace_latex_symbol_commands(cleaned)
    cleaned = _unwrap_formatting_commands(cleaned)
    cleaned = _strip_plaintext_latex_residue(cleaned, preserve_references=preserve_references)
    cleaned = FOOTNOTE_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"\\hline\b", " ", cleaned)
    cleaned = _apply_outside_inline_math(cleaned, _strip_empty_command_braces)
    cleaned = _apply_outside_inline_math(
        cleaned,
        lambda segment: re.sub(r"\\([A-Z][A-Za-z0-9]+)(?![A-Za-z0-9])", r"\1", segment),
    )
    cleaned = cleaned.replace(r"\_", "_")
    cleaned = cleaned.replace(r"\&", "&").replace(r"\%", "%").replace(r"\_", "_").replace(r"\#", "#")
    cleaned = cleaned.replace(r"\{", "{").replace(r"\}", "}")
    cleaned = re.sub(r"<(?:PLACEHOLDER|PROTECTED)_[^>]+>", " ", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = SIMPLE_SYMBOL_MATH_PATTERN.sub(r"\1", cleaned)
    cleaned = _strip_malformed_inline_math_fragments(cleaned)
    cleaned = re.sub(r"\\([A-Za-z0-9]*[A-Z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])", r"\1", cleaned)
    return cleaned.strip()


def _replace_latex_symbol_commands(text: str) -> str:
    cleaned = text
    for source, target in LATEX_SYMBOL_REPLACEMENTS.items():
        cleaned = cleaned.replace(source, target)
    return cleaned


def _replace_display_math_environments_with_dollars(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        body = (match.group("body") or "").strip()
        return f"$${body}$$" if body else ""

    return DISPLAY_MATH_ENV_BLOCK_PATTERN.sub(_replace, text or "")


def _strip_latex_reference_noise(text: str, *, preserve_references: bool = False) -> str:
    if preserve_references:
        return LABEL_PATTERN.sub("", text)

    cleaned = CITATION_PATTERN.sub("", text)
    cleaned = REFERENCE_PATTERN.sub("", cleaned)
    cleaned = LABEL_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"~?\\cite[a-zA-Z*]*(?:\s*\[[^\]]*\])*\s*\{[^}\n]*(?:\}|$)", "", cleaned)
    cleaned = re.sub(r"\\(?:eqref|autoref|cref|Cref|ref|label)\s*\{[^}\n]*(?:\}|$)", "", cleaned)
    return cleaned


def _strip_plaintext_latex_residue(text: str, *, preserve_references: bool = False) -> str:
    preserved_reference_commands = {
        "eqref",
        "autoref",
        "cref",
        "Cref",
        "ref",
        "label",
    }

    def _transform(segment: str) -> str:
        cleaned = segment
        cleaned = cleaned.replace(r"\ ", " ")
        cleaned = cleaned.replace(r"\,", " ")
        cleaned = cleaned.replace(r"\;", " ")
        cleaned = cleaned.replace(r"\:", " ")
        cleaned = cleaned.replace(r"\!", " ")
        cleaned = re.sub(r"\\penalty\s*-?\d+\b", " ", cleaned)
        cleaned = re.sub(r"\\(?:enspace|quad|qquad|thinspace|medspace|thickspace)\b", " ", cleaned)
        cleaned = ORPHAN_DELIMITER_COMMAND_PATTERN.sub(" ", cleaned)
        cleaned = FORMATTING_PREFIX_RESIDUE_PATTERN.sub("", cleaned)
        cleaned = re.sub(
            r"\\(?:textbf|textit|textup|emph|underline|textrm|textsc|mathrm|mathbf|mathit|bf|it|rm|tt)\b",
            " ",
            cleaned,
        )
        if not preserve_references:
            cleaned = re.sub(r"\\(?:begin|end)\{[^}]*\}", " ", cleaned)

        def _strip_lowercase_command(match: re.Match[str]) -> str:
            command = match.group("command") or ""
            if preserve_references and (command.startswith("cite") or command in preserved_reference_commands):
                return match.group(0)
            if command in {"texttt", "textsubscript", "textsuperscript", "href", "url", "textbackslash", "begin", "end"}:
                return match.group(0)
            return " "

        cleaned = re.sub(r"\\(?P<command>[a-z][A-Za-z@0-9]*)\b", _strip_lowercase_command, cleaned)
        return cleaned

    return _apply_outside_inline_math(text, _transform)


def _strip_empty_command_braces(segment: str) -> str:
    protected_commands = {"textbackslash", "texttt", "textsubscript", "textsuperscript", "href", "url"}

    def _replace(match: re.Match[str]) -> str:
        command = match.group("command") or ""
        if command in protected_commands:
            return match.group(0)
        return command

    return re.sub(r"\\(?P<command>[A-Za-z][A-Za-z0-9]+)\{\}", _replace, segment)


def _apply_outside_inline_math(text: str, transform) -> str:
    if not text:
        return text

    parts: List[str] = []
    cursor = 0
    for match in INLINE_MATH_SEGMENT_PATTERN.finditer(text):
        parts.append(transform(text[cursor : match.start()]))
        parts.append(match.group("block"))
        cursor = match.end()
    parts.append(transform(text[cursor:]))
    return "".join(parts)


def _strip_control_command_residue(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"(?m)^\s*\\renewcommand\*?.*$", " ", cleaned)
    cleaned = re.sub(r"(?m)^\s*\\setcounter\s*\{[^{}]*\}\s*\{[^{}]*\}\s*$", " ", cleaned)
    cleaned = re.sub(
        r"\\(?:re)?newcommand\*?\s*(?:\{[^{}]*\}|\\[A-Za-z@]+)\s*(?:\[[^\]]*\])?\s*\{[^{}]*\}",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"\\setcounter\s*\{[^{}]*\}\s*\{[^{}]*\}", " ", cleaned)
    for command_name in (
        "section",
        "section*",
        "subsection",
        "subsection*",
        "subsubsection",
        "subsubsection*",
        "paragraph",
        "paragraph*",
        "PAR",
        "PARR",
        "defn",
        "textup",
    ):
        cleaned = _replace_braced_command(cleaned, command_name, lambda body: body)
    cleaned = re.sub(r"\\(?:label|phantomsection)\{[^}]*\}", " ", cleaned)
    return cleaned


def _strip_malformed_inline_math_fragments(text: str) -> str:
    cleaned = text
    unescaped_dollar_count = len(re.findall(r"(?<!\\)\$", cleaned))
    if unescaped_dollar_count % 2 == 1:
        cleaned = re.sub(r"(?<!\\)\$[^$]*$", "", cleaned).rstrip()
    return cleaned


def _strip_cjk_wrappers(text: str) -> str:
    previous = text
    current = CJK_WRAPPER_PATTERN.sub(lambda match: match.group("body"), previous)
    while current != previous:
        previous = current
        current = CJK_WRAPPER_PATTERN.sub(lambda match: match.group("body"), previous)
    return current


def _normalize_lettrine_commands(text: str) -> str:
    needle = "\\lettrine"
    cursor = 0
    parts: List[str] = []

    def _normalize_fragment(fragment: str) -> str:
        cleaned = _unwrap_formatting_commands(fragment)
        cleaned = re.sub(r"\\fbox\{([^{}]*)\}\{([^{}]*)\}", r"\1\2", cleaned)
        cleaned = cleaned.replace(r"\{", "{").replace(r"\}", "}")
        cleaned = re.sub(r"\\[A-Za-z]+\*?", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    while True:
        start = text.find(needle, cursor)
        if start < 0:
            parts.append(text[cursor:])
            break

        parts.append(text[cursor:start])
        position = start + len(needle)
        while position < len(text) and text[position].isspace():
            position += 1

        if position < len(text) and text[position] == "[":
            _, next_position = _consume_balanced_group(text, position, "[", "]")
            if next_position <= position:
                parts.append(text[start : start + len(needle)])
                cursor = start + len(needle)
                continue
            position = next_position

        while position < len(text) and text[position].isspace():
            position += 1

        first, next_position = _consume_balanced_group(text, position, "{", "}")
        if first is None or next_position <= position:
            parts.append(text[start : start + len(needle)])
            cursor = start + len(needle)
            continue

        position = next_position
        while position < len(text) and text[position].isspace():
            position += 1

        second, second_end = _consume_balanced_group(text, position, "{", "}")
        if second is None or second_end <= position:
            parts.append(_normalize_fragment(first))
            cursor = position
            continue

        initial = _normalize_fragment(first)
        remainder = _normalize_fragment(second)
        parts.append(f"{initial}{remainder}".strip())
        cursor = second_end

    return "".join(parts)


def _replace_braced_command(text: str, command: str, replacer) -> str:
    needle = f"\\{command}{{"
    cursor = 0
    parts: List[str] = []
    while True:
        start = text.find(needle, cursor)
        if start < 0:
            parts.append(text[cursor:])
            break

        parts.append(text[cursor:start])
        brace_start = start + len(needle) - 1
        depth = 0
        end = None
        index = brace_start
        while index < len(text):
            char = text[index]
            previous = text[index - 1] if index > 0 else ""
            if char == "{" and previous != "\\":
                depth += 1
            elif char == "}" and previous != "\\":
                depth -= 1
                if depth == 0:
                    end = index
                    break
            index += 1

        if end is None:
            parts.append(text[start:])
            break

        body = text[brace_start + 1 : end]
        parts.append(replacer(body))
        cursor = end + 1

    return "".join(parts)


def _replace_command_with_arguments(
    text: str,
    command: str,
    argument_count: int,
    replacer,
    *,
    star_argument_indexes: Optional[set[int]] = None,
) -> str:
    needle = f"\\{command}"
    cursor = 0
    parts: List[str] = []

    while True:
        start = text.find(needle, cursor)
        if start < 0:
            parts.append(text[cursor:])
            break

        parts.append(text[cursor:start])
        position = start + len(needle)
        arguments: List[str] = []
        is_valid = True

        for argument_index in range(argument_count):
            while position < len(text) and text[position].isspace():
                position += 1

            if star_argument_indexes and argument_index in star_argument_indexes and position < len(text) and text[position] == "*":
                arguments.append("*")
                position += 1
                continue

            argument, next_position = _consume_balanced_group(text, position, "{", "}")
            if argument is None or next_position <= position:
                is_valid = False
                break
            arguments.append(argument)
            position = next_position

        if not is_valid:
            parts.append(text[start : start + len(needle)])
            cursor = start + len(needle)
            continue

        parts.append(replacer(arguments))
        cursor = position

    return "".join(parts)


def _build_anchor_html(url: str, label: Optional[str] = None) -> str:
    normalized_url = url.strip().strip("<>").strip()
    if not normalized_url:
        return html.escape(label or url, quote=False)

    normalized_label = _normalize_inline_text(label or normalized_url) or normalized_url
    return (
        f"<a class=\"paper-preview__link\" href=\"{html.escape(normalized_url, quote=True)}\" "
        "target=\"_blank\" rel=\"noreferrer noopener\">"
        f"{html.escape(normalized_label, quote=False)}"
        "</a>"
    )


def _sanitize_anchor_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip()).strip("-").lower()
    return normalized or "target"


def _reference_kind_from_label(label: str) -> str:
    lowered = str(label or "").lower()
    if lowered.startswith(("fig:", "figure:", "fig-")):
        return "figure"
    if lowered.startswith(("tab:", "table:", "tbl:", "tab-")):
        return "table"
    if lowered.startswith(("sec:", "subsec:", "section:", "sec-")):
        return "section"
    if lowered.startswith(("eq:", "equation:", "eq-")):
        return "equation"
    if lowered.startswith(("alg:", "algorithm:", "algo:")):
        return "algorithm"
    return "block"


def _reference_text_for_kind(kind: str, *, uppercase: bool = False) -> str:
    text = {
        "figure": "图",
        "table": "表",
        "section": "章节",
        "equation": "公式",
        "algorithm": "算法",
        "reference": "参考文献",
        "block": "位置",
    }.get(kind, "位置")
    return text.capitalize() if uppercase else text


def _extract_reference_search_url(reference_text: str) -> str:
    doi_match = DOI_PATTERN.search(reference_text)
    if doi_match:
        return f"https://doi.org/{doi_match.group(0)}"

    arxiv_match = ARXIV_REFERENCE_PATTERN.search(reference_text)
    if arxiv_match:
        return f"https://arxiv.org/abs/{arxiv_match.group('id')}"

    return f"https://scholar.google.com/scholar?q={quote_plus(reference_text)}"


def _extract_bibliography_entries(chunk: str) -> List[Dict[str, str]]:
    body = re.sub(r"^\\begin\{thebibliography\}\{[^}]*\}", "", chunk.strip(), count=1)
    body = re.sub(r"\\end\{thebibliography\}\s*$", "", body.strip(), count=1)
    entries: List[Dict[str, str]] = []
    for match in BIBITEM_ENTRY_PATTERN.finditer(body):
        key = str(match.group("key") or "").strip()
        text = _normalize_reference_text(match.group("body") or "")
        if key and text:
            entries.append({"key": key, "text": text})
    return entries


def _consume_balanced_group(text: str, start: int, opening: str, closing: str) -> tuple[Optional[str], int]:
    if start >= len(text) or text[start] != opening:
        return None, start

    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        previous = text[index - 1] if index > 0 else ""
        if char == opening and previous != "\\":
            depth += 1
        elif char == closing and previous != "\\":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index], index + 1

    return None, start


def _extract_tabular_body(chunk: str) -> Optional[str]:
    match = re.search(r"\\begin\{(?P<env>tabular\*?)\}", chunk)
    if not match:
        return None

    cursor = match.end()
    while cursor < len(chunk) and chunk[cursor].isspace():
        cursor += 1

    if cursor < len(chunk) and chunk[cursor] == "[":
        _, cursor = _consume_balanced_group(chunk, cursor, "[", "]")

    while cursor < len(chunk) and chunk[cursor].isspace():
        cursor += 1

    _, cursor = _consume_balanced_group(chunk, cursor, "{", "}")
    if cursor <= match.end():
        return None

    end_marker = f"\\end{{{match.group('env')}}}"
    end_index = chunk.find(end_marker, cursor)
    if end_index < 0:
        return None

    return chunk[cursor:end_index]


def _normalize_table_cell_text(cell: str) -> str:
    cleaned = cell
    cleaned = re.sub(r"^\s*\[[^\]]+\]\s*$", " ", cleaned, flags=re.MULTILINE)
    cleaned = _replace_command_with_arguments(
        cleaned,
        "multirow",
        3,
        lambda args: args[2],
        star_argument_indexes={1},
    )
    cleaned = _replace_command_with_arguments(
        cleaned,
        "multicolumn",
        3,
        lambda args: args[2],
    )
    cleaned = re.sub(r"\\begin\{sideways\}(.*?)\\end\{sideways\}", r"\1", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\\(?:cmidrule(?:\([^)]*\))?|cline)\{[^}]*\}", " ", cleaned)
    cleaned = re.sub(r"\\(?:hdashline|cdashline(?:\{[^}]*\})?)\b", " ", cleaned)
    cleaned = re.sub(r"\\(?:arraybackslash|centering)\b", " ", cleaned)
    cleaned = re.sub(r"\\(?:bf|it|rm|small|footnotesize|scriptsize|tiny)\b", " ", cleaned)
    cleaned = re.sub(r"\\resizebox\{[^}]*\}\{[^}]*\}", " ", cleaned)
    return _normalize_inline_text(cleaned, preserve_references=True)


def _extract_display_math_environment(chunk: str) -> Optional[str]:
    environment_pattern = re.compile(
        r"\\begin\{(?P<env>equation\*?|align\*?|alignat\*?|gather\*?|multline\*?|eqnarray\*?|split|CD)\}"
        r"(?P<body>.*?)"
        r"\\end\{(?P=env)\}",
        re.DOTALL,
    )
    match = environment_pattern.search(chunk)
    if match:
        return match.group(0).strip()

    bracket_match = re.search(r"\\\[(?P<body>.*?)\\\]", chunk, re.DOTALL)
    if bracket_match:
        return bracket_match.group(0).strip()

    return None


def _normalize_display_math_text(text: str) -> str:
    cleaned = LABEL_PATTERN.sub("", text)
    cleaned = _replace_latex_math_macros(cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _replace_latex_math_macros(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"\\argmax(?=(_|\b))", r"\\operatorname*{arg\\,max}", cleaned)
    cleaned = re.sub(r"\\argmin(?=(_|\b))", r"\\operatorname*{arg\\,min}", cleaned)
    cleaned = re.sub(r"\\mean(?=(_|\b))", r"\\operatorname{mean}", cleaned)
    cleaned = re.sub(r"\\softmax(?=(_|\b))", r"\\operatorname{softmax}", cleaned)
    cleaned = re.sub(r"\\trilerp(?=(_|\b))", r"\\operatorname{trilerp}", cleaned)
    cleaned = re.sub(r"\\operatorname\{mean\}_([A-Za-z0-9]+)", r"\\operatorname{mean}_{\1}", cleaned)
    cleaned = re.sub(r"\\operatorname\{softmax\}_([A-Za-z0-9]+)", r"\\operatorname{softmax}_{\1}", cleaned)
    cleaned = re.sub(r"\\mathbb\{R\}_([A-Za-z0-9]+)", r"\\mathbb{R}_{\1}", cleaned)
    cleaned = re.sub(r"\\Re(?=(\b|[\^_{}]))", r"\\mathbb{R}", cleaned)
    cleaned = re.sub(r"(?<![\\A-Za-z])trilerp(?=\s*\()", r"\\operatorname{trilerp}", cleaned)
    return cleaned


def _looks_like_formula_noise(text: str) -> bool:
    compact = FORMULA_NOISE_PATTERN.sub("", text)
    if len(compact) < 18:
        return False

    if re.search(r"[\u4e00-\u9fff]", compact):
        return False

    contains_math_marker = any(
        token in compact for token in ("=", "∑", "τ", "^", "_", "\\frac", "log", "exp", "\\left", "\\right")
    )
    if not contains_math_marker:
        return False

    readable_chars = len(re.findall(r"[A-Za-z0-9=+\-*/^_(){}\[\]<>∑τλ|./]", compact))
    return readable_chars / max(len(compact), 1) >= 0.7


def _strip_formula_noise_from_paragraph(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""

    if re.search(r"[A-Za-z]{3,}(?:\s+[A-Za-z]{2,}){2,}", cleaned):
        return cleaned

    if _looks_like_formula_noise(cleaned):
        return ""

    for separator in ("：", ":"):
        if separator not in cleaned:
            continue
        prefix, suffix = cleaned.rsplit(separator, 1)
        if prefix.strip() and _looks_like_formula_noise(suffix):
            return f"{prefix.strip()}{separator}"

    return cleaned


def _should_render_as_latex_fallback(text: str) -> bool:
    stripped = text.lstrip()
    if stripped.startswith("\\begin{"):
        if stripped.startswith("\\begin{quote") or stripped.startswith("\\begin{snugshade"):
            return False
        return True

    if "\n" not in text:
        return False

    if re.search(r"[\u4e00-\u9fff]", text):
        return False

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    prose_lines = sum(1 for line in lines if re.search(r"[A-Za-z]", line) and not line.startswith("\\"))
    command_lines = sum(1 for line in lines if line.startswith("\\"))

    if prose_lines and "$" in text:
        return False

    if command_lines >= max(2, len(lines) // 2) and text.count("\\") >= 4:
        return True

    return text.count("\\") >= 6 and prose_lines == 0


def _normalize_code_text(text: str) -> str:
    cleaned = _strip_cjk_wrappers(text)
    cleaned = cleaned.replace("\\textbackslash", "\\")
    cleaned = re.sub(r"\\\s+", r"\\", cleaned)
    cleaned = cleaned.replace("\\{", "{").replace("\\}", "}")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _normalize_command_block_text(text: str) -> str:
    cleaned = _strip_cjk_wrappers(text)
    cleaned = re.sub(r"\\(?:ttfamily|rmfamily|sffamily|small|footnotesize|scriptsize|tiny|normalsize|large|Large|LARGE|huge|Huge)\b", " ", cleaned)
    cleaned = cleaned.replace("\\textbackslash", "\\")
    cleaned = cleaned.replace("\\{", "{").replace("\\}", "}")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _contains_latex_source_commands(text: str) -> bool:
    snippet = (text or "").strip()
    if not snippet:
        return False
    if re.search(r"\\begin\{[^}]+\}", snippet) or re.search(r"\\end\{[^}]+\}", snippet):
        return True
    if re.search(r"\\includegraphics(?:\[[^\]]*\])?\{", snippet):
        return True
    if re.search(r"\\[A-Za-z]{2,}", snippet) and snippet.count("\\") >= 2:
        return True
    return False


def _render_latex_source_omitted_note() -> str:
    return (
        "<div class=\"paper-preview__note\">"
        "LaTeX source snippet omitted in HTML preview. Please refer to the PDF version."
        "</div>"
    )


def _render_inline_html(text: str) -> str:
    working = _strip_cjk_wrappers(text)
    code_tokens: Dict[str, str] = {}
    anchor_tokens: Dict[str, str] = {}
    inline_tokens: Dict[str, str] = {}

    def _code_replacer(body: str) -> str:
        token = f"__PAPER_PREVIEW_CODE_{len(code_tokens)}__"
        code_tokens[token] = f"<code>{html.escape(_normalize_code_text(body), quote=False)}</code>"
        return token

    def _anchor_replacer(url: str, label: Optional[str] = None) -> str:
        token = f"__PAPER_PREVIEW_ANCHOR_{len(anchor_tokens)}__"
        anchor_tokens[token] = _build_anchor_html(url, label)
        return token

    def _inline_tag_replacer(tag: str):
        def _replacer(body: str) -> str:
            normalized = _normalize_inline_text(body, preserve_references=True)
            token = f"__PAPER_PREVIEW_INLINE_{len(inline_tokens)}__"
            inline_tokens[token] = (
                f"<{tag}>{html.escape(normalized, quote=False)}</{tag}>"
                if normalized
                else ""
            )
            return token

        return _replacer

    working = _replace_braced_command(working, "texttt", _code_replacer)
    working = _replace_braced_command(working, "textsubscript", _inline_tag_replacer("sub"))
    working = _replace_braced_command(working, "textsuperscript", _inline_tag_replacer("sup"))
    working = _replace_braced_command(working, "bd", lambda body: _normalize_inline_text(body, preserve_references=True))
    working = HREF_COMMAND_PATTERN.sub(
        lambda match: _anchor_replacer(match.group("url"), match.group("label")),
        working,
    )
    working = URL_COMMAND_PATTERN.sub(
        lambda match: _anchor_replacer(match.group("url")),
        working,
    )
    working = ANGLE_BRACKET_URL_PATTERN.sub(
        lambda match: f"[{_anchor_replacer(match.group('url'))}]",
        working,
    )
    working = BARE_URL_PATTERN.sub(lambda match: _anchor_replacer(match.group("url")), working)
    working = working.replace(r"\textbackslash{}", "\\").replace(r"\textbackslash", "\\")
    working = working.replace(r"\%", "%")
    working = working.replace("``", "“").replace("''", "”")
    escaped = html.escape(working, quote=False)
    for token, code_html in code_tokens.items():
        escaped = escaped.replace(html.escape(token, quote=False), code_html)
    for token, anchor_html in anchor_tokens.items():
        escaped = escaped.replace(html.escape(token, quote=False), anchor_html)
    for token, inline_html in inline_tokens.items():
        escaped = escaped.replace(html.escape(token, quote=False), inline_html)
    return escaped


def _normalize_reference_text(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"\\newblock\b", " ", cleaned)
    cleaned = _replace_braced_command(cleaned, "natexlab", lambda body: body)
    cleaned = re.sub(r"\{([^{}]+)\}", r"\1", cleaned)
    cleaned = re.sub(r"(\d{4})\s*([a-z])\b", r"\1\2", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return _normalize_inline_text(cleaned)


def _render_mixed_content_html(text: str) -> Optional[str]:
    if "$$" not in text and r"\[" not in text and "\\begin{" not in text:
        return None

    parts: List[str] = []
    cursor = 0
    matched_math = False
    for match in DISPLAY_MATH_INLINE_PATTERN.finditer(text):
        prose = text[cursor : match.start()]
        parts.extend(_render_mixed_prose_segments(prose))

        raw_block = match.group("block") or ""
        normalized_block = _normalize_display_math_fragment(raw_block)
        if normalized_block:
            matched_math = True
            parts.append(f"<div class=\"paper-preview__math-block\">{html.escape(normalized_block, quote=False)}</div>")

        cursor = match.end()

    if not matched_math:
        return None

    parts.extend(_render_mixed_prose_segments(text[cursor:]))
    return "".join(parts) if parts else None


def _render_mixed_prose_segments(text: str) -> List[str]:
    rendered: List[str] = []
    for paragraph in _paragraphs_from_text(text):
        normalized = _strip_formula_noise_from_paragraph(_normalize_inline_text(paragraph, preserve_references=True))
        if normalized:
            rendered.append(f"<p>{_render_inline_html(normalized)}</p>")
    return rendered


def _normalize_display_math_fragment(text: str) -> str:
    block = text.strip()
    if block.startswith("$$") and block.endswith("$$"):
        inner = block[2:-2]
    elif block.startswith(r"\[") and block.endswith(r"\]"):
        inner = block[2:-2]
    elif block.startswith(r"\begin{"):
        environment_match = re.match(
            r"\\begin\{(?P<env>equation\*?|align\*?|alignat\*?|gather\*?|multline\*?|eqnarray\*?|split|CD)\}(?P<body>[\s\S]*?)\\end\{(?P=env)\}\s*$",
            block,
        )
        inner = environment_match.group("body") if environment_match else block
    else:
        inner = block
    normalized = _normalize_display_math_text(inner)
    return f"$${normalized}$$" if normalized else ""


def _parse_custom_subheading(chunk: str) -> tuple[Optional[str], Optional[str]]:
    match = CUSTOM_SUBHEADING_OPEN_PATTERN.match(chunk)
    if not match:
        return None, None

    cursor = match.end()
    while cursor < len(chunk) and chunk[cursor].isspace():
        cursor += 1

    title, next_cursor = _consume_balanced_group(chunk, cursor, "{", "}")
    if title is None or next_cursor <= cursor:
        return None, None

    return _normalize_inline_text(title), chunk[next_cursor:].strip()


def _extract_title_and_body(text: str) -> tuple[Optional[str], str]:
    raw_text = str(text or "").strip()
    match = HEADING_COMMAND_PATTERN.search(raw_text)
    if not match:
        return None, _normalize_inline_text(raw_text)

    title = _normalize_inline_text(match.group("title")) or None
    prefix = _normalize_inline_text(raw_text[: match.start()]).strip()
    suffix = raw_text[match.end() :].strip()
    body = "\n\n".join(part for part in (prefix, suffix) if part)
    return title, body


def _heading_tag(section_id: str) -> str:
    depth = max(0, str(section_id).count("_"))
    return {0: "h2", 1: "h3", 2: "h4"}.get(depth, "h4")


def _paragraphs_from_text(text: str) -> List[str]:
    cleaned = (text or "").replace("\r\n", "\n").strip()
    if not cleaned:
        return []

    raw_chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", cleaned) if chunk.strip()]
    paragraphs: List[str] = []
    for chunk in raw_chunks:
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        filtered_lines = [line for line in lines if not STRUCTURAL_LINE_PATTERN.match(line)]
        if not filtered_lines:
            continue
        paragraphs.append("\n".join(filtered_lines).strip())
    return paragraphs


def _extract_caption_text(chunk: str) -> Optional[str]:
    captions = _extract_command_group_values(chunk, "caption")
    if not captions:
        return None
    caption = _normalize_inline_text(captions[-1], preserve_references=True)
    return caption or None


def _extract_command_group_values(text: str, command: str) -> List[str]:
    values: List[str] = []
    needle = f"\\{command}"
    cursor = 0

    while True:
        start = text.find(needle, cursor)
        if start < 0:
            break

        group_start = start + len(needle)
        while group_start < len(text) and text[group_start].isspace():
            group_start += 1

        if group_start < len(text) and text[group_start] == "[":
            _, group_start = _consume_balanced_group(text, group_start, "[", "]")

        while group_start < len(text) and text[group_start].isspace():
            group_start += 1

        value, next_cursor = _consume_balanced_group(text, group_start, "{", "}")
        if value is None or next_cursor <= group_start:
            if group_start < len(text) and text[group_start] == "{":
                fallback = _salvage_unbalanced_command_group(text[group_start + 1 :])
                if fallback:
                    values.append(fallback)
            cursor = start + len(needle)
            continue

        values.append(value)
        cursor = next_cursor

    return values


def _strip_first_command_group(text: str, command: str) -> str:
    needle = f"\\{command}"
    start = text.find(needle)
    if start < 0:
        return text

    group_start = start + len(needle)
    while group_start < len(text) and text[group_start].isspace():
        group_start += 1

    if group_start < len(text) and text[group_start] == "[":
        _, group_start = _consume_balanced_group(text, group_start, "[", "]")

    while group_start < len(text) and text[group_start].isspace():
        group_start += 1

    _, next_cursor = _consume_balanced_group(text, group_start, "{", "}")
    if next_cursor <= group_start:
        if group_start < len(text) and text[group_start] == "{":
            fallback = _salvage_unbalanced_command_group(text[group_start + 1 :])
            if fallback:
                fallback_end = group_start + 1 + len(fallback)
                return f"{text[:start]}{text[fallback_end:]}"
        return text

    return f"{text[:start]}{text[next_cursor:]}"


def _salvage_unbalanced_command_group(text: str) -> str:
    fallback = re.split(r"\n\s*\\end\{", text, maxsplit=1)[0]
    fallback = re.split(r"\n\s*\\(?:section|subsection|subsubsection|paragraph|PAR|PARR)\{", fallback, maxsplit=1)[0]
    return fallback.strip()


def _section_anchor_id(section_id: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", str(section_id or "").strip()).strip("-")
    return f"section-{normalized or 'unknown'}"


def _register_label_targets(
    render_state: Dict[str, Any],
    *,
    labels: List[str],
    href: str,
    kind: str,
) -> str:
    if not labels:
        return ""

    anchors: List[str] = []
    label_targets = render_state.setdefault("label_targets", {})
    for label in labels:
        normalized_label = str(label or "").strip()
        if not normalized_label:
            continue
        anchor_id = f"label-{_sanitize_anchor_id(normalized_label)}"
        existing_target = label_targets.get(normalized_label)
        if existing_target and existing_target.get("kind") == "section" and kind != "section":
            continue
        target_href = href if kind == "section" else f"#{anchor_id}"
        label_targets[normalized_label] = {
            "href": target_href,
            "kind": kind or _reference_kind_from_label(normalized_label),
        }
        if kind != "section":
            anchors.append(
                f"<span id=\"{html.escape(anchor_id, quote=True)}\" "
                "class=\"paper-preview__anchor-target\" aria-hidden=\"true\"></span>"
            )
    return "".join(anchors)


def _wrap_reader_block(
    *,
    inner_html: str,
    section_anchor_id: str,
    block_index: int,
    kind: str,
    raw_chunk: Optional[str] = None,
    render_state: Optional[Dict[str, Any]] = None,
) -> str:
    block_id = f"{section_anchor_id}-block-{block_index}"
    label_html = ""
    if render_state is not None and raw_chunk:
        label_html = _register_label_targets(
            render_state,
            labels=_extract_command_group_values(raw_chunk, "label"),
            href=f"#{block_id}",
            kind=kind or "block",
        )
    return (
        f"<div class=\"paper-preview__block paper-preview__block--{kind}\" "
        f"id=\"{html.escape(block_id, quote=True)}\" "
        f"data-block-id=\"{html.escape(block_id, quote=True)}\" "
        f"data-block-kind=\"{html.escape(kind, quote=True)}\">"
        f"{label_html}"
        f"{inner_html}"
        "</div>"
    )


def _is_display_math_block(chunk: str) -> bool:
    stripped = chunk.lstrip()
    if stripped.startswith("\\["):
        return True
    return any(stripped.startswith(f"\\begin{{{environment}}}") for environment in DISPLAY_MATH_ENVIRONMENTS)


def _normalize_source_directories(
    source_dirs: Optional[Iterable[Path | str]],
    output_dir: Optional[Path] = None,
) -> List[Path]:
    candidates: List[Path] = []
    seen: set[str] = set()

    def _add(candidate: Optional[Path | str]) -> None:
        if not candidate:
            return
        path = Path(candidate)
        try:
            normalized = str(path.resolve())
        except Exception:
            normalized = str(path)
        if normalized in seen:
            return
        seen.add(normalized)
        if path.exists() and path.is_dir():
            candidates.append(path)

    for source_dir in source_dirs or []:
        _add(source_dir)

    if output_dir is not None:
        _add(output_dir)
        _add(output_dir.parent)
        try:
            for child in output_dir.parent.iterdir():
                if child.is_dir():
                    _add(child)
        except Exception:
            pass

    return candidates


def _resolve_graphic_path(graphic_path: str, source_dirs: List[Path]) -> Optional[Path]:
    normalized = graphic_path.strip().strip('"').strip("'")
    if not normalized:
        return None

    candidate_path = Path(normalized)
    if candidate_path.is_absolute() and candidate_path.exists():
        return candidate_path

    path_variants = [Path(*normalized.replace("\\", "/").split("/"))]
    if candidate_path.suffix == "":
        path_variants.extend(Path(f"{normalized}{suffix}") for suffix in (".png", ".jpg", ".jpeg", ".webp", ".svg"))

    for source_dir in source_dirs:
        for variant in path_variants:
            candidate = source_dir / variant
            if candidate.exists() and candidate.is_file():
                return candidate

    file_name = candidate_path.name
    if not file_name:
        return None

    for source_dir in source_dirs:
        try:
            return next(path for path in source_dir.rglob(file_name) if path.is_file())
        except StopIteration:
            continue

    return None


def _inline_image_data_uri(path: Optional[Path]) -> Optional[str]:
    if path is None or not path.exists() or not path.is_file():
        return None

    mime_type = mimetypes.guess_type(path.name)[0] or ""
    if not mime_type.startswith("image/"):
        return None

    try:
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return None
    return f"data:{mime_type};base64,{payload}"


def _inline_pdf_data_uri(path: Optional[Path]) -> Optional[str]:
    if path is None or not path.exists() or not path.is_file() or path.suffix.lower() != ".pdf":
        return None

    rasterizer = shutil.which("pdftocairo") or shutil.which("pdftoppm")
    if not rasterizer:
        return None

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_prefix = Path(temp_dir) / "page"
            command = [
                rasterizer,
                "-f",
                "1",
                "-l",
                "1",
                "-singlefile",
                "-png",
                str(path),
                str(output_prefix),
            ]
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                timeout=30,
            )
            return _inline_image_data_uri(output_prefix.with_suffix(".png"))
    except Exception:
        return None


def _extract_graphic_paths(chunk: str) -> List[str]:
    return [match.group("path").strip() for match in INCLUDE_GRAPHICS_PATTERN.finditer(chunk) if match.group("path").strip()]


def _render_list_block(chunk: str, ordered: bool) -> Optional[str]:
    body = re.sub(r"^\\begin\{(?:itemize|enumerate)\}(?:\[[^\]]*\])?", "", chunk.strip(), count=1)
    body = re.sub(r"\\end\{(?:itemize|enumerate)\}\s*$", "", body.strip(), count=1)
    parts = LIST_ITEM_PATTERN.split(body)
    items = []
    for part in parts[1:]:
        normalized = _normalize_inline_text(part, preserve_references=True)
        if normalized:
            items.append(normalized)
    if not items:
        return None

    tag = "ol" if ordered else "ul"
    items_html = "".join(f"<li>{_render_inline_html(item)}</li>" for item in items)
    return f"<{tag} class=\"paper-preview__list\">{items_html}</{tag}>"


def _render_table_block(chunk: str) -> Optional[str]:
    caption = _extract_caption_text(chunk)
    table_body = _extract_tabular_body(chunk) or chunk
    table_body = re.sub(r"(?m)^\s*\[[^\]]+\]\s*$", "\n", table_body)
    table_body = re.sub(r"\\(?:toprule|midrule|bottomrule|hline|hdashline)\b", "\n", table_body)
    table_body = re.sub(r"\\(?:cmidrule(?:\([^)]*\))?|cline)\{[^}]*\}", "\n", table_body)
    table_body = _replace_command_with_arguments(
        table_body,
        "multicolumn",
        3,
        lambda args: args[2],
    )
    table_body = _replace_command_with_arguments(
        table_body,
        "multirow",
        3,
        lambda args: args[2],
        star_argument_indexes={1},
    )
    table_body = re.sub(r"\\begin\{sideways\}(.*?)\\end\{sideways\}", r"\1", table_body, flags=re.DOTALL)

    rows: List[List[str]] = []
    for row in re.split(r"(?<!\\)\\\\", table_body):
        cells = []
        for cell in re.split(r"(?<!\\)&", row):
            normalized = _normalize_table_cell_text(cell)
            if normalized:
                cells.append(normalized)
        if cells:
            rows.append(cells)
    if not rows:
        return None

    header = rows[0]
    body_rows = rows[1:] if len(rows) > 1 else []
    thead = "<thead><tr>" + "".join(f"<th>{_render_inline_html(cell)}</th>" for cell in header) + "</tr></thead>"
    tbody = ""
    if body_rows:
        tbody = "<tbody>" + "".join(
            "<tr>" + "".join(f"<td>{_render_inline_html(cell)}</td>" for cell in row) + "</tr>"
            for row in body_rows
        ) + "</tbody>"

    caption_html = (
        f"<figcaption class=\"paper-preview__caption\">{_render_inline_html(caption)}</figcaption>"
        if caption
        else ""
    )
    return (
        "<figure class=\"paper-preview__figure paper-preview__figure--table\">"
        "<div class=\"paper-preview__table-wrap\">"
        f"<table class=\"paper-preview__table\">{thead}{tbody}</table>"
        "</div>"
        f"{caption_html}"
        "</figure>"
    )


def _render_bibliography_block(chunk: str) -> Optional[str]:
    body = re.sub(r"^\\begin\{thebibliography\}\{[^}]*\}", "", chunk.strip(), count=1)
    body = re.sub(r"\\end\{thebibliography\}\s*$", "", body.strip(), count=1)
    parts = BIBITEM_PATTERN.split(body)
    references = []
    for part in parts[1:]:
        normalized = _normalize_reference_text(part)
        if normalized:
            references.append(normalized)
    if not references:
        return None

    items_html = "".join(
        f"<li class=\"paper-preview__reference-item\">{_render_inline_html(reference)}</li>"
        for reference in references
    )
    return (
        "<section class=\"paper-preview__references\">"
        "<h3 class=\"paper-preview__references-title\">参考文献</h3>"
        f"<ol class=\"paper-preview__references-list\">{items_html}</ol>"
        "</section>"
    )


def _render_bibliography_block_with_links(
    chunk: str,
    render_state: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    references = _extract_bibliography_entries(chunk)
    if not references:
        return None

    reference_targets = render_state.setdefault("reference_targets", {}) if render_state is not None else {}
    items: List[str] = []
    for index, reference in enumerate(references, start=1):
        key = reference["key"]
        reference_id = f"reference-{_sanitize_anchor_id(key)}"
        if render_state is not None:
            reference_targets[key] = {
                "href": f"#{reference_id}",
                "index": index,
                "kind": "reference",
            }

        external_url = _extract_reference_search_url(reference["text"])
        items.append(
            "<li "
            f"id=\"{html.escape(reference_id, quote=True)}\" "
            f"class=\"paper-preview__reference-item\" data-reference-key=\"{html.escape(key, quote=True)}\">"
            f"{_render_inline_html(reference['text'])}"
            f"<a class=\"paper-preview__reference-link\" href=\"{html.escape(external_url, quote=True)}\" "
            "target=\"_blank\" rel=\"noreferrer noopener\">在线检索</a>"
            "</li>"
        )
    items_html = "".join(items)
    return (
        "<section class=\"paper-preview__references\">"
        "<h3 class=\"paper-preview__references-title\">参考文献</h3>"
        f"<ol class=\"paper-preview__references-list\">{items_html}</ol>"
        "</section>"
    )


def _render_figure_block(chunk: str, source_dirs: List[Path]) -> Optional[str]:
    captions = [
        normalized for normalized in (_normalize_inline_text(value, preserve_references=True) for value in _extract_command_group_values(chunk, "caption")) if normalized
    ]
    graphic_paths = _extract_graphic_paths(chunk)
    media_items: List[str] = []
    unresolved: List[str] = []

    for graphic_path in graphic_paths:
        resolved = _resolve_graphic_path(graphic_path, source_dirs)
        data_uri = _inline_image_data_uri(resolved) or _inline_pdf_data_uri(resolved)
        if data_uri:
            alt_text = captions[-1] if captions else Path(graphic_path).stem
            media_items.append(
                "<div class=\"paper-preview__figure-item\">"
                f"<img class=\"paper-preview__figure-image\" src=\"{data_uri}\" alt=\"{html.escape(alt_text, quote=True)}\" loading=\"lazy\" />"
                "</div>"
            )
        else:
            unresolved.append(Path(graphic_path).name or graphic_path)

    caption = captions[-1] if captions else None
    caption_html = (
        f"<figcaption class=\"paper-preview__caption\">{_render_inline_html(caption)}</figcaption>"
        if caption
        else ""
    )
    if media_items:
        unresolved_html = ""
        if unresolved:
            unresolved_html = (
                "<div class=\"paper-preview__note\">"
                f"部分图像仍需查看 PDF：{html.escape(' / '.join(unresolved), quote=False)}"
                "</div>"
            )
        return (
            "<figure class=\"paper-preview__figure paper-preview__figure--rich\">"
            f"<div class=\"paper-preview__figure-grid\">{''.join(media_items)}</div>"
            f"{unresolved_html}"
            f"{caption_html}"
            "</figure>"
        )

    return (
        "<figure class=\"paper-preview__figure\">"
        "<div class=\"paper-preview__note\">图表内容请查看 PDF 版本</div>"
        f"{caption_html}"
        "</figure>"
    )


def _render_environment_block(
    chunk: str,
    source_dirs: List[Path],
    render_state: Optional[Dict[str, Any]] = None,
) -> Optional[tuple[str, str]]:
    stripped = chunk.lstrip()
    if stripped.startswith("\\begin{figure"):
        rendered = _render_figure_block(chunk, source_dirs)
        return ("figure", rendered) if rendered else None

    if stripped.startswith("\\begin{table") or stripped.startswith("\\begin{tabular"):
        rendered = _render_table_block(chunk)
        return ("table", rendered) if rendered else None

    if stripped.startswith("\\begin{itemize"):
        rendered = _render_list_block(chunk, ordered=False)
        return ("list", rendered) if rendered else None

    if stripped.startswith("\\begin{enumerate"):
        rendered = _render_list_block(chunk, ordered=True)
        return ("list", rendered) if rendered else None

    if stripped.startswith("\\begin{thebibliography"):
        rendered = _render_bibliography_block_with_links(chunk, render_state=render_state)
        return ("references", rendered) if rendered else None

    if stripped.startswith("\\begin{algorithm"):
        rendered = _render_algorithm_block(chunk)
        return ("algorithm", rendered) if rendered else None

    if stripped.startswith("\\begin{center"):
        center_body = re.sub(r"^\\begin\{center\}", "", chunk.strip())
        center_body = re.sub(r"\\end\{center\}$", "", center_body.strip(), flags=re.DOTALL)
        if re.search(r"\\begin\{(?:table\*?|tabular\*?)\}", center_body):
            rendered_table = _render_table_block(center_body)
            if rendered_table:
                return ("table", rendered_table)
        if re.search(r"\\includegraphics(?:\[[^\]]*\])?\{", center_body):
            rendered_figure = _render_figure_block(center_body, source_dirs)
            if rendered_figure:
                return ("figure", rendered_figure)

        command_text = _normalize_command_block_text(center_body)
        if not command_text:
            return None
        if _contains_latex_source_commands(command_text):
            return ("note", _render_latex_source_omitted_note())
        rendered = (
            "<div class=\"paper-preview__command-block\">"
            f"<code>{html.escape(command_text, quote=False)}</code>"
            "</div>"
        )
        return ("command", rendered)

    if stripped.startswith("\\begin{quote"):
        quote_text = re.sub(r"^\s*\\begin\{quote\}", "", chunk.strip(), count=1)
        quote_text = re.sub(r"\\end\{quote\}\s*$", "", quote_text.strip(), count=1, flags=re.DOTALL)
        quote_text = _strip_formula_noise_from_paragraph(_normalize_inline_text(quote_text, preserve_references=True))
        if not quote_text:
            return None
        rendered = f"<blockquote><p>{_render_inline_html(quote_text)}</p></blockquote>"
        return ("quote", rendered)

    if stripped.startswith("\\begin{snugshade"):
        shaded_text = re.sub(r"^\s*\\begin\{snugshade\*?\}", "", chunk.strip(), count=1)
        shaded_text = re.sub(r"\\end\{snugshade\*?\}\s*$", "", shaded_text.strip(), count=1, flags=re.DOTALL)
        mixed = _render_mixed_content_html(shaded_text)
        if mixed:
            return ("rich-text", mixed)

        shaded_paragraph = _strip_formula_noise_from_paragraph(
            _normalize_inline_text(shaded_text, preserve_references=True)
        )
        if not shaded_paragraph:
            return None
        return ("paragraph", f"<p>{_render_inline_html(shaded_paragraph)}</p>")

    if _is_display_math_block(chunk):
        equation = _extract_display_math_environment(chunk) or _normalize_inline_text(chunk)
        equation = _normalize_display_math_fragment(equation)
        if not equation:
            return None
        return ("math", f"<div class=\"paper-preview__math-block\">{html.escape(equation, quote=False)}</div>")

    return None


def _extract_special_blocks(
    text: str,
    source_dirs: List[Path],
    render_state: Optional[Dict[str, Any]] = None,
) -> tuple[str, Dict[str, tuple[str, str, str]]]:
    block_map: Dict[str, tuple[str, str, str]] = {}

    def _replace(match: re.Match[str]) -> str:
        token = f"__PAPER_PREVIEW_BLOCK_{len(block_map)}__"
        raw_chunk = match.group(0)
        rendered = _render_environment_block(raw_chunk, source_dirs, render_state=render_state)
        if rendered:
            kind, rendered_html = rendered
            block_map[token] = (kind, rendered_html, raw_chunk)
        else:
            block_map[token] = ("placeholder", "", raw_chunk)
        return f"\n\n{token}\n\n"

    return SPECIAL_ENV_PATTERN.sub(_replace, text), block_map


def _render_subheading_block(chunk: str) -> Optional[str]:
    title, body_raw = _parse_custom_subheading(chunk)
    if title is None and body_raw is None:
        return None

    parts: List[str] = []
    if title:
        parts.append(f"<h4 class=\"paper-preview__subheading\">{html.escape(title, quote=False)}</h4>")

    if body_raw:
        nested_segments = [
            segment.strip()
            for segment in re.split(r"(?=\\(?:subsubsection|subsection|PARR|PAR|paragraph)\{)", body_raw)
            if segment.strip()
        ]
        for segment in nested_segments:
            nested_subheading = _render_subheading_block(segment)
            if nested_subheading:
                parts.append(nested_subheading)
                continue

            mixed_html = _render_mixed_content_html(segment)
            if mixed_html:
                parts.append(mixed_html)
                continue

            body = _strip_formula_noise_from_paragraph(_normalize_inline_text(segment, preserve_references=True))
            if body:
                parts.append(f"<p>{_render_inline_html(body)}</p>")
    return "".join(parts) if parts else None


def _render_algorithm_block(chunk: str) -> Optional[str]:
    body = re.sub(r"^\\begin\{algorithm\*?\}", "", chunk.strip(), count=1)
    body = re.sub(r"\\end\{algorithm\*?\}\s*$", "", body.strip(), count=1)
    caption = _extract_caption_text(body)
    if caption:
        body = _strip_first_command_group(body, "caption")

    body = re.sub(r"\\(?:SetAlgoLined|DontPrintSemicolon|BlankLine|Indp|Indm|tcp\*?)\b", "\n", body)
    body = body.replace("\\\\", "\n")

    steps: List[tuple[int, str]] = []
    depth = 0
    lines = [line.strip() for line in body.splitlines() if line.strip()]

    def _append_step(text: str, step_depth: int) -> None:
        normalized = _normalize_inline_text(text).strip()
        normalized = normalized.strip("{} ").strip()
        if normalized:
            steps.append((max(step_depth, 0), normalized))

    keyword_labels = {
        "KwData": "Data",
        "KwIn": "Input",
        "KwInput": "Input",
        "KwOut": "Output",
        "KwOutput": "Output",
        "KwResult": "Result",
    }
    block_labels = {
        "For": "For",
        "ForEach": "For each",
        "ForPar": "Parallel for",
        "While": "While",
        "If": "If",
        "uIf": "If",
        "ElseIf": "Else if",
        "lElseIf": "Else if",
        "Switch": "Switch",
        "Case": "Case",
        "Repeat": "Repeat",
    }

    for raw_line in lines:
        line = raw_line
        while line.startswith("}"):
            depth = max(depth - 1, 0)
            line = line[1:].lstrip()
        if not line:
            continue

        matched_keyword = False
        for command, label in keyword_labels.items():
            if not line.startswith(f"\\{command}"):
                continue
            argument, _ = _consume_balanced_group(line, len(command) + 1, "{", "}")
            _append_step(f"{label}: {argument or ''}", depth)
            matched_keyword = True
            break
        if matched_keyword:
            continue

        if line.startswith("\\Else"):
            remainder = line.removeprefix("\\Else").strip()
            _append_step(f"Else {remainder}".strip(), depth)
            if line.endswith("{"):
                depth += 1
            continue

        matched_block = False
        for command, label in block_labels.items():
            if not line.startswith(f"\\{command}"):
                continue

            condition, cursor = _consume_balanced_group(line, len(command) + 1, "{", "}")
            if condition is None:
                _append_step(line, depth)
                matched_block = True
                break

            header = f"{label} {condition}".strip()
            _append_step(header, depth)

            inline_body, inline_cursor = _consume_balanced_group(line, cursor, "{", "}")
            if inline_body:
                nested_lines = [nested.strip() for nested in inline_body.splitlines() if nested.strip()]
                for nested_line in nested_lines:
                    _append_step(nested_line, depth + 1)
            elif line.endswith("{") or (inline_cursor <= cursor and cursor < len(line) and line[cursor:].strip().startswith("{")):
                depth += 1

            matched_block = True
            break

        if matched_block:
            continue

        _append_step(line, depth)

    if not caption and not steps:
        return None

    title_html = (
        f"<p class=\"paper-preview__algorithm-title\">{_render_inline_html(caption)}</p>"
        if caption
        else ""
    )
    steps_html = "".join(
        (
            "<li class=\"paper-preview__algorithm-step\" "
            f"data-depth=\"{step_depth}\" style=\"margin-left:{step_depth * 1.25}rem\">"
            f"{_render_inline_html(step_text)}"
            "</li>"
        )
        for step_depth, step_text in steps
    )
    return (
        "<section class=\"paper-preview__algorithm\">"
        f"{title_html}"
        f"<ol class=\"paper-preview__algorithm-steps\">{steps_html}</ol>"
        "</section>"
    )


def _render_block(
    chunk: str,
    source_dirs: List[Path],
    render_state: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    if BLOCK_PLACEHOLDER_PATTERN.fullmatch(chunk):
        return ("placeholder", chunk)

    environment_block = _render_environment_block(chunk, source_dirs, render_state=render_state)
    if environment_block:
        return environment_block

    subheading_block = _render_subheading_block(chunk)
    if subheading_block:
        return ("subheading", subheading_block)

    mixed_html = _render_mixed_content_html(chunk)
    if mixed_html:
        return ("rich-text", mixed_html)

    cleaned = _normalize_inline_text(chunk, preserve_references=True)
    cleaned = _strip_formula_noise_from_paragraph(cleaned)
    if not cleaned:
        return ("empty", "")

    if _should_render_as_latex_fallback(cleaned):
        command_text = _normalize_command_block_text(cleaned)
        if not command_text:
            return ("empty", "")
        if _contains_latex_source_commands(command_text):
            return ("note", _render_latex_source_omitted_note())
        return (
            "command",
            "<div class=\"paper-preview__command-block\">"
            f"<code>{html.escape(command_text, quote=False)}</code>"
            "</div>",
        )

    return ("paragraph", f"<p>{_render_inline_html(cleaned)}</p>")


def _render_section(
    section: Dict[str, Any],
    placeholder_map: Dict[str, str],
    source_dirs: List[Path],
    render_state: Optional[Dict[str, Any]] = None,
) -> str:
    translated = str(section.get("trans_content") or section.get("content") or "").strip()
    if not translated:
        return ""

    translated = _replace_placeholders(translated, placeholder_map)
    translated, block_map = _extract_special_blocks(translated, source_dirs, render_state=render_state)
    title, body = _extract_title_and_body(translated)
    section_anchor_id = _section_anchor_id(str(section.get("section") or ""))
    blocks: List[str] = []
    block_index = 0
    if render_state is not None:
        section_labels = [
            label
            for label in _extract_command_group_values(translated[: max(400, len(title or "") + 160)], "label")
            if label
        ]
        _register_label_targets(
            render_state,
            labels=section_labels,
            href=f"#{section_anchor_id}",
            kind="section",
        )

    if title:
        tag = _heading_tag(str(section.get("section") or ""))
        blocks.append(f"<{tag}>{html.escape(title, quote=False)}</{tag}>")

    for paragraph in _paragraphs_from_text(body):
        if paragraph in block_map:
            kind, rendered, raw_chunk = block_map[paragraph]
            if rendered and kind != "placeholder":
                blocks.append(
                    _wrap_reader_block(
                        inner_html=rendered,
                        section_anchor_id=section_anchor_id,
                        block_index=block_index,
                        kind=kind,
                        raw_chunk=raw_chunk,
                        render_state=render_state,
                    )
                )
                block_index += 1
            continue
        kind, rendered = _render_block(paragraph, source_dirs, render_state=render_state)
        if rendered and kind not in {"empty", "placeholder"}:
            blocks.append(
                _wrap_reader_block(
                    inner_html=rendered,
                    section_anchor_id=section_anchor_id,
                    block_index=block_index,
                    kind=kind,
                    raw_chunk=paragraph,
                    render_state=render_state,
                )
            )
            block_index += 1

    if not blocks:
        return ""

    return (
        f"<section class=\"paper-preview__section\" id=\"{html.escape(section_anchor_id, quote=True)}\" "
        f"data-section-id=\"{html.escape(section_anchor_id, quote=True)}\">"
        + "".join(blocks)
        + "</section>"
    )


def _replace_reference_commands_in_html(html_body: str, render_state: Dict[str, Any]) -> str:
    label_targets: Dict[str, Dict[str, Any]] = render_state.get("label_targets", {})
    reference_targets: Dict[str, Dict[str, Any]] = render_state.get("reference_targets", {})

    def _replace_reference(match: re.Match[str]) -> str:
        labels = [label.strip() for label in (match.group("labels") or "").split(",") if label.strip()]
        command = match.group("command") or "ref"
        links: List[str] = []
        for label in labels:
            target = label_targets.get(label)
            if not target:
                continue
            link_text = _reference_text_for_kind(target.get("kind") or _reference_kind_from_label(label), uppercase=command == "Cref")
            links.append(
                f"<a class=\"paper-preview__xref paper-preview__xref--{html.escape(str(target.get('kind') or 'block'), quote=True)}\" "
                f"href=\"{html.escape(str(target['href']), quote=True)}\">{html.escape(link_text, quote=False)}</a>"
            )
        return "、".join(links)

    def _replace_citation(match: re.Match[str]) -> str:
        keys = [key.strip() for key in (match.group("keys") or "").split(",") if key.strip()]
        links: List[str] = []
        for key in keys:
            target = reference_targets.get(key)
            if not target:
                continue
            citation_index = target.get("index")
            label = f"[{citation_index}]" if citation_index is not None else "[参考文献]"
            links.append(
                f"<a class=\"paper-preview__xref paper-preview__xref--citation\" "
                f"href=\"{html.escape(str(target['href']), quote=True)}\">{html.escape(label, quote=False)}</a>"
            )
        return "".join(links)

    processed = REFERENCE_COMMAND_PATTERN.sub(_replace_reference, html_body)
    processed = CITATION_COMMAND_PATTERN.sub(_replace_citation, processed)
    return processed


def _render_preview_header(paper_metadata: Optional[Dict[str, Any]]) -> str:
    """渲染预览页面头部（论文标题和作者）"""
    if not isinstance(paper_metadata, dict):
        return ""

    title = html.escape(str(paper_metadata.get("title") or "").strip(), quote=False)
    authors = [
        html.escape(str(author or "").strip(), quote=False)
        for author in (paper_metadata.get("authors") or [])
        if str(author or "").strip()
    ]
    if not title and not authors:
        return ""

    authors_html = ""
    if authors:
        authors_html = (
            "<p class=\"paper-preview__authors\">"
            + ", ".join(authors)
            + "</p>"
        )

    return (
        "<header class=\"paper-preview__header\">"
        + (f"<h1 class=\"paper-preview__title\">{title}</h1>" if title else "")
        + authors_html
        + "</header>"
    )


def generate_preview_html(
    output_dir: Path,
    target_dir: Path | None = None,
    source_dirs: Optional[Iterable[Path | str]] = None,
    paper_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """从翻译输出目录生成结构化 HTML 预览页面

    参数:
        output_dir: 翻译输出目录（包含 sections_map.json 等）
        target_dir: 预览文件输出目录（可选，默认使用 output_dir）
        source_dirs: LaTeX 源文件目录列表（用于解析图像路径）
        paper_metadata: 论文元数据（标题、作者等）

    返回:
        包含 asset_type, file_path, file_name, mime_type 的字典

    异常:
        FileNotFoundError: 当 sections_map.json 不存在或无可翻译章节时
    """
    output_root = Path(output_dir)
    sections = _load_json(output_root / "sections_map.json")
    if not sections:
        raise FileNotFoundError("sections_map.json not found or empty")

    placeholder_map = _build_placeholder_map(output_root)
    normalized_source_dirs = _normalize_source_directories(source_dirs, output_root)
    render_state: Dict[str, Any] = {}
    rendered_sections = [
        _render_section(section, placeholder_map, normalized_source_dirs, render_state=render_state)
        for section in sections
        if str(section.get("section")) not in {"-1", "0"}
    ]
    rendered_sections = [section for section in rendered_sections if section]
    if not rendered_sections:
        raise FileNotFoundError("No translated sections available for preview")

    html_body = "".join(rendered_sections)
    html_body = _replace_reference_commands_in_html(html_body, render_state)
    preview_root = Path(target_dir) if target_dir is not None else output_root
    preview_root.mkdir(parents=True, exist_ok=True)
    preview_path = preview_root / "preview.html"
    preview_header = _render_preview_header(paper_metadata)
    preview_html = (
        f"<article class=\"paper-preview\" data-reader-version=\"{PREVIEW_READER_VERSION}\">"
        f"{preview_header}"
        f"{html_body}"
        "</article>"
    )
    preview_path.write_text(preview_html, encoding="utf-8")

    return {
        "asset_type": "preview_html",
        "file_path": str(preview_path),
        "file_name": preview_path.name,
        "mime_type": mimetypes.guess_type(preview_path.name)[0] or "text/html",
    }
