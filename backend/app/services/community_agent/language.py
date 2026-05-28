"""语言检测与响应语言配置"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable

# CJK 字符正则模式
_CJK_PATTERN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")


def normalize_response_language(value: str | None) -> str:
    """规范化响应语言代码（'zh' 或 'en'）"""
    normalized = str(value or "").strip().lower()
    if normalized.startswith("zh"):
        return "zh"
    return "en"


def is_chinese_language(value: str | None) -> bool:
    """判断语言代码是否为中文"""
    return normalize_response_language(value) == "zh"


def detect_response_language(
    input_text: str,
    *,
    history: Iterable[Dict[str, Any]] | None = None,
    context: Dict[str, Any] | None = None,
) -> str:
    """从上下文和输入中自动检测响应语言

    优先级: context > 输入文本 CJK 检测 > 历史记录 CJK 检测 > 默认英文
    """
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
    """根据语言返回摘要区块标签"""
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
