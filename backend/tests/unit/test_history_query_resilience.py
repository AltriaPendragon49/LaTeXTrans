import asyncio
import os

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import history as history_route


class _Repository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int, str | None]] = []

    def list_tasks_for_user(self, user_id: str, *, page: int, page_size: int, status_filter: str | None):
        self.calls.append((user_id, page, page_size, status_filter))
        return [], 0


def test_history_route_queries_local_repository_via_run_db_blocking(monkeypatch):
    repository = _Repository()

    async def _fake_run_db_blocking(shared_call, *, per_call_client_call=None):
        assert per_call_client_call is None
        return shared_call()

    monkeypatch.setattr(history_route, "run_db_blocking", _fake_run_db_blocking)

    response = asyncio.run(
        history_route.get_user_history(
            current_user={"id": "usr_local_1", "roles": ["user"]},
            repository=repository,
            page=1,
            page_size=10,
            status_filter=None,
        )
    )

    assert response.total == 0
    assert response.tasks == []
    assert repository.calls == [("usr_local_1", 1, 10, None)]
