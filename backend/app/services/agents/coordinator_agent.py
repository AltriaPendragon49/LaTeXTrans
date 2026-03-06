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

    Phase 4a: Execution authority has been delegated to langgraph_orchestrator.
    The public API (workflow_latextrans / workflow_latextrans_async) is unchanged.
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
        Executes the LaTeX translation workflow via the Phase 4a StateGraph orchestrator.

        Delegates to langgraph_orchestrator.run_pipeline(), which drives the same
        parse → translate → validate → generate → finalize sequence using a StateGraph.
        All existing agent logic is unchanged; only execution authority has moved.

        Returns:
            Structured workflow result with status/pdf_path/error_summary.
        """
        from .langgraph_orchestrator import run_pipeline
        return await run_pipeline(
            config=self.config,
            project_dir=self.project_dir,
            output_dir=self.output_dir,
            on_progress=self.on_progress,
        )

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
