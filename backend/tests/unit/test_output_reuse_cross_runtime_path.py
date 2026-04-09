import asyncio
from pathlib import Path
from types import SimpleNamespace

from backend.app.api.routes import translate as translate_route


def test_find_reusable_output_falls_back_to_local_outputs_dir(monkeypatch, tmp_path: Path):
    outputs_dir = tmp_path / "outputs"
    reusable_task_id = "historical-success-task"
    reusable_output = outputs_dir / reusable_task_id
    reusable_output.mkdir(parents=True, exist_ok=True)

    observed = {}

    class _FakeTranslationTaskRepository:
        def find_reusable_completed_task(self, config_hash: str, *, exclude_task_id: str):
            observed["config_hash"] = config_hash
            observed["exclude_task_id"] = exclude_task_id
            return {
                "task_id": reusable_task_id,
                "output_path": f"/app/backend/data/outputs/{reusable_task_id}",
            }

    async def _fake_run_db_blocking(shared_call, per_call_client_call=None):
        observed["per_call_client_call"] = per_call_client_call
        return shared_call()

    monkeypatch.setattr(translate_route, "settings", SimpleNamespace(outputs_dir=outputs_dir))
    monkeypatch.setattr(
        translate_route,
        "get_translation_task_repository",
        lambda: _FakeTranslationTaskRepository(),
    )
    monkeypatch.setattr(translate_route, "run_db_blocking", _fake_run_db_blocking)

    reusable_path = asyncio.run(
        translate_route.find_reusable_output(
            config_hash="hash-value",
            task_id="current-task-id",
        )
    )

    assert reusable_path == str(reusable_output)
    assert observed == {
        "config_hash": "hash-value",
        "exclude_task_id": "current-task-id",
        "per_call_client_call": None,
    }
