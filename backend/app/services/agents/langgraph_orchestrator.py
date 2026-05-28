"""Origin CLI parity LangGraph 编排器。

生产后端有意运行单一的翻译核心管线：
解析 -> 翻译 -> 验证/重试 -> 生成 -> 收尾。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from backend.app.core.config import get_settings
from backend.app.core.timezone_utils import get_cst_now_iso
from backend.app.models.config_models import (
    ORIGIN_CLI_PARITY_MODE,
    normalize_origin_cli_parity_agent_config,
)
from backend.app.utils.async_blocking import run_blocking

from .generator_agent import GeneratorAgent
from .parser_agent import ParserAgent
from .translator_agent import TranslatorAgent
from .validator_agent import ValidatorAgent

logger = logging.getLogger(__name__)

# 管线超时和重试配置常量
MAX_PIPELINE_TIMEOUT_SEC: float = 1800.0
MAX_VALIDATE_RETRIES: int = 3
MAX_CONSECUTIVE_NO_PROGRESS_REMEDIAL_ATTEMPTS: int = 3


class PipelineState(TypedDict, total=False):
    """管线状态 TypedDict，用于 LangGraph StateGraph 的节点间状态传递。"""
    config: Dict[str, Any]
    project_dir: str
    output_dir: str
    mode: int
    on_progress: Optional[Callable[[int, str], None]]
    task_id: str
    transed_project_dir: str
    base_name: str
    translator_agent: Any
    validation_warning: Optional[str]
    generation_result: Optional[Dict[str, Any]]
    final_result: Dict[str, Any]


def _resolve_pipeline_timeout_seconds(config: Dict[str, Any]) -> float:
    """从配置中解析管线超时秒数。"""
    raw_value = (config or {}).get("pipeline_timeout_seconds")
    if raw_value is None:
        raw_value = getattr(get_settings(), "pipeline_timeout_seconds", MAX_PIPELINE_TIMEOUT_SEC)
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return float(MAX_PIPELINE_TIMEOUT_SEC)


def _write_audit_log(
    transed_project_dir: str,
    task_id: str,
    event: str,
    payload: Optional[dict] = None,
) -> None:
    """将审计事件追加写入 audit.jsonl 文件。"""
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
    except Exception as exc:
        logger.error("Failed to write audit log: %s", exc)


def _write_task_log(output_dir: str, event: str, data: Optional[dict] = None) -> None:
    """将结构化事件追加写入 task_log.json 文件。"""
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
    except Exception as exc:
        logger.error("Failed to write task log: %s", exc)


def _update_progress(state: PipelineState, pct: int, msg: str = "") -> None:
    """通过管线状态中的回调函数更新进度。"""
    cb = state.get("on_progress")
    if cb:
        cb(pct, msg)


def _write_stage_failed_log(output_dir: str, stage: str, error: Exception) -> None:
    """将标准化的阶段失败事件写入任务日志。"""
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
    """合并两个警告字符串，用换行符分隔。"""
    if primary and secondary:
        return f"{primary}\n{secondary}"
    return primary or secondary


def _normalize_error_signature(errors_report: Optional[List[Dict[str, Any]]]) -> tuple[tuple[Any, ...], ...]:
    """将错误报告列表规范化为可哈希的签名元组，用于比较验证重试是否有进展。"""
    signature: list[tuple[Any, ...]] = []
    for item in errors_report or []:
        if not isinstance(item, dict):
            continue
        signature.append(
            (
                item.get("part"),
                item.get("num_or_ph"),
                item.get("error_type"),
                item.get("command_error"),
                item.get("ph_error"),
                item.get("bracket_error"),
                item.get("math_error"),
                item.get("env_boundary_error"),
                item.get("protected_cmd_error"),
                item.get("immutable_placeholder_error"),
                item.get("list_structure_error"),
                item.get("escaped_dollar_error"),
                item.get("document_boundary_error"),
                item.get("completeness_error"),
                item.get("global_ph_error"),
            )
        )
    signature.sort()
    return tuple(signature)


async def node_parse(state: PipelineState) -> PipelineState:
    """管线节点：解析 LaTeX 源文件。"""
    transed_project_dir = state["transed_project_dir"]
    base_name = state["base_name"]
    config = state["config"]
    task_id = state.get("task_id", base_name)
    _write_audit_log(transed_project_dir, task_id, "node_enter:parse")
    started = time.monotonic()

    logger.info("Starting LaTeX parsing for %s", base_name)
    _update_progress(state, 5, "Initializing parser")
    try:
        parser_agent = ParserAgent(
            config=config,
            project_dir=state["project_dir"],
            output_dir=transed_project_dir,
            on_progress=lambda _s, p, m: _update_progress(state, 5 + int(p * 0.05), m),
        )
        await parser_agent.execute()
        _write_task_log(transed_project_dir, "parsing_completed")
        _update_progress(state, 10, "Parsing completed")
        _write_audit_log(
            transed_project_dir,
            task_id,
            "node_exit:parse",
            {"status": "ok", "elapsed_ms": (time.monotonic() - started) * 1000},
        )
    except Exception as exc:
        _write_audit_log(
            transed_project_dir,
            task_id,
            "node_exit:parse",
            {
                "status": "error",
                "elapsed_ms": (time.monotonic() - started) * 1000,
                "error": str(exc),
            },
        )
        _write_stage_failed_log(transed_project_dir, "parse", exc)
        raise
    return state


async def node_translate(state: PipelineState) -> PipelineState:
    """管线节点：翻译已解析的内容（含 RAG 术语注入）。"""
    transed_project_dir = state["transed_project_dir"]
    config = state["config"]
    task_id = state.get("task_id", state.get("base_name", ""))
    _write_audit_log(transed_project_dir, task_id, "node_enter:translate")
    started = time.monotonic()

    logger.info("Starting translation")
    _update_progress(state, 10, "Initializing translator")
    try:
        translator_agent = TranslatorAgent(
            config=config,
            project_dir=state["project_dir"],
            output_dir=transed_project_dir,
            trans_mode=state["mode"],
            generate_terminology=config.get("generate_terminology", False),
            on_progress=lambda _s, p, m: _update_progress(state, -1, m)
            if p == -1
            else _update_progress(state, 10 + int(p * 0.6), m),
        )

        # RAG 术语注入：如果启用了 RAG，则加载已批准的术语
        enable_rag = config.get("enable_rag_terminology", False)
        if enable_rag:
            _update_progress(state, 10, "Loading RAG terminology...")
            try:
                from backend.app.services.rag.domain_constants import map_arxiv_categories_to_domain
                from backend.app.services.terminology_service import TerminologyService

                rag_service = TerminologyService()
                if rag_service.is_enabled:
                    rag_domain = config.get("rag_terminology_domain") or None

                    # 如果未明确设置，从 arXiv 分类自动检测领域
                    if not rag_domain:
                        category_map = config.get("category") or {}
                        if category_map:
                            # category_map 格式为 {arxiv_id: ["cs.CL", ...]}
                            all_categories: list[str] = []
                            for cats in category_map.values():
                                if isinstance(cats, list):
                                    all_categories.extend(cats)
                                elif isinstance(cats, str):
                                    all_categories.append(cats)
                            if all_categories:
                                rag_domain = map_arxiv_categories_to_domain(all_categories)
                                if rag_domain:
                                    logger.info(
                                        "Auto-detected RAG terminology domain '%s' from arXiv categories: %s",
                                        rag_domain,
                                        all_categories,
                                    )
                                else:
                                    logger.info(
                                        "Could not map arXiv categories to a known domain: %s",
                                        all_categories,
                                    )

                    if rag_domain:
                        logger.info("Using RAG terminology domain filter: %s", rag_domain)

                    term_dict = rag_service.get_all_approved_terms_dict(
                        user_id=config.get("user_id"), domain=rag_domain,
                    )
                    if term_dict:
                        translator_agent.term_dict = term_dict
                        translator_agent.trans_mode = 2
                        msg = f"RAG terminology loaded: {len(term_dict)} terms"
                        if rag_domain:
                            msg += f" (domain: {rag_domain})"
                        _update_progress(state, 12, msg)
                        logger.info(
                            "RAG terminology injected: %d terms loaded into translator agent%s.",
                            len(term_dict),
                            f" (domain={rag_domain})" if rag_domain else "",
                        )
                    else:
                        _update_progress(state, 12, "RAG: no approved terms found")
                        logger.info(
                            "RAG terminology enabled but no approved terms found%s.",
                            f" for domain '{rag_domain}'" if rag_domain else "",
                        )
                else:
                    _update_progress(state, 12, "RAG: not enabled at server level")
                    logger.info("RAG terminology not enabled at server level; skipping injection.")
            except Exception:
                _update_progress(state, 12, "RAG: terminology loading failed (non-fatal)")
                logger.warning("Failed to inject RAG terminology (non-fatal)", exc_info=True)

        await translator_agent.execute()
        _write_task_log(transed_project_dir, "translation_completed")
        _update_progress(state, 70, "Translation completed")
        _write_audit_log(
            transed_project_dir,
            task_id,
            "node_exit:translate",
            {"status": "ok", "elapsed_ms": (time.monotonic() - started) * 1000},
        )
    except Exception as exc:
        _write_audit_log(
            transed_project_dir,
            task_id,
            "node_exit:translate",
            {
                "status": "error",
                "elapsed_ms": (time.monotonic() - started) * 1000,
                "error": str(exc),
            },
        )
        _write_stage_failed_log(transed_project_dir, "translate", exc)
        raise
    return {**state, "translator_agent": translator_agent}


async def node_validate_and_retry(state: PipelineState) -> PipelineState:
    """管线节点：验证翻译结果并最多重试 MAX_VALIDATE_RETRIES 次。"""
    transed_project_dir = state["transed_project_dir"]
    config = state["config"]
    mode = state["mode"]
    translator_agent = state["translator_agent"]
    task_id = state.get("task_id", state.get("base_name", ""))
    _write_audit_log(transed_project_dir, task_id, "node_enter:validate_and_retry")
    started = time.monotonic()
    _update_progress(state, 70, "Validating translation")
    validation_warning: Optional[str] = None

    try:
        validator_agent = ValidatorAgent(
            config=config,
            project_dir=state["project_dir"],
            output_dir=transed_project_dir,
            on_progress=lambda _s, p, m: _update_progress(state, 70 + int(p * 0.05), m),
        )
        errors_report = await run_blocking(lambda: validator_agent.execute())
        initial_errors_count = len(errors_report) if errors_report else 0

        retry_count = 0
        previous_error_signature = _normalize_error_signature(errors_report)
        no_progress_retry_count = 0

        if mode == 3:
            logger.info("Quick scan mode: skipping error repair to preserve translation boundary")
            if errors_report:
                logger.warning(
                    "Quick scan mode detected %d validation errors, but repair is disabled",
                    len(errors_report),
                )
        else:
            if errors_report:
                translator_agent.trans_mode = 1

            while errors_report and retry_count < MAX_VALIDATE_RETRIES:
                logger.info(
                    "Retrying translation for errors, attempt %d/%d",
                    retry_count + 1,
                    MAX_VALIDATE_RETRIES,
                )
                _update_progress(
                    state,
                    75 + int((retry_count / MAX_VALIDATE_RETRIES) * 10),
                    f"Retrying errors (attempt {retry_count + 1}/{MAX_VALIDATE_RETRIES})",
                )
                translator_agent.errors_report = errors_report
                await translator_agent.execute(
                    error_retry_count=retry_count,
                    Maxtry=MAX_VALIDATE_RETRIES,
                )
                errors_report = await run_blocking(lambda: validator_agent.execute(errors_report))
                current_error_signature = _normalize_error_signature(errors_report)
                retry_count += 1
                if errors_report and current_error_signature == previous_error_signature:
                    no_progress_retry_count += 1
                    if no_progress_retry_count >= MAX_CONSECUTIVE_NO_PROGRESS_REMEDIAL_ATTEMPTS:
                        logger.warning(
                            "Validation retry made no progress for %d consecutive attempts; "
                            "short-circuiting remaining retries after attempt %d/%d",
                            no_progress_retry_count,
                            retry_count,
                            MAX_VALIDATE_RETRIES,
                        )
                        _write_task_log(
                            transed_project_dir,
                            "validation_retry_short_circuited_no_progress",
                            {
                                "attempt": retry_count,
                                "remaining_errors_count": len(errors_report),
                                "no_progress_retry_count": no_progress_retry_count,
                            },
                        )
                        break
                else:
                    no_progress_retry_count = 0
                previous_error_signature = current_error_signature

        final_errors_count = len(errors_report) if errors_report else 0
        filtered_code_like_math_tokens = int(
            getattr(validator_agent, "code_like_filtered_bare_tokens", 0) or 0
        )
        noop_sections = list(getattr(translator_agent, "noop_sections", []) or [])
        payload_invariant_sections = list(
            getattr(translator_agent, "payload_invariant_sections", []) or []
        )

        _write_task_log(
            transed_project_dir,
            "validation_completed",
            {
                "errors_count": final_errors_count,
                "initial_errors_count": initial_errors_count,
                "final_errors_count": final_errors_count,
                "retry_count": retry_count,
                "filtered_code_like_math_tokens": filtered_code_like_math_tokens,
                "noop_sections": noop_sections,
                "payload_invariant_sections": payload_invariant_sections,
            },
        )
        _update_progress(state, 85, "Validation completed")
    except Exception as exc:
        _write_audit_log(
            transed_project_dir,
            task_id,
            "node_exit:validate_and_retry",
            {
                "status": "error",
                "elapsed_ms": (time.monotonic() - started) * 1000,
                "error": str(exc),
            },
        )
        _write_stage_failed_log(transed_project_dir, "validate", exc)
        raise

    _write_audit_log(
        transed_project_dir,
        task_id,
        "node_exit:validate_and_retry",
        {"status": "ok", "elapsed_ms": (time.monotonic() - started) * 1000},
    )
    return {**state, "validation_warning": validation_warning}


async def node_generate(state: PipelineState) -> PipelineState:
    """管线节点：生成 PDF（重建 LaTeX 并编译）。"""
    transed_project_dir = state["transed_project_dir"]
    config = state["config"]
    task_id = state.get("task_id", state.get("base_name", ""))
    _write_audit_log(transed_project_dir, task_id, "node_enter:generate")
    started = time.monotonic()

    logger.info("Generating PDF")
    _update_progress(state, 85, "Generating PDF")

    from backend.app.services.task_manager import task_manager as _tm

    def _on_compile_start(pid: int, engine: str) -> None:
        _tm.set_compile_runtime(task_id, pid=pid, engine=engine, started_at=get_cst_now_iso())

    def _on_compile_end() -> None:
        _tm.set_compile_runtime(task_id, pid=None, engine=None, started_at=None)

    config_with_runtime = dict(config)
    config_with_runtime["_on_compile_start"] = _on_compile_start
    config_with_runtime["_on_compile_end"] = _on_compile_end

    generator_agent = GeneratorAgent(
        config=config_with_runtime,
        project_dir=state["project_dir"],
        output_dir=transed_project_dir,
        on_progress=lambda _s, p, m: _update_progress(state, 85 + int(p * 0.15), m),
    )
    try:
        if hasattr(generator_agent, "execute_async"):
            generation_result = await generator_agent.execute_async()
        else:
            generation_result = await run_blocking(lambda: generator_agent.execute())
        _write_audit_log(
            transed_project_dir,
            task_id,
            "node_exit:generate",
            {
                "status": "ok",
                "elapsed_ms": (time.monotonic() - started) * 1000,
                "compile_queue_wait_ms": (generation_result or {}).get("compile_queue_wait_ms"),
                "compile_exec_ms": (generation_result or {}).get("compile_exec_ms"),
            },
        )
    except Exception as exc:
        _write_audit_log(
            transed_project_dir,
            task_id,
            "node_exit:generate",
            {
                "status": "error",
                "elapsed_ms": (time.monotonic() - started) * 1000,
                "error": str(exc),
            },
        )
        _write_stage_failed_log(transed_project_dir, "generate", exc)
        raise
    finally:
        _on_compile_end()

    return {**state, "generation_result": generation_result}


async def node_finalize(state: PipelineState) -> PipelineState:
    """管线节点：收尾 —— 移动 PDF、记录日志、执行 RAG 后处理。"""
    transed_project_dir = state["transed_project_dir"]
    base_name = state["base_name"]
    generation_result = state["generation_result"] or {}
    config = state["config"]
    target_language = config.get("target_language", "zh")
    validation_warning = state.get("validation_warning")
    task_id = state.get("task_id", base_name)
    _write_audit_log(transed_project_dir, task_id, "node_enter:finalize")
    started = time.monotonic()

    pdf_file_path = generation_result.get("pdf_path")
    if pdf_file_path:
        if not Path(pdf_file_path).exists():
            error_summary = (
                generation_result.get("error_summary")
                or f"Compilation returned a missing PDF path: {pdf_file_path}"
            )
            logger.error("Failed to finalize PDF for %s: %s", base_name, error_summary)
            _write_task_log(
                transed_project_dir,
                "compilation_failed",
                {
                    "error_summary": error_summary,
                    "pdf_path": pdf_file_path,
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
            _write_audit_log(
                transed_project_dir,
                task_id,
                "node_exit:finalize",
                {"status": "ok", "elapsed_ms": (time.monotonic() - started) * 1000},
            )
            return {**state, "final_result": final_result}

        new_pdf_path = os.path.join(transed_project_dir, f"{target_language}_{base_name}.pdf")
        try:
            shutil.move(pdf_file_path, new_pdf_path)
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
                    "pdf_path": pdf_file_path,
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
            _write_audit_log(
                transed_project_dir,
                task_id,
                "node_exit:finalize",
                {"status": "ok", "elapsed_ms": (time.monotonic() - started) * 1000},
            )
            return {**state, "final_result": final_result}

        compile_status = generation_result.get("status", "completed")
        compile_warnings = _merge_warnings(validation_warning, generation_result.get("warnings"))
        if compile_status == "completed" and compile_warnings:
            compile_status = "completed_with_warnings"

        if compile_status == "completed_with_warnings":
            _write_task_log(
                transed_project_dir,
                "compilation_completed_with_warnings",
                {"pdf_path": new_pdf_path, "warnings": compile_warnings},
            )
            _update_progress(state, 100, "Translation completed with compilation warnings")
        else:
            _write_task_log(transed_project_dir, "compilation_completed", {"pdf_path": new_pdf_path})
            _update_progress(state, 100, "Translation completed successfully")

        final_result = {
            "status": compile_status,
            "pdf_path": new_pdf_path,
            "error_summary": None,
            "warnings": compile_warnings,
        }
        _write_audit_log(
            transed_project_dir,
            task_id,
            "node_exit:finalize",
            {"status": "ok", "elapsed_ms": (time.monotonic() - started) * 1000},
        )
        _run_post_translation_rag(state, config, task_id)
        return {**state, "final_result": final_result}

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
    _write_audit_log(
        transed_project_dir,
        task_id,
        "node_exit:finalize",
        {"status": "ok", "elapsed_ms": (time.monotonic() - started) * 1000},
    )
    _run_post_translation_rag(state, config, task_id)
    return {**state, "final_result": final_result}


def _run_post_translation_rag(state: PipelineState, config: dict, task_id: str) -> None:
    """如果启用了 RAG 术语，则运行翻译后 RAG 术语提取。"""
    enable_rag = config.get("enable_rag_terminology", False)
    if not enable_rag:
        return
    try:
        from backend.app.services.rag.translation_hook import run_post_translation_extraction
        translator_agent = state.get("translator_agent")
        if translator_agent is None:
            return
        # 从翻译器 Agent 的 sections 中收集源文和目标文块
        sections = getattr(translator_agent, "translated_sections", None) or getattr(translator_agent, "sections", [])
        source_chunks: list[str] = []
        target_chunks: list[str] = []
        for sec in sections:
            src = sec.get("content", "") or sec.get("source", "")
            tgt = sec.get("trans_content", "") or sec.get("translation", "")
            if src and tgt:
                source_chunks.append(src)
                target_chunks.append(tgt)
        if source_chunks and target_chunks:
            run_post_translation_extraction(
                task_id=task_id,
                source_chunks=source_chunks,
                target_chunks=target_chunks,
                user_id=config.get("user_id"),
            )
    except Exception:
        logger.warning("Post-translation RAG extraction failed (non-fatal)", exc_info=True)


def build_pipeline_graph(
    enable_diagnostics: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> Any:
    """构建生产 parity 管线图。

    `enable_diagnostics` 的参数仅为兼容调用方而保留，实际被忽略。
    """
    graph = StateGraph(PipelineState)
    graph.add_node("parse", node_parse)
    graph.add_node("translate", node_translate)
    graph.add_node("validate_and_retry", node_validate_and_retry)
    graph.add_node("generate", node_generate)
    graph.add_node("finalize", node_finalize)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "translate")
    graph.add_edge("translate", "validate_and_retry")
    graph.add_edge("validate_and_retry", "generate")
    graph.add_edge("generate", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


async def run_pipeline(
    config: Dict[str, Any],
    project_dir: str,
    output_dir: str,
    on_progress: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """运行完整的 LaTeX 翻译管线。

    Args:
        config: 系统配置字典
        project_dir: LaTeX 项目目录路径
        output_dir: 输出目录路径
        on_progress: 可选进度回调函数 (percentage, message)

    Returns:
        包含 status/pdf_path/error_summary/warnings 的结果字典。
    """
    config = normalize_origin_cli_parity_agent_config(config or {})
    base_name = os.path.basename(project_dir)
    target_language = config.get("target_language", "zh")
    transed_project_dir = os.path.join(output_dir, f"{target_language}_{base_name}")
    task_id: str = config.get("task_id") or base_name

    os.makedirs(transed_project_dir, exist_ok=True)
    log_config = {k: v for k, v in config.items() if k != "llm_config"}
    llm_config = dict(config.get("llm_config") or {})
    if llm_config:
        api_key = str(llm_config.get("api_key") or "")
        if api_key:
            llm_config["api_key_masked"] = "*" * min(max(len(api_key), 8), 24)
            llm_config.pop("api_key", None)
        log_config["llm_config"] = llm_config
    _write_task_log(
        transed_project_dir,
        "task_started",
        {
            "project": base_name,
            "config": log_config,
        },
    )
    _write_audit_log(transed_project_dir, task_id, "pipeline_start", {"project": base_name, "mode": config.get("mode", 0)})
    if config.get("translation_core_mode") == ORIGIN_CLI_PARITY_MODE:
        _write_audit_log(
            transed_project_dir,
            task_id,
            "origin_cli_parity_kernel_selected",
            {"single_kernel_lineage": True},
        )

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
        "final_result": {
            "status": "failed",
            "pdf_path": None,
            "error_summary": "Workflow did not run",
            "warnings": None,
        },
    }

    graph = build_pipeline_graph(config=config)
    pipeline_timeout_sec = _resolve_pipeline_timeout_seconds(config)
    try:
        if pipeline_timeout_sec > 0:
            final_state = await asyncio.wait_for(
                graph.ainvoke(initial_state),
                timeout=pipeline_timeout_sec,
            )
        else:
            final_state = await graph.ainvoke(initial_state)
    except asyncio.TimeoutError:
        _write_audit_log(
            transed_project_dir,
            task_id,
            "pipeline_timeout",
            {"timeout_sec": pipeline_timeout_sec},
        )
        raise

    _write_audit_log(
        transed_project_dir,
        task_id,
        "pipeline_end",
        {"status": final_state.get("final_result", {}).get("status")},
    )
    return final_state["final_result"]
