"""任务详情推断服务

根据任务状态、阶段、消息和进度推断当前任务的详细状态码和参数，
供前端展示精细化的任务进度信息。
"""

from __future__ import annotations

import re
from typing import Any, Optional

from backend.app.core.config import CompilationStage, TaskStatus


StageDetail = tuple[Optional[str], Optional[dict[str, Any]]]

# 进度消息正则匹配模式
_TRANSLATED_RE = re.compile(r"Translated (\d+)/(\d+)", re.IGNORECASE)
_RETRANSLATED_RE = re.compile(r"Retranslated (\d+)/(\d+) \(B:retry\)", re.IGNORECASE)
_PROCESSED_A_RE = re.compile(r"Processed (\d+)/(\d+) \(A:[^)]+\)", re.IGNORECASE)
_PROCESSED_C1_RE = re.compile(r"Processed (\d+)/(\d+) \(C1:[^)]+\)", re.IGNORECASE)
_PROCESSED_C2_RE = re.compile(r"Processed (\d+)/(\d+) \(C2:[^)]+\)", re.IGNORECASE)
_RATE_LIMIT_RE = re.compile(r"rate limited", re.IGNORECASE)
_RATE_LIMIT_WAIT_RE = re.compile(r"waiting\s+(?P<wait>\d+)s", re.IGNORECASE)


def normalize_stage(stage: Optional[str]) -> Optional[str]:
    """规范化阶段名称（如 'extracting' -> 'downloading'）"""
    if stage == "extracting":
        return "downloading"
    return stage


def normalize_detail_params(
    params: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """规范化详情参数，去除 None 值并确保值类型为基本类型"""
    if not params:
        return None

    normalized: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            normalized[key] = value
        else:
            normalized[key] = str(value)
    return normalized or None


def infer_task_detail(
    *,
    status: Optional[str],
    stage: Optional[str],
    message: Optional[str],
    progress: Optional[int],
    warnings: Optional[str] = None,
) -> StageDetail:
    """根据任务状态推断当前详情码和参数

    参数:
        status: 任务状态（如 queued, processing, completed 等）
        stage: 任务阶段（如 downloading, translating, compiling 等）
        message: 状态消息
        progress: 进度百分比 (0-100)
        warnings: 警告信息

    返回:
        (detail_code, detail_params) 元组，code 为 None 表示无法推断
    """
    normalized_stage = normalize_stage(stage)
    msg = (message or "").strip()

    if status == TaskStatus.QUEUED.value:
        return "task_queued", None

    if status == TaskStatus.PENDING.value:
        if normalized_stage == "downloading":
            return "download_source_complete", None
        return "task_waiting", None

    if status in {
        TaskStatus.COMPLETED.value,
        TaskStatus.COMPLETED_WITH_WARNINGS.value,
    }:
        return "compile_complete", None

    if normalized_stage == "downloading":
        if progress in (None, 0):
            return "download_source_starting", None
        if progress >= 100:
            return "download_source_complete", None
        return "download_source_progress", {"percent": progress}

    if normalized_stage == "downloading_pdf":
        if progress in (None, 0):
            return "download_pdf_starting", None
        if progress >= 100:
            return "download_pdf_complete", None
        return "download_pdf_progress", {"percent": progress}

    if normalized_stage == "validating":
        if progress in (None, 0):
            return "validate_source_starting", None
        return "validate_source_complete", None if progress >= 100 else {"percent": progress}

    if normalized_stage == CompilationStage.PARSING.value:
        return "translation_starting", None

    if normalized_stage == CompilationStage.TRANSLATING.value:
        if not msg or "Initializing translation" in msg:
            return "translation_starting", None

        translated_match = _TRANSLATED_RE.search(msg)
        if translated_match:
            current, total = translated_match.groups()
            return "translation_running", {"current": int(current), "total": int(total)}

        retried_match = _RETRANSLATED_RE.search(msg)
        if retried_match:
            current, total = retried_match.groups()
            return "translation_retry_failed_chunks", {"current": int(current), "total": int(total)}

        processed_a_match = _PROCESSED_A_RE.search(msg)
        if processed_a_match:
            current, total = processed_a_match.groups()
            return "translation_restore_environment", {"current": int(current), "total": int(total)}

        processed_c1_match = _PROCESSED_C1_RE.search(msg)
        if processed_c1_match:
            current, total = processed_c1_match.groups()
            return "translation_restore_structure", {"current": int(current), "total": int(total)}

        processed_c2_match = _PROCESSED_C2_RE.search(msg)
        if processed_c2_match:
            current, total = processed_c2_match.groups()
            return "translation_apply_fallback", {"current": int(current), "total": int(total)}

        if "Validating translation results" in msg or "Structure invariant" in msg:
            return "translation_validate_results", None

        rate_limit_match = _RATE_LIMIT_RE.search(msg)
        if rate_limit_match:
            wait_match = _RATE_LIMIT_WAIT_RE.search(msg)
            wait = wait_match.group("wait") if wait_match else None
            params = {"retry_in_seconds": int(wait)} if wait else None
            return "task_rate_limited_retrying", params

        return "translation_running", None

    if normalized_stage == CompilationStage.COMPILING.value:
        if "Applying formatting config" in msg:
            return "formatting_apply_config", None

        if msg.startswith("⚠ 排版提示："):
            return "formatting_warning", {"warning_text": msg.replace("⚠ 排版提示：", "", 1).strip()}

        if "Compiling PDF document" in msg:
            return "compile_prepare_pdf", None

        if msg:
            return "compile_running", None

    if normalized_stage == CompilationStage.DONE.value:
        return "compile_complete", None

    if warnings:
        return "formatting_warning", {"warning_text": warnings}

    return None, None
