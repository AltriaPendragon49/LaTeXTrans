from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any, Dict, Iterable, List

import httpx

from backend.app.core.config import settings

from .language import detect_response_language, is_chinese_language
from .runtime import AgentRuntimeState
from .skills import ReadPaperContextSkill, instantiate_discovered_skills
from .validator import ValidationError, validate_skill_call

REASONING_PROVIDER_URL_ENV = "COMMUNITY_AGENT_REASONING_API_URL"
REASONING_PROVIDER_KEY_ENV = "COMMUNITY_AGENT_REASONING_API_KEY"
REASONING_PROVIDER_MODEL_ENV = "COMMUNITY_AGENT_REASONING_MODEL"

_SEARCH_MARKERS = ("search", "find", "look up", "papers", "论文", "搜索", "查找", "查一下")
_TRANSLATE_MARKERS = ("translate", "translation", "翻译", "译成", "中文版", "中文版本")


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_history(context: Dict[str, Any]) -> List[Dict[str, str]]:
    history = context.get("history")
    if not isinstance(history, list):
        return []
    normalized: List[Dict[str, str]] = []
    for entry in history[-8:]:
        if not isinstance(entry, dict):
            continue
        role = _normalize_text(entry.get("role")).lower()
        content = _normalize_text(entry.get("content"))
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content})
    return normalized


def _extract_arxiv_id(input_text: str) -> str | None:
    text = input_text.strip()
    url_match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", text, re.IGNORECASE)
    if url_match:
        return url_match.group(1)
    id_match = re.search(r"(?<![0-9A-Za-z_])(\d{4}\.\d{4,5})(?:v\d+)?(?![0-9A-Za-z_])", text)
    return id_match.group(1) if id_match else None


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


def _make_trace(kind: str, label: str, provider: str, status: str, detail: str | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "id": f"trace-{uuid.uuid4().hex[:8]}",
        "kind": kind,
        "label": label,
        "provider": provider,
        "status": status,
    }
    if detail:
        payload["detail"] = detail
    return payload


def _make_event(event_type: str, **data: Any) -> Dict[str, Any]:
    return {"type": event_type, "data": data}


