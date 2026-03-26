from __future__ import annotations

from typing import Any, Dict

from backend.app.api.routes.translate import TranslateRequest
from backend.app.services import paper_service

from .base import AgentSkill


class StartTranslationKernelSkill(AgentSkill):
    contract_slug = "start_translation_kernel"

    async def execute(self, arguments: Dict[str, Any], runtime_state) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        paper_id = str(arguments["paper_id"])
        try:
            detail = await paper_service.get_community_paper_detail(
                paper_id=paper_id,
                viewer_user_id=None,
                fast_path=True,
            )
            reader = detail.get("reader") if isinstance(detail, dict) else {}
            paper = detail.get("paper") if isinstance(detail, dict) else {}
            if isinstance(reader, dict) and reader.get("state") == "translated_ready":
                existing_task_id = paper.get("community_selected_task_id") if isinstance(paper, dict) else None
                return {
                    "paper_id": paper_id,
                    "task_id": existing_task_id,
                    "status": "translated_ready",
                    "reused_existing_task": True,
                    "processing_url": f"/processing?taskId={existing_task_id}" if existing_task_id else None,
                }
        except Exception:
            # Keep legacy behavior when prewarm-readiness lookup is temporarily unavailable.
            pass

        request = TranslateRequest(
            source_language=str(arguments.get("source_language") or "en"),
            target_language=str(arguments.get("target_language") or "zh"),
        )
        submitter_user_id = None
        if isinstance(getattr(runtime_state, "context", None), dict):
            submitter_user_id = runtime_state.context.get("user_id")

        kwargs: Dict[str, Any] = {
            "paper_id": paper_id,
            "request": request,
            "credentials": None,
        }
        if submitter_user_id:
            kwargs["submitter_user_id"] = str(submitter_user_id)

        return await paper_service.start_paper_translation(
            **kwargs,
        )
