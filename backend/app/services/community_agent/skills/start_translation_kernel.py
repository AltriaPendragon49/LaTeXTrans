from __future__ import annotations

from typing import Any, Dict

from backend.app.api.routes.translate import TranslateRequest
from backend.app.services import paper_service

from .base import AgentSkill


class StartTranslationKernelSkill(AgentSkill):
    contract_slug = "start_translation_kernel"

    async def execute(self, arguments: Dict[str, Any], runtime_state) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        request = TranslateRequest(
            source_language=str(arguments.get("source_language") or "en"),
            target_language=str(arguments.get("target_language") or "zh"),
        )
        return await paper_service.start_paper_translation(
            paper_id=arguments["paper_id"],
            request=request,
            credentials=None,
        )
