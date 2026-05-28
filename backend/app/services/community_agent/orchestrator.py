from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import uuid
import xml.etree.ElementTree as ET
from typing import Any, Awaitable, Callable, Dict, Iterable, List

import httpx

from backend.app.core.config import settings

from .language import detect_response_language, is_chinese_language
from .runtime import AgentRuntimeState
from .skills.read_paper_context import ReadPaperContextSkill
from .skills_runtime import build_skill_prompt_bundle
from .tools import ToolRegistry
from .validator import ValidationError, validate_skill_call

REASONING_PROVIDER_URL_ENV = "COMMUNITY_AGENT_REASONING_API_URL"
REASONING_PROVIDER_KEY_ENV = "COMMUNITY_AGENT_REASONING_API_KEY"
REASONING_PROVIDER_MODEL_ENV = "COMMUNITY_AGENT_REASONING_MODEL"

_SEARCH_MARKERS = ("search", "find", "look up", "paper", "papers", "论文", "搜索", "查找", "找一下")
_TRANSLATE_MARKERS = ("translate", "translation", "翻译", "译成", "中文版", "中文版本")
_MAX_PLANNER_TURNS = 6
_DEEP_RESEARCH_MIN_EVIDENCE = 15
_DEEP_RESEARCH_TARGET_EVIDENCE = 18
_DEEP_RESEARCH_MAX_EVIDENCE = 20
_DEEP_RESEARCH_PER_QUERY_LIMIT = 5
_DEEP_RESEARCH_MAX_QUERY_ROUNDS = 4
_DEEP_RESEARCH_TIMEOUT_SECONDS = 120.0
_REASONING_MAX_RETRIES = 2
_REASONING_RETRY_BASE_SECONDS = 0.8
_REASONING_RETRY_MAX_SECONDS = 4.0
_RETRYABLE_REASONING_STATUS_CODES = {403, 408, 409, 425, 429, 500, 502, 503, 504}

EventCallback = Callable[[Dict[str, Any]], Awaitable[None] | None]


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


def _normalize_reader_selection(context: Dict[str, Any]) -> Dict[str, str] | None:
    payload = context.get("reader_selection")
    if not isinstance(payload, dict):
        return None

    text = _normalize_text(payload.get("text"))
    if not text:
        return None

    normalized: Dict[str, str] = {"text": text[:4000]}
    anchor_id = _normalize_text(payload.get("anchor_id"))
    mode = _normalize_text(payload.get("mode"))
    note = _normalize_text(payload.get("note"))
    if anchor_id:
        normalized["anchor_id"] = anchor_id
    if mode:
        normalized["mode"] = mode
    if note:
        normalized["note"] = note[:2000]
    return normalized


def _extract_arxiv_id(input_text: str) -> str | None:
    text = input_text.strip()
    url_match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", text, re.IGNORECASE)
    if url_match:
        return url_match.group(1)
    id_match = re.search(r"(?<![0-9A-Za-z_])(\d{4}\.\d{4,5})(?:v\d+)?(?![0-9A-Za-z_])", text)
    return id_match.group(1) if id_match else None


def _normalized_title_tokens(value: str) -> List[str]:
    normalized = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", value.lower())
    return [token for token in normalized.split() if token]


def _title_similarity_score(query: str, candidate_title: str) -> float:
    query_tokens = _normalized_title_tokens(query)
    candidate_tokens = _normalized_title_tokens(candidate_title)
    if not query_tokens or not candidate_tokens:
        return 0.0

    query_text = " ".join(query_tokens)
    candidate_text = " ".join(candidate_tokens)
    if query_text == candidate_text:
        return 1.0
    if query_text in candidate_text or candidate_text in query_text:
        return 0.9

    overlap = len(set(query_tokens) & set(candidate_tokens))
    return overlap / max(len(set(query_tokens)), 1)


def _looks_like_standalone_title_query(input_text: str) -> bool:
    text = _normalize_text(input_text)
    if not text or len(text) > 220:
        return False
    if _extract_arxiv_id(text):
        return True
    lowered = text.lower()
    imperative_markers = (
        "start translation",
        "translate this",
        "translate it",
        "启动翻译",
        "开始翻译",
        "帮我翻译",
    )
    if any(marker in lowered for marker in imperative_markers):
        return False
    if re.search(r"[?？!！]", text):
        return False
    conversational_markers = (
        "please",
        "what is",
        "what's",
        "how",
        "why",
        "tell me",
        "explain",
        "summarize",
        "总结",
        "解释",
        "请",
        "启动",
    )
    if any(marker in lowered for marker in conversational_markers):
        return False

    latin_words = re.findall(r"[A-Za-z][A-Za-z0-9\-]*", text)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    return len(latin_words) >= 3 or len(cjk_chars) >= 6


def _pick_candidate_citation_for_query(
    citations: Iterable[Dict[str, Any]],
    *,
    input_text: str,
) -> Dict[str, Any] | None:
    normalized_query = " ".join(_normalized_title_tokens(_derive_search_query(input_text)))
    best: Dict[str, Any] | None = None
    best_score = 0.0

    for citation in citations:
        if not isinstance(citation, dict):
            continue
        paper_id = _normalize_text(citation.get("paper_id"))
        arxiv_id = _normalize_text(citation.get("arxiv_id"))
        title = _normalize_text(citation.get("title"))
        if not (paper_id or arxiv_id):
            continue

        score = 0.1
        if paper_id:
            score += 0.1
        if title and normalized_query:
            score += _title_similarity_score(normalized_query, title)
        if score > best_score:
            best = citation
            best_score = score
    return best


