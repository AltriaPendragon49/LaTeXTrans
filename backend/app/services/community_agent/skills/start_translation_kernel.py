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
        submitter_user_id = None
        if isinstance(getattr(runtime_state, "context", None), dict):
            submitter_user_id = runtime_state.context.get("user_id")

        kwargs: Dict[str, Any] = {
            "paper_id": arguments["paper_id"],
            "request": request,
            "credentials": None,
        }
        if submitter_user_id:
            kwargs["submitter_user_id"] = str(submitter_user_id)

        return await paper_service.start_paper_translation(
            **kwargs,
        )
