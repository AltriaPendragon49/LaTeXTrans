import os
import shutil
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import asyncio
import logging

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

        # Step 1: Parse LaTeX (10% total progress)
        logger.info(f"Starting LaTeX parsing for {base_name}")
        self.update_progress(5, "Initializing parser")
        
        parser_agent = ParserAgent(
            config=self.config,
            project_dir=self.project_dir,
            output_dir=transed_project_dir,
            on_progress=lambda s, p, m: self.update_progress(5 + int(p * 0.05), m)
        )
        await parser_agent.execute()
        self._write_task_log(transed_project_dir, "parsing_completed")
        self.update_progress(10, "Parsing completed")

        # Step 2: Translate (10% - 70% total progress)
        logger.info("Starting translation")
        self.update_progress(10, "Initializing translator")
        
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

        # Step 3: Validate (70% - 75% total progress)
        logger.info("Validating translation")
        self.update_progress(70, "Validating translation")
        
        validator_agent = ValidatorAgent(
            config=self.config,
            project_dir=self.project_dir,
            output_dir=transed_project_dir,
            on_progress=lambda s, p, m: self.update_progress(70 + int(p * 0.05), m)
        )
        errors_report = validator_agent.execute()
        self._write_task_log(transed_project_dir, "validation_completed", {"errors_count": len(errors_report) if errors_report else 0})
        
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
        
        self.update_progress(85, "Validation completed")

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
            logger.error(f"Failed to generate PDF for {base_name}: {e}")
            self._write_task_log(
                transed_project_dir,
                "compilation_failed",
                {"error_summary": str(e)}
            )
            self.update_progress(100, f"Failed: {e}")
            return {
                "status": "failed_compilation",
                "pdf_path": None,
                "error_summary": str(e),
                "warnings": None,
            }
        
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
                    "warnings": generation_result.get("warnings"),
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
                    "warnings": generation_result.get("warnings"),
                }
            
            # Verify PDF is fully ready before updating status
            from backend.app.services.latex.compiler import verify_pdf_ready

            compile_status = generation_result.get("status", "completed")
            compile_warnings = generation_result.get("warnings")
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
                "warnings": generation_result.get("warnings"),
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
