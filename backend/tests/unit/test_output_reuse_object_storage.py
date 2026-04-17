import asyncio
from types import SimpleNamespace

from backend.app.api.routes import translate as translate_route


def test_find_reusable_output_accepts_object_storage_path_without_local_files(monkeypatch):
    class _FakeTranslationTaskRepository:
        def find_reusable_completed_task(self, config_hash: str, *, exclude_task_id: str):
            assert config_hash == "hash-value"
            assert exclude_task_id == "current-task-id"
            return {
                "task_id": "historical-success-task",
                "output_path": "data/outputs/historical-success-task",
            }

    async def _fake_run_db_blocking(shared_call, per_call_client_call=None):
        return shared_call()

    monkeypatch.setattr(
        translate_route,
        "settings",
        SimpleNamespace(outputs_dir="/unused", storage_backend_mode="cos"),
    )
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

    assert reusable_path == "data/outputs/historical-success-task"
