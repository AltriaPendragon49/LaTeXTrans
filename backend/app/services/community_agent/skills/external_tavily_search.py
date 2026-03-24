from __future__ import annotations

from typing import Any, Dict, List

import httpx

from backend.app.core.config import settings

from .base import AgentSkill


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


class ExternalTavilySearchSkill(AgentSkill):
    contract_slug = "external_tavily_search"

    def is_visible(self, runtime_state) -> bool:  # type: ignore[no-untyped-def]
        return bool((runtime_state.skill_toggles or {}).get("external_search"))

    async def execute(self, arguments: Dict[str, Any], runtime_state) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        api_key = settings.community_agent_tavily_api_key
        if not api_key:
            raise RuntimeError("COMMUNITY_AGENT_TAVILY_API_KEY is not configured")

        base_url = settings.community_agent_tavily_base_url.rstrip("/")
        payload: Dict[str, Any] = {
            "query": _normalize_text(arguments.get("query")),
            "topic": arguments.get("topic") or "general",
            "search_depth": arguments.get("search_depth") or "basic",
            "max_results": int(arguments.get("max_results") or 4),
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "include_favicon": True,
            "include_usage": True,
            "auto_parameters": False,
        }
        for key in ("time_range", "include_domains", "exclude_domains"):
            value = arguments.get(key)
            if value:
                payload[key] = value

        async with httpx.AsyncClient(timeout=max(float(settings.llm_timeout), 10.0)) as client:
            response = await client.post(
                f"{base_url}/search",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

        raw_results = data.get("results") if isinstance(data, dict) else []
        results: List[Dict[str, Any]] = []
        if isinstance(raw_results, list):
            for index, item in enumerate(raw_results):
                if not isinstance(item, dict):
                    continue
                title = _normalize_text(item.get("title") or item.get("url"))
                if not title:
                    continue
                results.append(
                    {
                        "id": f"tavily-{index}",
                        "title": title,
                        "url": item.get("url"),
                        "snippet": _normalize_text(item.get("content")),
                        "score": item.get("score"),
                        "source": "tavily",
                        "favicon": item.get("favicon"),
                    }
                )

        return {
            "provider": "tavily",
            "query_executed": payload["query"],
            "request_id": data.get("request_id") if isinstance(data, dict) else None,
            "response_time": data.get("response_time") if isinstance(data, dict) else None,
            "usage_credits": data.get("usage", {}).get("credits_used") if isinstance(data, dict) else None,
            "results": results,
        }
