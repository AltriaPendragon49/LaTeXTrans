"""
langgraph_orchestrator.py
Phase 4a — StateGraph 执行层
Phase 4b 准入基础设施（Gate 4b-1 / 4b-2）
Phase 4b 功能引入（Gate 4b-3）：CompilationDiagnosticNode（默认禁用）

目标：纯执行权迁移
  - StateGraph 接管 parse→translate→validate→generate→finalize 的执行顺序与失败路径
  - 所有现有 agent（ParserAgent / TranslatorAgent / ValidatorAgent / GeneratorAgent）逻辑零修改
  - 禁止引入任何新推理、新重试逻辑、shadow run 或双架构并行

Phase 4b 准入基础设施（Gate 4b-1 / 4b-2）：
  - 写入 JSONL 审计日志（audit.jsonl），含 task_id
  - 全局流水线超时拦截（MAX_PIPELINE_TIMEOUT_SEC）
  - 节点内不得引入 retry 决策逻辑以外的流程判断

Phase 4b Gate 4b-3：CompilationDiagnosticNode
  - 独立节点，config["use_compilation_diagnostics"]=True 时激活（根据用户要求已调整为默认 True）
  - 仅在 failed_compilation 终态后执行，只输出 DiagnosticReport
  - 绝对零副作用：不修改任何 .tex 文件
"""
from __future__ import annotations

import asyncio
import datetime
import hashlib
import json
import logging
import os
import re
import shutil
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from backend.app.core.timezone_utils import get_cst_now_iso
from .generator_agent import GeneratorAgent
from .parser_agent import ParserAgent
from .translator_agent import TranslatorAgent
from .validator_agent import ValidatorAgent
from .compilation_diagnostic_node import CompilationDiagnosticNode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gate 4b-2 常量：全局超时（秒），可被测试 monkeypatch
# ---------------------------------------------------------------------------
MAX_PIPELINE_TIMEOUT_SEC: float = 1800.0  # 30 分钟

# Gate 4b-2 常量：validate_and_retry 最大轮次
MAX_VALIDATE_RETRIES: int = 3

# ---------------------------------------------------------------------------
# State Schema
# ---------------------------------------------------------------------------


class PipelineState(TypedDict, total=False):
    # 输入字段（run_pipeline 初始化）
    config: Dict[str, Any]
    project_dir: str
    output_dir: str
    mode: int
    on_progress: Optional[Callable[[int, str], None]]

    # 运行时字段（节点间传递）
    task_id: str                     # Gate 4b-1：审计追踪 ID
    transed_project_dir: str
    base_name: str
    translator_agent: Any            # TranslatorAgent 实例（validate 节点复用）
    validation_warning: Optional[str]
    generation_result: Optional[Dict[str, Any]]

    # 输出字段
    final_result: Dict[str, Any]
    diagnostic_report: Optional[Any]  # Gate 4b-3：DiagnosticReport（启用时写入）


# ---------------------------------------------------------------------------
# Gate 4b-1：JSONL 审计日志写入
# ---------------------------------------------------------------------------


def _write_audit_log(
    transed_project_dir: str,
    task_id: str,
    event: str,
    payload: dict = None,
) -> None:
    """向 audit.jsonl 追加一条审计记录（Gate 4b-1）。"""
    audit_path = Path(transed_project_dir) / "audit.jsonl"
    entry = {
        "task_id": task_id,
        "event": event,
        "timestamp": get_cst_now_iso(),
    }
    if payload:
        entry["payload"] = payload
    try:
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error("Failed to write audit log: %s", e)


# ---------------------------------------------------------------------------
# 辅助工具（与 coordinator_agent 完全等价，不共享实现以避免耦合）
# ---------------------------------------------------------------------------


def _update_progress(state: PipelineState, pct: int, msg: str = "") -> None:
    cb = state.get("on_progress")
    if cb:
        cb(pct, msg)


def _write_task_log(output_dir: str, event: str, data: dict = None) -> None:
    log_file = Path(output_dir) / "task_log.json"
    entry = {
        "timestamp": get_cst_now_iso(),
        "event": event,
        **(data or {}),
    }
    logs: list = []
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    logs.append(entry)
    try:
        log_file.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error("Failed to write task log: %s", e)


