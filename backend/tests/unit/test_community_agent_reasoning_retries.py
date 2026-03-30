import asyncio

import httpx
import pytest

from backend.app.services.community_agent import orchestrator


class _FakeResponse:
    def __init__(self, status_code: int, *, text: str = "", payload: dict | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


def test_chat_completion_retries_transient_http_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(
        [
            _FakeResponse(status_code=403, text="temporary upstream denial"),
            _FakeResponse(
                status_code=200,
                payload={
                    "choices": [
                        {
                            "message": {
                                "content": "ok",
                                "tool_calls": [],
                            }
                        }
                    ]
                },
            ),
        ]
    )
    calls = {"count": 0}

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            del args, kwargs
            calls["count"] += 1
            return next(responses)

    async def _fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(
        orchestrator,
        "_provider_config",
        lambda: ("https://example.com/v1/chat/completions", "key", "model"),
    )
    monkeypatch.setattr(orchestrator.httpx, "AsyncClient", lambda timeout: _FakeClient())
    monkeypatch.setattr(orchestrator.asyncio, "sleep", _fake_sleep)

    result = asyncio.run(
        orchestrator._call_chat_completion(
            messages=[{"role": "user", "content": "ping"}],
            tools=[],
        )
    )
    assert calls["count"] == 2
    assert result is not None
    assert result.get("content") == "ok"


def test_chat_completion_fails_fast_on_non_retryable_status(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            del args, kwargs
            return _FakeResponse(status_code=401, text="unauthorized")

    monkeypatch.setattr(
        orchestrator,
        "_provider_config",
        lambda: ("https://example.com/v1/chat/completions", "key", "model"),
    )
    monkeypatch.setattr(orchestrator.httpx, "AsyncClient", lambda timeout: _FakeClient())

    with pytest.raises(RuntimeError, match="HTTP 401"):
        asyncio.run(
            orchestrator._call_chat_completion(
                messages=[{"role": "user", "content": "ping"}],
                tools=[],
            )
        )


def test_chat_completion_retries_transport_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            del args, kwargs
            calls["count"] += 1
            if calls["count"] == 1:
                raise httpx.ReadTimeout("timed out")
            return _FakeResponse(
                status_code=200,
                payload={
                    "choices": [
                        {
                            "message": {
                                "content": "recovered",
                                "tool_calls": [],
                            }
                        }
                    ]
                },
            )

    async def _fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(
        orchestrator,
        "_provider_config",
        lambda: ("https://example.com/v1/chat/completions", "key", "model"),
    )
    monkeypatch.setattr(orchestrator.httpx, "AsyncClient", lambda timeout: _FakeClient())
    monkeypatch.setattr(orchestrator.asyncio, "sleep", _fake_sleep)

    result = asyncio.run(
        orchestrator._call_chat_completion(
            messages=[{"role": "user", "content": "ping"}],
            tools=[],
        )
    )
    assert calls["count"] == 2
    assert result is not None
    assert result.get("content") == "recovered"
