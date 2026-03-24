from __future__ import annotations

import importlib
import inspect
from functools import lru_cache
from pathlib import Path
from typing import List, Type

from .base import AgentSkill
from .community_search import CommunitySearchPapersSkill as CommunitySearchPapersImplementation
from .compose_academic_answer import ComposeAcademicAnswerSkill as ComposeAcademicAnswerImplementation
from .external_tavily_search import ExternalTavilySearchSkill as ExternalTavilySearchImplementation
from .import_arxiv_paper import ImportArxivPaperSkill as ImportArxivPaperImplementation
from .read_paper_context import ReadPaperContextSkill as ReadPaperContextImplementation
from .start_translation_kernel import StartTranslationKernelSkill as StartTranslationKernelImplementation
from .contracts.community_search_papers import CommunitySearchPapersSkill
from .contracts.compose_academic_answer import ComposeAcademicAnswerSkill
from .contracts.external_tavily_search import ExternalTavilySearchSkill
from .contracts.import_arxiv_paper import ImportArxivPaperSkill
from .contracts.read_paper_context import ReadPaperContextSkill
from .contracts.start_translation_kernel import StartTranslationKernelSkill

_SKILL_CONTRACTS_ROOT = Path(__file__).resolve().parent / "contracts"


@lru_cache(maxsize=1)
def discover_skill_types() -> List[Type[AgentSkill]]:
    discovered: List[Type[AgentSkill]] = []
    for skill_dir in sorted(_SKILL_CONTRACTS_ROOT.iterdir(), key=lambda path: path.name):
        if not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").exists() or not (skill_dir / "executor.py").exists():
            continue

        module_name = f"{__name__}.contracts.{skill_dir.name}.executor"
        module = importlib.import_module(module_name)
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate is AgentSkill or not issubclass(candidate, AgentSkill):
                continue
            if candidate.__module__ != module.__name__:
                continue
            discovered.append(candidate)
    return discovered


def instantiate_discovered_skills() -> List[AgentSkill]:
    return [skill_type() for skill_type in discover_skill_types()]


__all__ = [
    "AgentSkill",
    "CommunitySearchPapersSkill",
    "ComposeAcademicAnswerSkill",
    "ExternalTavilySearchSkill",
    "ImportArxivPaperSkill",
    "ReadPaperContextSkill",
    "StartTranslationKernelSkill",
    "CommunitySearchPapersImplementation",
    "ComposeAcademicAnswerImplementation",
    "ExternalTavilySearchImplementation",
    "ImportArxivPaperImplementation",
    "ReadPaperContextImplementation",
    "StartTranslationKernelImplementation",
    "discover_skill_types",
    "instantiate_discovered_skills",
]