async def _resolve_arxiv_id_from_title(query: str) -> str | None:
    normalized_query = _normalize_text(query).strip("\"'")
    if not normalized_query:
        return None

    search_queries = [f'ti:"{normalized_query}"', f'all:"{normalized_query}"']
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    best_id: str | None = None
    best_score = 0.0

    async with httpx.AsyncClient(timeout=15.0) as client:
        for search_query in search_queries:
            try:
                response = await client.get(
                    "https://export.arxiv.org/api/query",
                    params={
                        "search_query": search_query,
                        "start": 0,
                        "max_results": 5,
                    },
                    headers={"User-Agent": "LaTeXTrans/CommunityAgentTitleBridge"},
                )
                response.raise_for_status()
            except Exception:
                continue

            try:
                root = ET.fromstring(response.text)
            except ET.ParseError:
                continue

            for entry in root.findall("atom:entry", namespace):
                entry_id = _normalize_text(entry.findtext("atom:id", default="", namespaces=namespace))
                title = _normalize_text(entry.findtext("atom:title", default="", namespaces=namespace))
                arxiv_id = _extract_arxiv_id(entry_id or "")
                if not arxiv_id or not title:
                    continue
                score = _title_similarity_score(normalized_query, title)
                if score > best_score:
                    best_score = score
                    best_id = arxiv_id

            if best_id and best_score >= 0.55:
                return best_id

    return best_id if best_score >= 0.35 else None


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
        citation_id = _normalize_text(citation.get("id"))
        paper_id = _normalize_text(citation.get("paper_id"))
        anchor_id = _normalize_text(citation.get("anchor_id"))
        key = citation_id or (
            f"{paper_id}#{anchor_id}" if paper_id and anchor_id else (
                paper_id
                or _normalize_text(citation.get("arxiv_id"))
                or _normalize_text(citation.get("url"))
                or _normalize_text(citation.get("title"))
            )
        )
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


def _chunk_text(text: str, chunk_size: int = 280) -> List[str]:
    normalized = str(text or "")
    if not normalized:
        return []

    chunks: List[str] = []
    cursor = 0
    while cursor < len(normalized):
        chunks.append(normalized[cursor : cursor + chunk_size])
        cursor += chunk_size
    return chunks


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
    candidate = re.sub(r"^(请帮我)?(解释|总结|概述|查找|搜索)\s*", "", candidate)
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
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_retryable_reasoning_status(status_code: int) -> bool:
    return status_code in _RETRYABLE_REASONING_STATUS_CODES


def _reasoning_retry_delay(attempt: int) -> float:
    return min(_REASONING_RETRY_BASE_SECONDS * (2**attempt), _REASONING_RETRY_MAX_SECONDS)


def _context_citation(paper_context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": paper_context.get("paper_id") or f"context-{uuid.uuid4().hex[:8]}",
        "title": paper_context.get("title") or "Current paper",
        "url": f"/paper/{paper_context.get('paper_id')}" if paper_context.get("paper_id") else None,
        "source": "community",
        "arxiv_id": paper_context.get("arxiv_id"),
        "paper_id": paper_context.get("paper_id"),
        "anchor_id": paper_context.get("active_anchor_id"),
        "snippet": paper_context.get("abstract_translated") or paper_context.get("abstract_raw"),
    }


def _provider_config() -> tuple[str | None, str | None, str | None]:
    provider_url = _resolve_chat_completions_url(os.getenv(REASONING_PROVIDER_URL_ENV) or settings.llm_base_url)
    provider_key = os.getenv(REASONING_PROVIDER_KEY_ENV) or settings.llm_api_key
    provider_model = os.getenv(REASONING_PROVIDER_MODEL_ENV) or settings.llm_model
    return provider_url, provider_key, provider_model


