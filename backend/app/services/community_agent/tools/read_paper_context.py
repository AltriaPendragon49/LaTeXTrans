from __future__ import annotations

from functools import cached_property

from backend.app.services.community_agent.skills.read_paper_context import (
    ReadPaperContextSkill as LegacyReadPaperContextSkill,
)

from .base import CommunityAgentTool


class ReadPaperContextTool(CommunityAgentTool):
    @cached_property
    def legacy_skill(self) -> LegacyReadPaperContextSkill:
        return LegacyReadPaperContextSkill()