def _write_stage_failed_log(output_dir: str, stage: str, error: Exception) -> None:
    tb = traceback.format_exc()
    digest = hashlib.sha256(tb.encode("utf-8", errors="replace")).hexdigest()[:16]
    _write_task_log(
        output_dir,
        "stage_failed",
        {
            "stage": stage,
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "traceback_digest": digest,
        },
    )


def _merge_warnings(primary: Optional[str], secondary: Optional[str]) -> Optional[str]:
    if primary and secondary:
        return f"{primary}\n{secondary}"
    return primary or secondary


# ---------------------------------------------------------------------------
# Node: parse
# ---------------------------------------------------------------------------


async def node_parse(state: PipelineState) -> PipelineState:
    transed_project_dir = state["transed_project_dir"]
    base_name = state["base_name"]
    config = state["config"]
    task_id = state.get("task_id", base_name)
    _write_audit_log(transed_project_dir, task_id, "node_enter:parse")
    _t0 = time.monotonic()

    logger.info("Starting LaTeX parsing for %s", base_name)
    _update_progress(state, 5, "Initializing parser")
    try:
        parser_agent = ParserAgent(
            config=config,
            project_dir=state["project_dir"],
            output_dir=transed_project_dir,
            on_progress=lambda s, p, m: _update_progress(state, 5 + int(p * 0.05), m),
        )
        await parser_agent.execute()
        _write_task_log(transed_project_dir, "parsing_completed")
        _update_progress(state, 10, "Parsing completed")
        _write_audit_log(transed_project_dir, task_id, "node_exit:parse",
                         {"status": "ok", "elapsed_ms": (time.monotonic() - _t0) * 1000})
    except Exception as e:
        _write_audit_log(transed_project_dir, task_id, "node_exit:parse",
                         {"status": "error", "elapsed_ms": (time.monotonic() - _t0) * 1000,
                          "error": str(e)})
        _write_stage_failed_log(transed_project_dir, "parse", e)
        raise
    return state


# ---------------------------------------------------------------------------
# Node: translate
# ---------------------------------------------------------------------------


async def node_translate(state: PipelineState) -> PipelineState:
    transed_project_dir = state["transed_project_dir"]
    config = state["config"]
    task_id = state.get("task_id", state.get("base_name", ""))
    _write_audit_log(transed_project_dir, task_id, "node_enter:translate")
    _t0 = time.monotonic()

    logger.info("Starting translation")
    _update_progress(state, 10, "Initializing translator")
    try:
        translator_agent = TranslatorAgent(
            config=config,
            project_dir=state["project_dir"],
            output_dir=transed_project_dir,
            trans_mode=state["mode"],
            generate_terminology=config.get("generate_terminology", False),
            on_progress=lambda s, p, m: _update_progress(state, -1, m)
            if p == -1
            else _update_progress(state, 10 + int(p * 0.6), m),
        )
        await translator_agent.execute()
        _write_task_log(transed_project_dir, "translation_completed")
        _update_progress(state, 70, "Translation completed")
        _write_audit_log(transed_project_dir, task_id, "node_exit:translate",
                         {"status": "ok", "elapsed_ms": (time.monotonic() - _t0) * 1000})
    except Exception as e:
        _write_audit_log(transed_project_dir, task_id, "node_exit:translate",
                         {"status": "error", "elapsed_ms": (time.monotonic() - _t0) * 1000,
                          "error": str(e)})
        _write_stage_failed_log(transed_project_dir, "translate", e)
        raise
    return {**state, "translator_agent": translator_agent}


# ---------------------------------------------------------------------------
# Node: validate_and_retry
# ---------------------------------------------------------------------------


