import asyncio
import json
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


def test_create_agent_run_injects_verified_owner_user_id_into_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_context: dict[str, object] = {}

    async def fake_run_agent(*, input_text, context, skill_toggles, run_mode, event_callback):  # type: ignore[no-untyped-def]
        del input_text, skill_toggles, run_mode, event_callback
        observed_context.update(context or {})
        return {
            "status": "completed",
            "intent": "answer",
            "message": "ok",
            "summary": "ok",
            "tool_trace": [],
            "citations": [],
            "provider_state": {"internal_search": "enabled"},
            "action": None,
            "events": [],
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.run_agent",
        fake_run_agent,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "hello",
            {"source": "conversation"},
            {"external_search": False},
            owner_user_id="user-123",
        )
    )

    assert result["status"] == "completed"
    assert observed_context["user_id"] == "user-123"


def test_create_agent_run_does_not_store_runtime_access_token_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_agent(*, input_text, context, skill_toggles, run_mode, event_callback):  # type: ignore[no-untyped-def]
        del input_text, context, skill_toggles, run_mode, event_callback
        return {
            "status": "completed",
            "intent": "answer",
            "message": "ok",
            "summary": "ok",
            "tool_trace": [],
            "citations": [],
            "provider_state": {"internal_search": "enabled"},
            "action": None,
            "events": [],
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.run_agent",
        fake_run_agent,
    )

    payload = asyncio.run(
        community_agent_service.create_agent_run(
            "hello",
            {"source": "conversation"},
            {"external_search": False},
            owner_user_id="user-123",
            access_token="header.payload.signature",
        )
    )

    runtime_record = community_agent_service._RUNTIME_AGENT_RUNS[payload["run_id"]]
    assert not hasattr(runtime_record, "auth_token_hash")


def test_agent_run_requires_matching_owner_user_id(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_agent(*, input_text, context, skill_toggles, run_mode, event_callback):  # type: ignore[no-untyped-def]
        del input_text, context, skill_toggles, run_mode, event_callback
        return {
            "status": "completed",
            "intent": "answer",
            "message": "ok",
            "summary": "ok",
            "tool_trace": [],
            "citations": [],
            "provider_state": {"internal_search": "enabled"},
            "action": None,
            "events": [],
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.run_agent",
        fake_run_agent,
    )

    created = asyncio.run(
        community_agent_service.create_agent_run(
            "hello",
            {"source": "conversation"},
            {"external_search": False},
            owner_user_id="user-123",
        )
    )

    payload = asyncio.run(
        community_agent_service.get_agent_run(
            created["run_id"],
            owner_user_id="user-123",
        )
    )
    assert payload["run_id"] == created["run_id"]

    with pytest.raises(PermissionError):
        asyncio.run(
            community_agent_service.get_agent_run(
                created["run_id"],
                owner_user_id="user-456",
            )
        )


def test_get_agent_run_uses_authorize_entrypoint_for_owner_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorize_calls: list[dict[str, object]] = []

    class _Decision:
        allowed = False
        reason = "policy denied run access"

    async def fake_run_agent(*, input_text, context, skill_toggles, run_mode, event_callback):  # type: ignore[no-untyped-def]
        del input_text, context, skill_toggles, run_mode, event_callback
        return {
            "status": "completed",
            "intent": "answer",
            "message": "ok",
            "summary": "ok",
            "tool_trace": [],
            "citations": [],
            "provider_state": {"internal_search": "enabled"},
            "action": None,
            "events": [],
        }

    def fake_authorize(user, resource, action, context=None):  # type: ignore[no-untyped-def]
        authorize_calls.append(
            {
                "user": user,
                "resource": resource,
                "action": action,
                "context": context,
            }
        )
        return _Decision()

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.run_agent",
        fake_run_agent,
    )
    monkeypatch.setattr(
        community_agent_service,
        "authorize",
        fake_authorize,
        raising=False,
    )

    created = asyncio.run(
        community_agent_service.create_agent_run(
            "hello",
            {"source": "conversation"},
            {"external_search": False},
            owner_user_id="user-123",
        )
    )

    with pytest.raises(PermissionError, match="policy denied run access"):
        asyncio.run(
            community_agent_service.get_agent_run(
                created["run_id"],
                owner_user_id="user-456",
                strict=True,
            )
        )

    assert authorize_calls
    assert authorize_calls[0]["resource"] == "community_run"
    assert authorize_calls[0]["action"] == "read"


