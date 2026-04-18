import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List

import aiohttp
import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy/v1/chat/completions")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import translate as translate_route
from backend.app.core import config as config_module
from backend.app.models.config_models import AdvancedConfig
from backend.app.services.agents.translator_agent import TranslatorAgent


class _FakeResponse:
    def __init__(self, status: int, json_data: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None):
        self.status = status
        self._json_data = json_data or {}
        self.headers = headers or {}

    async def json(self) -> Dict[str, Any]:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status >= 400 and self.status not in (429, 503):
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=self.status,
                message=f"HTTP {self.status}",
                headers=self.headers,
            )


class _FakePostContext:
    def __init__(self, response: _FakeResponse):
        self._response = response

    async def __aenter__(self) -> _FakeResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeSession:
    def __init__(self, responses: List[_FakeResponse]):
        self._responses = list(responses)
        self.calls: List[Dict[str, Any]] = []

    def post(self, base_url: str, *, json: Dict[str, Any], headers: Dict[str, str], timeout: aiohttp.ClientTimeout):
        if not self._responses:
            raise AssertionError("No fake responses left for session.post")
        auth = str(headers.get("Authorization") or "")
        token = auth.removeprefix("Bearer ").strip()
        self.calls.append(
            {
                "base_url": base_url,
                "api_key": token,
                "member_id": headers.get("X-LLM-Pool-Member"),
                "payload": json,
            }
        )
        return _FakePostContext(self._responses.pop(0))


def _build_translator(tmp_path: Path, llm_config: Dict[str, Any]) -> TranslatorAgent:
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True, exist_ok=True)
    return TranslatorAgent(
        config={
            "target_language": "zh",
            "source_language": "en",
            "llm_config": llm_config,
        },
        trans_mode=0,
        project_dir=str(tmp_path),
        output_dir=str(output_dir),
        generate_terminology=False,
    )


def test_settings_parse_system_llm_pool_groups_json():
    settings = config_module.Settings(
        _env_file=None,
        llm_api_key="dummy-key",
        llm_base_url="http://dummy/v1/chat/completions",
        llm_model="gpt-4o",
        llm_system_pool_groups_json='[{"base_url":"https://relay-a.example/v1/chat/completions","api_keys":["k1","k2"]},{"base_url":"https://relay-b.example/v1/chat/completions","api_keys":["k3","k4","k5"]}]',
    )

    groups = settings.get_llm_system_pool_groups()

    assert len(groups) == 2
    assert groups[0]["api_keys"] == ["k1", "k2"]
    assert groups[1]["api_keys"] == ["k3", "k4", "k5"]


@pytest.mark.asyncio
async def test_build_llm_config_async_uses_system_pool_for_author_api(monkeypatch):
    monkeypatch.setattr(
        type(translate_route.settings),
        "get_llm_system_pool_groups",
        lambda self: [
            {"group_id": "g1", "base_url": "https://relay-a.example/v1/chat/completions", "api_keys": ["k1", "k2"]},
            {"group_id": "g2", "base_url": "https://relay-b.example/v1/chat/completions", "api_keys": ["k3", "k4", "k5"]},
        ],
        raising=False,
    )
    monkeypatch.setattr(translate_route.settings, "llm_timeout", 120, raising=False)

    cfg = await translate_route.build_llm_config_async(AdvancedConfig(use_author_api=True), user_id=None)

    assert cfg["pool_mode"] == "system_managed"
    assert len(cfg["pool_members"]) == 5


@pytest.mark.asyncio
async def test_build_llm_config_async_keeps_custom_user_key_single_route():
    cfg = await translate_route.build_llm_config_async(
        AdvancedConfig(
            use_author_api=False,
            custom_base_url="https://custom.example",
            custom_api_key="user-key",
        ),
        user_id=None,
    )

    assert cfg.get("pool_mode") != "system_managed"
    assert cfg["api_key"] == "user-key"


@pytest.mark.asyncio
async def test_pool_fails_over_to_another_member_after_429():
    from backend.app.services.agents.llm_token_pool import post_chat_completion_with_pool

    llm_config = {
        "model": "test-model",
        "pool_mode": "system_managed",
        "pool_members": [
            {"member_id": "a1", "base_url": "https://relay-a.example/v1/chat/completions", "api_key": "k1"},
            {"member_id": "a2", "base_url": "https://relay-a.example/v1/chat/completions", "api_key": "k2"},
        ],
    }
    session = _FakeSession(
        [
            _FakeResponse(status=429, headers={"Retry-After": "0"}),
            _FakeResponse(status=200, json_data={"choices": [{"message": {"content": "ok"}}]}),
        ]
    )

    result = await post_chat_completion_with_pool(
        session=session,
        llm_config=llm_config,
        payload={"model": "test-model", "messages": []},
        timeout=aiohttp.ClientTimeout(total=5),
    )

    assert result["choices"][0]["message"]["content"] == "ok"
    assert len(session.calls) == 2
    assert session.calls[0]["api_key"] != session.calls[1]["api_key"]


