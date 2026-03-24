from __future__ import annotations

from typing import Any, Dict

from backend.app.services import paper_service

from .base import AgentSkill


class ImportArxivPaperSkill(AgentSkill):
    contract_slug = "import_arxiv_paper"

    async def execute(self, arguments: Dict[str, Any], runtime_state) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        return await paper_service.import_or_reuse_paper(source="arxiv", arxiv_id=arguments["arxiv_id"])