async def node_validate_and_retry(state: PipelineState) -> PipelineState:
    transed_project_dir = state["transed_project_dir"]
    config = state["config"]
    mode = state["mode"]
    translator_agent = state["translator_agent"]
    task_id = state.get("task_id", state.get("base_name", ""))
    _write_audit_log(transed_project_dir, task_id, "node_enter:validate_and_retry")
    _t0 = time.monotonic()
    _update_progress(state, 70, "Validating translation")
    validation_warning: Optional[str] = None

    try:
        validator_agent = ValidatorAgent(
            config=config,
            project_dir=state["project_dir"],
            output_dir=transed_project_dir,
            on_progress=lambda s, p, m: _update_progress(state, 70 + int(p * 0.05), m),
        )
        errors_report = validator_agent.execute()
        initial_errors_count = len(errors_report) if errors_report else 0

        MAX_RETRIES = 3
        retry_count = 0

        if mode == 3:
            # Quick scan mode: skip repair to preserve semantic boundary
            logger.info("Quick scan mode: skipping error repair to preserve translation boundary")
            if errors_report:
                logger.warning(
                    "Quick scan mode detected %d validation errors, but repair is disabled",
                    len(errors_report),
                )
        else:
            if errors_report:
                translator_agent.trans_mode = 1

            while errors_report and retry_count < MAX_RETRIES:
                logger.info(
                    "Retrying translation for errors, attempt %d/%d", retry_count + 1, MAX_RETRIES
                )
                _update_progress(
                    state,
                    75 + int((retry_count / MAX_RETRIES) * 10),
                    f"Retrying errors (attempt {retry_count + 1}/{MAX_RETRIES})",
                )
                translator_agent.errors_report = errors_report
                await translator_agent.execute(error_retry_count=retry_count, Maxtry=MAX_RETRIES)
                errors_report = validator_agent.execute(errors_report)
                retry_count += 1

        final_errors_count = len(errors_report) if errors_report else 0
        fallback_count = int(getattr(translator_agent, "structural_fallback_count", 0) or 0)
        fallback_ratio = float(getattr(translator_agent, "structural_fallback_ratio", 0.0) or 0.0)
        fallback_cap = float(getattr(translator_agent, "structural_fallback_cap", 0.10) or 0.10)
        fallback_cap_mode = str(
            getattr(translator_agent, "structural_fallback_cap_mode", "soft") or "soft"
        )
        filtered_code_like_math_tokens = int(
            getattr(validator_agent, "code_like_filtered_bare_tokens", 0) or 0
        )
        fallback_parts = list(getattr(translator_agent, "structural_fallback_parts", []) or [])
        noop_sections = list(getattr(translator_agent, "noop_sections", []) or [])
        c1_retry_enforced_once = bool(getattr(translator_agent, "c1_retry_enforced_once", False))
        validation_warning = getattr(translator_agent, "structural_fallback_warning", None)

        # Dual-scope validation metrics（与 coordinator_agent 完全等价）
        fallback_count_full = fallback_count_translatable = None
        same_content_sections_full = same_content_sections_translatable = None
        fallback_count_env_math = fallback_count_env_list = fallback_count_env_other = None
        try:
            level_a_re = re.compile(
                r"\\begin\{(?:table|figure|algorithm|algorithmic|theorem|lemma|proof|definition"
                r"|tikzpicture|lstlisting|verbatim|minted)\*?\}"
            )

            def _has_level_a_env(text: str) -> bool:
                return bool(level_a_re.search(text or ""))

            sections_path = Path(transed_project_dir) / "sections_map.json"
            if sections_path.exists():
                sections = json.loads(sections_path.read_text(encoding="utf-8"))
                normal_sections = [s for s in sections if str(s.get("section", "")) != "-1"]
                same_full = [
                    s
                    for s in normal_sections
                    if (s.get("trans_content") or "") == (s.get("content") or "")
                ]
                same_trans = [
                    s for s in same_full if not _has_level_a_env(s.get("content") or "")
                ]
                same_content_sections_full = len(same_full)
                same_content_sections_translatable = len(same_trans)
                fallback_sections = [
                    s
                    for s in normal_sections
                    if s.get("translation_status") == "fallback_source_compile_first"
                ]
                fallback_sections_translatable = [
                    s for s in fallback_sections if not _has_level_a_env(s.get("content") or "")
                ]
                fallback_count_full = len(fallback_sections)
                fallback_count_translatable = len(fallback_sections_translatable)

            envs_path = Path(transed_project_dir) / "envs_map.json"
            if envs_path.exists():
                envs = json.loads(envs_path.read_text(encoding="utf-8"))
                env_fallbacks = [
                    e
                    for e in envs
                    if e.get("translation_status") == "fallback_source_compile_first"
                ]
                fallback_count_env_math = sum(
                    1 for e in env_fallbacks if e.get("fallback_subtype") == "math_env_fallback"
                )
                fallback_count_env_list = sum(
                    1 for e in env_fallbacks if e.get("fallback_subtype") == "list_env_fallback"
                )
                fallback_count_env_other = sum(
                    1
                    for e in env_fallbacks
                    if e.get("fallback_subtype") not in {"math_env_fallback", "list_env_fallback"}
                )
        except Exception as metric_exc:
            logger.warning("Failed to compute dual-scope validation metrics: %s", metric_exc)

        _write_task_log(
            transed_project_dir,
            "validation_completed",
            {
                "errors_count": final_errors_count,
                "initial_errors_count": initial_errors_count,
                "final_errors_count": final_errors_count,
                "retry_count": retry_count,
                "fallback_count": fallback_count,
                "fallback_ratio": round(fallback_ratio, 6),
                "fallback_cap": fallback_cap,
                "fallback_cap_mode": fallback_cap_mode,
                "filtered_code_like_math_tokens": filtered_code_like_math_tokens,
                "fallback_parts": fallback_parts,
                "noop_sections": noop_sections,
                "c1_retry_enforced_once": c1_retry_enforced_once,
                "fallback_count_full": fallback_count_full,
                "fallback_count_translatable": fallback_count_translatable,
                "same_content_sections_full": same_content_sections_full,
                "same_content_sections_translatable": same_content_sections_translatable,
                "fallback_count_env_math": fallback_count_env_math,
                "fallback_count_env_list": fallback_count_env_list,
                "fallback_count_env_other": fallback_count_env_other,
            },
        )
        if validation_warning:
            _write_task_log(
                transed_project_dir,
                "structural_fallback_warning",
                {
                    "warning": validation_warning,
                    "fallback_count": fallback_count,
                    "fallback_ratio": round(fallback_ratio, 6),
                    "fallback_cap": fallback_cap,
                    "fallback_cap_mode": fallback_cap_mode,
                },
            )
        _update_progress(state, 85, "Validation completed")
    except Exception as e:
        _write_audit_log(transed_project_dir, task_id, "node_exit:validate_and_retry",
                         {"status": "error", "elapsed_ms": (time.monotonic() - _t0) * 1000,
                          "error": str(e)})
        _write_stage_failed_log(transed_project_dir, "validate", e)
        raise

    _write_audit_log(transed_project_dir, task_id, "node_exit:validate_and_retry",
                     {"status": "ok", "elapsed_ms": (time.monotonic() - _t0) * 1000})
    return {**state, "validation_warning": validation_warning}


