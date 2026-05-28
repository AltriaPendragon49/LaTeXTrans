"""翻译系统的主协调 Agent 模块。"""

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
    翻译系统的主协调 Agent。

    根据文档格式和配置协调各个工具 Agent 的工作流。

    Phase 4a: 执行权限已委托给 langgraph_orchestrator。
    公开 API（workflow_latextrans / workflow_latextrans_async）保持不变。
    """

    def __init__(self,
                 config: Dict[str, Any],
                 project_dir: str = None,
                 output_dir: Optional[str] = None,
                 on_progress: Optional[Callable[[int, str], None]] = None,
                 ):
        """
        初始化 CoordinatorAgent。

        Args:
            config: 系统配置字典
            project_dir: 项目目录路径
            output_dir: 输出目录路径
            on_progress: 进度回调函数 (percentage, message)
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
        """通过回调函数更新进度（如果可用）。"""
        if self.on_progress:
            self.on_progress(percentage, message)

    def run_async(self, coro):
        """
        在现有事件循环中运行异步协程。
        """
        return self.loop.run_until_complete(coro)

    def _write_task_log(self, output_dir: str, event: str, data: dict = None):
        """将结构化事件写入任务专属日志文件。"""
        import json
        import datetime
        log_file = Path(output_dir) / "task_log.json"
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event": event,
            **(data or {})
        }
        # 追加到日志
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
        """将标准化的阶段失败事件写入任务日志。"""
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
        通过 Phase 4a StateGraph 协调器执行 LaTeX 翻译工作流。

        委托给 langgraph_orchestrator.run_pipeline()，后者通过 StateGraph
        驱动相同的 解析 -> 翻译 -> 验证 -> 生成 -> 收尾 流程。
        所有现有 Agent 逻辑保持不变，仅执行权限已转移。

        Returns:
            结构化的工作流结果，包含 status/pdf_path/error_summary。
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
        初始化工具 Agent 并执行 LaTeX 转换工作流
        （含事件循环安全管理）。
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
            # 完成所有异步资源回收
            import sys
            if tasks := asyncio.all_tasks(self.loop):
                self.loop.run_until_complete(
                    asyncio.gather(*tasks, return_exceptions=True)
                )

            # Windows 下异步 I/O 回收的特殊处理
            if sys.platform == "win32":
                self.loop.run_until_complete(
                    self.loop.shutdown_asyncgens()
                )

            self.loop.run_until_complete(self.loop.shutdown_default_executor())
        return result
