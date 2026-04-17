from __future__ import annotations

import os
import re
from difflib import SequenceMatcher
from typing import Optional


class PipelineInvariantViolation(RuntimeError):
    """Raised when a hard pipeline invariant is violated."""

    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class SpeculativeRepairForbiddenError(PipelineInvariantViolation):
    """Raised when forbidden speculative structure repair is invoked."""

    def __init__(self, message: str = "forbidden: speculative repair") -> None:
        super().__init__(message, error_code="SPEC_REPAIR_FORBIDDEN")


class RawStructurePayloadViolation(PipelineInvariantViolation):
    """Raised when raw structure tokens are found in an LLM payload."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="RAW_STRUCTURE_EXPOSED")


class RawContentLeakageViolation(PipelineInvariantViolation):
    """Raised when a long contiguous raw source span leaks into payload."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="RAW_ENV_BODY_EXPOSED")


class HardFreezeProtocolViolation(PipelineInvariantViolation):
    """Raised when hard-freeze transport tokens are mutated by the model."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="HARD_FREEZE_PROTOCOL_VIOLATION")


_RAW_STRUCTURE_PATTERNS = (
    (re.compile(r"\\begin\{"), r"\begin{"),
    (re.compile(r"\\end\{"), r"\end{"),
    (re.compile(r"(?<!\\)\$"), "unescaped $"),
)


def assert_no_raw_structure(payload_text: str, *, context: str = "") -> None:
    """Hard-fail if structural delimiters leak into LLM payload."""
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
    """Hard-fail if long contiguous source text leaks into payload."""
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
    if not isinstance(value, str) or not value.strip():
        return False
    if os.path.isabs(value):
        return True
    return bool(re.match(r"^[A-Za-z]:[\\/]", value)) or value.startswith("\\\\")
