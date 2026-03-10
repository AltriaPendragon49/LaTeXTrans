"""
pipeline_schema.py
Phase 4b 准入基础设施 — Gate 4b-1
eliminate-silent-fallback — FallbackReport schema

Pydantic 强类型 schema：节点级 I/O 契约、审计日志记录模型。
此文件严禁包含任何 DiagnosticNode 相关逻辑（Gate 4b-3 锁）。
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Literal, Optional

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


# ---------------------------------------------------------------------------
# eliminate-silent-fallback — Fallback Observability
# ---------------------------------------------------------------------------


class FallbackReport(BaseModel):
    """结构化 Fallback 报告（eliminate-silent-fallback spec）。

    当翻译管道将某段落回退到源语言时必须发出此报告。
    它作为后续修复节点（TranslationRepairAgent / StructureRepairNode）的上下文载体，
    同时提供完整的可观测诊断信息。

    约束：
    - 数学环境、code 块、verbatim 环境内的文本不属于「自然语言段落」，
      此类 fallback 无需发出报告（exempt）。
    - fallback_kind 枚举值之外不得使用自定义字符串。
    """

    fallback_kind: Literal[
        "oversize_downgrade",         # 超出 safe_input_limit，整段跳过翻译
        "c2_structural_collapse",     # C2 级结构折叠，强制回退到源文本
        "c1_structural_rollback",     # C1 级局部回退（1 次 LLM 重试后仍失败）
    ] = Field(..., description="Fallback 类型枚举")

    chunk_scope: str = Field(
        ...,
        description="受影响段落的唯一标识：section_id（节段）或 placeholder（env/caption）",
    )

    root_cause: str = Field(
        ...,
        description=(
            "根因分类字符串，例如 'oversize_no_safe_boundary'、"
            "'c2_global_structure_collapse'、'c1_local_structural_mismatch'"
        ),
    )

    validation_evidence: Optional[Dict[str, Any]] = Field(
        default=None,
        description="ValidatorAgent 产生的错误详情（error_type、bracket_diff 等），C2/C1 fallback 时应填写",
    )

    translated_text: Optional[str] = Field(
        default=None,
        description="可用的已翻译文本（可能结构损坏）；oversize_downgrade 时为 None",
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now().isoformat(),
        description="报告生成 ISO 时间",
    )

    def to_dict(self) -> Dict[str, Any]:
        """返回可 JSON 序列化的字典（供审计日志 / task_log 写入）。"""
        return self.model_dump()

