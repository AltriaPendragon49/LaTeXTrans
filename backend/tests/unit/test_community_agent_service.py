import asyncio

import pytest
from postgrest.exceptions import APIError

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


def test_conversational_agent_accepts_direct_assistant_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        assert messages
        assert tools
        return {
            "role": "assistant",
            "content": "我是 LaTeXTrans，一个可以对话并调用论文工具的研究助手。",
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._call_chat_completion",
        fake_call_chat_completion,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "你是什么模型？",
            {"source": "conversation", "history": []},
            {"external_search": False},
        )
    )

    assert result["intent"] == "answer"
    assert result["message"] == "我是 LaTeXTrans，一个可以对话并调用论文工具的研究助手。"
    assert result["summary"] == result["message"]
    assert result["tool_trace"] == []


def test_conversational_agent_executes_tool_calls_and_returns_grounded_reply(
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
                "content": (
                    "I found a relevant community paper: Graph Neural Networks for Molecular "
                    "Property Prediction. It focuses on molecular representation learning."
                ),
            },
        ]
    )

    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        assert messages
        assert any(tool["function"]["name"] == "community_search_papers" for tool in tools)
        return next(responses)

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
                    "abstract_translated": "一篇关于图神经网络分子性质预测的论文。",
                }
            ]
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._call_chat_completion",
        fake_call_chat_completion,
    )
    monkeypatch.setattr(
        community_agent_service.paper_service,
        "list_community_papers",
        fake_list_community_papers,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "Please find community papers about graph neural networks for molecular property prediction",
            {"source": "conversation", "history": []},
            {"external_search": False},
        )
    )

    assert result["message"].startswith("I found a relevant community paper")
    assert result["summary"] == result["message"]
    assert result["citations"][0]["title"] == "Graph Neural Networks for Molecular Property Prediction"
    assert any(
        trace["provider"] == "community_search_papers" and trace["status"] == "completed"
        for trace in result["tool_trace"]
    )


def test_hidden_tool_call_falls_back_safely_when_external_search_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        assert all(tool["function"]["name"] != "external_tavily_search" for tool in tools)
        return _tool_call(
            "external_tavily_search",
            '{"query":"vision transformer","max_results":3}',
        )

    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._call_chat_completion",
        fake_call_chat_completion,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "Please search the web for recent vision transformer papers",
            {"source": "homepage"},
            {"external_search": False},
        )
    )

    assert result["provider_state"]["external_search"] == "disabled_by_user"
    assert result["message"]
    assert any(
        trace["kind"] == "validation" and trace["status"] == "failed"
        for trace in result["tool_trace"]
    )
    assert any(trace["status"] == "fallback" for trace in result["tool_trace"])


def test_chinese_prompt_fallback_message_stays_in_chinese(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._call_chat_completion",
        fake_call_chat_completion,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "请解释一下 V-JEPA 2.1 这篇论文的主要贡献",
            {"source": "conversation", "history": []},
            {"external_search": False},
        )
    )

    assert "论文" in result["message"]
    assert "Conclusion/Current status" not in result["message"]
    assert result["summary"] == result["message"]


def test_cjk_adjacent_arxiv_prompt_uses_import_fallback_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        return None

    async def fake_import_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        observed["arxiv_id"] = arguments["arxiv_id"]
        return {"paper_id": "paper-2602", "imported": True, "reused": False}

    async def fake_read_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        return {
            "paper_id": "paper-2602",
            "title": "A Community Agent Workflow for Research Reading",
            "arxiv_id": "2602.24209",
            "translated_ready": True,
            "abstract_raw": "A paper about orchestrating research-paper assistance.",
            "abstract_translated": "一篇关于科研论文辅助编排的论文。",
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._call_chat_completion",
        fake_call_chat_completion,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.import_arxiv_paper.ImportArxivPaperSkill.execute",
        fake_import_execute,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.read_paper_context.ReadPaperContextSkill.execute",
        fake_read_execute,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "2602.24209讲了什么",
            {"source": "conversation", "history": []},
            {"external_search": False},
        )
    )

    assert observed["arxiv_id"] == "2602.24209"
    assert result["intent"] == "answer"
    assert "A Community Agent Workflow for Research Reading" in result["message"]
    assert any(
        trace["provider"] == "import_arxiv_paper" and trace["status"] == "completed"
        for trace in result["tool_trace"]
    )


def test_upsert_conversation_recovers_from_duplicate_insert_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def __init__(self, client):
            self.client = client
            self.action = None
            self.payload = None

        def select(self, *_args, **_kwargs):
            self.action = "select"
            return self

        def order(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def insert(self, payload):
            self.action = "insert"
            self.payload = payload
            return self

        def update(self, payload):
            self.action = "update"
            self.payload = payload
            return self

        def delete(self):
            self.action = "delete"
            return self

        def execute(self):
            if self.action == "select":
                return FakeResponse([])
            if self.action == "insert":
                self.client.insert_calls += 1
                raise APIError(
                    {
                        "message": 'duplicate key value violates unique constraint "community_agent_conversations_pkey"',
                        "code": "23505",
                    }
                )
            if self.action == "update":
                self.client.updated_payload = self.payload
                return FakeResponse(
                    [
                        {
                            "conversation_id": self.payload["conversation_id"],
                            "title": self.payload["title"],
                            "created_at": self.payload.get("created_at"),
                            "updated_at": self.payload["updated_at"],
                            "turns": self.payload["turns"],
                        }
                    ]
                )
            raise AssertionError(f"unexpected action: {self.action}")

    class FakeClient:
        def __init__(self):
            self.insert_calls = 0
            self.updated_payload = None

        def table(self, _name):
            return FakeQuery(self)

    async def fake_run_db_blocking(shared_call, per_call_client_call=None):  # type: ignore[no-untyped-def]
        return per_call_client_call() if per_call_client_call else shared_call()

    fake_client = FakeClient()
    monkeypatch.setattr(
        "backend.app.services.community_agent_service.clone_supabase_client_with_same_auth",
        lambda client: client,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent_service.run_db_blocking",
        fake_run_db_blocking,
    )

    result = asyncio.run(
        community_agent_service.upsert_conversation(
            supabase_client=fake_client,
            record={
                "id": "conversation-race",
                "title": "Race-safe conversation",
                "created_at": "2026-03-23T16:00:00Z",
                "updated_at": "2026-03-23T16:00:01Z",
                "turns": [
                    {
                        "id": "user-1",
                        "role": "user",
                        "content": "Explain the paper.",
                        "created_at": "2026-03-23T16:00:00Z",
                    },
                    {
                        "id": "assistant-1",
                        "role": "assistant",
                        "content": "Here is the grounded answer.",
                        "created_at": "2026-03-23T16:00:01Z",
                        "status": "completed",
                    },
                ],
            },
        )
    )

    assert fake_client.insert_calls == 1
    assert fake_client.updated_payload is not None
    assert len(fake_client.updated_payload["turns"]) == 2
    assert result["id"] == "conversation-race"