def test_get_agent_run_strict_raises_when_missing() -> None:
    with pytest.raises(community_agent_service.RunNotFoundError):
        asyncio.run(
            community_agent_service.get_agent_run(
                "run-missing-strict-test",
                access_token="header.payload.signature",
                strict=True,
            )
        )


def test_get_agent_run_falls_back_to_repository_when_runtime_state_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRunRepository:
        def get_run(self, run_id: str):  # type: ignore[no-untyped-def]
            assert run_id == "run-db-1"
            return {
                "run_id": run_id,
                "user_id": "user-123",
                "status": "completed",
                "intent": "answer",
                "mode": "chat",
                "message": "from-db",
                "summary": "from-db",
                "error": None,
                "report": None,
            }

        def list_events(self, run_id: str):  # type: ignore[no-untyped-def]
            assert run_id == "run-db-1"
            return [
                {
                    "type": "status",
                    "run_id": run_id,
                    "sequence": 1,
                    "timestamp": "2026-04-09T10:00:00+00:00",
                    "data": {"status": "running"},
                },
                {
                    "type": "complete",
                    "run_id": run_id,
                    "sequence": 2,
                    "timestamp": "2026-04-09T10:00:01+00:00",
                    "data": {
                        "snapshot": {
                            "run_id": run_id,
                            "status": "completed",
                            "intent": "answer",
                            "mode": "chat",
                            "message": "from-db",
                            "summary": "from-db",
                            "tool_trace": [],
                            "citations": [],
                            "provider_state": {"internal_search": "enabled"},
                            "action": None,
                            "report": None,
                            "events": [],
                        }
                    },
                },
            ]

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.CommunityAgentRunRepository",
        lambda: FakeRunRepository(),
    )

    payload = asyncio.run(
        community_agent_service.get_agent_run(
            "run-db-1",
            owner_user_id="user-123",
            strict=True,
        )
    )

    assert payload["run_id"] == "run-db-1"
    assert payload["status"] == "completed"
    assert payload["message"] == "from-db"
    assert len(payload["events"]) == 2


def test_get_agent_run_repository_fallback_enforces_owner_user_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRunRepository:
        def get_run(self, run_id: str):  # type: ignore[no-untyped-def]
            return {
                "run_id": run_id,
                "user_id": "user-123",
                "status": "completed",
                "intent": "answer",
                "mode": "chat",
                "message": "from-db",
                "summary": "from-db",
                "error": None,
                "report": None,
            }

        def list_events(self, run_id: str):  # type: ignore[no-untyped-def]
            return []

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.CommunityAgentRunRepository",
        lambda: FakeRunRepository(),
    )

    with pytest.raises(PermissionError):
        asyncio.run(
            community_agent_service.get_agent_run(
                "run-db-2",
                owner_user_id="other-user",
            )
        )


def test_create_agent_run_attempts_repository_persistence_for_owned_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved: dict[str, object] = {"run_upserts": [], "events": []}

    class FakeRunRepository:
        def upsert_run(self, record: dict[str, object]):  # type: ignore[no-untyped-def]
            saved["run_upserts"].append(record)

        def append_event(self, run_id: str, sequence_no: int, event: dict[str, object]):  # type: ignore[no-untyped-def]
            saved["events"].append((run_id, sequence_no, event))

    async def fake_run_agent(*, input_text, context, skill_toggles, run_mode, event_callback):  # type: ignore[no-untyped-def]
        del input_text, context, skill_toggles, run_mode, event_callback
        return {
            "status": "completed",
            "intent": "answer",
            "mode": "chat",
            "message": "ok",
            "summary": "ok",
            "tool_trace": [],
            "citations": [],
            "provider_state": {"internal_search": "enabled"},
            "action": None,
            "report": None,
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.CommunityAgentRunRepository",
        lambda: FakeRunRepository(),
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent_service.run_agent",
        fake_run_agent,
    )

    payload = asyncio.run(
        community_agent_service.create_agent_run(
            "hello",
            {"source": "conversation"},
            {"external_search": False},
            owner_user_id="user-123",
        )
    )

    assert payload["status"] == "completed"
    assert saved["run_upserts"]
    assert saved["events"]


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
        "backend.app.services.paper_service.list_community_papers",
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
    assert not any(trace["provider"] == "start_translation_kernel" for trace in result["tool_trace"])


