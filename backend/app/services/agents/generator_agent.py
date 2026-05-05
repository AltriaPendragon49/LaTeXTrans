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
    compile_with_origin_cli_parity,
    compile_with_intelligent_fallback,
    compile_with_intelligent_fallback_async,
    find_main_tex_file,
)
from backend.app.services.agents.compile_runtime import get_compile_semaphore
from backend.app.services.latex.structure_guard import (
    REASON_WALKER_EOF_MACRO_ARGS,
    REASON_WALKER_UNEXPECTED_CLOSING,
    validate_project_structure,
)
from backend.app.core.config import get_settings
from backend.app.models.config_models import is_origin_cli_parity_config
from backend.app.services.latex.utils import apply_formatting_config
from pathlib import Path
import os
import re
import shutil
import logging
import json
from hashlib import sha256

logger = logging.getLogger(__name__)

_SOURCE_BASELINE_GUARD_REASON_CODES = {
    REASON_WALKER_UNEXPECTED_CLOSING,
    REASON_WALKER_EOF_MACRO_ARGS,
}
_STRUCTURE_GUARD_OFFSET_RE = re.compile(r"@\(\d+,\d+\)")


class GeneratorAgent(BaseToolAgent):
    @staticmethod
    def _coerce_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return default

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
        self._structure_guard_warning: Optional[Dict[str, Any]] = None

    def _is_precompile_structure_guard_enabled(self) -> bool:
        explicit_value = self.config.get("enable_precompile_structure_guard")
        if explicit_value is not None:
            return self._coerce_bool(explicit_value, default=True)
        return self._coerce_bool(get_settings().enable_precompile_structure_guard, default=True)

    def _is_origin_cli_parity_enabled(self) -> bool:
        return is_origin_cli_parity_config(self.config)

    def _update_replay_bundle(self, **fields: Any) -> Optional[str]:
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
        payload.update({k: v for k, v in fields.items() if v is not None})
        replay_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(replay_path)

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
                "guard_reason_code": reason_code,
                "structure_guard_message": message,
                "main_tex_path": main_tex,
                "main_tex_digest": main_digest,
                "guard_blocking": True,
                "guard_warning_only": False,
                "compile_attempted": False,
                "compile_verdict_source": "guard",
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

    def _resolve_and_validate_compile_bundle(
        self, transed_latex_dir: str
    ) -> tuple[Optional[Path], Optional[Dict[str, Any]]]:
        main_tex = find_main_tex_file(transed_latex_dir)
        if not main_tex:
            error_summary = f"No reliable main .tex file found in {transed_latex_dir}"
            logger.error(error_summary)
            self.update_progress(100, "No main .tex file found")
            return None, {
                "status": "failed_compilation",
                "pdf_path": None,
                "error_summary": error_summary,
                "warnings": None,
                "engine": None,
                "error_count": 0,
            }

        self.update_progress(80, "Checking project structure...")
        structure_result = validate_project_structure(str(main_tex))
        structure_result = self._downgrade_source_equivalent_guard_failure(
            main_tex=main_tex,
            structure_result=structure_result,
        )
        structure_result = self._downgrade_disabled_precompile_guard_failure(
            structure_result=structure_result,
        )
        self._structure_guard_warning = None
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
            return None, {
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
                "guard_blocking": True,
                "guard_warning_only": False,
                "compile_attempted": False,
                "compile_verdict_source": "guard",
            }

        if structure_result.get("warning_only"):
            reason_code = str(structure_result.get("reason_code") or "structure_guard_warning")
            message = str(structure_result.get("message") or "Structure guard emitted warning")
            details = structure_result.get("details") or {}
            guard_scope = structure_result.get("guard_scope") or "project"
            replay_bundle_ref = self._update_replay_bundle(
                tex_write_decision="written",
                guard_phase="precompile",
                guard_reason_code=reason_code,
                structure_guard_message=message,
                structure_guard_details=details if isinstance(details, dict) else {},
                guard_blocking=False,
                guard_warning_only=True,
                guard_scope=guard_scope,
                main_tex_path=str(main_tex),
                main_tex_digest=sha256(Path(main_tex).read_text(encoding="utf-8", errors="replace").encode("utf-8")).hexdigest(),
                compile_attempted=False,
            )
            self._structure_guard_warning = {
                "reason_code": reason_code,
                "message": message,
                "details": details,
                "guard_scope": guard_scope,
                "replay_bundle_ref": replay_bundle_ref,
            }
            logger.warning("Structure guard emitted warning only: %s (%s)", message, reason_code)

        return Path(main_tex), None

    @staticmethod
    def _normalize_structure_guard_message(message: str) -> str:
        normalized = _STRUCTURE_GUARD_OFFSET_RE.sub("@(?,?)", message or "")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _downgrade_source_equivalent_guard_failure(
        self,
        *,
        main_tex: Path,
        structure_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        if structure_result.get("ok", False):
            return structure_result

        reason_code = str(structure_result.get("reason_code") or "")
        if reason_code not in _SOURCE_BASELINE_GUARD_REASON_CODES:
            return structure_result

        if not self.project_dir:
            return structure_result

        source_main_tex = find_main_tex_file(self.project_dir)
        if not source_main_tex:
            return structure_result

        if str(Path(source_main_tex).resolve()) == str(Path(main_tex).resolve()):
            return structure_result

        source_result = validate_project_structure(str(source_main_tex))
        if source_result.get("ok", False):
            return structure_result

        if str(source_result.get("reason_code") or "") != reason_code:
            return structure_result

        translated_signature = self._normalize_structure_guard_message(
            str(structure_result.get("message") or "")
        )
        source_signature = self._normalize_structure_guard_message(
            str(source_result.get("message") or "")
        )
        if translated_signature != source_signature:
            return structure_result

        details = dict(structure_result.get("details") or {})
        details.update(
            {
                "source_baseline_guard_reason_code": source_result.get("reason_code"),
                "source_baseline_guard_message": source_result.get("message"),
                "source_baseline_main_tex": str(source_main_tex),
            }
        )
        logger.warning(
            "Structure guard downgraded to warning because translated bundle matches source baseline guard failure: %s",
            reason_code,
        )
        return {
            "ok": True,
            "reason_code": reason_code,
            "message": "Structure guard warning only: translated bundle matches source baseline walker failure",
            "details": details,
            "warning_only": True,
            "guard_blocking": False,
            "guard_scope": structure_result.get("guard_scope") or "project",
        }

    def _augment_result_with_guard_warning(self, result: Dict[str, Any]) -> Dict[str, Any]:
        warning = self._structure_guard_warning
        if not warning:
            return result
        warning_text = f"[Structure Guard Warning] {warning['message']}"
        existing_warnings = result.get("warnings")
        result["warnings"] = warning_text if not existing_warnings else f"{warning_text} | {existing_warnings}"
        result["guard_warning_only"] = True
        result["guard_reason_code"] = warning.get("reason_code")
        result["guard_scope"] = warning.get("guard_scope")
        result["replay_bundle_ref"] = warning.get("replay_bundle_ref")
        result["guard_details"] = warning.get("details")
        return result

    def _downgrade_disabled_precompile_guard_failure(
        self,
        *,
        structure_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        if structure_result.get("ok", False):
            return structure_result

        if self._is_precompile_structure_guard_enabled():
            return structure_result

        reason_code = str(structure_result.get("reason_code") or "structure_guard_disabled")
        details = dict(structure_result.get("details") or {})
        details.update(
            {
                "guard_disabled_via_config": True,
                "disabled_flag": "enable_precompile_structure_guard",
            }
        )
        logger.warning(
            "Precompile structure guard disabled via config; downgrading blocking failure to warning: %s",
            reason_code,
        )
        return {
            "ok": True,
            "reason_code": reason_code,
            "message": "Structure guard warning only: precompile structure guard disabled via config",
            "details": details,
            "warning_only": True,
            "guard_blocking": False,
            "guard_scope": structure_result.get("guard_scope") or "project",
        }

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
        origin_cli_parity = self._is_origin_cli_parity_enabled()
        latex_constructor = LatexConstructor(
            sections=sections,
            captions=captions,
            envs=envs,
            inputs=inputs,
            newcommands=newcommands,
            output_latex_dir=transed_latex_dir,
            target_language=target_language,
            origin_cli_parity=origin_cli_parity,
        )
        latex_constructor.construct(on_progress=self.on_progress)

        if origin_cli_parity:
            main_tex_path = find_main_tex_file(transed_latex_dir)
            if not main_tex_path:
                error_summary = f"No reliable main .tex file found in {transed_latex_dir}"
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

            main_tex = Path(main_tex_path)
            self.update_progress(80, "Compiling PDF document")
            logger.info(f"Compiling {main_tex.name} with origin CLI parity...")
            self._update_replay_bundle(
                compile_attempted=True,
                compile_verdict_source="origin_cli_parity_compiler",
                guard_blocking=False,
                guard_warning_only=False,
            )
            result = compile_with_origin_cli_parity(str(main_tex), transed_latex_dir)
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
                    "guard_warning_only": False,
                    "guard_reason_code": None,
                    "guard_scope": None,
                    "guard_details": None,
                    "replay_bundle_ref": result.get("replay_bundle_ref"),
                }

            self.update_progress(100, "PDF compilation failed")
            self.log("Failed to compile PDF document", level="error")
            return {
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

        main_tex, precompile_failure = self._resolve_and_validate_compile_bundle(transed_latex_dir)
        if precompile_failure is not None:
            return precompile_failure

        self.update_progress(80, "Compiling PDF document")
        
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
        self._update_replay_bundle(
            compile_attempted=True,
            compile_verdict_source="compiler",
            guard_blocking=False,
            guard_warning_only=bool(self._structure_guard_warning),
        )
        result = compile_with_intelligent_fallback(
            tex_file=str(main_tex),
            output_dir=transed_latex_dir,
            preferred_order=preferred_order,
            target_language=target_language,
        )
        result = self._augment_result_with_guard_warning(result)

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
                "guard_warning_only": result.get("guard_warning_only", False),
                "guard_reason_code": result.get("guard_reason_code"),
                "guard_scope": result.get("guard_scope"),
                "guard_details": result.get("guard_details"),
                "replay_bundle_ref": result.get("replay_bundle_ref"),
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
            "guard_warning_only": result.get("guard_warning_only", False),
            "guard_reason_code": result.get("guard_reason_code"),
            "guard_scope": result.get("guard_scope"),
            "guard_details": result.get("guard_details"),
            "replay_bundle_ref": result.get("replay_bundle_ref"),
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
        origin_cli_parity = self._is_origin_cli_parity_enabled()
        latex_constructor = LatexConstructor(
            sections=sections,
            captions=captions,
            envs=envs,
            inputs=inputs,
            newcommands=newcommands,
            output_latex_dir=transed_latex_dir,
            target_language=target_language,
            origin_cli_parity=origin_cli_parity,
        )
        await asyncio.to_thread(latex_constructor.construct, self.on_progress)

        if origin_cli_parity:
            main_tex_path = find_main_tex_file(transed_latex_dir)
            if not main_tex_path:
                error_summary = f"No reliable main .tex file found in {transed_latex_dir}"
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

            main_tex = Path(main_tex_path)
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
                return {
                    "status": result.get("status", "completed"),
                    "pdf_path": pdf_file,
                    "error_summary": None,
                    "warnings": result.get("warnings"),
                    "engine": result.get("engine"),
                    "error_count": result.get("error_count", 0),
                    "compile_queue_wait_ms": compile_queue_wait_ms,
                    "compile_exec_ms": compile_exec_ms,
                    "guard_warning_only": False,
                    "guard_reason_code": None,
                    "guard_scope": None,
                    "guard_details": None,
                    "replay_bundle_ref": result.get("replay_bundle_ref"),
                }

            self.update_progress(100, "PDF compilation failed")
            return {
                "status": "failed_compilation",
                "pdf_path": None,
                "error_summary": result.get("errors") or "Compilation failed without detailed error output",
                "warnings": result.get("warnings"),
                "engine": result.get("engine"),
                "error_count": result.get("error_count", 0),
                "compile_queue_wait_ms": compile_queue_wait_ms,
                "compile_exec_ms": compile_exec_ms,
                "guard_warning_only": False,
                "guard_reason_code": None,
                "guard_scope": None,
                "guard_details": None,
                "replay_bundle_ref": result.get("replay_bundle_ref"),
            }

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

        main_tex, precompile_failure = self._resolve_and_validate_compile_bundle(transed_latex_dir)
        if precompile_failure is not None:
            return precompile_failure

        preferred_order = None
        if self.latex_engine and self.latex_engine != "auto":
            all_engines = ["pdflatex", "xelatex", "lualatex"]
            if self.latex_engine in all_engines:
                all_engines.remove(self.latex_engine)
                preferred_order = [self.latex_engine] + all_engines

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
                compile_verdict_source="compiler",
                guard_blocking=False,
                guard_warning_only=bool(self._structure_guard_warning),
            )
            result = await compile_with_intelligent_fallback_async(
                tex_file=str(main_tex),
                output_dir=transed_latex_dir,
                preferred_order=preferred_order,
                target_language=target_language,
                on_process_start=self._notify_compile_start,
                on_process_end=self._notify_compile_end,
            )
            compile_exec_ms = int((time.monotonic() - compile_started_at) * 1000)
        finally:
            compile_sem.release()
        result = self._augment_result_with_guard_warning(result)
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
                "guard_warning_only": result.get("guard_warning_only", False),
                "guard_reason_code": result.get("guard_reason_code"),
                "guard_scope": result.get("guard_scope"),
                "guard_details": result.get("guard_details"),
                "replay_bundle_ref": result.get("replay_bundle_ref"),
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
            "guard_warning_only": result.get("guard_warning_only", False),
            "guard_reason_code": result.get("guard_reason_code"),
            "guard_scope": result.get("guard_scope"),
            "guard_details": result.get("guard_details"),
            "replay_bundle_ref": result.get("replay_bundle_ref"),
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