# ---------------------------------------------------------------------------
# Node: generate
# ---------------------------------------------------------------------------


async def node_generate(state: PipelineState) -> PipelineState:
    transed_project_dir = state["transed_project_dir"]
    config = state["config"]
    task_id = state.get("task_id", state.get("base_name", ""))
    _write_audit_log(transed_project_dir, task_id, "node_enter:generate")
    _t0 = time.monotonic()

    logger.info("Generating PDF")
    _update_progress(state, 85, "Generating PDF")

    generator_agent = GeneratorAgent(
        config=config,
        project_dir=state["project_dir"],
        output_dir=transed_project_dir,
        on_progress=lambda s, p, m: _update_progress(state, 85 + int(p * 0.15), m),
    )
    try:
        generation_result = generator_agent.execute()
        _write_audit_log(transed_project_dir, task_id, "node_exit:generate",
                         {"status": "ok", "elapsed_ms": (time.monotonic() - _t0) * 1000})
    except Exception as e:
        _write_audit_log(transed_project_dir, task_id, "node_exit:generate",
                         {"status": "error", "elapsed_ms": (time.monotonic() - _t0) * 1000,
                          "error": str(e)})
        _write_stage_failed_log(transed_project_dir, "generate", e)
        raise

    return {**state, "generation_result": generation_result}


# ---------------------------------------------------------------------------
# Node: abort_structure_invalid
# ---------------------------------------------------------------------------