@pytest.mark.asyncio
async def test_pool_switches_after_consecutive_503():
    from backend.app.services.agents.llm_token_pool import post_chat_completion_with_pool

    llm_config = {
        "model": "test-model",
        "pool_mode": "system_managed",
        "pool_members": [
            {"member_id": "a1", "base_url": "https://relay-a.example/v1/chat/completions", "api_key": "k1"},
            {"member_id": "b1", "base_url": "https://relay-b.example/v1/chat/completions", "api_key": "k3"},
        ],
    }
    session = _FakeSession(
        [
            _FakeResponse(status=503),
            _FakeResponse(status=503),
            _FakeResponse(status=200, json_data={"choices": [{"message": {"content": "ok"}}]}),
        ]
    )

    result = await post_chat_completion_with_pool(
        session=session,
        llm_config=llm_config,
        payload={"model": "test-model", "messages": []},
        timeout=aiohttp.ClientTimeout(total=5),
    )

    assert result["choices"][0]["message"]["content"] == "ok"
    assert len(session.calls) == 3
    assert session.calls[0]["api_key"] == session.calls[1]["api_key"]
    assert session.calls[1]["api_key"] != session.calls[2]["api_key"]


@pytest.mark.asyncio
async def test_pool_sticks_to_current_member_when_all_members_exhausted():
    from backend.app.services.agents.llm_token_pool import post_chat_completion_with_pool

    llm_config = {
        "model": "test-model",
        "pool_mode": "system_managed",
        "pool_members": [
            {"member_id": "solo", "base_url": "https://relay-a.example/v1/chat/completions", "api_key": "k1"},
        ],
    }
    session = _FakeSession(
        [
            _FakeResponse(status=429, headers={"Retry-After": "0"}),
            _FakeResponse(status=429, headers={"Retry-After": "0"}),
            _FakeResponse(status=200, json_data={"choices": [{"message": {"content": "ok"}}]}),
        ]
    )

    result = await post_chat_completion_with_pool(
        session=session,
        llm_config=llm_config,
        payload={"model": "test-model", "messages": []},
        timeout=aiohttp.ClientTimeout(total=5),
    )

    assert result["choices"][0]["message"]["content"] == "ok"
    assert len({call["api_key"] for call in session.calls}) == 1


@pytest.mark.asyncio
async def test_translator_agent_system_pool_uses_pool_helper(monkeypatch, tmp_path: Path):
    import backend.app.services.agents.translator_agent as translator_module

    agent = _build_translator(
        tmp_path,
        {
            "model": "test-model",
            "pool_mode": "system_managed",
            "pool_members": [
                {"member_id": "a1", "base_url": "https://relay-a.example/v1/chat/completions", "api_key": "k1"},
                {"member_id": "a2", "base_url": "https://relay-a.example/v1/chat/completions", "api_key": "k2"},
            ],
        },
    )
    monkeypatch.setattr(
        agent,
        "_prepare_llm_payload_text",
        lambda text: (text, {"mask_mapping": {}, "hard_freeze_audit_entries": []}),
    )
    monkeypatch.setattr(agent, "_restore_llm_output_text", lambda text, _ctx: text)
    monkeypatch.setattr(agent, "_log_protection_actions", lambda *args, **kwargs: None)

    called: Dict[str, Any] = {}

    async def _fake_pool_call(**kwargs):
        called["pool_mode"] = kwargs["llm_config"].get("pool_mode")
        return {"choices": [{"message": {"content": "translated"}}]}

    monkeypatch.setattr(translator_module, "post_chat_completion_with_pool", _fake_pool_call, raising=False)

    class _BoomSession:
        def post(self, *args, **kwargs):
            raise AssertionError("session.post should not be called directly for pooled system credentials")

    result = await agent._call_llm_with_freeze(
        system_prompt="Translate",
        user_text="hello world",
        fail_part="sec_1",
        part_type="sec",
        session=_BoomSession(),
        fallback_text="fallback",
        include_glossary=False,
    )

    assert result == "translated"
    assert called["pool_mode"] == "system_managed"
