import asyncio

import httpx

from backend.app.services import paper_service


def test_run_db_blocking_with_retry_recovers_from_connect_timeout(monkeypatch):
    calls = {"count": 0}

    async def _fake_run_db_blocking(_operation):
        calls["count"] += 1
        if calls["count"] < 3:
            raise httpx.ConnectTimeout("timeout")
        return {"ok": True}

    monkeypatch.setattr(paper_service, "run_db_blocking", _fake_run_db_blocking)

    result = asyncio.run(
        paper_service._run_db_blocking_with_retry(
            "retry_connect_timeout",
            lambda: {"unused": True},
        )
    )

    assert result == {"ok": True}
    assert calls["count"] == 3


def test_run_db_blocking_with_retry_raises_after_exhausted_retries(monkeypatch):
    calls = {"count": 0}

    async def _fake_run_db_blocking(_operation):
        calls["count"] += 1
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(paper_service, "run_db_blocking", _fake_run_db_blocking)

    try:
        asyncio.run(
            paper_service._run_db_blocking_with_retry(
                "retry_exhausted",
                lambda: {"unused": True},
                retries=1,
            )
        )
        assert False, "expected ConnectTimeout"
    except httpx.ConnectTimeout:
        pass

    assert calls["count"] == 2
