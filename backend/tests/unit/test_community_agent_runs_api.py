import asyncio
from typing import Any, Dict

import httpx
import pytest

from backend.app.api.routes import community_agent as community_agent_route
from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


def test_agent_run_route_passes_skill_toggles_to_service_and_returns_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: Dict[str, Any] = {}

    async def fake_create_run(*, input_text, context, skill_toggles, execution_mode, run_mode, owner_user_id):  # type: ignore[no-untyped-def]
        captured["input_text"] = input_text
        captured["context"] = context
        captured["skill_toggles"] = skill_toggles
        captured["execution_mode"] = execution_mode
        captured["run_mode"] = run_mode
        captured["owner_user_id"] = owner_user_id
        return {
            "run_id": "run-1",
            "status": "completed",
            "intent": "answer",
            "message": "A conversational answer",
            "summary": "A conversational answer",
            "tool_trace": [],
            "citations": [],
            "provider_state": {
                "internal_search": "enabled",
                "external_search": "disabled_by_user",
                "reasoning": "enabled",
                "translation_bridge": "enabled",
            },
            "action": None,
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.create_agent_run",
        fake_create_run,
    )
    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-123"}

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/community-agent/runs",
                json={
                    "input": "Explain this paper",
                    "paper_id": "paper-1",
                    "context": {"source": "conversation"},
                    "skill_toggles": {"external_search": True},
                },
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["message"] == "A conversational answer"
    assert response.json()["summary"] == "A conversational answer"
    assert captured["input_text"] == "Explain this paper"
    assert captured["context"] == {"source": "conversation", "paper_id": "paper-1"}
    assert captured["skill_toggles"] == {"external_search": True}
    assert captured["run_mode"] == "chat"
    assert captured["owner_user_id"] == "usr-123"


def test_agent_run_route_accepts_omitted_skill_toggles(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, Any] = {}

    async def fake_create_run(*, input_text, context, skill_toggles, execution_mode, run_mode, owner_user_id):  # type: ignore[no-untyped-def]
        captured["input_text"] = input_text
        captured["context"] = context
        captured["skill_toggles"] = skill_toggles
        captured["execution_mode"] = execution_mode
        captured["run_mode"] = run_mode
        captured["owner_user_id"] = owner_user_id
        return {
            "run_id": "run-2",
            "status": "completed",
            "intent": "answer",
            "message": "A direct assistant reply",
            "summary": "A direct assistant reply",
            "tool_trace": [],
            "citations": [],
            "provider_state": None,
            "action": None,
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.create_agent_run",
        fake_create_run,
    )
    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-123"}

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/community-agent/runs",
                json={"input": "Explain this paper", "context": {"source": "conversation"}},
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["message"] == "A direct assistant reply"
    assert captured["skill_toggles"] is None
    assert captured["run_mode"] == "chat"
    assert captured["owner_user_id"] == "usr-123"


def test_agent_run_route_supports_async_mode_and_returns_stream_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: Dict[str, Any] = {}

    async def fake_create_run(
        *,
        input_text,
        context,
        skill_toggles,
        execution_mode,
        run_mode,
        owner_user_id,
    ):  # type: ignore[no-untyped-def]
        captured["input_text"] = input_text
        captured["context"] = context
        captured["skill_toggles"] = skill_toggles
        captured["execution_mode"] = execution_mode
        captured["run_mode"] = run_mode
        captured["owner_user_id"] = owner_user_id
        return {
            "run_id": "run-async-1",
            "status": "accepted",
            "intent": "answer",
            "message": None,
            "summary": None,
            "tool_trace": [],
            "citations": [],
            "provider_state": None,
            "action": None,
            "stream_url": "/api/community-agent/runs/run-async-1/events",
            "result_url": "/api/community-agent/runs/run-async-1",
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.create_agent_run",
        fake_create_run,
    )
    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-async"}

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/community-agent/runs",
                json={
                    "input": "Explain this paper",
                    "context": {"source": "conversation"},
                    "execution_mode": "async",
                },
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["stream_url"].endswith("/api/community-agent/runs/run-async-1/events")
    assert response.json()["result_url"].endswith("/api/community-agent/runs/run-async-1")
    assert captured["execution_mode"] == "async"
    assert captured["run_mode"] == "chat"
    assert captured["owner_user_id"] == "usr-async"


def test_agent_run_route_forwards_deep_research_mode_to_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: Dict[str, Any] = {}

    async def fake_create_run(
        *,
        input_text,
        context,
        skill_toggles,
        execution_mode,
        run_mode,
        owner_user_id,
    ):  # type: ignore[no-untyped-def]
        captured["input_text"] = input_text
        captured["context"] = context
        captured["skill_toggles"] = skill_toggles
        captured["execution_mode"] = execution_mode
        captured["run_mode"] = run_mode
        captured["owner_user_id"] = owner_user_id
        return {
            "run_id": "run-research-1",
            "status": "accepted",
            "intent": "answer",
            "mode": "deep_research",
            "message": None,
            "summary": None,
            "tool_trace": [],
            "citations": [],
            "provider_state": None,
            "action": None,
            "report": None,
            "stream_url": "/api/community-agent/runs/run-research-1/events",
            "result_url": "/api/community-agent/runs/run-research-1",
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.create_agent_run",
        fake_create_run,
    )
    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-research"}

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/community-agent/runs",
                json={
                    "input": "Compare retrieval-augmented generation methods",
                    "context": {"source": "conversation"},
                    "mode": "deep_research",
                    "execution_mode": "async",
                },
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["mode"] == "deep_research"
    assert captured["run_mode"] == "deep_research"
    assert captured["owner_user_id"] == "usr-research"


