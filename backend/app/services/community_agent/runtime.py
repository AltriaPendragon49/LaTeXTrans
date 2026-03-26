from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentRuntimeState:
    input_text: str
    context: Dict[str, Any]
    skill_toggles: Dict[str, Any]
    provider_state: Dict[str, str]
    response_language: str = "en"
    history: List[Dict[str, str]] = field(default_factory=list)
    paper_context: Dict[str, Any] | None = None
    citations: List[Dict[str, Any]] = field(default_factory=list)
    citations_by_id: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tool_trace: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    executed_skill_results: List[Dict[str, Any]] = field(default_factory=list)
    executed_tool_results: List[Dict[str, Any]] = field(default_factory=list)
    generated_slots: Dict[str, Any] | None = None
    generated_citation_ids: List[str] = field(default_factory=list)
    action: Dict[str, Any] | None = None
    latest_intent: str = "answer"
    repair_count: int = 0
    planner_turn_count: int = 0

    def add_citations(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        added: List[Dict[str, Any]] = []
        for citation in citations:
            citation_id = str(citation.get("id") or "").strip()
            if not citation_id or citation_id in self.citations_by_id:
                continue
            self.citations.append(citation)
            self.citations_by_id[citation_id] = citation
            added.append(citation)
        return added
