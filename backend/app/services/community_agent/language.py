from __future__ import annotations

import re
from typing import Any, Dict, Iterable

_CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def normalize_response_language(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("zh"):
        return "zh"
    return "en"


def is_chinese_language(value: str | None) -> bool:
    return normalize_response_language(value) == "zh"


def detect_response_language(
    input_text: str,
    *,
    history: Iterable[Dict[str, Any]] | None = None,
    context: Dict[str, Any] | None = None,
) -> str:
    preferred = str((context or {}).get("response_language") or (context or {}).get("target_language") or "").strip()
    if preferred:
        return normalize_response_language(preferred)

    if _CJK_PATTERN.search(str(input_text or "")):
        return "zh"

    for entry in reversed(list(history or [])):
        if _CJK_PATTERN.search(str(entry.get("content") or "")):
            return "zh"

    return "en"


def summary_labels(language: str) -> Dict[str, str]:
    if is_chinese_language(language):
        return {
            "current_status": "结论/当前状态",
            "background_answer": "背景解释/回答",
            "paper_overview": "论文概览",
            "core_points": "核心要点",
            "next_steps": "下一步建议",
            "citations": "引用论文",
        }

    return {
        "current_status": "Conclusion/Current status",
        "background_answer": "Background / Answer",
        "paper_overview": "Paper overview",
        "core_points": "Core points",
        "next_steps": "Next steps",
        "citations": "Citations",
    }

