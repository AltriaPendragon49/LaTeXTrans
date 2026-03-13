"""
Generator Agent

Adapted from prototype system with:
- All Streamlit dependencies removed
- Integrated new compile_with_fallback() function
- Progress callback mechanism added
- Python logging integrated
"""

from typing import Dict, Any, Optional, Callable
from .base_tool_agent import BaseToolAgent
from backend.app.services.latex.reconstruct import LatexConstructor
import asyncio
import time
from backend.app.services.latex.compiler import (
    compile_with_intelligent_fallback,
    compile_with_intelligent_fallback_async,
    find_main_tex_file,
)
from backend.app.services.agents.compile_runtime import get_compile_semaphore
from backend.app.services.latex.structure_guard import validate_project_structure
from backend.app.services.latex.utils import apply_formatting_config
from pathlib import Path
import os
import shutil
import logging
import json
from hashlib import sha256

logger = logging.getLogger(__name__)


class GeneratorAgent(BaseToolAgent):
    def __init__(self, 
                 config: Dict[str, Any],
                 project_dir: str = None,
                 output_dir: str = None,
                 on_progress: Optional[Callable[[str, int, str], None]] = None
                 ):
        super().__init__(agent_name="GeneratorAgent", config=config, on_progress=on_progress)
        self.config = config
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.latex_engine = config.get("latex_engine", "auto")

    def _write_structure_replay_bundle(
        self,
        *,
        main_tex: str,
        reason_code: str,
        guard_phase: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
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

        try:
            main_text = Path(main_tex).read_text(encoding="utf-8", errors="replace")
            main_digest = sha256(main_text.encode("utf-8")).hexdigest()
        except Exception:
            main_digest = ""

        payload.update(
            {
                "replay_version": payload.get("replay_version", "v1"),
                "tex_write_decision": "written",
                "guard_phase": guard_phase,
                "failure_reason_code": reason_code,
                "structure_guard_message": message,
                "main_tex_path": main_tex,
                "main_tex_digest": main_digest,
            }
        )
        if details:
            payload["structure_guard_details"] = details
        replay_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(replay_path)

    def _notify_compile_start(self, pid: int, engine: str) -> None:
        cb = self.config.get("_on_compile_start")
        if callable(cb):
            try:
                cb(pid, engine)
            except Exception:
                logger.debug("compile start callback failed", exc_info=True)

    def _notify_compile_end(self) -> None:
        cb = self.config.get("_on_compile_end")
        if callable(cb):
            try:
                cb()
            except Exception:
                logger.debug("compile end callback failed", exc_info=True)

    def execute(self) -> Dict[str, Any]:
        """
        Execute generation task: reconstruct LaTeX and compile to PDF
        
        Returns:
            Structured generation result:
            - status: "completed" | "completed_with_warnings" | "failed_compilation"
            - pdf_path: Path to generated PDF when available
            - error_summary: Compilation error summary when failed
            - warnings: Warning summary when compilation completed with warnings
        """
        self.log(f"Starting generation for project: {os.path.basename(self.project_dir)}")
        self.update_progress(5, "Starting generation")

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
            target_language=target_language
        )
        latex_constructor.construct(on_progress=self.on_progress)

        self.update_progress(80, "Applying formatting config")
        
        # Apply typography formatting config to main .tex file (if specified)
        formatting_config = self.config.get("formatting")
        if formatting_config:
            transed_main_tex = find_main_tex_file(transed_latex_dir)
            if transed_main_tex:
                try:
                    with open(transed_main_tex, 'r', encoding='utf-8', errors='replace') as f:
                        tex_content = f.read()
                    tex_content, fmt_warnings = apply_formatting_config(tex_content, formatting_config)
                    with open(transed_main_tex, 'w', encoding='utf-8') as f:
                        f.write(tex_content)
                    logger.info(f"Applied formatting config to {transed_main_tex}")
                    # Surface any auto-downgrade warnings via progress callback
                    for warn in fmt_warnings:
                        logger.warning(f"[FormattingConfig] {warn}")
                        self.update_progress(80, f"⚠ 排版提示：{warn}")
                    # Store warnings for caller to forward to task_manager
                    if fmt_warnings and not hasattr(self, '_fmt_warnings'):
                        self._fmt_warnings = []
                    if fmt_warnings:
                        self._fmt_warnings.extend(fmt_warnings)
                except Exception as e:
                    logger.warning(f"Failed to apply formatting config: {e}")
            else:
                logger.warning("No main .tex file found; formatting config not applied")

        self.update_progress(80, "Compiling PDF document")
        
        # Use intelligent main tex file detection
        main_tex = find_main_tex_file(transed_latex_dir)
        
        if not main_tex:
            error_summary = f"No main .tex file found in {transed_latex_dir}"
            logger.error(error_summary)
            self.update_progress(100, "No main .tex file found")
            return {
                "status": "failed_compilation",
                "pdf_path": None,
                "error_summary": error_summary,
                "warnings": None,
                "engine": None,
                "error_count": 0,
            }

        # Precompile hard gate: reject structurally unsafe bundles before compile.
        structure_result = validate_project_structure(str(main_tex))
        if not structure_result.get("ok", False):
            reason_code = str(structure_result.get("reason_code") or "structure_env_stack_mismatch")
            message = str(structure_result.get("message") or "Structure guard rejected LaTeX bundle")
            details = structure_result.get("details") or {}
            replay_bundle_ref = self._write_structure_replay_bundle(
                main_tex=str(main_tex),
                reason_code=reason_code,
                guard_phase="precompile",
                message=message,
                details=details if isinstance(details, dict) else None,
            )
            logger.error("Structure guard rejected compile bundle: %s (%s)", message, reason_code)
            self.update_progress(100, "Structure guard rejected compile bundle")
            return {
                "status": "structure_invalid",
                "pdf_path": None,
                "error_summary": message,
                "warnings": None,
                "engine": None,
                "error_count": 0,
                "failure_reason_code": reason_code,
                "failure_class": "structural",
                "guard_phase": "precompile",
                "replay_bundle_ref": replay_bundle_ref,
            }
        
        logger.info(f"Compiling {Path(main_tex).name}...")
        
        # Build engine order based on user configuration
        preferred_order = None
        if self.latex_engine and self.latex_engine != "auto":
            # User selected specific engine - prioritize it
            all_engines = ["pdflatex", "xelatex", "lualatex"]
            if self.latex_engine in all_engines:
                all_engines.remove(self.latex_engine)
                preferred_order = [self.latex_engine] + all_engines
                logger.info(f"Using user-specified engine order: {preferred_order}")
        
        # Use new intelligent compiler with fallback
        result = compile_with_intelligent_fallback(
            tex_file=str(main_tex),
            output_dir=transed_latex_dir,
            preferred_order=preferred_order,
            target_language=target_language,
        )

        pdf_file = result.get("pdf_path")
        if pdf_file and not Path(pdf_file).exists():
            logger.error(f"Compiler returned a missing PDF path: {pdf_file}")
            result["errors"] = result.get("errors") or f"Compilation returned a missing PDF path: {pdf_file}"
            pdf_file = None
        
        if pdf_file:
            self.update_progress(100, "PDF generation complete")
            self.log(f"Successfully generated PDF: {pdf_file}")
            return {
                "status": result.get("status", "completed"),
                "pdf_path": pdf_file,
                "error_summary": None,
                "warnings": result.get("warnings"),
                "engine": result.get("engine"),
                "error_count": result.get("error_count", 0),
            }

        self.update_progress(100, "PDF compilation failed")
        self.log("Failed to compile PDF document", level="error")

        error_summary = result.get("errors") or "Compilation failed without detailed error output"
        if result.get("errors"):
            self.log(f"Errors: {result['errors']}", level="error")

        return {
            "status": "failed_compilation",
            "pdf_path": None,
            "error_summary": error_summary,
            "warnings": result.get("warnings"),
            "engine": result.get("engine"),
            "error_count": result.get("error_count", 0),
        }

    async def execute_async(self) -> Dict[str, Any]:
        """
        Async generation path: same semantics as execute(), but async compilation.
        """
        self.log(f"Starting generation for project: {os.path.basename(self.project_dir)}")
        self.update_progress(5, "Starting generation")

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
            target_language=target_language
        )
        await asyncio.to_thread(latex_constructor.construct, self.on_progress)

        self.update_progress(80, "Applying formatting config")
        formatting_config = self.config.get("formatting")
        if formatting_config:
            transed_main_tex = find_main_tex_file(transed_latex_dir)
            if transed_main_tex:
                try:
                    with open(transed_main_tex, 'r', encoding='utf-8', errors='replace') as f:
                        tex_content = f.read()
                    tex_content, fmt_warnings = apply_formatting_config(tex_content, formatting_config)
                    with open(transed_main_tex, 'w', encoding='utf-8') as f:
                        f.write(tex_content)
                    if fmt_warnings and not hasattr(self, '_fmt_warnings'):
                        self._fmt_warnings = []
                    if fmt_warnings:
                        self._fmt_warnings.extend(fmt_warnings)
                except Exception as e:
                    logger.warning(f"Failed to apply formatting config: {e}")

        self.update_progress(80, "Waiting for compile slot")
        main_tex = find_main_tex_file(transed_latex_dir)
        if not main_tex:
            error_summary = f"No main .tex file found in {transed_latex_dir}"
            self.update_progress(100, "No main .tex file found")
            return {
                "status": "failed_compilation",
                "pdf_path": None,
                "error_summary": error_summary,
                "warnings": None,
                "engine": None,
                "error_count": 0,
            }

        structure_result = validate_project_structure(str(main_tex))
        if not structure_result.get("ok", False):
            reason_code = str(structure_result.get("reason_code") or "structure_env_stack_mismatch")
            message = str(structure_result.get("message") or "Structure guard rejected LaTeX bundle")
            details = structure_result.get("details") or {}
            replay_bundle_ref = self._write_structure_replay_bundle(
                main_tex=str(main_tex),
                reason_code=reason_code,
                guard_phase="precompile",
                message=message,
                details=details if isinstance(details, dict) else None,
            )
            return {
                "status": "structure_invalid",
                "pdf_path": None,
                "error_summary": message,
                "warnings": None,
                "engine": None,
                "error_count": 0,
                "failure_reason_code": reason_code,
                "failure_class": "structural",
                "guard_phase": "precompile",
                "replay_bundle_ref": replay_bundle_ref,
            }

        preferred_order = None
        if self.latex_engine and self.latex_engine != "auto":
            all_engines = ["pdflatex", "xelatex", "lualatex"]
            if self.latex_engine in all_engines:
                all_engines.remove(self.latex_engine)
                preferred_order = [self.latex_engine] + all_engines

        wait_started_at = time.monotonic()
        compile_sem = get_compile_semaphore()
        async with compile_sem:
            compile_queue_wait_ms = int((time.monotonic() - wait_started_at) * 1000)
            self.update_progress(80, "Compiling PDF document")
            compile_started_at = time.monotonic()
            result = await compile_with_intelligent_fallback_async(
                tex_file=str(main_tex),
                output_dir=transed_latex_dir,
                preferred_order=preferred_order,
                target_language=target_language,
                on_process_start=self._notify_compile_start,
                on_process_end=self._notify_compile_end,
            )
            compile_exec_ms = int((time.monotonic() - compile_started_at) * 1000)
        logger.info(
            "Compile timing for %s: queue_wait=%dms exec=%dms",
            Path(main_tex).name,
            compile_queue_wait_ms,
            compile_exec_ms,
        )
        pdf_file = result.get("pdf_path")
        if pdf_file and not Path(pdf_file).exists():
            result["errors"] = result.get("errors") or f"Compilation returned a missing PDF path: {pdf_file}"
            pdf_file = None

        if pdf_file:
            self.update_progress(100, "PDF generation complete")
            return {
                "status": result.get("status", "completed"),
                "pdf_path": pdf_file,
                "error_summary": None,
                "warnings": result.get("warnings"),
                "engine": result.get("engine"),
                "error_count": result.get("error_count", 0),
                "compile_queue_wait_ms": compile_queue_wait_ms,
                "compile_exec_ms": compile_exec_ms,
            }

        self.update_progress(100, "PDF compilation failed")
        error_summary = result.get("errors") or "Compilation failed without detailed error output"
        return {
            "status": "failed_compilation",
            "pdf_path": None,
            "error_summary": error_summary,
            "warnings": result.get("warnings"),
            "engine": result.get("engine"),
            "error_count": result.get("error_count", 0),
            "compile_queue_wait_ms": compile_queue_wait_ms,
            "compile_exec_ms": compile_exec_ms,
        }
        
    def _create_transed_latex_folder(self, src_dir: str) -> str:
        """
        Create a translated folder by copying the source directory.
        
        Args:
            src_dir: Source LaTeX project directory
            
        Returns:
            Path to created translation directory
        """
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
