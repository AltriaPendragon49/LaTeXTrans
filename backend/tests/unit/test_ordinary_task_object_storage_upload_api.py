import asyncio
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import httpx

from backend.app.main import app


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


class _ValidationResult:
    is_valid = True
    main_file = "main.tex"
    tex_files = ["main.tex"]
    warnings = []
    errors = []

    def model_dump(self):
        return {
            "is_valid": self.is_valid,
            "main_file": self.main_file,
            "tex_files": self.tex_files,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def test_upload_persists_valid_source_to_object_storage(monkeypatch, tmp_path: Path):
    from backend.app.api.routes import upload as upload_route

    uploaded_calls = []
    update_calls = []

    class _FakeTaskManager:
        def create_task(self, **kwargs):
            return "task-upload-1"

        def update_task(self, **kwargs):
            update_calls.append(kwargs)
            return True

        def get_task(self, _task_id):
            return {"task_id": "task-upload-1"}

    settings = SimpleNamespace(
        allowed_extensions={".tex"},
        uploads_dir=tmp_path / "backend" / "data" / "uploads",
        storage_backend_mode="cos",
    )
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(upload_route, "settings", settings)
    monkeypatch.setattr(upload_route, "task_manager", _FakeTaskManager())
    monkeypatch.setattr(upload_route, "validate_latex_directory", lambda _path: _ValidationResult())
    monkeypatch.setattr(upload_route, "resolve_current_user_id", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        upload_route.task_artifact_storage,
        "persist_task_directory",
        lambda local_dir, *, stored_path, delete_local: uploaded_calls.append(
            (Path(local_dir), stored_path, delete_local)
        ) or "data/uploads/task-upload-1",
    )
    monkeypatch.setattr(
        upload_route.task_artifact_storage,
        "normalize_stored_task_path",
        lambda value: "data/uploads/task-upload-1",
    )

    async def _call():
        async with _make_client() as client:
            return await client.post(
                "/api/upload",
                files={"file": ("main.tex", BytesIO(b"\\documentclass{article}"), "text/plain")},
            )

    response = asyncio.run(_call())

    assert response.status_code == 200
    assert response.json()["source_path"] == "data/uploads/task-upload-1"
    assert uploaded_calls and uploaded_calls[0][1] == "data/uploads/task-upload-1"
    assert uploaded_calls[0][2] is True
    assert update_calls[-1]["source_path"] == "data/uploads/task-upload-1"
