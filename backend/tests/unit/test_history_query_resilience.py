import asyncio
import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import history as history_route


class _ExecuteQuery:
    def __init__(self, label: str):
        self.label = label

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self.label == "shared":
            raise AssertionError("shared authenticated client should not execute in threaded mode")

        class _Result:
            data = []
            count = 0

        return _Result()


class _Client:
    def __init__(self, label: str):
        self.label = label

    def table(self, table_name):
        assert table_name == "translation_tasks"
        return _ExecuteQuery(self.label)


def test_history_query_uses_per_call_authenticated_clone(monkeypatch):
    async def _fake_run_db_blocking(_shared_call, *, per_call_client_call=None):
        assert per_call_client_call is not None
        return per_call_client_call()

    monkeypatch.setattr(history_route, "run_db_blocking", _fake_run_db_blocking)
    monkeypatch.setattr(
        history_route,
        "clone_supabase_client_with_same_auth",
        lambda _client: _Client("per-call"),
    )

    result, offset = asyncio.run(
        history_route._execute_history_list_query(
            _Client("shared"),
            page=1,
            page_size=10,
            status_filter=None,
        )
    )

    assert result.count == 0
    assert offset == 0
