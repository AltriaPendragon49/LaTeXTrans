"""Agent 输出格式化 - 将结构化槽位渲染为自然语言摘要"""

from __future__ import annotations

from typing import Any, Dict, List

from .language import summary_labels


def format_summary(
    *,
    slots: Dict[str, Any],
    citations: List[Dict[str, Any]],
    citation_ids: List[str],
    language: str = "en",
) -> str:
    """将结构化槽位和引用格式化为人类可读的摘要文本

    参数:
        slots: 结构化答案槽位（current_status, background_answer 等）
        citations: 引用条目列表
        citation_ids: 引用 ID 列表（决定引用顺序）
        language: 输出语言

    返回:
        格式化后的多段文本
    """
    labels = summary_labels(language)
    sections: List[str] = [
        f"{labels['current_status']}: {str(slots.get('current_status') or '').strip()}",
        f"{labels['background_answer']}: {str(slots.get('background_answer') or '').strip()}",
    ]

    paper_overview = str(slots.get("paper_overview") or "").strip()
    if paper_overview:
        sections.append(f"{labels['paper_overview']}: {paper_overview}")

    core_points = [str(item).strip() for item in (slots.get("core_points") or []) if str(item).strip()]
    if core_points:
        sections.append(f"{labels['core_points']}:\n" + "\n".join(f"- {item}" for item in core_points))

    next_steps = [str(item).strip() for item in (slots.get("next_steps") or []) if str(item).strip()]
    if next_steps:
        sections.append(f"{labels['next_steps']}:\n" + "\n".join(f"- {item}" for item in next_steps))

    if citation_ids:
        citation_map = {str(item.get("id")): item for item in citations}
        lines: List[str] = []
        for index, citation_id in enumerate(citation_ids, start=1):
            citation = citation_map.get(citation_id)
            if not citation:
                continue
            line = f"{index}. {citation.get('title')}"
            if citation.get("arxiv_id"):
                line += f" (arXiv:{citation.get('arxiv_id')})"
            lines.append(line)
        if lines:
            sections.append(f"{labels['citations']}:\n" + "\n".join(lines))

    return "\n\n".join(sections)
