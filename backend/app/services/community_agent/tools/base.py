from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from backend.app.services.community_agent.skills.base import AgentSkill


class CommunityAgentTool(ABC):
    @property
    @abstractmethod
    def legacy_skill(self) -> AgentSkill:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.legacy_skill.name

    @property
    def description(self) -> str:
        return self.legacy_skill.description

    @property
    def trace_kind(self) -> str:
        return self.legacy_skill.trace_kind

    @property
    def trace_label(self) -> str:
        return self.legacy_skill.trace_label

    @property
    def provider(self) -> str:
        return self.legacy_skill.provider

    def input_schema(self) -> Dict[str, Any]:
        return self.legacy_skill.input_schema()

    def is_visible(self, runtime_state) -> bool:  # type: ignore[no-untyped-def]
        return self.legacy_skill.is_visible(runtime_state)

    def serialize_for_model(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema(),
            },
        }

    async def execute(self, arguments: Dict[str, Any], runtime_state) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        return await self.legacy_skill.execute(arguments, runtime_state)
