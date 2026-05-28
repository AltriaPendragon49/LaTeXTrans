"""管线不变量检查模块。

定义在翻译管线中必须强制遵守的硬性不变量异常类及断言函数。
"""
from __future__ import annotations

import os
import re
from difflib import SequenceMatcher
from typing import Optional


class PipelineInvariantViolation(RuntimeError):
    """当硬性管线不变量被违反时抛出。"""

    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class SpeculativeRepairForbiddenError(PipelineInvariantViolation):
    """当禁止的推测性结构修复被调用时抛出。"""

    def __init__(self, message: str = "forbidden: speculative repair") -> None:
        super().__init__(message, error_code="SPEC_REPAIR_FORBIDDEN")


class RawStructurePayloadViolation(PipelineInvariantViolation):
    """当 LLM 载荷中发现原始结构标记时抛出。"""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="RAW_STRUCTURE_EXPOSED")


class RawContentLeakageViolation(PipelineInvariantViolation):
    """当连续的长原始源文本泄漏到载荷中时抛出。"""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="RAW_ENV_BODY_EXPOSED")


class HardFreezeProtocolViolation(PipelineInvariantViolation):
    """当硬冻结传输令牌被模型修改时抛出。"""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="HARD_FREEZE_PROTOCOL_VIOLATION")


# 原始结构标记的正则表达式模式
_RAW_STRUCTURE_PATTERNS = (
    (re.compile(r"\\begin\{"), r"\begin{"),
    (re.compile(r"\\end\{"), r"\end{"),
    (re.compile(r"(?<!\\)\$"), "unescaped $"),
)


def assert_no_raw_structure(payload_text: str, *, context: str = "") -> None:
    """如果结构分隔符泄漏到 LLM 载荷中，则硬性失败。"""
    text = payload_text or ""
    for pattern, label in _RAW_STRUCTURE_PATTERNS:
        hit = pattern.search(text)
        if not hit:
            continue
        pos = hit.start()
        sample = text[max(0, pos - 40): pos + 40]
        raise RawStructurePayloadViolation(
            f"raw structure token detected ({label}) in payload"
            f"{' [' + context + ']' if context else ''}: {sample!r}"
        )


def assert_no_long_raw_span(
    payload_text: str,
    source_text: str,
    *,
    min_span: int = 200,
    context: str = "",
) -> None:
    """如果连续长源文本泄漏到载荷中，则硬性失败。"""
    payload = payload_text or ""
    source = source_text or ""
    if min_span <= 0 or len(payload) < min_span or len(source) < min_span:
        return

    match = SequenceMatcher(a=payload, b=source, autojunk=False).find_longest_match(
        0, len(payload), 0, len(source)
    )
    if match.size < min_span:
        return

    leaked = payload[match.a: match.a + min(match.size, min_span + 40)]
    raise RawContentLeakageViolation(
        "long contiguous raw source span leaked into payload"
        f"{' [' + context + ']' if context else ''} (span={match.size}): {leaked!r}"
    )


def is_absolute_path_like(value: str) -> bool:
    """判断给定字符串是否类似于绝对路径。"""
    if not isinstance(value, str) or not value.strip():
        return False
    if os.path.isabs(value):
        return True
    return bool(re.match(r"^[A-Za-z]:[\\/]", value)) or value.startswith("\\\\")
