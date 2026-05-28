"""生成器 Agent —— 负责 LaTeX 文档重建和 PDF 编译。"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from backend.app.services.agents.compile_runtime import get_compile_semaphore
from backend.app.services.latex.compiler import (
    compile_with_origin_cli_parity,
    find_main_tex_file,
)
from backend.app.services.latex.reconstruct import LatexConstructor

from .base_tool_agent import BaseToolAgent

logger = logging.getLogger(__name__)


class GeneratorAgent(BaseToolAgent):
    """生成器 Agent：重建 LaTeX 文档结构并使用 origin CLI parity 编译 PDF。"""

    def __init__(
        self,
        config: Dict[str, Any],
        project_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        on_progress: Optional[Callable[[str, int, str], None]] = None,
    ):
        """初始化 GeneratorAgent。"""
        super().__init__(agent_name="GeneratorAgent", config=config, on_progress=on_progress)
        self.config = config
        self.project_dir = project_dir
        self.output_dir = output_dir

    def _update_replay_bundle(self, **fields: Any) -> Optional[str]:
        """更新或创建 replay_bundle.json 文件，用于调试和复现。"""
        if not self.output_dir:
            return None
        replay_path = Path(self.output_dir) / "replay_bundle.json"
        payload: Dict[str, Any] = {}
        if replay_path.exists():
            try:
                loaded = json.loads(replay_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    payload = loaded
            except Exception:
                payload = {}
        payload.setdefault("replay_version", "v1")
        payload.update({key: value for key, value in fields.items() if value is not None})
        replay_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(replay_path)

    def _read_maps(self) -> tuple[list, list, list, list, list]:
        """读取所有 JSON 映射文件（sections、captions、envs、newcommands、inputs）。"""
        self.update_progress(10, "Reading JSON maps")
        sections = self.read_file(Path(self.output_dir, "sections_map.json"), "json")
        self.update_progress(20, "Loading sections")
        captions = self.read_file(Path(self.output_dir, "captions_map.json"), "json")
        self.update_progress(30, "Loading captions")
        envs = self.read_file(Path(self.output_dir, "envs_map.json"), "json")
        self.update_progress(40, "Loading environments")
        newcommands = self.read_file(Path(self.output_dir, "newcommands_map.json"), "json")
        self.update_progress(50, "Loading newcommands")
        inputs = self.read_file(Path(self.output_dir, "inputs_map.json"), "json")
        self.update_progress(60, "Loading inputs")
        return sections, captions, envs, newcommands, inputs

    def _construct_latex(self) -> str:
        """同步重建 LaTeX 文档结构。"""
        sections, captions, envs, newcommands, inputs = self._read_maps()
        self.update_progress(65, "Creating translation project directory")
        transed_latex_dir = self._create_transed_latex_folder(self.project_dir)
        self.log(f"Created translation directory: {transed_latex_dir}")

        self.update_progress(70, "Reconstructing LaTeX document")
        target_language = self.config.get("target_language", "en")
        latex_constructor = LatexConstructor(
            sections=sections,
            captions=captions,
            envs=envs,
            inputs=inputs,
            newcommands=newcommands,
            output_latex_dir=transed_latex_dir,
            target_language=target_language,
            origin_cli_parity=True,
        )
        latex_constructor.construct(on_progress=self.on_progress)
        return transed_latex_dir

    async def _construct_latex_async(self) -> str:
        """异步重建 LaTeX 文档结构（在线程池中运行同步重建逻辑）。"""
        sections, captions, envs, newcommands, inputs = self._read_maps()
        self.update_progress(65, "Creating translation project directory")
        transed_latex_dir = self._create_transed_latex_folder(self.project_dir)

        self.update_progress(70, "Reconstructing LaTeX document")
        target_language = self.config.get("target_language", "en")
        latex_constructor = LatexConstructor(
            sections=sections,
            captions=captions,
            envs=envs,
            inputs=inputs,
            newcommands=newcommands,
            output_latex_dir=transed_latex_dir,
            target_language=target_language,
            origin_cli_parity=True,
        )
        await asyncio.to_thread(latex_constructor.construct, self.on_progress)
        return transed_latex_dir

    @staticmethod
    def _main_tex_failure(transed_latex_dir: str) -> Dict[str, Any]:
        """当找不到主 .tex 文件时，返回失败结果。"""
        return {
            "status": "failed_compilation",
            "pdf_path": None,
            "error_summary": f"No reliable main .tex file found in {transed_latex_dir}",
            "warnings": None,
            "engine": None,
            "error_count": 0,
        }

    @staticmethod
    def _success_result(
        result: Dict[str, Any],
        pdf_file: str,
        *,
        compile_queue_wait_ms: Optional[int] = None,
        compile_exec_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """构建编译成功的标准结果字典。"""
        payload = {
            "status": result.get("status", "completed"),
            "pdf_path": pdf_file,
            "error_summary": None,
            "warnings": result.get("warnings"),
            "engine": result.get("engine"),
            "error_count": result.get("error_count", 0),
            "guard_warning_only": False,
            "guard_reason_code": None,
            "guard_scope": None,
            "guard_details": None,
            "replay_bundle_ref": result.get("replay_bundle_ref"),
        }
        if compile_queue_wait_ms is not None:
            payload["compile_queue_wait_ms"] = compile_queue_wait_ms
        if compile_exec_ms is not None:
            payload["compile_exec_ms"] = compile_exec_ms
        return payload

    @staticmethod
    def _failure_result(
        result: Dict[str, Any],
        *,
        compile_queue_wait_ms: Optional[int] = None,
        compile_exec_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """构建编译失败的标准结果字典。"""
        payload = {
            "status": "failed_compilation",
            "pdf_path": None,
            "error_summary": result.get("errors") or "Compilation failed without detailed error output",
            "warnings": result.get("warnings"),
            "engine": result.get("engine"),
            "error_count": result.get("error_count", 0),
            "guard_warning_only": False,
            "guard_reason_code": None,
            "guard_scope": None,
            "guard_details": None,
            "replay_bundle_ref": result.get("replay_bundle_ref"),
        }
        if compile_queue_wait_ms is not None:
            payload["compile_queue_wait_ms"] = compile_queue_wait_ms
        if compile_exec_ms is not None:
            payload["compile_exec_ms"] = compile_exec_ms
        return payload

    def execute(self) -> Dict[str, Any]:
        """同步重建 LaTeX 并使用 origin CLI parity 编译 PDF。"""
        self.log(f"Starting generation for project: {os.path.basename(self.project_dir)}")
        self.update_progress(5, "Starting generation")

        transed_latex_dir = self._construct_latex()
        main_tex_path = find_main_tex_file(transed_latex_dir)
        if not main_tex_path:
            error_summary = f"No reliable main .tex file found in {transed_latex_dir}"
            logger.error(error_summary)
            self.update_progress(100, "No main .tex file found")
            return self._main_tex_failure(transed_latex_dir)

        main_tex = Path(main_tex_path)
        target_language = self.config.get("target_language", "en")
        self.update_progress(80, "Compiling PDF document")
        logger.info("Compiling %s with origin CLI parity", main_tex.name)
        self._update_replay_bundle(
            compile_attempted=True,
            compile_verdict_source="origin_cli_parity_compiler",
            guard_blocking=False,
            guard_warning_only=False,
        )
        result = compile_with_origin_cli_parity(
            str(main_tex),
            transed_latex_dir,
            target_language=target_language,
        )

        pdf_file = result.get("pdf_path")
        if pdf_file and not Path(pdf_file).exists():
            logger.error("Compiler returned a missing PDF path: %s", pdf_file)
            result["errors"] = result.get("errors") or f"Compilation returned a missing PDF path: {pdf_file}"
            pdf_file = None

        if pdf_file:
            self.update_progress(100, "PDF generation complete")
            self.log(f"Successfully generated PDF: {pdf_file}")
            return self._success_result(result, pdf_file)

        self.update_progress(100, "PDF compilation failed")
        self.log("Failed to compile PDF document", level="error")
        return self._failure_result(result)

    async def execute_async(self) -> Dict[str, Any]:
        """异步构建 LaTeX 并使用 origin CLI parity 编译 PDF（含编译信号量控制）。"""
        self.log(f"Starting generation for project: {os.path.basename(self.project_dir)}")
        self.update_progress(5, "Starting generation")

        transed_latex_dir = await self._construct_latex_async()
        main_tex_path = find_main_tex_file(transed_latex_dir)
        if not main_tex_path:
            error_summary = f"No reliable main .tex file found in {transed_latex_dir}"
            logger.error(error_summary)
            self.update_progress(100, "No main .tex file found")
            return self._main_tex_failure(transed_latex_dir)

        main_tex = Path(main_tex_path)
        target_language = self.config.get("target_language", "en")
        wait_started_at = time.monotonic()
        compile_sem = get_compile_semaphore()
        if compile_sem.locked():
            self.update_progress(80, "Waiting for compile slot")
        await compile_sem.acquire()
        try:
            compile_queue_wait_ms = int((time.monotonic() - wait_started_at) * 1000)
            self.update_progress(80, "Compiling PDF document")
            compile_started_at = time.monotonic()
            self._update_replay_bundle(
                compile_attempted=True,
                compile_verdict_source="origin_cli_parity_compiler",
                guard_blocking=False,
                guard_warning_only=False,
            )
            result = await asyncio.to_thread(
                compile_with_origin_cli_parity,
                str(main_tex),
                transed_latex_dir,
                target_language,
            )
            compile_exec_ms = int((time.monotonic() - compile_started_at) * 1000)
        finally:
            compile_sem.release()

        logger.info(
            "Origin CLI parity compile timing for %s: queue_wait=%dms exec=%dms",
            main_tex.name,
            compile_queue_wait_ms,
            compile_exec_ms,
        )
        pdf_file = result.get("pdf_path")
        if pdf_file and not Path(pdf_file).exists():
            result["errors"] = result.get("errors") or f"Compilation returned a missing PDF path: {pdf_file}"
            pdf_file = None

        if pdf_file:
            self.update_progress(100, "PDF generation complete")
            return self._success_result(
                result,
                pdf_file,
                compile_queue_wait_ms=compile_queue_wait_ms,
                compile_exec_ms=compile_exec_ms,
            )

        self.update_progress(100, "PDF compilation failed")
        return self._failure_result(
            result,
            compile_queue_wait_ms=compile_queue_wait_ms,
            compile_exec_ms=compile_exec_ms,
        )

    def _create_transed_latex_folder(self, src_dir: str) -> str:
        """复制源 LaTeX 项目目录到输出目录，用于后续编译。"""
        if not os.path.isdir(src_dir):
            raise NotADirectoryError(f"The path {src_dir} is not a valid directory.")

        base_name = os.path.basename(src_dir)
        dest_dir = os.path.join(self.output_dir, base_name)

        if os.path.exists(dest_dir):
            self.log(f"Removing existing directory: {dest_dir}", level="debug")
            shutil.rmtree(dest_dir)

        shutil.copytree(src_dir, dest_dir)
        self.log(f"Copied {src_dir} to {dest_dir}", level="debug")
        return dest_dir
