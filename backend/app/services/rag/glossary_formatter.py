"""术语表格式化工具 - 将检索到的术语渲染为 <Glossary> XML 块"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── 术语表块格式 ─────────────────────────────────────────────────────

_GLOSSARY_OPEN = "<Glossary>"
_GLOSSARY_CLOSE = "</Glossary>"
_GLOSSARY_LINE_TPL = "{source_term} -> {target_term}"


def format_glossary_block(terms: list[dict]) -> str:
    """将术语字典列表格式化为紧凑的 ``<Glossary>`` 块。

    参数
    ----------
    terms : list[dict]
        每个字典必须包含 ``"source_term"`` 和 ``"target_term"`` 键。

    返回
    -------
    str
        格式化后的块::

            <Glossary>
            source_term_1 -> target_term_1
            source_term_2 -> target_term_2
            </Glossary>

        如果 *terms* 为空，返回空字符串（无块输出）。
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

    # 如果所有条目均为空，返回空字符串。
    if len(lines) <= 2:
        return ""

    return "\n".join(lines)


def estimate_token_count(glossary_block: str) -> int:
    """粗略估计术语表块的 token 数量。

    使用 ``len(text) // 4`` 作为粗略启发式估计，适用于上下文预算检查。

    参数
    ----------
    glossary_block : str
        已格式化的术语表块（或空字符串）。

    返回
    -------
    int
        估计的 token 数量（空输入返回 ``0``）。
    """
    if not glossary_block:
        return 0
    return max(1, len(glossary_block) // 4)


def truncate_glossary(glossary_block: str, max_tokens: int) -> str:
    """截断术语表块以适应 token 预算。

    在不超过 ``max_tokens`` 的前提下尽可能保留完整的术语行。
    只要至少有一行术语能放入预算，``<Glossary>`` 和 ``</Glossary>`` 分隔符始终包含。

    参数
    ----------
    glossary_block : str
        已格式化的术语表块。
    max_tokens : int
        最大允许的 token 数量。

    返回
    -------
    str
        可能被截断的术语表块，如果仅分隔符就超出预算则返回空字符串。
    """
    if not glossary_block or max_tokens <= 0:
        return ""

    lines = glossary_block.splitlines()
    if len(lines) < 2:
        return ""

    # 仅保留分隔符。
    kept = [_GLOSSARY_OPEN, _GLOSSARY_CLOSE]
    delimiters_block = "\n".join(kept)
    if estimate_token_count(delimiters_block) > max_tokens:
        return ""

    # 在预算内逐条添加内容行。
    content_lines = lines[1:-1]  # 开闭标签之间的所有内容
    for line in content_lines:
        candidate_block = "\n".join(kept[:-1] + [line, _GLOSSARY_CLOSE])
        if estimate_token_count(candidate_block) > max_tokens:
            break
        kept.insert(-1, line)

    return "\n".join(kept)
