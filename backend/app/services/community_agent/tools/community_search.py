from __future__ import annotations

from functools import cached_property

from backend.app.services.community_agent.skills.community_search import (
    CommunitySearchPapersSkill as LegacyCommunitySearchPapersSkill,
)

from .base import CommunityAgentTool


class CommunitySearchPapersTool(CommunityAgentTool):
    @cached_property
    def legacy_skill(self) -> LegacyCommunitySearchPapersSkill:
        return LegacyCommunitySearchPapersSkill()
