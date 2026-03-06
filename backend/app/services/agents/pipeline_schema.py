"""
pipeline_schema.py
Phase 4b 准入基础设施 — Gate 4b-1

Pydantic 强类型 schema：节点级 I/O 契约、审计日志记录模型。
此文件严禁包含任何 DiagnosticNode 相关逻辑（Gate 4b-3 锁）。
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class PipelineInput(BaseModel):
    """流水线入口强类型 Schema（Gate 4b-1）。"""

    task_id: str = Field(..., description="全局唯一任务 ID")
    config: Dict[str, Any] = Field(..., description="翻译配置字典")
    project_dir: str = Field(..., description="原始 LaTeX 项目目录")
    output_dir: str = Field(..., description="输出根目录")
    mode: int = Field(default=0, description="翻译模式（0=normal, 3=quick-scan）")
    started_at: str = Field(
        default_factory=lambda: datetime.datetime.now().isoformat(),
        description="任务开始 ISO 时间",
    )


class NodeOutput(BaseModel):
    """节点出口强类型 Schema（Gate 4b-1）。"""

    node: str = Field(..., description="节点名称")
    status: Literal["ok", "error"] = Field(..., description="执行状态")
    elapsed_ms: float = Field(..., ge=0, description="节点执行耗时（毫秒）")
    ended_at: str = Field(
        default_factory=lambda: datetime.datetime.now().isoformat(),
        description="节点完成 ISO 时间",
    )
    error: Optional[str] = Field(default=None, description="错误描述（status=error 时填写）")


class PipelineAuditEntry(BaseModel):
    """JSONL 审计日志单条记录（Gate 4b-1）。"""

    task_id: str = Field(..., description="全局唯一任务 ID")
    event: str = Field(..., description="审计事件名称")
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now().isoformat(),
        description="事件 ISO 时间",
    )
    payload: Optional[Dict[str, Any]] = Field(default=None, description="附加数据")
