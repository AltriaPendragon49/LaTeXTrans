import asyncio
import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")
os.environ["ASYNC_BLOCKING_WRAPPERS_ENABLED"] = "true"
os.environ["DB_EXECUTION_MODE"] = "per_call_client"


def test_run_db_blocking_prefers_per_call_client():
    from backend.app.utils.async_blocking import run_db_blocking

    calls = {"shared": 0, "per_call": 0}

    def _shared():
        calls["shared"] += 1
        return "shared"

    def _per_call():
        calls["per_call"] += 1
        return "per_call"

    result = asyncio.run(
        run_db_blocking(_shared, per_call_client_call=_per_call)
    )
    assert result == "per_call"
    assert calls["per_call"] == 1
    assert calls["shared"] == 0

