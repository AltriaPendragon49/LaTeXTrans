from __future__ import annotations

from functools import cached_property

from backend.app.services.community_agent.skills.start_translation_kernel import (
    StartTranslationKernelSkill as LegacyStartTranslationKernelSkill,
)

from .base import CommunityAgentTool


class StartTranslationKernelTool(CommunityAgentTool):
    @cached_property
    def legacy_skill(self) -> LegacyStartTranslationKernelSkill:
        return LegacyStartTranslationKernelSkill()