def test_agent_run_route_requires_authentication() -> None:
    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/community-agent/runs",
                json={"input": "Explain this paper", "context": {"source": "conversation"}},
            )

    response = asyncio.run(_call())
    assert response.status_code == 401


def test_agent_stream_route_requires_authentication() -> None:
    async def _call():
        async with _make_client() as client:
            return await client.get("/api/community-agent/runs/run-1/events")

    response = asyncio.run(_call())
    assert response.status_code == 401


def test_agent_run_route_rejects_blank_input() -> None:
    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-blank"}

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/community-agent/runs",
                json={"input": "   ", "context": {"source": "homepage"}},
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()
    assert response.status_code == 400


def test_agent_run_result_route_uses_verified_current_user(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, Any] = {}

    async def fake_get_agent_run(run_id: str, *, owner_user_id: str):  # type: ignore[no-untyped-def]
        captured["run_id"] = run_id
        captured["owner_user_id"] = owner_user_id
        return {
            "run_id": run_id,
            "status": "completed",
            "intent": "answer",
            "mode": "chat",
            "message": "done",
            "summary": "done",
            "tool_trace": [],
            "citations": [],
            "provider_state": None,
            "action": None,
            "report": None,
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.get_agent_run",
        fake_get_agent_run,
    )
    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-result"}

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/community-agent/runs/run-42")

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["run_id"] == "run-42"
    assert captured == {"run_id": "run-42", "owner_user_id": "usr-result"}


def test_agent_run_create_route_respects_centralized_authorization_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Denied:
        allowed = False
        reason = "policy denied run creation"

    async def fake_create_run(*, input_text, context, skill_toggles, execution_mode, run_mode, owner_user_id):  # type: ignore[no-untyped-def]
        del input_text, context, skill_toggles, execution_mode, run_mode, owner_user_id
        return {"run_id": "run-ignored", "status": "completed", "intent": "answer"}

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.create_agent_run",
        fake_create_run,
    )
    monkeypatch.setattr(
        community_agent_route,
        "authorize",
        lambda *_args, **_kwargs: _Denied(),
    )
    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-run-1", "roles": ["user"]}

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/community-agent/runs",
                json={"input": "Explain this paper"},
            )

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "policy denied run creation"


def test_agent_run_result_route_maps_permission_error_to_forbidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_agent_run(run_id: str, *, owner_user_id: str):  # type: ignore[no-untyped-def]
        del run_id, owner_user_id
        raise PermissionError("policy denied run read")

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.get_agent_run",
        fake_get_agent_run,
    )
    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-result"}

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/community-agent/runs/run-denied")

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "policy denied run read"


def test_agent_conversation_routes_forward_authenticated_crud_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    saved_calls: Dict[str, Any] = {}

    async def fake_list_conversations(*, owner_user_id):  # type: ignore[no-untyped-def]
        saved_calls["list_owner_user_id"] = owner_user_id
        return [
            {
                "id": "conversation-1",
                "title": "V-JEPA overview",
                "created_at": "2026-03-23T10:00:00Z",
                "updated_at": "2026-03-23T10:05:00Z",
                "turns": [
                    {
                        "id": "turn-1",
                        "role": "user",
                        "content": "Tell me about V-JEPA 2.1",
                        "created_at": "2026-03-23T10:00:00Z",
                    }
                ],
            }
        ]

    async def fake_upsert_conversation(*, owner_user_id, record):  # type: ignore[no-untyped-def]
        saved_calls["upsert_owner_user_id"] = owner_user_id
        saved_calls["record"] = record
        return record

    async def fake_delete_conversation(*, owner_user_id, conversation_id):  # type: ignore[no-untyped-def]
        saved_calls["delete_owner_user_id"] = owner_user_id
        saved_calls["delete_conversation_id"] = conversation_id
        return {"deleted": True, "conversation_id": conversation_id}

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.list_conversations",
        fake_list_conversations,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent_service.upsert_conversation",
        fake_upsert_conversation,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent_service.delete_conversation",
        fake_delete_conversation,
    )

    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-conv-1"}

    async def _call():
        async with _make_client() as client:
            list_response = await client.get("/api/community-agent/conversations")
            upsert_response = await client.put(
                "/api/community-agent/conversations/conversation-1",
                json={
                    "id": "conversation-1",
                    "title": "V-JEPA overview",
                    "created_at": "2026-03-23T10:00:00Z",
                    "updated_at": "2026-03-23T10:05:00Z",
                    "turns": [
                        {
                            "id": "turn-1",
                            "role": "user",
                            "content": "Tell me about V-JEPA 2.1",
                            "created_at": "2026-03-23T10:00:00Z",
                        }
                    ],
                },
            )
            delete_response = await client.delete("/api/community-agent/conversations/conversation-1")
            return list_response, upsert_response, delete_response

    list_response, upsert_response, delete_response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert upsert_response.status_code == 200
    assert delete_response.status_code == 200
    assert saved_calls["list_owner_user_id"] == "usr-conv-1"
    assert saved_calls["upsert_owner_user_id"] == "usr-conv-1"
    assert saved_calls["delete_owner_user_id"] == "usr-conv-1"
    assert saved_calls["record"]["id"] == "conversation-1"
    assert saved_calls["delete_conversation_id"] == "conversation-1"


def test_agent_conversation_routes_respect_authorization_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Denied:
        allowed = False
        reason = "policy denied conversation access"

    monkeypatch.setattr(
        community_agent_route,
        "authorize",
        lambda *_args, **_kwargs: _Denied(),
    )
    app.dependency_overrides[community_agent_route.require_current_user] = lambda: {"id": "usr-conv-1"}

    async def _call():
        async with _make_client() as client:
            return await client.get("/api/community-agent/conversations")

    response = asyncio.run(_call())
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "policy denied conversation access"