async def node_abort_structure_invalid(state: PipelineState) -> PipelineState:
    transed_project_dir = state["transed_project_dir"]
    generation_result = state["generation_result"]
    validation_warning = state.get("validation_warning")
    task_id = state.get("task_id", state.get("base_name", ""))
    _write_audit_log(transed_project_dir, task_id, "node_enter:abort_structure_invalid")
    _t0 = time.monotonic()

    error_text = (
        generation_result.get("error_summary")
        or "LaTeX structure guard rejected bundle before compilation"
    )
    failure_reason_code = generation_result.get("failure_reason_code")
    failure_class = generation_result.get("failure_class") or "structural"
    guard_phase = generation_result.get("guard_phase") or "precompile"
    replay_bundle_ref = generation_result.get("replay_bundle_ref")
    warning_text = validation_warning or generation_result.get("warnings")

    _write_task_log(
        transed_project_dir,
        f"structure_guard_failed_{guard_phase}",
        {
            "failure_reason_code": failure_reason_code,
            "failure_class": failure_class,
            "guard_phase": guard_phase,
            "replay_bundle_ref": replay_bundle_ref,
            "error_summary": error_text,
        },
    )
    _write_task_log(
        transed_project_dir,
        "structure_invalid_aborted",
        {
            "failure_reason_code": failure_reason_code,
            "failure_class": failure_class,
            "guard_phase": guard_phase,
            "replay_bundle_ref": replay_bundle_ref,
            "error_summary": error_text,
        },
    )
    _update_progress(state, 100, "Aborted due to structure guard")

    final_result = {
        "status": "structure_invalid",
        "pdf_path": None,
        "error_summary": error_text,
        "warnings": warning_text,
        "failure_reason_code": failure_reason_code,
        "failure_class": failure_class,
        "guard_phase": guard_phase,
        "replay_bundle_ref": replay_bundle_ref,
    }
    _write_audit_log(transed_project_dir, task_id, "node_exit:abort_structure_invalid",
                     {"status": "ok", "elapsed_ms": (time.monotonic() - _t0) * 1000})
    return {**state, "final_result": final_result}


# ---------------------------------------------------------------------------
# Node: finalize（PDF 后处理）
# ---------------------------------------------------------------------------


async def node_finalize(state: PipelineState) -> PipelineState:
    transed_project_dir = state["transed_project_dir"]
    base_name = state["base_name"]
    generation_result = state["generation_result"]
    config = state["config"]
    target_language = config.get("target_language", "zh")
    validation_warning = state.get("validation_warning")
    task_id = state.get("task_id", base_name)
    _write_audit_log(transed_project_dir, task_id, "node_enter:finalize")
    _t0 = time.monotonic()

    PDF_file_path = generation_result.get("pdf_path")

    if PDF_file_path:
        if not Path(PDF_file_path).exists():
            error_summary = (
                generation_result.get("error_summary")
                or f"Compilation returned a missing PDF path: {PDF_file_path}"
            )
            logger.error("Failed to finalize PDF for %s: %s", base_name, error_summary)
            _write_task_log(
                transed_project_dir,
                "compilation_failed",
                {
                    "error_summary": error_summary,
                    "pdf_path": PDF_file_path,
                    "warnings": generation_result.get("warnings"),
                    "error_count": generation_result.get("error_count"),
                    "engine": generation_result.get("engine"),
                },
            )
            _update_progress(state, 100, "Failed to generate PDF")
            final_result = {
                "status": "failed_compilation",
                "pdf_path": None,
                "error_summary": error_summary,
                "warnings": _merge_warnings(validation_warning, generation_result.get("warnings")),
            }
            _write_audit_log(transed_project_dir, task_id, "node_exit:finalize",
                             {"status": "ok", "elapsed_ms": (time.monotonic() - _t0) * 1000})
            return {**state, "final_result": final_result}
        new_PDF_path = os.path.join(
            transed_project_dir, f"{target_language}_{base_name}.pdf"
        )
        try:
            shutil.move(PDF_file_path, new_PDF_path)
        except Exception as move_error:
            error_summary = (
                generation_result.get("error_summary")
                or f"Failed to finalize compiled PDF: {move_error}"
            )
            logger.error("Failed to move compiled PDF for %s: %s", base_name, move_error)
            _write_task_log(
                transed_project_dir,
                "compilation_failed",
                {
                    "error_summary": error_summary,
                    "pdf_path": PDF_file_path,
                    "warnings": generation_result.get("warnings"),
                    "error_count": generation_result.get("error_count"),
                    "engine": generation_result.get("engine"),
                },
            )
            _update_progress(state, 100, "Failed to generate PDF")
            final_result = {
                "status": "failed_compilation",
                "pdf_path": None,
                "error_summary": error_summary,
                "warnings": _merge_warnings(validation_warning, generation_result.get("warnings")),
            }
            _write_audit_log(transed_project_dir, task_id, "node_exit:finalize",
                             {"status": "ok", "elapsed_ms": (time.monotonic() - _t0) * 1000})
            return {**state, "final_result": final_result}

        from backend.app.services.latex.compiler import verify_pdf_ready

        compile_status = generation_result.get("status", "completed")
        compile_warnings = _merge_warnings(validation_warning, generation_result.get("warnings"))
        if compile_status == "completed" and compile_warnings:
            compile_status = "completed_with_warnings"
        if verify_pdf_ready(new_PDF_path):
            logger.info("PDF verified ready: %s", new_PDF_path)
            if compile_status == "completed_with_warnings":
                _write_task_log(
                    transed_project_dir,
                    "compilation_completed_with_warnings",
                    {"pdf_path": new_PDF_path, "warnings": compile_warnings},
                )
                _update_progress(state, 100, "Translation completed with compilation warnings")
            else:
                _write_task_log(
                    transed_project_dir,
                    "compilation_completed",
                    {"pdf_path": new_PDF_path},
                )
                _update_progress(state, 100, "Translation completed successfully")
        else:
            logger.warning("PDF may not be fully ready: %s", new_PDF_path)
            compile_status = "completed_with_warnings"
            compile_warnings = (
                compile_warnings or "PDF generated but readiness verification timed out"
            )
            _write_task_log(
                transed_project_dir,
                "compilation_completed_with_warnings",
                {"pdf_path": new_PDF_path, "warnings": compile_warnings},
            )
            _update_progress(state, 100, "Translation completed, PDF may need refresh")

        final_result = {
            "status": compile_status,
            "pdf_path": new_PDF_path,
            "error_summary": None,
            "warnings": compile_warnings,
        }
        _write_audit_log(transed_project_dir, task_id, "node_exit:finalize",
                         {"status": "ok", "elapsed_ms": (time.monotonic() - _t0) * 1000})
        return {**state, "final_result": final_result}

    else:
        error_summary = generation_result.get("error_summary") or "No PDF path returned"
        logger.error("Failed to generate PDF for %s: %s", base_name, error_summary)
        _write_task_log(
            transed_project_dir,
            "compilation_failed",
            {
                "error_summary": error_summary,
                "warnings": generation_result.get("warnings"),
                "error_count": generation_result.get("error_count"),
                "engine": generation_result.get("engine"),
            },
        )
        _update_progress(state, 100, "Failed to generate PDF")
        final_result = {
            "status": "failed_compilation",
            "pdf_path": None,
            "error_summary": error_summary,
            "warnings": _merge_warnings(validation_warning, generation_result.get("warnings")),
        }
        _write_audit_log(transed_project_dir, task_id, "node_exit:finalize",
                         {"status": "ok", "elapsed_ms": (time.monotonic() - _t0) * 1000})
        return {**state, "final_result": final_result}


