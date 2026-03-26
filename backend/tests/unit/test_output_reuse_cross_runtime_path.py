import asyncio
from pathlib import Path
from types import SimpleNamespace

from backend.app.api.routes import translate as translate_route


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client, rows):
        self._client = client
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, _key, _value):
        return self

    def in_(self, key, values):
        if key == "status":
            self._client.captured_status_values = list(values)
        return self

    def neq(self, _key, _value):
        return self

    def limit(self, _value):
        return self

    def execute(self):
        return _FakeResult(self._rows)


class _FakeClient:
    def __init__(self, rows):
        self._rows = rows
        self.captured_status_values = None

    def table(self, _name: str):
        return _FakeQuery(self, self._rows)


def test_find_reusable_output_falls_back_to_local_outputs_dir(monkeypatch, tmp_path: Path):
    outputs_dir = tmp_path / "outputs"
    reusable_task_id = "historical-success-task"
    reusable_output = outputs_dir / reusable_task_id
    reusable_output.mkdir(parents=True, exist_ok=True)

    fake_client = _FakeClient(
        [
            {
                "task_id": reusable_task_id,
                "output_path": f"/app/backend/data/outputs/{reusable_task_id}",
            }
        ]
    )

    async def _fake_run_db_blocking(shared_call, per_call_client_call=None):
        return shared_call()

    monkeypatch.setattr(translate_route, "settings", SimpleNamespace(outputs_dir=outputs_dir))
    monkeypatch.setattr(translate_route, "get_supabase_admin_client", lambda: fake_client)
    monkeypatch.setattr(translate_route, "create_supabase_admin_client", lambda: fake_client)
    monkeypatch.setattr(translate_route, "run_db_blocking", _fake_run_db_blocking)

    reusable_path = asyncio.run(
        translate_route.find_reusable_output(
            config_hash="hash-value",
            task_id="current-task-id",
        )
    )

    assert reusable_path == str(reusable_output)
    assert fake_client.captured_status_values == ["completed", "completed_with_warnings"]
