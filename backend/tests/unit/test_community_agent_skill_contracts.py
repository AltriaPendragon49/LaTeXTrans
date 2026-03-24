from backend.app.services.community_agent.skills import (
    CommunitySearchPapersSkill,
    ComposeAcademicAnswerSkill,
    ExternalTavilySearchSkill,
    discover_skill_types,
)


def test_skill_contracts_are_loaded_from_markdown() -> None:
    skill = CommunitySearchPapersSkill()

    serialized = skill.serialize_for_planner()

    assert serialized["name"] == "community_search_papers"
    assert serialized["description"] == "Search existing community papers using a normalized academic query."
    assert serialized["input_schema"]["properties"]["query"]["type"] == "string"
    assert serialized["trace"]["kind"] == "search"
    assert serialized["source"].endswith("community_search_papers\\SKILL.md") or serialized["source"].endswith(
        "community_search_papers/SKILL.md"
    )


def test_external_search_contract_exposes_visibility_toggle() -> None:
    serialized = ExternalTavilySearchSkill().serialize_for_planner()

    assert serialized["visibility"]["type"] == "toggle"
    assert serialized["visibility"]["toggle"] == "external_search"
    assert "extracting search strategy" in serialized["planner_notes"].lower()


def test_compose_skill_contract_exposes_slot_output_shape() -> None:
    serialized = ComposeAcademicAnswerSkill().serialize_for_planner()

    slots = serialized["output_schema"]["properties"]["slots"]["properties"]
    assert "current_status" in slots
    assert "background_answer" in slots
    assert "next_steps" in slots


def test_discovery_scans_contract_skill_packages() -> None:
    discovered = {skill_type().name for skill_type in discover_skill_types()}

    assert "community_search_papers" in discovered
    assert "external_tavily_search" in discovered
    assert "compose_academic_answer" in discovered
