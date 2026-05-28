"""Agent 数据模型 - Pydantic 规划与应答模型"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


IntentKind = Literal["search", "answer", "translate"]


class AnswerSlots(BaseModel):
    """结构化答案槽位"""
    current_status: str
    background_answer: str
    paper_overview: str = ""
    core_points: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class PlannerStep(BaseModel):
    """规划器单步决策"""
    mode: Literal["call_skill", "finalize"]
    intent: IntentKind
    skill_name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    slots: Optional[AnswerSlots] = None
    citation_ids: List[str] = Field(default_factory=list)
    action: Optional[Dict[str, Any]] = None
    self_check: str = ""
    decision_note: str = ""
