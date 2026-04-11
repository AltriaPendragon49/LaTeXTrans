from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

import httpx

from backend.app.core.config import settings

from ..language import is_chinese_language
from .base import AgentSkill

REASONING_PROVIDER_URL_ENV = "COMMUNITY_AGENT_REASONING_API_URL"
REASONING_PROVIDER_KEY_ENV = "COMMUNITY_AGENT_REASONING_API_KEY"
REASONING_PROVIDER_MODEL_ENV = "COMMUNITY_AGENT_REASONING_MODEL"


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_string_list(value: Any) -> List[str]:
    if isinstance(value, str):
        normalized = _normalize_text(value)
        return [normalized] if normalized else []
    if not isinstance(value, list):
        return []
    return [_normalize_text(item) for item in value if _normalize_text(item)]


def _resolve_chat_completions_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    normalized = raw_url.strip().rstrip("/")
    if not normalized:
        return None
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def _extract_json_object(raw_text: str) -> Dict[str, Any] | None:
    text = raw_text.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        return None


class ComposeAcademicAnswerSkill(AgentSkill):
    contract_slug = "compose_academic_answer"

    def _deterministic_slots(self, runtime_state, arguments: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        is_zh = is_chinese_language(arguments.get("answer_language") or runtime_state.response_language)
        citation_ids: List[str] = list(arguments.get("evidence_citation_ids") or [])
        citations = [
            runtime_state.citations_by_id[citation_id]
            for citation_id in citation_ids
            if citation_id in runtime_state.citations_by_id
        ]
        lead_title = citations[0]["title"] if citations else ("当前论文上下文" if is_zh else "the current paper context")
        intent = str(arguments.get("intent") or runtime_state.latest_intent or "answer")

        if intent == "translate" and runtime_state.action and runtime_state.action.get("task_id"):
            current_status = "已成功启动论文翻译任务。" if is_zh else "Translation has started successfully."
            next_steps = (
                ["打开论文阅读器，一边阅读一边等待翻译更新。"]
                if is_zh
                else ["Open the paper reader and keep reading while the translation updates."]
            )
        elif intent == "search":
            current_status = "我找到了与你问题相关的论文证据。" if is_zh else "I found paper evidence relevant to your request."
            next_steps = (
                ["打开最相关的论文，并与其他结果继续对比。"]
                if is_zh
                else ["Open the top paper and compare it with nearby results."]
            )
        else:
            current_status = (
                "我已经基于现有论文证据整理好回答。"
                if is_zh
                else "I prepared a grounded answer from the available paper evidence."
            )
            next_steps = (
                ["继续追问更具体的问题，或打开关联论文继续阅读。"]
                if is_zh
                else ["Ask a follow-up question or open the linked paper."]
            )

        return {
            "slots": {
                "current_status": current_status,
                "background_answer": (
                    f"当前回答基于现有论文证据整理，重点参考 {lead_title}。"
                    if is_zh
                    else f"This answer is grounded in the available evidence, led by {lead_title}."
                ),
                "paper_overview": runtime_state.paper_context.get("title") if runtime_state.paper_context else lead_title,
                "core_points": (
                    [
                        "仅使用当前已提供的论文证据。",
                        "回答范围保持在论文相关任务之内。",
                    ]
                    if is_zh
                    else [
                        "Uses the currently available paper evidence only.",
                        "Keeps the answer scoped to paper-related tasks.",
                    ]
                ),
                "next_steps": next_steps,
            },
            "citation_ids": citation_ids,
        }

    async def _call_generation_llm(self, runtime_state, arguments: Dict[str, Any]) -> Dict[str, Any] | None:  # type: ignore[no-untyped-def]
        provider_url = _resolve_chat_completions_url(
            os.getenv(REASONING_PROVIDER_URL_ENV) or settings.llm_base_url
        )
        provider_key = os.getenv(REASONING_PROVIDER_KEY_ENV) or settings.llm_api_key
        provider_model = os.getenv(REASONING_PROVIDER_MODEL_ENV) or settings.llm_model
        if not provider_url or not provider_key or not provider_model:
            return None

        citation_ids: List[str] = list(arguments.get("evidence_citation_ids") or [])
        citations = [
            runtime_state.citations_by_id[citation_id]
            for citation_id in citation_ids
            if citation_id in runtime_state.citations_by_id
        ]

        evidence = [
            {
                "id": citation.get("id"),
                "title": citation.get("title"),
                "snippet": citation.get("snippet"),
                "source": citation.get("source"),
                "url": citation.get("url"),
                "arxiv_id": citation.get("arxiv_id"),
                "paper_id": citation.get("paper_id"),
            }
            for citation in citations
        ]

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the grounded answer composer for the PaperX community paper agent. "
                    "Return strict JSON only. Use only the provided evidence. "
                    "Do not output markdown. Do not output a long-form summary. "
                    "Write every slot value in the requested answer_language so it matches the user's prompt language. "
                    "Return exactly {\"slots\": {...}, \"citation_ids\": [...]}."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "answer_language": arguments.get("answer_language") or runtime_state.response_language,
                        "intent": arguments.get("intent"),
                        "user_input": arguments.get("user_input"),
                        "history_summary": arguments.get("history_summary"),
                        "paper_context": arguments.get("paper_context"),
                        "action_context": arguments.get("action_context"),
                        "evidence": evidence,
                        "allowed_citation_ids": citation_ids,
                        "required_slots": [
                            "current_status",
                            "background_answer",
                            "paper_overview",
                            "core_points",
                            "next_steps",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        async with httpx.AsyncClient(timeout=max(float(settings.llm_timeout), 10.0)) as client:
            response = await client.post(
                provider_url,
                json={
                    "model": provider_model,
                    "messages": messages,
                    "temperature": 0.2,
                    "stream": False,
                },
                headers={
                    "Authorization": f"Bearer {provider_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices:
            return None

        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        payload = _extract_json_object(content) if isinstance(content, str) else None
        if not isinstance(payload, dict):
            return None

        slots = payload.get("slots")
        llm_citation_ids = payload.get("citation_ids")
        if not isinstance(slots, dict) or not isinstance(llm_citation_ids, list):
            return None

        required_slot_keys = {"current_status", "background_answer", "core_points", "next_steps"}
        if not required_slot_keys.issubset(slots):
            return None

        normalized_citation_ids = [citation_id for citation_id in llm_citation_ids if citation_id in citation_ids]
        if not normalized_citation_ids:
            normalized_citation_ids = citation_ids

        return {
            "slots": {
                "current_status": _normalize_text(slots.get("current_status")),
                "background_answer": _normalize_text(slots.get("background_answer")),
                "paper_overview": _normalize_text(slots.get("paper_overview")),
                "core_points": _normalize_string_list(slots.get("core_points")),
                "next_steps": _normalize_string_list(slots.get("next_steps")),
            },
            "citation_ids": normalized_citation_ids,
        }

    async def _generate_slots(self, runtime_state, arguments: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        generated = await self._call_generation_llm(runtime_state, arguments)
        if generated:
            return generated
        return self._deterministic_slots(runtime_state, arguments)

    async def execute(self, arguments: Dict[str, Any], runtime_state) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        return await self._generate_slots(runtime_state, arguments)
