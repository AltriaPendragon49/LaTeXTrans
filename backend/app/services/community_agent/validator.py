from __future__ import annotations

import re
from typing import Any, Dict, Set


class ValidationError(ValueError):
    pass


_FILLER_PATTERNS = (
    "please search",
    "search the web",
    "find papers about",
    "i want you to search",
    "帮我查一下",
    "请帮我查",
    "请搜索",
)

_TIME_RANGE_HINTS = (
    "today",
    "yesterday",
    "this week",
    "last week",
    "this month",
    "last month",
    "this year",
    "last year",
    "recent",
    "过去一天",
    "过去一周",
    "过去一个月",
    "过去一年",
    "最近",
)

_DOMAIN_PATTERN = re.compile(r"(?:site:)?([a-z0-9-]+\.[a-z]{2,})(?:/[^\s]*)?", re.IGNORECASE)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _extract_domains(text: str) -> Set[str]:
    return {match.group(1).lower() for match in _DOMAIN_PATTERN.finditer(text)}


def _mentions_time_constraint(text: str) -> bool:
    normalized = text.lower()
    return any(marker in normalized for marker in _TIME_RANGE_HINTS)


def validate_search_query(
    *,
    raw_input: str,
    query: str,
    arguments: Dict[str, Any] | None = None,
    require_constraint_capture: bool = False,
) -> None:
    normalized_input = _normalize_text(raw_input).lower()
    normalized_query = _normalize_text(query).lower()
    normalized_arguments = arguments or {}

    if not normalized_query:
        raise ValidationError("search query is required")

    if normalized_query == normalized_input:
        if any(pattern in normalized_query for pattern in _FILLER_PATTERNS):
            raise ValidationError("search query copied the raw conversational utterance")
        if len(re.findall(r"\w+|[\u4e00-\u9fff]", normalized_query)) >= 8:
            raise ValidationError("search query is too close to the raw utterance")

    if not require_constraint_capture:
        return

    explicit_domains = _extract_domains(normalized_input)
    include_domains = {str(item).lower() for item in normalized_arguments.get("include_domains") or []}
    exclude_domains = {str(item).lower() for item in normalized_arguments.get("exclude_domains") or []}
    if explicit_domains and not (explicit_domains & (include_domains | exclude_domains)):
        raise ValidationError("search query omitted explicit domain constraints from the user request")

    if _mentions_time_constraint(normalized_input) and not normalized_arguments.get("time_range"):
        raise ValidationError("search query omitted an explicit time constraint from the user request")


def _collect_known_paper_ids(runtime_state: Any) -> Set[str]:
    known_paper_ids: Set[str] = set()
    paper_context = getattr(runtime_state, "paper_context", None)
    if isinstance(paper_context, dict) and paper_context.get("paper_id"):
        known_paper_ids.add(str(paper_context["paper_id"]))

    for citation in getattr(runtime_state, "citations", []) or []:
        if isinstance(citation, dict) and citation.get("paper_id"):
            known_paper_ids.add(str(citation["paper_id"]))

    for entry in getattr(runtime_state, "executed_skill_results", []) or []:
        if not isinstance(entry, dict):
            continue
        result = entry.get("result")
        if isinstance(result, dict) and result.get("paper_id"):
            known_paper_ids.add(str(result["paper_id"]))

    return known_paper_ids


def validate_skill_call(
    *,
    skill_name: str,
    arguments: Dict[str, Any],
    raw_input: str,
    visible_skill_names: Set[str],
) -> None:
    if skill_name not in visible_skill_names:
        raise ValidationError(f"skill '{skill_name}' is not visible")

    if skill_name == "community_search_papers":
        validate_search_query(raw_input=raw_input, query=str(arguments.get("query") or ""))
    elif skill_name == "external_tavily_search":
        validate_search_query(
            raw_input=raw_input,
            query=str(arguments.get("query") or ""),
            arguments=arguments,
            require_constraint_capture=True,
        )


def validate_finalize_payload(
    payload: Dict[str, Any],
    *,
    runtime_state: Any,
    visible_skill_names: Set[str],
) -> None:
    if payload.get("summary"):
        raise ValidationError("finalize payload must not contain raw summary text")

    slots = payload.get("slots")
    if not isinstance(slots, dict):
        raise ValidationError("finalize payload must contain slots")

    for key in ("current_status", "background_answer", "core_points", "next_steps"):
        if key not in slots:
            raise ValidationError(f"missing slot '{key}'")

    if runtime_state is not None:
        generated_slots = getattr(runtime_state, "generated_slots", None)
        if not generated_slots:
            raise ValidationError("finalize requires a prior compose_academic_answer result")
        if slots != generated_slots:
            raise ValidationError("finalize slots are inconsistent with compose_academic_answer output")

    citation_ids = payload.get("citation_ids") or []
    known_citations = getattr(runtime_state, "citations_by_id", {}) if runtime_state is not None else {}
    for citation_id in citation_ids:
        if citation_id not in known_citations:
            raise ValidationError(f"unknown citation id '{citation_id}'")

    if runtime_state is not None:
        generated_citation_ids = list(getattr(runtime_state, "generated_citation_ids", []) or [])
        if generated_citation_ids and citation_ids != generated_citation_ids:
            raise ValidationError("finalize citation ids are inconsistent with compose_academic_answer output")

    action = payload.get("action")
    intent = payload.get("intent")
    if action:
        if action.get("type") == "navigate_paper" and not action.get("paper_id"):
            raise ValidationError("navigate_paper requires paper_id")

        known_paper_ids = _collect_known_paper_ids(runtime_state) if runtime_state is not None else set()
        action_paper_id = action.get("paper_id")
        if action_paper_id and known_paper_ids and str(action_paper_id) not in known_paper_ids:
            raise ValidationError("action paper_id is inconsistent with executed skill results")

        if intent == "translate":
            executed = list(getattr(runtime_state, "executed_skill_results", []) or [])
            translation_results = [
                item for item in executed if item.get("skill_name") == "start_translation_kernel"
            ]
            if not translation_results:
                raise ValidationError("translate finalize requires a successful translation skill result")
            task_id = action.get("task_id")
            if task_id and task_id not in {
                str(item.get("result", {}).get("task_id") or "") for item in translation_results
            }:
                raise ValidationError("translation action task_id is inconsistent with executed skill results")
        elif action.get("task_id") or action.get("auto_started_translation"):
            raise ValidationError("non-translate finalize cannot emit translation task actions")

    if runtime_state is not None:
        executed_skills = list(getattr(runtime_state, "executed_skill_results", []) or [])
        used_external_search = any(item.get("skill_name") == "external_tavily_search" for item in executed_skills)
        cited_external_sources = any(
            str(known_citations.get(citation_id, {}).get("source") or "").lower() == "tavily"
            for citation_id in citation_ids
        )
        if cited_external_sources and not used_external_search:
            raise ValidationError("finalize cites external-network evidence without an executed Tavily search")
        if cited_external_sources and "external_tavily_search" not in visible_skill_names:
            raise ValidationError("finalize cites external-network evidence while external search is hidden")
