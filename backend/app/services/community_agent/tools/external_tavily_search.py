from __future__ import annotations

from functools import cached_property

from backend.app.services.community_agent.skills.external_tavily_search import (
    ExternalTavilySearchSkill as LegacyExternalTavilySearchSkill,
)

from .base import CommunityAgentTool


class ExternalTavilySearchTool(CommunityAgentTool):
    @cached_property
    def legacy_skill(self) -> LegacyExternalTavilySearchSkill:
        return LegacyExternalTavilySearchSkill()
