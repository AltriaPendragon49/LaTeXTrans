import os
import shutil
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import asyncio
import logging
import traceback
import hashlib
import re

from .parser_agent import ParserAgent
from .translator_agent import TranslatorAgent 
from .generator_agent import GeneratorAgent
from .validator_agent import ValidatorAgent

logger = logging.getLogger(__name__)


class CoordinatorAgent:
    """
    The main orchestrator agent for the translation system.
    It coordinates the workflow of various tool agents based on document format
    and configuration.
    """

    def __init__(self, 
                 config: Dict[str, Any],
                 project_dir: str = None,
                 output_dir: Optional[str] = None,
                 on_progress: Optional[Callable[[int, str], None]] = None,
                 ):
        """
        Initializes the CoordinatorAgent.
        """
        self.config = config
        self.name = config.get("sys_name", "LaTeXTrans")
        self.target_language = config.get("target_language", "ch")
        self.source_language = config.get("source_language", "en")
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.loop = asyncio.new_event_loop()
        self.mode = config.get("mode", 0)
        self.on_progress = on_progress

    def update_progress(self, percentage: int, message: str = "") -> None:
        """Update progress via callback if available"""
        if self.on_progress:
            self.on_progress(percentage, message)

    def run_async(self, coro):
        """
        Run asynchronous coroutines in the existing event loop
        """
        return self.loop.run_until_complete(coro)

    def _write_task_log(self, output_dir: str, event: str, data: dict = None):
        """Write structured event to task-specific log file"""
        import json
        import datetime
        log_file = Path(output_dir) / "task_log.json"
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event": event,
            **(data or {})
        }
        # Append to log
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding="utf-8"))
            except:
                pass
        logs.append(entry)
        try:
            log_file.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write task log: {e}")

    def _write_stage_failed_log(self, output_dir: str, stage: str, error: Exception) -> None:
        """Write a normalized stage failure event to task log."""
        tb = traceback.format_exc()
        digest = hashlib.sha256(tb.encode("utf-8", errors="replace")).hexdigest()[:16]
        self._write_task_log(
            output_dir,
            "stage_failed",
            {
                "stage": stage,
                "error_type": error.__class__.__name__,
                "error_message": str(error),
                "traceback_digest": digest,
            },
        )

    async def workflow_latextrans_async(self) -> Dict[str, Any]:
        """
        Initializes the tool agent based on the provided agent name key.

        Returns:
            Structured workflow result with status/pdf_path/error_summary.
        """
        base_name = os.path.basename(self.project_dir)
        transed_project_dir = os.path.join(self.output_dir, f"{self.target_language}_{base_name}")

        os.makedirs(transed_project_dir, exist_ok=True)
        self._write_task_log(transed_project_dir, "task_started", {"project": base_name, "config": {k: v for k, v in self.config.items() if k != "llm_config"}})
        validation_warning: Optional[str] = None

        # Step 1: Parse LaTeX (10% total progress)
        logger.info(f"Starting LaTeX parsing for {base_name}")
        self.update_progress(5, "Initializing parser")
        try:
            parser_agent = ParserAgent(
                config=self.config,
                project_dir=self.project_dir,
                output_dir=transed_project_dir,
                on_progress=lambda s, p, m: self.update_progress(5 + int(p * 0.05), m)
            )
            await parser_agent.execute()
            self._write_task_log(transed_project_dir, "parsing_completed")
            self.update_progress(10, "Parsing completed")
        except Exception as e:
            self._write_stage_failed_log(transed_project_dir, "parse", e)
            raise

        # Step 2: Translate (10% - 70% total progress)
        logger.info("Starting translation")
        self.update_progress(10, "Initializing translator")
        try:
            translator_agent = TranslatorAgent(
                config=self.config,
                project_dir=self.project_dir,
                output_dir=transed_project_dir,
                trans_mode=self.mode,
                generate_terminology=self.config.get("generate_terminology", False),
                on_progress=lambda s, p, m: self.update_progress(-1, m) if p == -1 else self.update_progress(10 + int(p * 0.6), m)
            )
            await translator_agent.execute()
            self._write_task_log(transed_project_dir, "translation_completed")
            self.update_progress(70, "Translation completed")
        except Exception as e:
            self._write_stage_failed_log(transed_project_dir, "translate", e)
            raise

        # Step 3: Validate (70% - 75% total progress)
        logger.info("Validating translation")
        self.update_progress(70, "Validating translation")
        try:
            validator_agent = ValidatorAgent(
                config=self.config,
                project_dir=self.project_dir,
                output_dir=transed_project_dir,
                on_progress=lambda s, p, m: self.update_progress(70 + int(p * 0.05), m)
            )
            errors_report = validator_agent.execute()
            initial_errors_count = len(errors_report) if errors_report else 0
            
            # Step 4: Retry if needed (75% - 85% total progress)
            # NOTE: Quick scan mode (mode == 3) skips repair to preserve semantic boundary
            MAX_RETRIES = 3
            retry_count = 0
            
            if self.mode == 3:
                # Quick scan mode: skip repair to preserve semantic boundary
                logger.info("Quick scan mode: skipping error repair to preserve translation boundary")
                if errors_report:
                    logger.warning(f"Quick scan mode detected {len(errors_report)} validation errors, but repair is disabled")
            else:
                # Normal modes: perform repair if errors exist
                if errors_report:
                    translator_agent.trans_mode = 1

                while errors_report and retry_count < MAX_RETRIES:
                    logger.info(f"Retrying translation for errors, attempt {retry_count + 1}/{MAX_RETRIES}")
                    self.update_progress(75 + int((retry_count / MAX_RETRIES) * 10), 
                                       f"Retrying errors (attempt {retry_count + 1}/{MAX_RETRIES})")
                    
                    translator_agent.errors_report = errors_report
                    await translator_agent.execute(error_retry_count=retry_count, Maxtry=MAX_RETRIES)
                    errors_report = validator_agent.execute(errors_report)
                    retry_count += 1

            final_errors_count = len(errors_report) if errors_report else 0
            fallback_count = int(getattr(translator_agent, "structural_fallback_count", 0) or 0)
            fallback_ratio = float(getattr(translator_agent, "structural_fallback_ratio", 0.0) or 0.0)
            fallback_cap = float(getattr(translator_agent, "structural_fallback_cap", 0.10) or 0.10)
            fallback_cap_mode = str(getattr(translator_agent, "structural_fallback_cap_mode", "soft") or "soft")
            filtered_code_like_math_tokens = int(
                getattr(validator_agent, "code_like_filtered_bare_tokens", 0) or 0
            )
            fallback_parts = list(getattr(translator_agent, "structural_fallback_parts", []) or [])
            noop_sections = list(getattr(translator_agent, "noop_sections", []) or [])
            c1_retry_enforced_once = bool(getattr(translator_agent, "c1_retry_enforced_once", False))
            validation_warning = getattr(translator_agent, "structural_fallback_warning", None)

            fallback_count_full: Optional[int] = None
            fallback_count_translatable: Optional[int] = None
            same_content_sections_full: Optional[int] = None
            same_content_sections_translatable: Optional[int] = None
            fallback_count_env_math: Optional[int] = None
            fallback_count_env_list: Optional[int] = None
            fallback_count_env_other: Optional[int] = None
            try:
                import json

                level_a_re = re.compile(
                    r'\\begin\{(?:table|figure|algorithm|algorithmic|theorem|lemma|proof|definition|tikzpicture|lstlisting|verbatim|minted)\*?\}'
                )

                def _has_level_a_env(text: str) -> bool:
                    return bool(level_a_re.search(text or ""))

                sections_path = Path(transed_project_dir) / "sections_map.json"
                if sections_path.exists():
                    sections = json.loads(sections_path.read_text(encoding="utf-8"))
                    normal_sections = [s for s in sections if str(s.get("section", "")) != "-1"]

                    same_full = [
                        s for s in normal_sections
                        if (s.get("trans_content") or "") == (s.get("content") or "")
                    ]
                    same_trans = [s for s in same_full if not _has_level_a_env(s.get("content") or "")]
                    same_content_sections_full = len(same_full)
                    same_content_sections_translatable = len(same_trans)

                    fallback_sections = [
                        s for s in normal_sections
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
                        e for e in envs
                        if e.get("translation_status") == "fallback_source_compile_first"
                    ]
                    fallback_count_env_math = sum(
                        1 for e in env_fallbacks if e.get("fallback_subtype") == "math_env_fallback"
                    )
                    fallback_count_env_list = sum(
                        1 for e in env_fallbacks if e.get("fallback_subtype") == "list_env_fallback"
                    )
                    fallback_count_env_other = sum(
                        1 for e in env_fallbacks
                        if e.get("fallback_subtype") not in {"math_env_fallback", "list_env_fallback"}
                    )
            except Exception as metric_exc:
                logger.warning("Failed to compute dual-scope validation metrics: %s", metric_exc)

            self._write_task_log(
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
                self._write_task_log(
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

            self.update_progress(85, "Validation completed")
        except Exception as e:
            self._write_stage_failed_log(transed_project_dir, "validate", e)
            raise

        # Step 5: Generate PDF (85% - 100% total progress)
        logger.info("Generating PDF")
        self.update_progress(85, "Generating PDF")
        
        generator_agent = GeneratorAgent(
            config=self.config,
            project_dir=self.project_dir,
            output_dir=transed_project_dir,
            on_progress=lambda s, p, m: self.update_progress(85 + int(p * 0.15), m)
        )
        
        try:
            generation_result = generator_agent.execute()
        except Exception as e:
            self._write_stage_failed_log(transed_project_dir, "generate", e)
            raise

        if generation_result.get("status") == "structure_invalid":
            error_text = generation_result.get("error_summary") or "LaTeX structure guard rejected bundle before compilation"
            failure_reason_code = generation_result.get("failure_reason_code")
            failure_class = generation_result.get("failure_class") or "structural"
            guard_phase = generation_result.get("guard_phase") or "precompile"
            replay_bundle_ref = generation_result.get("replay_bundle_ref")
            warning_text = validation_warning or generation_result.get("warnings")
            self._write_task_log(
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
            self._write_task_log(
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
            self.update_progress(100, "Aborted due to structure guard")
            return {
                "status": "structure_invalid",
                "pdf_path": None,
                "error_summary": error_text,
                "warnings": warning_text,
                "failure_reason_code": failure_reason_code,
                "failure_class": failure_class,
                "guard_phase": guard_phase,
                "replay_bundle_ref": replay_bundle_ref,
            }

        def _merge_warnings(primary: Optional[str], secondary: Optional[str]) -> Optional[str]:
            if primary and secondary:
                return f"{primary}\n{secondary}"
            return primary or secondary

        PDF_file_path = generation_result.get("pdf_path")
        if PDF_file_path:
            if not Path(PDF_file_path).exists():
                error_summary = (
                    generation_result.get("error_summary")
                    or f"Compilation returned a missing PDF path: {PDF_file_path}"
                )
                logger.error(f"Failed to finalize PDF for {base_name}: {error_summary}")
                self._write_task_log(
                    transed_project_dir,
                    "compilation_failed",
                    {
                        "error_summary": error_summary,
                        "pdf_path": PDF_file_path,
                        "warnings": generation_result.get("warnings"),
                        "error_count": generation_result.get("error_count"),
                        "engine": generation_result.get("engine"),
                    }
                )
                self.update_progress(100, "Failed to generate PDF")
                return {
                    "status": "failed_compilation",
                    "pdf_path": None,
                    "error_summary": error_summary,
                    "warnings": _merge_warnings(validation_warning, generation_result.get("warnings")),
                }

            new_PDF_path = os.path.join(transed_project_dir, f"{self.target_language}_{base_name}.pdf")
            try:
                shutil.move(PDF_file_path, new_PDF_path)
            except Exception as move_error:
                error_summary = (
                    generation_result.get("error_summary")
                    or f"Failed to finalize compiled PDF: {move_error}"
                )
                logger.error(f"Failed to move compiled PDF for {base_name}: {move_error}")
                self._write_task_log(
                    transed_project_dir,
                    "compilation_failed",
                    {
                        "error_summary": error_summary,
                        "pdf_path": PDF_file_path,
                        "warnings": generation_result.get("warnings"),
                        "error_count": generation_result.get("error_count"),
                        "engine": generation_result.get("engine"),
                    }
                )
                self.update_progress(100, "Failed to generate PDF")
                return {
                    "status": "failed_compilation",
                    "pdf_path": None,
                    "error_summary": error_summary,
                    "warnings": _merge_warnings(validation_warning, generation_result.get("warnings")),
                }
            
            # Verify PDF is fully ready before updating status
            from backend.app.services.latex.compiler import verify_pdf_ready

            compile_status = generation_result.get("status", "completed")
            compile_warnings = _merge_warnings(validation_warning, generation_result.get("warnings"))
            if compile_status == "completed" and compile_warnings:
                compile_status = "completed_with_warnings"
            if verify_pdf_ready(new_PDF_path):
                logger.info(f"PDF verified ready: {new_PDF_path}")
                if compile_status == "completed_with_warnings":
                    self._write_task_log(
                        transed_project_dir,
                        "compilation_completed_with_warnings",
                        {"pdf_path": new_PDF_path, "warnings": compile_warnings}
                    )
                    self.update_progress(100, "Translation completed with compilation warnings")
                else:
                    self._write_task_log(transed_project_dir, "compilation_completed", {"pdf_path": new_PDF_path})
                    self.update_progress(100, "Translation completed successfully")
            else:
                logger.warning(f"PDF may not be fully ready: {new_PDF_path}")
                compile_status = "completed_with_warnings"
                compile_warnings = compile_warnings or "PDF generated but readiness verification timed out"
                self._write_task_log(
                    transed_project_dir,
                    "compilation_completed_with_warnings",
                    {"pdf_path": new_PDF_path, "warnings": compile_warnings}
                )
                self.update_progress(100, "Translation completed, PDF may need refresh")
            return {
                "status": compile_status,
                "pdf_path": new_PDF_path,
                "error_summary": None,
                "warnings": compile_warnings,
            }
        else:
            error_summary = generation_result.get("error_summary") or "No PDF path returned"
            logger.error(f"Failed to generate PDF for {base_name}: {error_summary}")
            self._write_task_log(
                transed_project_dir,
                "compilation_failed",
                {
                    "error_summary": error_summary,
                    "warnings": generation_result.get("warnings"),
                    "error_count": generation_result.get("error_count"),
                    "engine": generation_result.get("engine"),
                }
            )
            self.update_progress(100, "Failed to generate PDF")
            return {
                "status": "failed_compilation",
                "pdf_path": None,
                "error_summary": error_summary,
                "warnings": _merge_warnings(validation_warning, generation_result.get("warnings")),
            }

    def workflow_latextrans(self) -> Dict[str, Any]:
        """
        Initialize the tool agent and execute the LaTeX conversion workflow 
        (with event loop security management)
        """

        if hasattr(self, 'loop') and not self.loop.is_closed():
            self.loop.close()

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        result: Dict[str, Any] = {
            "status": "failed",
            "pdf_path": None,
            "error_summary": "Workflow did not run",
            "warnings": None,
        }

        try:
            result = self.loop.run_until_complete(self.workflow_latextrans_async())

        finally:
            # Complete all asynchronous resource recycling
            import sys
            if tasks := asyncio.all_tasks(self.loop):
                self.loop.run_until_complete(
                    asyncio.gather(*tasks, return_exceptions=True)
                )

            # Special handling of asynchronous I/O recycling in Windows
            if sys.platform == "win32":
                self.loop.run_until_complete(
                    self.loop.shutdown_asyncgens()
                )

            self.loop.run_until_complete(self.loop.shutdown_default_executor())
        return result
