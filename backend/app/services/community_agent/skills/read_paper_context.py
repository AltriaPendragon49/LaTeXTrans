from __future__ import annotations

from typing import Any, Dict

from backend.app.services import paper_service

from .base import AgentSkill


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _extract_anchor_ids(resource: Any) -> list[str]:
    if not isinstance(resource, dict):
        return []
    anchors = resource.get("anchors")
    if not isinstance(anchors, list):
        return []

    ids: list[str] = []
    for item in anchors:
        if not isinstance(item, dict):
            continue
        anchor_id = _normalize_text(item.get("anchor_id"))
        if anchor_id and anchor_id not in ids:
            ids.append(anchor_id)
    return ids


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
        source_reader = reader.get("source") if isinstance(reader, dict) else {}
        reader_state = reader.get("state") if isinstance(reader, dict) else payload.get("reader_state")
        translated_anchor_ids = _extract_anchor_ids(translated_reader)
        source_anchor_ids = _extract_anchor_ids(source_reader)
        active_anchor_id = _normalize_text(
            (reader.get("active_anchor_id") if isinstance(reader, dict) else None)
        )
        if not active_anchor_id:
            active_anchor_id = translated_anchor_ids[0] if translated_anchor_ids else (source_anchor_ids[0] if source_anchor_ids else "")

        return {
            "paper_id": paper.get("id"),
            "title": _normalize_text(paper.get("title")),
            "arxiv_id": paper.get("arxiv_id"),
            "abstract_raw": _normalize_text(paper.get("abstract_raw")),
            "abstract_translated": _normalize_text(paper.get("abstract_translated")),
            "trans_status": paper.get("trans_status"),
            "reader_state": reader_state,
            "active_anchor_id": active_anchor_id or None,
            "reader_anchor_ids": translated_anchor_ids + [anchor_id for anchor_id in source_anchor_ids if anchor_id not in translated_anchor_ids],
            "translated_ready": reader_state == "translated_ready" or bool(
                isinstance(translated_reader, dict)
                and translated_reader.get("kind") in {"preview_html", "translated_pdf"}
            ),
        }
