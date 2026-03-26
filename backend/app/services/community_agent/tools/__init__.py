from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

from .base import CommunityAgentTool
from .community_search import CommunitySearchPapersTool
from .external_tavily_search import ExternalTavilySearchTool
from .import_arxiv_paper import ImportArxivPaperTool
from .read_paper_context import ReadPaperContextTool
from .start_translation_kernel import StartTranslationKernelTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools = instantiate_tools()

    def visible_tools(self, runtime_state) -> Dict[str, CommunityAgentTool]:  # type: ignore[no-untyped-def]
        return {
            tool.name: tool
            for tool in self._tools
            if tool.is_visible(runtime_state)
        }


@lru_cache(maxsize=1)
def instantiate_tools() -> List[CommunityAgentTool]:
    return [
        CommunitySearchPapersTool(),
        ExternalTavilySearchTool(),
        ImportArxivPaperTool(),
        ReadPaperContextTool(),
        StartTranslationKernelTool(),
    ]


__all__ = [
    "CommunityAgentTool",
    "CommunitySearchPapersTool",
    "ExternalTavilySearchTool",
    "ImportArxivPaperTool",
    "ReadPaperContextTool",
    "StartTranslationKernelTool",
    "ToolRegistry",
    "instantiate_tools",
]