def test_exact_paper_title_lookup_bridges_to_translation_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            _tool_call(
                "community_search_papers",
                '{"query":"Attention Is All You Need","limit":3}',
            ),
            {
                "role": "assistant",
                "content": "I found the paper and can summarize it while translation starts.",
            },
        ]
    )

    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        assert messages
        assert any(tool["function"]["name"] == "community_search_papers" for tool in tools)
        return next(responses)

    async def fake_search_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        del arguments, runtime_state
        return {
            "query_executed": "Attention Is All You Need",
            "results": [
                {
                    "id": "paper-1706",
                    "title": "Attention Is All You Need",
                    "url": "/paper/paper-1706",
                    "source": "community",
                    "arxiv_id": "1706.03762",
                    "paper_id": "paper-1706",
                    "snippet": "Transformer architecture paper.",
                }
            ],
            "count": 1,
        }

    async def fake_read_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["paper_id"] == "paper-1706"
        del runtime_state
        return {
            "paper_id": "paper-1706",
            "title": "Attention Is All You Need",
            "arxiv_id": "1706.03762",
            "translated_ready": False,
            "abstract_raw": "The paper introduces the Transformer architecture.",
            "abstract_translated": None,
        }

    async def fake_translate_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["paper_id"] == "paper-1706"
        del runtime_state
        return {
            "paper_id": "paper-1706",
            "task_id": "task-bridge-1706",
            "status": "queued",
            "reused_existing_task": False,
            "processing_url": "/processing?taskId=task-bridge-1706",
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._call_chat_completion",
        fake_call_chat_completion,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.community_search.CommunitySearchPapersSkill.execute",
        fake_search_execute,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.read_paper_context.ReadPaperContextSkill.execute",
        fake_read_execute,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.start_translation_kernel.StartTranslationKernelSkill.execute",
        fake_translate_execute,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "Attention Is All You Need",
            {"source": "conversation", "history": []},
            {"external_search": False},
        )
    )

    assert result["action"]["paper_id"] == "paper-1706"
    assert result["action"]["task_id"] == "task-bridge-1706"
    assert any(trace["provider"] == "read_paper_context" for trace in result["tool_trace"])
    assert any(trace["provider"] == "start_translation_kernel" for trace in result["tool_trace"])


def test_title_only_query_without_community_hit_resolves_and_starts_translation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            {
                "role": "assistant",
                "content": "I cannot find this paper in community yet.",
            }
        ]
    )

    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        assert messages
        assert tools
        return next(responses)

    async def fake_resolve_arxiv_id_from_title(query: str) -> str | None:
        assert query == "Attention Is All You Need"
        return "1706.03762"

    async def fake_import_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["arxiv_id"] == "1706.03762"
        return {"paper_id": "paper-1706", "imported": True, "reused": False}

    async def fake_read_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["paper_id"] == "paper-1706"
        return {
            "paper_id": "paper-1706",
            "title": "Attention Is All You Need",
            "arxiv_id": "1706.03762",
            "translated_ready": False,
            "abstract_raw": "The paper introduces the Transformer architecture.",
            "abstract_translated": None,
        }

    async def fake_translate_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["paper_id"] == "paper-1706"
        return {
            "paper_id": "paper-1706",
            "task_id": "task-title-1706",
            "status": "queued",
            "reused_existing_task": False,
            "processing_url": "/processing?taskId=task-title-1706",
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._call_chat_completion",
        fake_call_chat_completion,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._resolve_arxiv_id_from_title",
        fake_resolve_arxiv_id_from_title,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.import_arxiv_paper.ImportArxivPaperSkill.execute",
        fake_import_execute,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.read_paper_context.ReadPaperContextSkill.execute",
        fake_read_execute,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.start_translation_kernel.StartTranslationKernelSkill.execute",
        fake_translate_execute,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "Attention Is All You Need",
            {"source": "conversation", "history": []},
            {"external_search": False},
        )
    )

    assert result["action"]["paper_id"] == "paper-1706"
    assert result["action"]["task_id"] == "task-title-1706"
    assert any(trace["provider"] == "resolve_arxiv_by_title" and trace["status"] == "completed" for trace in result["tool_trace"])
    assert any(trace["provider"] == "import_arxiv_paper" for trace in result["tool_trace"])
    assert any(trace["provider"] == "start_translation_kernel" for trace in result["tool_trace"])