async def _call_chat_completion(*, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    provider_url, provider_key, provider_model = _provider_config()
    if not provider_url or not provider_key or not provider_model:
        return None

    async with httpx.AsyncClient(timeout=max(float(settings.llm_timeout), 10.0)) as client:
        max_attempts = _REASONING_MAX_RETRIES + 1
        data: Dict[str, Any] | None = None
        for attempt in range(max_attempts):
            try:
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
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < max_attempts - 1:
                    await asyncio.sleep(_reasoning_retry_delay(attempt))
                    continue
                raise RuntimeError(
                    f"Reasoning provider request failed after {max_attempts} attempts due to network error: {exc}"
                ) from exc

            if response.status_code >= 400:
                body_preview = _normalize_text(response.text)[:600]
                if _is_retryable_reasoning_status(response.status_code) and attempt < max_attempts - 1:
                    await asyncio.sleep(_reasoning_retry_delay(attempt))
                    continue
                raise RuntimeError(
                    f"Reasoning provider request failed with HTTP {response.status_code} after {attempt + 1} attempt(s). "
                    f"Response: {body_preview or '<empty>'}"
                )

            try:
                data = response.json()
            except ValueError as exc:
                raise RuntimeError("Reasoning provider returned a non-JSON response") from exc
            break
        if data is None:
            return None

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


async def _stream_chat_completion(*, messages: List[Dict[str, Any]]):
    provider_url, provider_key, provider_model = _provider_config()
    if not provider_url or not provider_key or not provider_model:
        return
        yield  # pragma: no cover

    async with httpx.AsyncClient(timeout=None) as client:
        max_attempts = _REASONING_MAX_RETRIES + 1
        for attempt in range(max_attempts):
            emitted_delta = False
            try:
                async with client.stream(
                    "POST",
                    provider_url,
                    json={
                        "model": provider_model,
                        "messages": messages,
                        "temperature": 0.2,
                        "stream": True,
                    },
                    headers={
                        "Authorization": f"Bearer {provider_key}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status_code >= 400:
                        body_text = await response.aread()
                        body_preview = _normalize_text(body_text.decode("utf-8", errors="replace"))[:600]
                        if _is_retryable_reasoning_status(response.status_code) and attempt < max_attempts - 1:
                            await asyncio.sleep(_reasoning_retry_delay(attempt))
                            continue
                        raise RuntimeError(
                            f"Reasoning provider stream request failed with HTTP {response.status_code} "
                            f"after {attempt + 1} attempt(s). Response: {body_preview or '<empty>'}"
                        )

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        payload = line[len("data:") :].strip()
                        if not payload or payload == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(payload)
                        except json.JSONDecodeError:
                            continue

                        choices = chunk.get("choices") if isinstance(chunk, dict) else None
                        if not isinstance(choices, list) or not choices:
                            continue
                        delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
                        if not isinstance(delta, dict):
                            continue

                        content = delta.get("content")
                        if isinstance(content, str) and content:
                            emitted_delta = True
                            yield content
                            continue

                        if isinstance(content, list):
                            for item in content:
                                if not isinstance(item, dict):
                                    continue
                                if item.get("type") == "text" and isinstance(item.get("text"), str):
                                    emitted_delta = True
                                    yield item["text"]
                return
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if emitted_delta or attempt >= max_attempts - 1:
                    raise RuntimeError(
                        f"Reasoning provider stream failed after {attempt + 1} attempt(s) due to network error: {exc}"
                    ) from exc
                await asyncio.sleep(_reasoning_retry_delay(attempt))


def _infer_intent(runtime_state: AgentRuntimeState) -> str:
    text = runtime_state.input_text.lower()
    executed = [item.get("tool_name") or item.get("skill_name") for item in runtime_state.executed_tool_results]
    if "start_translation_kernel" in executed or _has_any_marker(text, _TRANSLATE_MARKERS):
        return "translate"
    if any(name in {"community_search_papers", "external_tavily_search"} for name in executed):
        return "search"
    if _has_any_marker(text, _SEARCH_MARKERS) and not runtime_state.paper_context:
        return "search"
    return "answer"


def _build_planner_system_prompt(runtime_state: AgentRuntimeState, tool_names: List[str]) -> str:
    bundle = build_skill_prompt_bundle(runtime_state)
    tool_list = ", ".join(tool_names) or "none"
    return (
        "You are PaperX Copilot, a conversational research-paper assistant.\n"
        f"Answer naturally in {runtime_state.response_language}.\n"
        "Use prompt skills as behavior guidance only; executable actions must go through the visible tool registry.\n"
        "Prefer current paper context and internal community paper search before external web search.\n"
        "If the user references an arXiv id and the paper is missing, import it and read the paper context before answering.\n"
        "If the user asks for translated reading support and the paper is not translated yet, start the translation kernel as background work.\n"
        "Do not fabricate citations, paper metadata, tool results, or translation status.\n"
        f"Visible tools this turn: {tool_list}.\n\n"
        f"{bundle.skill_index_markdown}\n\n"
        f"{bundle.prompt_markdown}"
    )


def _build_final_system_prompt(runtime_state: AgentRuntimeState) -> str:
    translation_hint = (
        "If translation has already started, mention it as background progress without ending the answer early."
        if runtime_state.action and runtime_state.action.get("task_id")
        else "Focus on a grounded paper answer."
    )
    return (
        "You are PaperX Copilot.\n"
        f"Produce the final assistant answer in {runtime_state.response_language}.\n"
        "Write in Markdown-friendly normal prose, not synthetic slot sections.\n"
        "Lead with the most grounded answer you can support from the current paper context, retrieved citations, and tool results.\n"
        f"{translation_hint}\n"
        "Keep citations/tool metadata separate from the prose body; the UI renders them independently."
    )


def _build_planner_messages(runtime_state: AgentRuntimeState, visible_tools: Dict[str, Any]) -> List[Dict[str, Any]]:
    reader_selection = _normalize_reader_selection(runtime_state.context)
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": _build_planner_system_prompt(runtime_state, list(visible_tools))},
        {
            "role": "system",
            "content": json.dumps(
                {
                    "answer_language": runtime_state.response_language,
                    "current_paper_context": runtime_state.paper_context,
                    "reader_selection": reader_selection,
                    "known_citations": _dedupe_citations(runtime_state.citations)[:6],
                    "skill_toggles": runtime_state.skill_toggles,
                },
                ensure_ascii=False,
            ),
        },
    ]
    messages.extend(runtime_state.history)
    messages.append({"role": "user", "content": runtime_state.input_text})
    return messages


def _build_final_messages(runtime_state: AgentRuntimeState, planner_seed: str | None) -> List[Dict[str, Any]]:
    reader_selection = _normalize_reader_selection(runtime_state.context)
    return [
        {"role": "system", "content": _build_final_system_prompt(runtime_state)},
        {
            "role": "system",
            "content": json.dumps(
                {
                    "input_text": runtime_state.input_text,
                    "current_paper_context": runtime_state.paper_context,
                    "reader_selection": reader_selection,
                    "citations": _dedupe_citations(runtime_state.citations),
                    "tool_trace": runtime_state.tool_trace,
                    "executed_tools": runtime_state.executed_tool_results,
                    "action": runtime_state.action,
                    "planner_seed": planner_seed,
                },
                ensure_ascii=False,
            ),
        },
        {"role": "user", "content": runtime_state.input_text},
    ]


def _build_first_answer_from_context(runtime_state: AgentRuntimeState) -> str | None:
    paper_context = runtime_state.paper_context or {}
    title = _normalize_text(paper_context.get("title"))
    reader_selection = _normalize_reader_selection(runtime_state.context)
    selection_snippet = _normalize_text((reader_selection or {}).get("text"))
    snippet = _normalize_text(paper_context.get("abstract_translated") or paper_context.get("abstract_raw"))
    if not snippet:
        snippet = selection_snippet

    if selection_snippet and not title:
        compact_selection = selection_snippet[:360]
        if is_chinese_language(runtime_state.response_language):
            return f"你高亮的这段内容主要在讲：{compact_selection}"
        return f"The highlighted passage mainly says: {compact_selection}"

    if not title and not snippet:
        return None

    if is_chinese_language(runtime_state.response_language):
        answer = f"《{title or '当前论文'}》的核心内容是：{snippet or '目前已经拿到论文元数据，可以继续基于论文上下文展开解释。'}"
        if runtime_state.action and runtime_state.action.get("task_id"):
            answer += " 相关翻译已经在后台启动，你现在可以先继续阅读这篇论文，我会保持当前回答不断开。"
        return answer

    answer = f"The main point of {title or 'the current paper'} is: {snippet or 'the paper context is loaded and ready for a grounded explanation.'}"
    if runtime_state.action and runtime_state.action.get("task_id"):
        answer += " Translation is already running in the background while you keep reading."
    return answer


def _fallback_message(runtime_state: AgentRuntimeState) -> str:
    contextual_answer = _build_first_answer_from_context(runtime_state)
    if contextual_answer:
        return contextual_answer

    lead = runtime_state.citations[0] if runtime_state.citations else None
    lead_title = _normalize_text((lead or {}).get("title"))
    lead_snippet = _normalize_text((lead or {}).get("snippet"))
    if lead_title:
        if is_chinese_language(runtime_state.response_language):
            return f"我目前找到的最相关论文是《{lead_title}》。{lead_snippet or '如果你愿意，我可以继续解释方法、结果或相关工作。'}"
        return f"The most relevant paper I found is {lead_title}. {lead_snippet or 'I can continue into the method, results, or related work if you want.'}"

    if is_chinese_language(runtime_state.response_language):
        return "我已经拿到当前对话的上下文，但暂时没有更多可验证证据。你可以继续追问论文方法、结果或翻译需求。"
    return "I have the current conversation context, but I do not yet have more verifiable evidence. You can ask for the method, results, or translation support next."


def _finalize_payload(runtime_state: AgentRuntimeState, message: str) -> Dict[str, Any]:
    intent = "answer" if runtime_state.run_mode == "deep_research" else _infer_intent(runtime_state)
    citations = _dedupe_citations(runtime_state.citations)
    if runtime_state.run_mode == "deep_research":
        citations = citations[:_DEEP_RESEARCH_MAX_EVIDENCE]
    runtime_state.latest_intent = intent
    return {
        "status": "completed",
        "intent": intent,
        "mode": runtime_state.run_mode,
        "message": message,
        "summary": message,
        "tool_trace": runtime_state.tool_trace,
        "citations": citations,
        "provider_state": runtime_state.provider_state,
        "action": runtime_state.action,
        "report": runtime_state.report,
        "events": runtime_state.events,
    }


class CommunityReactAgent:
    """社区 ReAct Agent 编排器

    实现基于 LLM 的 ReAct（推理-行动）循环：
    1. 自动检测论文上下文并加载
    2. 规划阶段：LLM 决定调用哪些工具
    3. 工具执行：通过 ToolRegistry 调用社区工具
    4. 最终答案生成：流式输出自然语言回答
    5. 深度研究模式：多轮证据检索与综合报告
    6. 回退模式：当 LLM 不可用时使用确定性规则回答
    """

    def __init__(
        self,
        *,
        input_text: str,
        context: Dict[str, Any] | None = None,
        skill_toggles: Dict[str, Any] | None = None,
        run_mode: str = "chat",
        event_callback: EventCallback | None = None,
    ) -> None:
        safe_context = dict(context or {})
        history = _normalize_history(safe_context)
        self._event_callback = event_callback
        self.runtime_state = AgentRuntimeState(
            input_text=_normalize_text(input_text),
            context=safe_context,
            skill_toggles=dict(skill_toggles or {}),
            provider_state={
                "internal_search": "enabled",
                "external_search": "enabled"
                if (skill_toggles or {}).get("external_search")
                else "disabled_by_user",
                "reasoning": "enabled",
                "translation_bridge": "enabled",
            },
            run_mode=run_mode,
            response_language=detect_response_language(_normalize_text(input_text), history=history, context=safe_context),
            history=history,
        )
        self.registry = ToolRegistry()

    async def _emit_event(self, event_type: str, **data: Any) -> None:
        event = _make_event(event_type, **data)
        self.runtime_state.events.append(event)
        if self._event_callback is None:
            return

        result = self._event_callback(event)
        if inspect.isawaitable(result):
            await result

    async def _set_action(self, action: Dict[str, Any] | None) -> None:
        if action is None or action == self.runtime_state.action:
            self.runtime_state.action = action
            return
        self.runtime_state.action = action
        await self._emit_event("action", action=action)

    async def _add_citations(self, citations: List[Dict[str, Any]]) -> None:
        for citation in self.runtime_state.add_citations(citations):
            await self._emit_event("citation", citation=citation)

    async def _bootstrap_paper_context(self) -> None:
        paper_id = self.runtime_state.context.get("paper_id")
        if not paper_id:
            return
        try:
            paper_context = await ReadPaperContextSkill().execute({"paper_id": paper_id}, self.runtime_state)
        except Exception:
            self.runtime_state.paper_context = None
            return

        self.runtime_state.paper_context = paper_context
        await self._add_citations([_context_citation(paper_context)])
        bootstrap_entry = {"tool_name": "read_paper_context", "arguments": {"paper_id": paper_id}, "result": paper_context}
        self.runtime_state.executed_tool_results.append(bootstrap_entry)
        self.runtime_state.executed_skill_results.append(
            {"skill_name": "read_paper_context", "arguments": {"paper_id": paper_id}, "result": paper_context}
        )
        self.runtime_state.tool_trace.append(
            _make_trace("context", "Current paper context", "read_paper_context", "completed", paper_context.get("title") or paper_id)
        )

    async def _merge_tool_result(self, tool_name: str, result: Dict[str, Any]) -> None:
        if tool_name == "community_search_papers":
            await self._add_citations(result.get("results") or [])
        elif tool_name == "external_tavily_search":
            self.runtime_state.provider_state["external_search"] = "tavily"
            await self._add_citations(result.get("results") or [])
        elif tool_name == "read_paper_context":
            self.runtime_state.paper_context = result
            if result.get("paper_id"):
                await self._add_citations([_context_citation(result)])
                if not self.runtime_state.action:
                    await self._set_action({"type": "navigate_paper", "paper_id": result.get("paper_id")})
        elif tool_name == "import_arxiv_paper":
            paper_id = result.get("paper_id")
            if paper_id:
                self.runtime_state.context["paper_id"] = paper_id
                await self._set_action(
                    {
                        "type": "navigate_paper",
                        "paper_id": paper_id,
                        "imported": bool(result.get("imported")),
                        "reused": bool(result.get("reused")),
                    }
                )
        elif tool_name == "start_translation_kernel":
            await self._set_action(
                {
                    "type": "navigate_paper",
                    "paper_id": result.get("paper_id"),
                    "task_id": result.get("task_id"),
                    "auto_started_translation": bool(result.get("task_id")),
                }
            )

    async def _execute_tool_call(
        self,
        *,
        tool_call: Dict[str, Any],
        visible_tools: Dict[str, Any],
    ) -> tuple[bool, Dict[str, Any]]:
        function = tool_call.get("function") if isinstance(tool_call, dict) else {}
        tool_name = _normalize_text(function.get("name")) if isinstance(function, dict) else ""
        arguments = _parse_tool_arguments(function.get("arguments") if isinstance(function, dict) else None)

        try:
            validate_skill_call(
                skill_name=tool_name,
                arguments=arguments,
                raw_input=self.runtime_state.input_text,
                visible_skill_names=set(visible_tools),
            )
            tool = visible_tools[tool_name]
            running_trace = _make_trace(tool.trace_kind, tool.trace_label, tool.name, "running")
            self.runtime_state.tool_trace.append(running_trace)
            await self._emit_event("tool_start", tool=tool.name, arguments=arguments, trace=running_trace)

            result = await tool.execute(arguments, self.runtime_state)
            self.runtime_state.executed_tool_results.append(
                {"tool_name": tool.name, "arguments": arguments, "result": result}
            )
            self.runtime_state.executed_skill_results.append(
                {"skill_name": tool.name, "arguments": arguments, "result": result}
            )
            await self._merge_tool_result(tool.name, result)

            completed_trace = _make_trace(tool.trace_kind, tool.trace_label, tool.name, "completed")
            self.runtime_state.tool_trace.append(completed_trace)
            await self._emit_event(
                "tool_result",
                tool=tool.name,
                result=result,
                trace=completed_trace,
            )
            return True, result
        except ValidationError as exc:
            error_detail = str(exc)
            self.runtime_state.tool_trace.append(
                _make_trace("validation", "Tool validator", tool_name or "unknown_tool", "failed", error_detail)
            )
        except Exception as exc:
            error_detail = str(exc)
            self.runtime_state.tool_trace.append(
                _make_trace("validation", "Tool execution", tool_name or "unknown_tool", "failed", error_detail)
            )

        error_payload = {"error": error_detail, "tool": tool_name or "unknown_tool"}
        await self._emit_event("error", **error_payload)
        if self.runtime_state.repair_count >= 1:
            return False, error_payload
        self.runtime_state.repair_count += 1
        return True, error_payload

    async def _run_planner_phase(self) -> tuple[List[Dict[str, Any]] | None, str | None]:
        visible_tools = self.registry.visible_tools(self.runtime_state)
        messages = _build_planner_messages(self.runtime_state, visible_tools)
        await self._emit_event("status", status="running", phase="planner")

        for _ in range(_MAX_PLANNER_TURNS):
            visible_tools = self.registry.visible_tools(self.runtime_state)
            response = await _call_chat_completion(
                messages=messages,
                tools=[tool.serialize_for_model() for tool in visible_tools.values()],
            )
            if not response:
                return None, None

            content = _normalize_text(response.get("content"))
            tool_calls = response.get("tool_calls") if isinstance(response.get("tool_calls"), list) else []

            if not tool_calls:
                return messages, content or None

            messages.append(
                {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                }
            )

            for tool_call in tool_calls:
                should_continue, result = await self._execute_tool_call(
                    tool_call=tool_call,
                    visible_tools=visible_tools,
                )
                tool_call_id = _normalize_text(tool_call.get("id")) or f"call-{uuid.uuid4().hex[:8]}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
                if not should_continue:
                    return None, None

        return None, None

    async def _bridge_context_from_citations(self) -> bool:
        if self.runtime_state.paper_context:
            return True

        candidate = _pick_candidate_citation_for_query(
            self.runtime_state.citations,
            input_text=self.runtime_state.input_text,
        )
        if not candidate:
            return False

        visible_tools = self.registry.visible_tools(self.runtime_state)
        candidate_paper_id = _normalize_text(candidate.get("paper_id"))
        candidate_arxiv_id = _normalize_text(candidate.get("arxiv_id"))

        if candidate_paper_id:
            self.runtime_state.context["paper_id"] = candidate_paper_id
            visible_tools = self.registry.visible_tools(self.runtime_state)
        if candidate_paper_id and "read_paper_context" in visible_tools:
            await self._execute_tool_call(
                tool_call={
                    "id": "bridge-read-context",
                    "function": {
                        "name": "read_paper_context",
                        "arguments": json.dumps({"paper_id": candidate_paper_id}),
                    },
                },
                visible_tools=visible_tools,
            )
            return bool(self.runtime_state.paper_context)

        if candidate_arxiv_id and "import_arxiv_paper" in visible_tools:
            should_continue, result = await self._execute_tool_call(
                tool_call={
                    "id": "bridge-import-by-citation",
                    "function": {
                        "name": "import_arxiv_paper",
                        "arguments": json.dumps({"arxiv_id": candidate_arxiv_id}),
                    },
                },
                visible_tools=visible_tools,
            )
            if should_continue and result.get("paper_id"):
                visible_tools = self.registry.visible_tools(self.runtime_state)
                if "read_paper_context" in visible_tools:
                    await self._execute_tool_call(
                        tool_call={
                            "id": "bridge-read-after-citation-import",
                            "function": {
                                "name": "read_paper_context",
                                "arguments": json.dumps({"paper_id": result.get("paper_id")}),
                            },
                        },
                        visible_tools=visible_tools,
                    )
        return bool(self.runtime_state.paper_context)

    async def _bridge_context_from_title_resolution(self) -> bool:
        if self.runtime_state.paper_context:
            return True
        if not _looks_like_standalone_title_query(self.runtime_state.input_text):
            return False

        query = _derive_search_query(self.runtime_state.input_text)
        resolved_arxiv_id = await _resolve_arxiv_id_from_title(query)
        if resolved_arxiv_id:
            self.runtime_state.tool_trace.append(
                _make_trace(
                    "import",
                    "Resolve arXiv by title",
                    "resolve_arxiv_by_title",
                    "completed",
                    resolved_arxiv_id,
                )
            )
        else:
            self.runtime_state.tool_trace.append(
                _make_trace(
                    "import",
                    "Resolve arXiv by title",
                    "resolve_arxiv_by_title",
                    "failed",
                    "No confident arXiv match from title query",
                )
            )
            return False

        visible_tools = self.registry.visible_tools(self.runtime_state)
        if "import_arxiv_paper" not in visible_tools:
            return False

        should_continue, result = await self._execute_tool_call(
            tool_call={
                "id": "bridge-import-by-title",
                "function": {
                    "name": "import_arxiv_paper",
                    "arguments": json.dumps({"arxiv_id": resolved_arxiv_id}),
                },
            },
            visible_tools=visible_tools,
        )
        if not should_continue:
            return False

        paper_id = _normalize_text(result.get("paper_id"))
        if not paper_id:
            return False
        visible_tools = self.registry.visible_tools(self.runtime_state)
        if "read_paper_context" not in visible_tools:
            return False
        await self._execute_tool_call(
            tool_call={
                "id": "bridge-read-after-title-import",
                "function": {
                    "name": "read_paper_context",
                    "arguments": json.dumps({"paper_id": paper_id}),
                },
            },
            visible_tools=visible_tools,
        )
        return bool(self.runtime_state.paper_context)

    def _should_auto_start_translation(self) -> bool:
        paper_context = self.runtime_state.paper_context or {}
        if not paper_context.get("paper_id"):
            return False
        if paper_context.get("translated_ready"):
            return False

        input_text = self.runtime_state.input_text
        if _has_any_marker(input_text, _TRANSLATE_MARKERS):
            return True
        if _looks_like_standalone_title_query(input_text):
            return True
        if is_chinese_language(self.runtime_state.response_language):
            return True
        return False

    async def _bridge_context_and_translation(self) -> None:
        if not self.runtime_state.paper_context:
            await self._bridge_context_from_citations()
        if not self.runtime_state.paper_context:
            await self._bridge_context_from_title_resolution()

        if not self._should_auto_start_translation():
            return

        already_started = any(
            (entry.get("tool_name") or entry.get("skill_name")) == "start_translation_kernel"
            for entry in self.runtime_state.executed_tool_results
        )
        if already_started:
            return

        visible_tools = self.registry.visible_tools(self.runtime_state)
        if "start_translation_kernel" not in visible_tools:
            return
        paper_id = _normalize_text((self.runtime_state.paper_context or {}).get("paper_id"))
        if not paper_id:
            return

        await self._execute_tool_call(
            tool_call={
                "id": "bridge-translate",
                "function": {
                    "name": "start_translation_kernel",
                    "arguments": json.dumps(
                        {
                            "paper_id": paper_id,
                            "source_language": "en",
                            "target_language": "zh",
                        }
                    ),
                },
            },
            visible_tools=visible_tools,
        )

    async def _run_final_stream_phase(self, planner_seed: str | None) -> str | None:
        final_messages = _build_final_messages(self.runtime_state, planner_seed)
        await self._emit_event("status", status="running", phase="final_stream")

        collected_parts: List[str] = []
        try:
            async for delta in _stream_chat_completion(messages=final_messages):
                normalized = str(delta)
                if not normalized:
                    continue
                collected_parts.append(normalized)
                await self._emit_event("assistant_delta", delta=normalized)
        except Exception as exc:
            if not planner_seed or collected_parts:
                self.runtime_state.tool_trace.append(
                    _make_trace("validation", "Final answer stream", "runtime", "failed", str(exc))
                )
                await self._emit_event("error", message=str(exc))

        if collected_parts:
            return "".join(collected_parts)
        if planner_seed:
            await self._emit_event("assistant_delta", delta=planner_seed)
            return planner_seed
        return None

    def _build_deep_research_queries(self) -> List[str]:
        base_query = _derive_search_query(self.runtime_state.input_text) or self.runtime_state.input_text
        query_variants = [
            base_query,
            f"{base_query} survey",
            f"{base_query} benchmark",
            f"{base_query} limitations",
            f"{base_query} applications",
        ]

        deduped: List[str] = []
        for candidate in query_variants:
            normalized = _normalize_text(candidate)
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in {item.lower() for item in deduped}:
                continue
            deduped.append(normalized)
            if len(deduped) >= _DEEP_RESEARCH_MAX_QUERY_ROUNDS:
                break
        return deduped

    def _cap_deep_research_citations(self) -> List[Dict[str, Any]]:
        capped = _dedupe_citations(self.runtime_state.citations)[:_DEEP_RESEARCH_MAX_EVIDENCE]
        self.runtime_state.citations = list(capped)
        self.runtime_state.citations_by_id = {
            str(citation.get("id")): citation
            for citation in capped
            if _normalize_text(citation.get("id"))
        }
        return capped

    def _build_deep_research_report(self, *, citations: List[Dict[str, Any]], coverage_note: str) -> str:
        lines: List[str] = [
            "# Deep Research Brief",
            "",
            "## Executive Summary",
            (
                "This report synthesizes cross-paper evidence for the current research question and "
                "highlights converging findings, tensions, and practical takeaways."
            ),
            "",
            "## Research Question",
            self.runtime_state.input_text,
            "",
            "## Evidence Coverage",
            (
                f"- Retrieved evidence items: {len(citations)} "
                f"(target {_DEEP_RESEARCH_MIN_EVIDENCE}-{_DEEP_RESEARCH_MAX_EVIDENCE})."
            ),
            f"- {coverage_note}",
            (
                f"- Runtime guardrails: context pack <= {_DEEP_RESEARCH_MAX_EVIDENCE} items, "
                f"timeout <= {int(_DEEP_RESEARCH_TIMEOUT_SECONDS)}s."
            ),
            "",
            "## Cross-Paper Synthesis",
        ]

        if citations:
            for index, citation in enumerate(citations[:8], start=1):
                title = _normalize_text(citation.get("title")) or f"Evidence item {index}"
                snippet = _normalize_text(citation.get("snippet")) or "No snippet available."
                lines.append(f"{index}. **{title}** [{index}]")
                lines.append(f"   - {snippet}")
            lines.extend(
                [
                    "",
                    "## Limitations and Confidence",
                    (
                        "The synthesis is evidence-bounded: conclusions rely on retrieved citations and "
                        "do not claim exhaustive coverage beyond this run."
                    ),
                ]
            )
        else:
            lines.extend(
                [
                    "- No grounded evidence items were retrieved in this run.",
                    "",
                    "## Limitations and Confidence",
                    "Confidence is low because the evidence pool is empty for this request.",
                ]
            )

        lines.append("")
        lines.append("## References")
        if citations:
            for index, citation in enumerate(citations, start=1):
                title = _normalize_text(citation.get("title")) or f"Evidence item {index}"
                arxiv_id = _normalize_text(citation.get("arxiv_id"))
                url = _normalize_text(citation.get("url"))
                if arxiv_id:
                    lines.append(f"[{index}] {title}. arXiv:{arxiv_id}.")
                elif url:
                    lines.append(f"[{index}] {title}. {url}")
                else:
                    lines.append(f"[{index}] {title}.")
        else:
            lines.append("[1] No references captured.")

        return "\n".join(lines).strip()

    async def _emit_deep_research_report_stream(self, report_markdown: str) -> None:
        for chunk in _chunk_text(report_markdown):
            await self._emit_event("assistant_delta", delta=chunk)

    async def _run_deep_research_mode(self) -> Dict[str, Any]:
        await self._emit_event("status", status="running", phase="deep_research_retrieval")
        timeout_hit = False

        try:
            async with asyncio.timeout(_DEEP_RESEARCH_TIMEOUT_SECONDS):
                for query in self._build_deep_research_queries():
                    visible_tools = self.registry.visible_tools(self.runtime_state)
                    if "community_search_papers" not in visible_tools:
                        break

                    should_continue, _ = await self._execute_tool_call(
                        tool_call={
                            "id": f"deep-research-community-{uuid.uuid4().hex[:8]}",
                            "function": {
                                "name": "community_search_papers",
                                "arguments": json.dumps(
                                    {
                                        "query": query,
                                        "limit": _DEEP_RESEARCH_PER_QUERY_LIMIT,
                                    }
                                ),
                            },
                        },
                        visible_tools=visible_tools,
                    )
                    if not should_continue:
                        break
                    if len(_dedupe_citations(self.runtime_state.citations)) >= _DEEP_RESEARCH_TARGET_EVIDENCE:
                        break

                if len(_dedupe_citations(self.runtime_state.citations)) < _DEEP_RESEARCH_TARGET_EVIDENCE:
                    visible_tools = self.registry.visible_tools(self.runtime_state)
                    if "external_tavily_search" in visible_tools:
                        should_continue, _ = await self._execute_tool_call(
                            tool_call={
                                "id": f"deep-research-external-{uuid.uuid4().hex[:8]}",
                                "function": {
                                    "name": "external_tavily_search",
                                    "arguments": json.dumps(
                                        {
                                            "query": _derive_search_query(self.runtime_state.input_text),
                                            "max_results": _DEEP_RESEARCH_PER_QUERY_LIMIT,
                                            "search_depth": "advanced",
                                        }
                                    ),
                                },
                            },
                            visible_tools=visible_tools,
                        )
                        if not should_continue:
                            self.runtime_state.tool_trace.append(
                                _make_trace(
                                    "validation",
                                    "Deep research runtime",
                                    "deep_research",
                                    "fallback",
                                    "External retrieval failed; returning bounded partial report.",
                                )
                            )
        except TimeoutError:
            timeout_hit = True
            self.runtime_state.tool_trace.append(
                _make_trace(
                    "validation",
                    "Deep research timeout",
                    "deep_research",
                    "failed",
                    "Deep research retrieval timed out; returning partial report.",
                )
            )
            await self._emit_event(
                "error",
                message="Deep research retrieval timed out; returning partial report.",
            )

        citations = self._cap_deep_research_citations()
        partial_coverage = len(citations) < _DEEP_RESEARCH_MIN_EVIDENCE or timeout_hit
        if partial_coverage:
            coverage_note = (
                f"Coverage is partial: collected {len(citations)} items while target is "
                f"{_DEEP_RESEARCH_MIN_EVIDENCE}-{_DEEP_RESEARCH_MAX_EVIDENCE}."
            )
            if timeout_hit:
                coverage_note += " Retrieval timed out before full breadth was reached."
        else:
            coverage_note = (
                f"Coverage reached target breadth with {len(citations)} grounded evidence items."
            )

        await self._emit_event("status", status="running", phase="deep_research_synthesis")
        report_markdown = self._build_deep_research_report(
            citations=citations,
            coverage_note=coverage_note,
        )
        self.runtime_state.report = {
            "format": "markdown",
            "body_markdown": report_markdown,
            "evidence_count": len(citations),
            "target_min_evidence": _DEEP_RESEARCH_MIN_EVIDENCE,
            "target_max_evidence": _DEEP_RESEARCH_MAX_EVIDENCE,
            "context_pack_limit": _DEEP_RESEARCH_MAX_EVIDENCE,
            "timeout_seconds": int(_DEEP_RESEARCH_TIMEOUT_SECONDS),
            "partial_coverage": partial_coverage,
            "coverage_note": coverage_note,
        }

        await self._emit_deep_research_report_stream(report_markdown)
        return _finalize_payload(self.runtime_state, report_markdown)

    async def _run_fallback(self) -> Dict[str, Any]:
        visible_tools = self.registry.visible_tools(self.runtime_state)
        arxiv_id = _extract_arxiv_id(self.runtime_state.input_text)

        if arxiv_id and "import_arxiv_paper" in visible_tools and not self.runtime_state.paper_context:
            should_continue, result = await self._execute_tool_call(
                tool_call={
                    "id": "fallback-import",
                    "function": {"name": "import_arxiv_paper", "arguments": json.dumps({"arxiv_id": arxiv_id})},
                },
                visible_tools=visible_tools,
            )
            if should_continue and result.get("paper_id"):
                visible_after_import = self.registry.visible_tools(self.runtime_state)
                if "read_paper_context" in visible_after_import:
                    await self._execute_tool_call(
                        tool_call={
                            "id": "fallback-read-context",
                            "function": {
                                "name": "read_paper_context",
                                "arguments": json.dumps({"paper_id": result["paper_id"]}),
                            },
                        },
                        visible_tools=visible_after_import,
                    )

        visible_tools = self.registry.visible_tools(self.runtime_state)
        if not self.runtime_state.paper_context and not self.runtime_state.citations and "community_search_papers" in visible_tools:
            await self._execute_tool_call(
                tool_call={
                    "id": "fallback-search",
                    "function": {
                        "name": "community_search_papers",
                        "arguments": json.dumps({"query": _derive_search_query(self.runtime_state.input_text), "limit": 4}),
                    },
                },
                visible_tools=visible_tools,
            )

        await self._bridge_context_and_translation()

        self.runtime_state.tool_trace.append(
            _make_trace(
                "validation",
                "Conversational runtime",
                "fallback",
                "fallback",
                "Using deterministic paper-aware fallback reply",
            )
        )

        message = _build_first_answer_from_context(self.runtime_state) or _fallback_message(self.runtime_state)
        return _finalize_payload(self.runtime_state, message)

    async def run(self) -> Dict[str, Any]:
        """运行 Agent 的完整推理循环

        流程:
        1. 引导加载论文上下文
        2. 深度研究模式: 多轮检索 -> 综合报告
        3. 标准模式: 规划器 -> 上下文桥接 -> 最终流式输出
        4. 回退模式: LLM 不可用时的确定性回答
        """
        await self._bootstrap_paper_context()
        if self.runtime_state.run_mode == "deep_research":
            return await self._run_deep_research_mode()

        try:
            planner_messages, planner_seed = await self._run_planner_phase()
            if planner_messages is not None:
                await self._bridge_context_and_translation()
                final_message = await self._run_final_stream_phase(planner_seed)
                if final_message:
                    return _finalize_payload(self.runtime_state, final_message)
        except Exception as exc:
            self.runtime_state.tool_trace.append(
                _make_trace("validation", "Conversational runtime", "runtime", "failed", str(exc))
            )
            await self._emit_event("error", message=str(exc))

        return await self._run_fallback()


async def run_agent(
    input_text: str,
    context: Dict[str, Any] | None = None,
    skill_toggles: Dict[str, Any] | None = None,
    run_mode: str = "chat",
    event_callback: EventCallback | None = None,
) -> Dict[str, Any]:
    """运行社区 Agent 的顶层入口函数

    参数:
        input_text: 用户输入文本
        context: 上下文信息（paper_id, history 等）
        skill_toggles: 技能开关配置
        run_mode: 运行模式（chat / deep_research）
        event_callback: 流式事件回调

    返回:
        包含 status, intent, message, citations 等字段的结果字典
    """
    return await CommunityReactAgent(
        input_text=input_text,
        context=context,
        skill_toggles=skill_toggles,
        run_mode=run_mode,
        event_callback=event_callback,
    ).run()
