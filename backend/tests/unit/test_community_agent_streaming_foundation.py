import asyncio
from collections.abc import AsyncGenerator

import pytest

from backend.app.services import community_agent_service


def _tool_call(name: str, arguments: str, *, call_id: str = "call-1") -> dict[str, object]:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": arguments,
                },
            }
        ],
    }


async def _wait_for_completed_run(run_id: str, access_token: str) -> dict[str, object]:
    for _ in range(40):
        payload = await community_agent_service.get_agent_run(run_id, access_token=access_token)
        if payload.get("status") in {"completed", "failed"}:
            return payload
        await asyncio.sleep(0.01)
    raise AssertionError(f"run {run_id} did not complete in time")


def test_async_run_mode_emits_ordered_stream_events_and_final_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            _tool_call(
                "community_search_papers",
                '{"query":"graph neural network molecular property prediction","limit":3}',
            ),
            {
                "role": "assistant",
                "content": "Ground the final answer on the citation and keep it in Chinese.",
            },
        ]
    )

    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        assert messages
        assert any(tool["function"]["name"] == "community_search_papers" for tool in tools)
        return next(responses)

    async def fake_stream_chat_completion(*, messages) -> AsyncGenerator[str, None]:  # type: ignore[no-untyped-def]
        assert messages
        yield "这篇论文"
        yield "聚焦分子预测。"

    async def fake_list_community_papers(*, sort: str, q: str, limit: int):  # type: ignore[no-untyped-def]
        assert sort == "latest"
        assert q == "graph neural network molecular property prediction"
        assert limit == 3
        return {
            "items": [
                {
                    "id": "paper-1",
                    "title": "Graph Neural Networks for Molecular Property Prediction",
                    "arxiv_id": "2603.12345",
                    "abstract_raw": "A paper about graph neural network methods for molecules.",
                    "abstract_translated": "一篇关于图神经网络分子预测的论文。",
                }
            ]
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._call_chat_completion",
        fake_call_chat_completion,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._stream_chat_completion",
        fake_stream_chat_completion,
    )
    monkeypatch.setattr(
        "backend.app.services.paper_service.list_community_papers",
        fake_list_community_papers,
    )

    access_token = "header.payload.signature"
    accepted = asyncio.run(
        community_agent_service.create_agent_run(
            "请帮我找图神经网络分子性质预测相关论文",
            {"source": "conversation", "history": []},
            {"external_search": False},
            execution_mode="async",
            access_token=access_token,
        )
    )

    assert accepted["status"] == "accepted"
    assert accepted["stream_url"].endswith(f"/api/community-agent/runs/{accepted['run_id']}/events")
    assert accepted["result_url"].endswith(f"/api/community-agent/runs/{accepted['run_id']}")

    completed = asyncio.run(_wait_for_completed_run(accepted["run_id"], access_token))
    events = asyncio.run(
        community_agent_service.stream_agent_events(accepted["run_id"], access_token=access_token)
    )

    assert completed["message"] == "这篇论文聚焦分子预测。"
    assert completed["summary"] == completed["message"]

    sequences = [int(event["sequence"]) for event in events]
    assert sequences == sorted(sequences)

    event_types = [str(event["type"]) for event in events]
    assert "status" in event_types
    assert "tool_start" in event_types
    assert "tool_result" in event_types
    assert "citation" in event_types
    assert "assistant_delta" in event_types
    assert event_types[-1] == "complete"
    assert events[-1]["data"]["snapshot"]["message"] == completed["message"]


def test_translation_handoff_stays_non_blocking_and_returns_grounded_first_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        return None

    async def fake_get_community_paper_detail(*, paper_id, viewer_user_id=None, fast_path=True):  # type: ignore[no-untyped-def]
        assert paper_id == "paper-1"
        return {
            "paper": {
                "id": "paper-1",
                "title": "Graph Neural Networks for Molecular Property Prediction",
                "arxiv_id": "2603.12345",
                "abstract_raw": "This paper studies graph neural networks for molecular property prediction.",
                "abstract_translated": None,
                "trans_status": "not_started",
            },
            "reader": {
                "state": "source_ready",
                "translated": None,
            },
            "reader_state": "warming",
        }

    async def fake_start_paper_translation(*, paper_id, request, credentials=None):  # type: ignore[no-untyped-def]
        assert paper_id == "paper-1"
        return {
            "paper_id": paper_id,
            "task_id": "task-translate-1",
            "status": "queued",
            "reused_existing_task": False,
            "processing_url": "/processing?taskId=task-translate-1",
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._call_chat_completion",
        fake_call_chat_completion,
    )
    monkeypatch.setattr(
        "backend.app.services.paper_service.get_community_paper_detail",
        fake_get_community_paper_detail,
    )
    monkeypatch.setattr(
        "backend.app.services.paper_service.start_paper_translation",
        fake_start_paper_translation,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "请用中文解释这篇论文，并开始翻译。",
            {"source": "conversation", "paper_id": "paper-1", "history": []},
            {"external_search": False},
            execution_mode="blocking",
            access_token="header.payload.signature",
        )
    )

    assert result["action"]["task_id"] == "task-translate-1"
    assert "Graph Neural Networks for Molecular Property Prediction" in result["message"]
    assert "翻译" in result["message"]
    assert any(event["type"] == "action" for event in result["events"])