# ---------------------------------------------------------------------------
# Conditional edge router（generate 之后）
# ---------------------------------------------------------------------------


def _route_after_generate(state: PipelineState) -> str:
    result = state.get("generation_result") or {}
    if result.get("status") == "structure_invalid":
        return "abort_structure_invalid"
    return "finalize"


# ---------------------------------------------------------------------------
# Gate 4b-3：node_compilation_diagnostic（默认禁用，feature flag 激活后才挂入图）
# ---------------------------------------------------------------------------


async def node_compilation_diagnostic(state: PipelineState) -> PipelineState:
    """
    Phase 4b 诊断节点（Gate 4b-3）。

    只在 use_compilation_diagnostics=True 且编译失败后激活。
    输出：DiagnosticReport（写入 final_result["diagnostic_report"]）。
    零副作用：绝对不写任何 .tex 文件。
    """
    transed_project_dir = state["transed_project_dir"]
    task_id = state.get("task_id", state.get("base_name", ""))
    config = state["config"]
    final_result = state.get("final_result") or {}
    error_summary = final_result.get("error_summary") or ""
    error_count = final_result.get("error_count", 0) or 0

    _write_audit_log(transed_project_dir, task_id, "node_enter:compilation_diagnostic")
    _t0 = time.monotonic()

    try:
        diag_node = CompilationDiagnosticNode(config=config, task_id=task_id)
        report = await diag_node.execute(
            error_summary=error_summary,
            error_count=error_count,
        )
        _write_audit_log(
            transed_project_dir, task_id, "node_exit:compilation_diagnostic",
            {"status": "ok", "elapsed_ms": (time.monotonic() - _t0) * 1000,
             "is_actionable": report.is_actionable, "confidence": report.confidence},
        )
        return {**state,
                "diagnostic_report": report,
                "final_result": {**final_result, "diagnostic_report": report.to_dict()}}
    except Exception as e:
        _write_audit_log(
            transed_project_dir, task_id, "node_exit:compilation_diagnostic",
            {"status": "error", "elapsed_ms": (time.monotonic() - _t0) * 1000, "error": str(e)},
        )
        logger.warning("CompilationDiagnosticNode failed (non-fatal): %s", e)
        return state  # 失败静默降级，不影响主流程


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------