def _dedupe_citations(citations: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for citation in citations:
        key = (
            _normalize_text(citation.get("paper_id"))
            or _normalize_text(citation.get("arxiv_id"))
            or _normalize_text(citation.get("url"))
            or _normalize_text(citation.get("title"))
        )
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


def _derive_search_query(input_text: str) -> str:
    text = _normalize_text(input_text)
    if not text:
        return ""

    arxiv_id = _extract_arxiv_id(text)
    if arxiv_id:
        return arxiv_id

    quoted_title = re.search(r"['\"]([^'\"]+)['\"]", text)
    if quoted_title:
        candidate = _normalize_text(quoted_title.group(1))
        if candidate:
            return candidate

    candidate = re.sub(r"\(arxiv:\s*\d{4}\.\d{4,5}(?:v\d+)?\)", "", text, flags=re.IGNORECASE)
    candidate = re.sub(
        r"^(please\s+)?(tell me about|what is|what's|summarize|explain|search(?: the web)? for|find|look up)\s+",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(r"^(请帮我|请)?(解释|总结|概述|查找|搜索)\s*", "", candidate)
    candidate = re.sub(r"\s+(about|this paper)\??$", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\?$", "", candidate)
    candidate = _normalize_text(candidate)
    return candidate or text


def _has_any_marker(text: str, markers: Iterable[str]) -> bool:
    normalized = text.lower()
    return any(marker in normalized for marker in markers)


def _parse_tool_arguments(raw_arguments: Any) -> Dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not isinstance(raw_arguments, str):
        return {}
    try:
        payload = json.loads(raw_arguments)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def _context_citation(paper_context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": paper_context.get("paper_id") or f"context-{uuid.uuid4().hex[:8]}",
        "title": paper_context.get("title") or "Current paper",
        "url": f"/paper/{paper_context.get('paper_id')}" if paper_context.get("paper_id") else None,
        "source": "community",
        "arxiv_id": paper_context.get("arxiv_id"),
        "paper_id": paper_context.get("paper_id"),
        "snippet": paper_context.get("abstract_translated") or paper_context.get("abstract_raw"),
    }


async def _call_chat_completion(*, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    provider_url = _resolve_chat_completions_url(os.getenv(REASONING_PROVIDER_URL_ENV) or settings.llm_base_url)
    provider_key = os.getenv(REASONING_PROVIDER_KEY_ENV) or settings.llm_api_key
    provider_model = os.getenv(REASONING_PROVIDER_MODEL_ENV) or settings.llm_model
    if not provider_url or not provider_key or not provider_model:
        return None

    async with httpx.AsyncClient(timeout=max(float(settings.llm_timeout), 10.0)) as client:
        response = await client.post(
            provider_url,
            json={
                "model": provider_model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
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
    if not isinstance(message, dict):
        return None

    tool_calls = message.get("tool_calls")
    return {
        "role": "assistant",
        "content": message.get("content") if isinstance(message.get("content"), str) else "",
        "tool_calls": tool_calls if isinstance(tool_calls, list) else [],
    }


class SkillRegistry:
    def __init__(self) -> None:
        self._skills = instantiate_discovered_skills()

    def visible_skills(self, runtime_state: AgentRuntimeState) -> Dict[str, Any]:
        return {
            skill.name: skill
            for skill in self._skills
            if skill.name != "compose_academic_answer" and skill.is_visible(runtime_state)
        }


def _serialize_visible_tools(skills: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": skill.name,
                "description": skill.description,
                "parameters": skill.input_schema(),
            },
        }
        for skill in skills.values()
    ]


def _infer_intent(runtime_state: AgentRuntimeState) -> str:
    text = runtime_state.input_text.lower()
    executed = [item.get("skill_name") for item in runtime_state.executed_skill_results]
    if "start_translation_kernel" in executed or _has_any_marker(text, _TRANSLATE_MARKERS):
        return "translate"
    if any(name in {"community_search_papers", "external_tavily_search"} for name in executed):
        return "search"
    if _has_any_marker(text, _SEARCH_MARKERS) and not runtime_state.paper_context:
        return "search"
    return "answer"


def _build_system_prompt(runtime_state: AgentRuntimeState, visible_skills: Dict[str, Any]) -> str:
    tool_names = ", ".join(visible_skills) or "none"
    return (
        "You are LaTeXTrans Paper Copilot, a conversational research-paper assistant. "
        f"Answer naturally in {runtime_state.response_language}. "
        "You may respond directly when no tool is needed, or call tools when they improve correctness or complete a paper-domain action. "
        "Prefer current paper context and internal community paper search before external web search. "
        "If the user references an arXiv id and the paper is missing, import it and read the paper context before answering. "
        "If the user asks for translation or translated reading support and the paper is not translated yet, start the translation kernel. "
        "Do not fabricate citations, paper metadata, or tool results. "
        f"Available tools this turn: {tool_names}."
    )


def _build_initial_messages(runtime_state: AgentRuntimeState, visible_skills: Dict[str, Any]) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": _build_system_prompt(runtime_state, visible_skills)},
        {
            "role": "system",
            "content": json.dumps(
                {
                    "answer_language": runtime_state.response_language,
                    "current_paper_context": runtime_state.paper_context,
                    "known_citations": _dedupe_citations(runtime_state.citations)[:4],
                    "skill_toggles": runtime_state.skill_toggles,
                },
                ensure_ascii=False,
            ),
        },
    ]
    messages.extend(runtime_state.history)
    messages.append({"role": "user", "content": runtime_state.input_text})
    return messages


def _finalize_payload(runtime_state: AgentRuntimeState, message: str) -> Dict[str, Any]:
    intent = _infer_intent(runtime_state)
    citations = _dedupe_citations(runtime_state.citations)
    runtime_state.latest_intent = intent
    runtime_state.events.append(_make_event("final", summary=message, action=runtime_state.action))
    return {
        "status": "completed",
        "intent": intent,
        "message": message,
        "summary": message,
        "tool_trace": runtime_state.tool_trace,
        "citations": citations,
        "provider_state": runtime_state.provider_state,
        "action": runtime_state.action,
        "events": runtime_state.events,
    }


def _fallback_message(runtime_state: AgentRuntimeState) -> str:
    is_zh = is_chinese_language(runtime_state.response_language)
    title = _normalize_text((runtime_state.paper_context or {}).get("title"))
    snippet = _normalize_text(
        (runtime_state.paper_context or {}).get("abstract_translated")
        or (runtime_state.paper_context or {}).get("abstract_raw")
    )
    lead = runtime_state.citations[0] if runtime_state.citations else None
    lead_title = _normalize_text((lead or {}).get("title"))
    lead_snippet = _normalize_text((lead or {}).get("snippet"))

    if runtime_state.action and runtime_state.action.get("task_id"):
        paper_label = title or lead_title or ("这篇论文" if is_zh else "this paper")
        if is_zh:
            return f"我已经为《{paper_label}》启动翻译流程。你现在可以打开论文阅读器，一边阅读一边等待翻译更新。"
        return f"I started translation for {paper_label}. You can open the paper reader now and keep reading while the translation updates."

    if title:
        if is_zh:
            return (
                f"《{title}》是当前最相关的论文。"
                + (f" {snippet}" if snippet else "")
                + " 如果你愿意，我可以继续解释方法、实验结果或相关工作。"
            )
        return (
            f"{title} is the most relevant paper in the current context."
            + (f" {snippet}" if snippet else "")
            + " I can keep going into the method, results, or related work if you want."
        )

    if lead_title:
        if is_zh:
            return f"我目前找到的最相关论文是《{lead_title}》。{lead_snippet or '如果你愿意，我可以继续展开讲解。'}"
        return f"The most relevant paper I found is {lead_title}. {lead_snippet or 'I can expand on it further if you want.'}"

    if is_zh:
        return "我暂时还没有拿到足够的论文证据。请提供更具体的论文标题、arXiv 编号，或启用外部搜索后重试。"
    return "I do not have enough paper evidence yet. Please provide a more specific paper title, an arXiv id, or enable external search and try again."


class CommunityReactAgent:
    def __init__(self, input_text: str, context: Dict[str, Any] | None = None, skill_toggles: Dict[str, Any] | None = None) -> None:
        safe_context = dict(context or {})
        history = _normalize_history(safe_context)
        self.runtime_state = AgentRuntimeState(
            input_text=_normalize_text(input_text),
            context=safe_context,
            skill_toggles=dict(skill_toggles or {}),
            provider_state={
                "internal_search": "enabled",
                "external_search": "disabled_by_user" if not (skill_toggles or {}).get("external_search") else "unknown",
                "reasoning": "enabled" if _resolve_chat_completions_url(os.getenv(REASONING_PROVIDER_URL_ENV) or settings.llm_base_url) else "fallback",
                "translation_bridge": "enabled",
            },
            response_language=detect_response_language(_normalize_text(input_text), history=history, context=safe_context),
            history=history,
        )
        self.registry = SkillRegistry()
        self.runtime_state.events.append(_make_event("thinking", provider="conversational_runtime"))

    async def _bootstrap_paper_context(self) -> None:
        paper_id = self.runtime_state.context.get("paper_id")
        if not paper_id:
            return
        try:
            paper_context = await ReadPaperContextSkill().execute({"paper_id": paper_id}, self.runtime_state)
            self.runtime_state.paper_context = paper_context
            self.runtime_state.add_citations([_context_citation(paper_context)])
            self.runtime_state.executed_skill_results.append(
                {"skill_name": "read_paper_context", "arguments": {"paper_id": paper_id}, "result": paper_context}
            )
            self.runtime_state.tool_trace.append(
                _make_trace("context", "Current paper context", "read_paper_context", "completed", paper_context.get("title") or paper_id)
            )
        except Exception:
            self.runtime_state.paper_context = None

    def _merge_skill_result(self, skill_name: str, result: Dict[str, Any]) -> None:
        if skill_name == "community_search_papers":
            self.runtime_state.add_citations(result.get("results") or [])
        elif skill_name == "external_tavily_search":
            self.runtime_state.provider_state["external_search"] = "tavily"
            self.runtime_state.add_citations(result.get("results") or [])
        elif skill_name == "read_paper_context":
            self.runtime_state.paper_context = result
            if result.get("paper_id"):
                self.runtime_state.add_citations([_context_citation(result)])
                if not self.runtime_state.action:
                    self.runtime_state.action = {"type": "navigate_paper", "paper_id": result.get("paper_id")}
        elif skill_name == "import_arxiv_paper":
            paper_id = result.get("paper_id")
            if paper_id:
                self.runtime_state.context["paper_id"] = paper_id
            if paper_id and not self.runtime_state.action:
                self.runtime_state.action = {
                    "type": "navigate_paper",
                    "paper_id": paper_id,
                    "imported": bool(result.get("imported")),
                    "reused": bool(result.get("reused")),
                }
        elif skill_name == "start_translation_kernel":
            self.runtime_state.action = {
                "type": "navigate_paper",
                "paper_id": result.get("paper_id"),
                "task_id": result.get("task_id"),
                "auto_started_translation": bool(result.get("task_id")),
            }

    async def _execute_tool_call(
        self,
        *,
        tool_call: Dict[str, Any],
        visible_skills: Dict[str, Any],
    ) -> tuple[bool, Dict[str, Any]]:
        function = tool_call.get("function") if isinstance(tool_call, dict) else {}
        skill_name = _normalize_text(function.get("name")) if isinstance(function, dict) else ""
        arguments = _parse_tool_arguments(function.get("arguments") if isinstance(function, dict) else None)

        try:
            validate_skill_call(
                skill_name=skill_name,
                arguments=arguments,
                raw_input=self.runtime_state.input_text,
                visible_skill_names=set(visible_skills),
            )
            skill = visible_skills[skill_name]
            self.runtime_state.events.append(_make_event("tool_start", tool=skill.name, arguments=arguments))
            self.runtime_state.tool_trace.append(
                _make_trace(skill.trace_kind, skill.trace_label, skill.name, "running")
            )
            result = await skill.execute(arguments, self.runtime_state)
            self.runtime_state.executed_skill_results.append(
                {"skill_name": skill.name, "arguments": arguments, "result": result}
            )
            self._merge_skill_result(skill.name, result)
            self.runtime_state.events.append(_make_event("tool_result", tool=skill.name, result=result))
            self.runtime_state.tool_trace.append(
                _make_trace(skill.trace_kind, skill.trace_label, skill.name, "completed")
            )
            return True, result
        except ValidationError as exc:
            error_detail = str(exc)
            self.runtime_state.tool_trace.append(
                _make_trace("validation", "Tool validator", skill_name or "unknown_tool", "failed", error_detail)
            )
        except Exception as exc:
            error_detail = str(exc)
            self.runtime_state.tool_trace.append(
                _make_trace("validation", "Tool execution", skill_name or "unknown_tool", "failed", error_detail)
            )

        error_payload = {"error": error_detail, "tool": skill_name or "unknown_tool"}
        self.runtime_state.events.append(_make_event("error", **error_payload))
        if self.runtime_state.repair_count >= 1:
            return False, error_payload
        self.runtime_state.repair_count += 1
        return True, error_payload

    async def _run_conversational_loop(self) -> str | None:
        visible_skills = self.registry.visible_skills(self.runtime_state)
        messages = _build_initial_messages(self.runtime_state, visible_skills)

        for _ in range(6):
            visible_skills = self.registry.visible_skills(self.runtime_state)
            response = await _call_chat_completion(messages=messages, tools=_serialize_visible_tools(visible_skills))
            if not response:
                return None

            content = _normalize_text(response.get("content"))
            tool_calls = response.get("tool_calls") if isinstance(response.get("tool_calls"), list) else []

            if not tool_calls and content:
                return content

            if not tool_calls:
                return None

            messages.append(
                {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                }
            )

            for tool_call in tool_calls:
                should_continue, result = await self._execute_tool_call(tool_call=tool_call, visible_skills=visible_skills)
                tool_call_id = _normalize_text(tool_call.get("id")) or f"call-{uuid.uuid4().hex[:8]}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
                if not should_continue:
                    return None

        return None

    async def _run_fallback(self) -> Dict[str, Any]:
        visible_skills = self.registry.visible_skills(self.runtime_state)
        arxiv_id = _extract_arxiv_id(self.runtime_state.input_text)

        if arxiv_id and "import_arxiv_paper" in visible_skills and not self.runtime_state.paper_context:
            should_continue, result = await self._execute_tool_call(
                tool_call={
                    "id": "fallback-import",
                    "function": {"name": "import_arxiv_paper", "arguments": json.dumps({"arxiv_id": arxiv_id})},
                },
                visible_skills=visible_skills,
            )
            if should_continue and result.get("paper_id") and "read_paper_context" in self.registry.visible_skills(self.runtime_state):
                visible_after_import = self.registry.visible_skills(self.runtime_state)
                await self._execute_tool_call(
                    tool_call={
                        "id": "fallback-read-context",
                        "function": {
                            "name": "read_paper_context",
                            "arguments": json.dumps({"paper_id": result["paper_id"]}),
                        },
                    },
                    visible_skills=visible_after_import,
                )

        visible_skills = self.registry.visible_skills(self.runtime_state)
        needs_translation = (
            self.runtime_state.paper_context
            and (
                _has_any_marker(self.runtime_state.input_text, _TRANSLATE_MARKERS)
                or (is_chinese_language(self.runtime_state.response_language) and not self.runtime_state.paper_context.get("translated_ready"))
            )
            and not self.runtime_state.paper_context.get("translated_ready")
            and "start_translation_kernel" in visible_skills
        )
        if needs_translation and self.runtime_state.paper_context and self.runtime_state.paper_context.get("paper_id"):
            await self._execute_tool_call(
                tool_call={
                    "id": "fallback-translate",
                    "function": {
                        "name": "start_translation_kernel",
                        "arguments": json.dumps(
                            {
                                "paper_id": self.runtime_state.paper_context["paper_id"],
                                "source_language": "en",
                                "target_language": "zh",
                            }
                        ),
                    },
                },
                visible_skills=visible_skills,
            )

        visible_skills = self.registry.visible_skills(self.runtime_state)
        if not self.runtime_state.paper_context and not self.runtime_state.citations and "community_search_papers" in visible_skills:
            await self._execute_tool_call(
                tool_call={
                    "id": "fallback-search",
                    "function": {
                        "name": "community_search_papers",
                        "arguments": json.dumps({"query": _derive_search_query(self.runtime_state.input_text), "limit": 4}),
                    },
                },
                visible_skills=visible_skills,
            )

        self.runtime_state.tool_trace.append(
            _make_trace(
                "validation",
                "Conversational runtime",
                "fallback",
                "fallback",
                "Using deterministic paper-aware fallback reply",
            )
        )
        return _finalize_payload(self.runtime_state, _fallback_message(self.runtime_state))

    async def run(self) -> Dict[str, Any]:
        await self._bootstrap_paper_context()

        try:
            final_message = await self._run_conversational_loop()
            if final_message:
                return _finalize_payload(self.runtime_state, final_message)
        except Exception as exc:
            self.runtime_state.tool_trace.append(
                _make_trace("validation", "Conversational runtime", "runtime", "failed", str(exc))
            )

        return await self._run_fallback()


async def run_agent(input_text: str, context: Dict[str, Any] | None = None, skill_toggles: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return await CommunityReactAgent(input_text=input_text, context=context, skill_toggles=skill_toggles).run()
