import asyncio
from typing import Any

import aiohttp
import pytest

from backend.app.services.agents.llm_token_pool import (
    LlmMemberScheduler,
    ProviderErrorKind,
    classify_provider_error,
    post_chat_completion_with_pool,
)


class _FakeResponse:
    def __init__(self, status: int, json_data: dict[str, Any] | None = None):
        self.status = status
        self.headers: dict[str, str] = {}
        self._json_data = json_data or {"choices": [{"message": {"content": "ok"}}]}

    async def json(self) -> dict[str, Any]:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=self.status,
                message=f"HTTP {self.status}",
                headers=self.headers,
            )


class _DelayedPostContext:
    def __init__(self, session: "_DelayedSession", response: _FakeResponse):
        self._session = session
        self._response = response

    async def __aenter__(self) -> _FakeResponse:
        self._session.active += 1
        self._session.max_active = max(self._session.max_active, self._session.active)
        self._session.entered_count += 1
        if self._session.entered_count == 1:
            self._session.first_entered.set()
            await self._session.release_first.wait()
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self._session.active -= 1
        return False


class _DelayedSession:
    def __init__(self):
        self.active = 0
        self.max_active = 0
        self.entered_count = 0
        self.first_entered = asyncio.Event()
        self.release_first = asyncio.Event()
        self.calls: list[dict[str, Any]] = []

    def post(self, base_url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: aiohttp.ClientTimeout):
        self.calls.append({"base_url": base_url, "headers": headers, "payload": json})
        return _DelayedPostContext(self, _FakeResponse(status=200))


@pytest.mark.asyncio
async def test_single_key_default_path_is_scheduler_limited_to_one_inflight_request():
    session = _DelayedSession()
    llm_config = {
        "base_url": "https://single.example/v1/chat/completions",
        "api_key": "single-key",
        "model": "test-model",
    }

    async def _call() -> dict[str, Any]:
        return await post_chat_completion_with_pool(
            session=session,
            llm_config=llm_config,
            payload={"model": "test-model", "messages": []},
            timeout=aiohttp.ClientTimeout(total=5),
        )

    first = asyncio.create_task(_call())
    second = asyncio.create_task(_call())
    await asyncio.wait_for(session.first_entered.wait(), timeout=1)
    await asyncio.sleep(0.05)

    assert session.max_active == 1
    assert len(session.calls) == 1

    session.release_first.set()
    await asyncio.wait_for(asyncio.gather(first, second), timeout=1)

    assert session.max_active == 1
    assert len(session.calls) == 2
    assert all(call["headers"].get("X-LLM-Scheduler-Lease") for call in session.calls)


@pytest.mark.asyncio
async def test_three_independent_members_compute_two_task_leases_with_one_reserve():
    scheduler = LlmMemberScheduler(
        members=[
            {
                "member_id": "m1",
                "base_url": "https://relay-a.example/v1/chat/completions",
                "api_key": "k1",
                "account_id": "acct-1",
                "quota_scope": "independent",
                "concurrency": 1,
            },
            {
                "member_id": "m2",
                "base_url": "https://relay-b.example/v1/chat/completions",
                "api_key": "k2",
                "account_id": "acct-2",
                "quota_scope": "independent",
                "concurrency": 1,
            },
            {
                "member_id": "m3",
                "base_url": "https://relay-c.example/v1/chat/completions",
                "api_key": "k3",
                "account_id": "acct-3",
                "quota_scope": "independent",
                "concurrency": 1,
            },
        ],
        reserve_count=1,
    )

    assert scheduler.community_task_capacity() == 2

    lease_1 = await scheduler.acquire_task_lease("task-1")
    lease_2 = await scheduler.acquire_task_lease("task-2")

    assert {lease_1.member_id, lease_2.member_id} <= {"m1", "m2", "m3"}
    assert lease_1.member_id != lease_2.member_id
    assert scheduler.reserve_member_ids() == ({"m1", "m2", "m3"} - {lease_1.member_id, lease_2.member_id})

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(scheduler.acquire_task_lease("task-3"), timeout=0.05)

    await scheduler.release_task_lease("task-1")
    lease_3 = await asyncio.wait_for(scheduler.acquire_task_lease("task-3"), timeout=1)
    assert lease_3.member_id == lease_1.member_id


def test_provider_error_classification_marks_auth_quota_and_model_as_fatal():
    assert classify_provider_error(429, "rate limit").kind is ProviderErrorKind.RETRYABLE_RATE_LIMIT
    assert classify_provider_error(503, "upstream unavailable").kind is ProviderErrorKind.RETRYABLE_TRANSIENT

    for status, body in [
        (401, "invalid api key"),
        (403, "forbidden"),
        (429, "quota exhausted"),
        (400, "model not available"),
        (404, "unsupported model"),
    ]:
        classification = classify_provider_error(status, body)
        assert classification.kind is ProviderErrorKind.FATAL
        assert classification.retryable is False


def test_settings_builds_scheduler_pool_from_llm_members_json():
    from backend.app.core.config import Settings

    settings = Settings(
        _env_file=None,
        llm_api_key="fallback-key",
        llm_base_url="https://fallback.example/v1/chat/completions",
        llm_model="gpt-4o",
        llm_pool_reserve_count=1,
        llm_members_json="""
        [
          {
            "member_id": "m1",
            "base_url": "https://relay-a.example",
            "api_key": "k1",
            "account_id": "acct-1",
            "quota_scope": "independent",
            "concurrency": 2
          },
          {
            "member_id": "m2",
            "base_url": "https://relay-b.example/v1",
            "api_key": "k2",
            "account_id": "acct-2",
            "quota_scope": "independent"
          }
        ]
        """,
    )

    config = settings.get_llm_config()

    assert config["pool_mode"] == "system_managed"
    assert config["reserve_count"] == 1
    assert config["pool_members"][0] == {
        "member_id": "m1",
        "base_url": "https://relay-a.example/v1/chat/completions",
        "api_key": "k1",
        "account_id": "acct-1",
        "quota_scope": "independent",
        "concurrency": 2,
        "reserve": False,
    }
    assert config["pool_members"][1]["base_url"] == "https://relay-b.example/v1/chat/completions"