def test_title_only_query_after_empty_search_still_resolves_and_starts_translation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    title = "LaTeXTrans: Structured LaTeX Translation with Multi-Agent Coordination"
    responses = iter(
        [
            _tool_call(
                "community_search_papers",
                json.dumps({"query": title, "limit": 1}),
                call_id="call-search",
            ),
            {
                "role": "assistant",
                "content": "No exact match was found in the community.",
            },
        ]
    )

    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        assert messages
        assert tools
        return next(responses)

    async def fake_search_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["query"] == title
        del runtime_state
        return {"query_executed": title, "results": [], "count": 0}

    async def fake_resolve_arxiv_id_from_title(query: str) -> str | None:
        assert query == title
        return "2508.18791"

    async def fake_import_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["arxiv_id"] == "2508.18791"
        return {"paper_id": "paper-2508", "imported": True, "reused": False}

    async def fake_read_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["paper_id"] == "paper-2508"
        return {
            "paper_id": "paper-2508",
            "title": title,
            "arxiv_id": "2508.18791",
            "translated_ready": False,
            "abstract_raw": "A structured LaTeX translation framework.",
            "abstract_translated": None,
        }

    async def fake_translate_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["paper_id"] == "paper-2508"
        return {
            "paper_id": "paper-2508",
            "task_id": "task-title-fallback-2508",
            "status": "queued",
            "reused_existing_task": False,
            "processing_url": "/processing?taskId=task-title-fallback-2508",
        }

    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._call_chat_completion",
        fake_call_chat_completion,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.community_search.CommunitySearchPapersSkill.execute",
        fake_search_execute,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.orchestrator._resolve_arxiv_id_from_title",
        fake_resolve_arxiv_id_from_title,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.import_arxiv_paper.ImportArxivPaperSkill.execute",
        fake_import_execute,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.read_paper_context.ReadPaperContextSkill.execute",
        fake_read_execute,
    )
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.start_translation_kernel.StartTranslationKernelSkill.execute",
        fake_translate_execute,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            title,
            {"source": "conversation", "history": []},
            {"external_search": False},
        )
    )

    assert result["action"]["paper_id"] == "paper-2508"
    assert result["action"]["task_id"] == "task-title-fallback-2508"
    assert any(trace["provider"] == "resolve_arxiv_by_title" and trace["status"] == "completed" for trace in result["tool_trace"])
    assert any(trace["provider"] == "import_arxiv_paper" for trace in result["tool_trace"])
    assert any(trace["provider"] == "start_translation_kernel" for trace in result["tool_trace"])


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


