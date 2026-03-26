from backend.app.services.community_agent.runtime import AgentRuntimeState
from backend.app.services.community_agent.skills_runtime import build_skill_prompt_bundle
from backend.app.services.community_agent.tools import ToolRegistry


def _runtime_state(*, paper_id: str | None = None, external_search: bool = False) -> AgentRuntimeState:
    context = {"source": "conversation"}
    if paper_id:
        context["paper_id"] = paper_id

    return AgentRuntimeState(
        input_text="Explain the paper in Chinese",
        context=context,
        skill_toggles={"external_search": external_search},
        provider_state={
            "internal_search": "enabled",
            "external_search": "disabled_by_user",
            "reasoning": "enabled",
            "translation_bridge": "enabled",
        },
        response_language="zh",
    )


def test_prompt_skill_bundle_selects_runtime_visible_skill_packs() -> None:
    bundle_without_paper = build_skill_prompt_bundle(_runtime_state())
    assert "community_search_papers" in bundle_without_paper.skill_names
    assert "external_tavily_search" not in bundle_without_paper.skill_names
    assert "start_translation_kernel" not in bundle_without_paper.skill_names

    bundle_with_paper = build_skill_prompt_bundle(_runtime_state(paper_id="paper-1", external_search=True))
    assert "community_search_papers" in bundle_with_paper.skill_names
    assert "external_tavily_search" in bundle_with_paper.skill_names
    assert "read_paper_context" in bundle_with_paper.skill_names
    assert "start_translation_kernel" in bundle_with_paper.skill_names
    assert "Use this skill for internal paper retrieval" in bundle_with_paper.prompt_markdown


def test_tool_registry_keeps_executable_tools_separate_from_prompt_skills() -> None:
    registry = ToolRegistry()
    visible_tools = registry.visible_tools(_runtime_state(paper_id="paper-1", external_search=True))

    assert "community_search_papers" in visible_tools
    assert "external_tavily_search" in visible_tools
    assert "read_paper_context" in visible_tools
    assert "start_translation_kernel" in visible_tools
    assert "compose_academic_answer" not in visible_tools
