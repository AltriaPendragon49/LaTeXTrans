from __future__ import annotations

from typing import Any, Dict

from backend.app.services import paper_service

from .base import AgentSkill


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


class ReadPaperContextSkill(AgentSkill):
    contract_slug = "read_paper_context"

    def is_visible(self, runtime_state) -> bool:  # type: ignore[no-untyped-def]
        return bool(runtime_state.paper_context or runtime_state.context.get("paper_id"))

    async def execute(self, arguments: Dict[str, Any], runtime_state) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        payload = await paper_service.get_community_paper_detail(
            paper_id=arguments["paper_id"],
            viewer_user_id=None,
            fast_path=True,
        )
        paper = payload.get("paper") if isinstance(payload, dict) else {}
        reader = payload.get("reader") if isinstance(payload, dict) else {}
        translated_reader = reader.get("translated") if isinstance(reader, dict) else {}
        reader_state = reader.get("state") if isinstance(reader, dict) else payload.get("reader_state")
        return {
            "paper_id": paper.get("id"),
            "title": _normalize_text(paper.get("title")),
            "arxiv_id": paper.get("arxiv_id"),
            "abstract_raw": _normalize_text(paper.get("abstract_raw")),
            "abstract_translated": _normalize_text(paper.get("abstract_translated")),
            "trans_status": paper.get("trans_status"),
            "reader_state": reader_state,
            "translated_ready": reader_state == "translated_ready" or bool(
                isinstance(translated_reader, dict)
                and translated_reader.get("kind") in {"preview_html", "translated_pdf"}
            ),
        }