def test_nonexistent_community_paper_can_be_imported_and_auto_translation_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            _tool_call("import_arxiv_paper", '{"arxiv_id":"1706.03762"}', call_id="call-import"),
            _tool_call("read_paper_context", '{"paper_id":"paper-1706"}', call_id="call-read"),
            _tool_call(
                "start_translation_kernel",
                '{"paper_id":"paper-1706","source_language":"en","target_language":"zh"}',
                call_id="call-translate",
            ),
            {
                "role": "assistant",
                "content": (
                    "《Attention Is All You Need》提出了 Transformer，并且我已经在后台启动默认翻译流程，"
                    "你可以现在先开始阅读。"
                ),
            },
        ]
    )

    async def fake_call_chat_completion(*, messages, tools):  # type: ignore[no-untyped-def]
        assert messages
        tool_names = {tool["function"]["name"] for tool in tools}
        assert "import_arxiv_paper" in tool_names
        return next(responses)

    async def fake_import_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["arxiv_id"] == "1706.03762"
        return {"paper_id": "paper-1706", "imported": True, "reused": False}

    async def fake_read_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["paper_id"] == "paper-1706"
        return {
            "paper_id": "paper-1706",
            "title": "Attention Is All You Need",
            "arxiv_id": "1706.03762",
            "translated_ready": False,
            "abstract_raw": "The paper introduces the Transformer architecture.",
            "abstract_translated": None,
        }

    async def fake_translate_execute(self, arguments, runtime_state):  # type: ignore[no-untyped-def]
        assert arguments["paper_id"] == "paper-1706"
        return {
            "paper_id": "paper-1706",
            "task_id": "task-1706",
            "status": "queued",
            "reused_existing_task": False,
            "processing_url": "/processing?taskId=task-1706",
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
    monkeypatch.setattr(
        "backend.app.services.community_agent.skills.start_translation_kernel.StartTranslationKernelSkill.execute",
        fake_translate_execute,
    )

    result = asyncio.run(
        community_agent_service.create_agent_run(
            "请导入 arXiv 1706.03762，并启动默认翻译流程。",
            {"source": "conversation", "history": []},
            {"external_search": False},
        )
    )

    assert result["intent"] == "translate"
    assert "Attention Is All You Need" in result["message"]
    assert result["action"]["paper_id"] == "paper-1706"
    assert result["action"]["task_id"] == "task-1706"
    assert result["action"]["auto_started_translation"] is True
    assert any(trace["provider"] == "import_arxiv_paper" for trace in result["tool_trace"])
    assert any(trace["provider"] == "start_translation_kernel" for trace in result["tool_trace"])


def test_local_conversation_crud_routes_owner_to_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeRepository:
        def list_conversations_for_user(self, user_id: str):  # type: ignore[no-untyped-def]
            captured["list_user_id"] = user_id
            return [
                {
                    "id": "conversation-1",
                    "title": "Grounded chat",
                    "created_at": "2026-03-23T16:00:00Z",
                    "updated_at": "2026-03-23T16:00:01Z",
                    "turns": [],
                }
            ]

        def upsert_conversation_for_user(self, user_id: str, record: dict[str, object]):  # type: ignore[no-untyped-def]
            captured["upsert_user_id"] = user_id
            captured["upsert_record"] = record
            return record

        def delete_conversation_for_user(self, user_id: str, conversation_id: str):  # type: ignore[no-untyped-def]
            captured["delete_user_id"] = user_id
            captured["delete_conversation_id"] = conversation_id
            return True

    monkeypatch.setattr(
        "backend.app.services.community_agent_service.CommunityAgentConversationRepository",
        lambda: FakeRepository(),
    )

    listed = asyncio.run(
        community_agent_service.list_conversations(owner_user_id="usr-local-1")
    )
    upserted = asyncio.run(
        community_agent_service.upsert_conversation(
            owner_user_id="usr-local-1",
            record={
                "id": "conversation-1",
                "title": "Grounded chat",
                "created_at": "2026-03-23T16:00:00Z",
                "updated_at": "2026-03-23T16:00:01Z",
                "turns": [],
            },
        )
    )
    deleted = asyncio.run(
        community_agent_service.delete_conversation(
            owner_user_id="usr-local-1",
            conversation_id="conversation-1",
        )
    )

    assert listed[0]["id"] == "conversation-1"
    assert upserted["id"] == "conversation-1"
    assert deleted == {"deleted": True, "conversation_id": "conversation-1"}
    assert captured["list_user_id"] == "usr-local-1"
    assert captured["upsert_user_id"] == "usr-local-1"
    assert captured["delete_user_id"] == "usr-local-1"
    assert captured["delete_conversation_id"] == "conversation-1"