def build_pipeline_graph(enable_diagnostics: bool = True) -> Any:
    """组装并编译 PipelineState StateGraph，返回可调用的已编译图。

    Args:
        enable_diagnostics: 是否挂入 compilation_diagnostic 节点（Gate 4b-3）。
                            默认 True（根据用户要求已调整为默认开启）。
    """
    graph = StateGraph(PipelineState)

    graph.add_node("parse", node_parse)
    graph.add_node("translate", node_translate)
    graph.add_node("validate_and_retry", node_validate_and_retry)
    graph.add_node("generate", node_generate)
    graph.add_node("abort_structure_invalid", node_abort_structure_invalid)
    graph.add_node("finalize", node_finalize)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "translate")
    graph.add_edge("translate", "validate_and_retry")
    graph.add_edge("validate_and_retry", "generate")
    graph.add_conditional_edges(
        "generate",
        _route_after_generate,
        {
            "abort_structure_invalid": "abort_structure_invalid",
            "finalize": "finalize",
        },
    )
    graph.add_edge("abort_structure_invalid", END)

    if enable_diagnostics:
        # Gate 4b-3：将 finalize 的出口接到诊断节点，诊断后结束
        graph.add_node("compilation_diagnostic", node_compilation_diagnostic)
        graph.add_edge("finalize", "compilation_diagnostic")
        graph.add_edge("compilation_diagnostic", END)
    else:
        graph.add_edge("finalize", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_pipeline(
    config: Dict[str, Any],
    project_dir: str,
    output_dir: str,
    on_progress: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """
    执行 Phase 4a StateGraph 翻译流水线。

    与 CoordinatorAgent.workflow_latextrans_async() 行为完全等价。

    Args:
        config: 翻译配置字典
        project_dir: 原始项目目录
        output_dir: 输出根目录
        on_progress: 可选进度回调 (percentage, message) -> None

    Returns:
        结果字典 {status, pdf_path, error_summary, warnings, ...（视情况含 failure_* 字段）}
    """
    base_name = os.path.basename(project_dir)
    target_language = config.get("target_language", "zh")
    transed_project_dir = os.path.join(output_dir, f"{target_language}_{base_name}")

    # 从 config 中提取 task_id，便于审计日志追踪（Gate 4b-1）
    task_id: str = config.get("task_id") or base_name

    os.makedirs(transed_project_dir, exist_ok=True)
    _write_task_log(
        transed_project_dir,
        "task_started",
        {
            "project": base_name,
            "config": {k: v for k, v in config.items() if k != "llm_config"},
        },
    )

    # Gate 4b-1：写入 pipeline_start 审计条目
    _write_audit_log(transed_project_dir, task_id, "pipeline_start", {"project": base_name, "mode": config.get("mode", 0)})

    initial_state: PipelineState = {
        "config": config,
        "project_dir": project_dir,
        "output_dir": output_dir,
        "mode": config.get("mode", 0),
        "on_progress": on_progress,
        "transed_project_dir": transed_project_dir,
        "base_name": base_name,
        "task_id": task_id,
        "translator_agent": None,
        "validation_warning": None,
        "generation_result": None,
        "diagnostic_report": None,
        "final_result": {
            "status": "failed",
            "pdf_path": None,
            "error_summary": "Workflow did not run",
            "warnings": None,
        },
    }

    # Gate 4b-3：按 feature flag 决定是否挂入诊断节点（默认开启）
    enable_diagnostics = bool(config.get("use_compilation_diagnostics", True))
    graph = build_pipeline_graph(enable_diagnostics=enable_diagnostics)

    # Gate 4b-2：全局超时拦截
    try:
        final_state = await asyncio.wait_for(
            graph.ainvoke(initial_state),
            timeout=MAX_PIPELINE_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        _write_audit_log(
            transed_project_dir, task_id, "pipeline_timeout",
            {"timeout_sec": MAX_PIPELINE_TIMEOUT_SEC}
        )
        raise

    # Gate 4b-1：写入 pipeline_end 审计条目
    _write_audit_log(transed_project_dir, task_id, "pipeline_end", {"status": final_state.get("final_result", {}).get("status")})

    return final_state["final_result"]
