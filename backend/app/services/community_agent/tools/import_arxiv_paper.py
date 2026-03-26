from __future__ import annotations

from functools import cached_property

from backend.app.services.community_agent.skills.import_arxiv_paper import (
    ImportArxivPaperSkill as LegacyImportArxivPaperSkill,
)

from .base import CommunityAgentTool


class ImportArxivPaperTool(CommunityAgentTool):
    @cached_property
    def legacy_skill(self) -> LegacyImportArxivPaperSkill:
        return LegacyImportArxivPaperSkill()
