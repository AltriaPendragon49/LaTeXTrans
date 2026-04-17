import json
from pathlib import Path
from types import SimpleNamespace

from backend.app.services.storage_backend import StoredObjectRef


def test_persist_task_directory_uploads_tree_to_object_storage(monkeypatch, tmp_path: Path):
    from backend.app.services import task_artifact_storage as storage

    source_dir = tmp_path / "backend" / "data" / "uploads" / "task-1"
    nested_dir = source_dir / "figures"
    nested_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "main.tex").write_text("hello", encoding="utf-8")
    (nested_dir / "plot.png").write_bytes(b"png")

    uploaded: list[str] = []

    class _FakeBackend:
        def put_file(self, *, local_path: Path, object_key: str, content_type, delete_local: bool):
            uploaded.append(object_key)
            return StoredObjectRef(storage_backend="object_storage", object_key=object_key, content_type=content_type)

    settings = SimpleNamespace(
        base_dir=tmp_path / "backend",
        uploads_dir=tmp_path / "backend" / "data" / "uploads",
        outputs_dir=tmp_path / "backend" / "data" / "outputs",
        storage_backend_mode="cos",
        storage_temp_dir=tmp_path / "backend" / "data" / "tmp_storage",
    )
    settings.storage_temp_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(storage, "settings", settings)
    monkeypatch.setattr(storage, "_get_storage_backend", lambda: _FakeBackend())

    stored_path = storage.persist_task_directory(
        source_dir,
        stored_path="data/uploads/task-1",
        delete_local=False,
    )

    assert stored_path == "data/uploads/task-1"
    assert uploaded == [
        "data/uploads/task-1/figures/plot.png",
        "data/uploads/task-1/main.tex",
    ]


def test_materialize_task_directory_downloads_object_storage_tree(monkeypatch, tmp_path: Path):
    from backend.app.services import task_artifact_storage as storage

    downloaded: list[str] = []
    payloads = {
        "data/uploads/task-1/main.tex": b"\\documentclass{article}",
        "data/uploads/task-1/figures/plot.png": b"png-bytes",
    }

    class _FakeBackend:
        def list_files(self, *, prefix: str):
            return [
                StoredObjectRef(storage_backend="object_storage", object_key=key)
                for key in sorted(payloads)
                if key.startswith(prefix)
            ]

        def download_file(self, *, object_key: str, local_path: Path):
            downloaded.append(object_key)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(payloads[object_key])
            return local_path

    settings = SimpleNamespace(
        base_dir=tmp_path / "backend",
        uploads_dir=tmp_path / "backend" / "data" / "uploads",
        outputs_dir=tmp_path / "backend" / "data" / "outputs",
        storage_backend_mode="cos",
        storage_temp_dir=tmp_path / "backend" / "data" / "tmp_storage",
    )
    settings.storage_temp_dir.mkdir(parents=True, exist_ok=True)

    destination = settings.storage_temp_dir / "hydrate" / "task-1"

    monkeypatch.setattr(storage, "settings", settings)
    monkeypatch.setattr(storage, "_get_storage_backend", lambda: _FakeBackend())

    materialized = storage.materialize_task_directory(
        "data/uploads/task-1",
        destination=destination,
        force=True,
    )

    assert materialized == destination
    assert downloaded == [
        "data/uploads/task-1/figures/plot.png",
        "data/uploads/task-1/main.tex",
    ]
    assert (destination / "main.tex").read_text(encoding="utf-8") == "\\documentclass{article}"
    assert (destination / "figures" / "plot.png").read_bytes() == b"png-bytes"


def test_materialize_task_directory_accepts_full_prefixed_object_keys(monkeypatch, tmp_path: Path):
    from backend.app.services import task_artifact_storage as storage

    downloaded: list[str] = []
    payloads = {
        "latextrans-prod/data/uploads/task-1/main.tex": b"\\documentclass{article}",
        "latextrans-prod/data/uploads/task-1/figures/plot.png": b"png-bytes",
    }

    class _FakeBackend:
        def list_files(self, *, prefix: str):
            assert prefix == "data/uploads/task-1"
            return [
                StoredObjectRef(storage_backend="object_storage", object_key=key)
                for key in sorted(payloads)
            ]

        def download_file(self, *, object_key: str, local_path: Path):
            downloaded.append(object_key)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(payloads[object_key])
            return local_path

    settings = SimpleNamespace(
        base_dir=tmp_path / "backend",
        uploads_dir=tmp_path / "backend" / "data" / "uploads",
        outputs_dir=tmp_path / "backend" / "data" / "outputs",
        storage_backend_mode="cos",
        storage_temp_dir=tmp_path / "backend" / "data" / "tmp_storage",
        cos_base_prefix="latextrans-prod",
    )
    settings.storage_temp_dir.mkdir(parents=True, exist_ok=True)

    destination = settings.storage_temp_dir / "hydrate" / "task-1"

    monkeypatch.setattr(storage, "settings", settings)
    monkeypatch.setattr(storage, "_get_storage_backend", lambda: _FakeBackend())

    materialized = storage.materialize_task_directory(
        "data/uploads/task-1",
        destination=destination,
        force=True,
    )

    assert materialized == destination
    assert downloaded == [
        "latextrans-prod/data/uploads/task-1/figures/plot.png",
        "latextrans-prod/data/uploads/task-1/main.tex",
    ]
    assert (destination / "main.tex").read_text(encoding="utf-8") == "\\documentclass{article}"


def test_persist_task_output_directory_writes_manifest_and_source_archive(monkeypatch, tmp_path: Path):
    from backend.app.services import task_artifact_storage as storage

    output_dir = tmp_path / "backend" / "data" / "outputs" / "task-1"
    translated_dir = output_dir / "paper"
    translated_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = translated_dir / "paper_translated.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    (translated_dir / "main.tex").write_text("\\begin{document}Hi\\end{document}", encoding="utf-8")
    (output_dir / "task_log.json").write_text(
        json.dumps([{"event": "compilation_completed", "pdf_path": str(pdf_path)}]),
        encoding="utf-8",
    )
    (output_dir / "terminology_table.csv").write_text("a,b\n", encoding="utf-8")
    (translated_dir / "paper.log").write_text("ok", encoding="utf-8")

    uploaded: list[str] = []

    class _FakeBackend:
        def put_file(self, *, local_path: Path, object_key: str, content_type, delete_local: bool):
            uploaded.append(object_key)
            return StoredObjectRef(storage_backend="object_storage", object_key=object_key, content_type=content_type)

    settings = SimpleNamespace(
        base_dir=tmp_path / "backend",
        uploads_dir=tmp_path / "backend" / "data" / "uploads",
        outputs_dir=tmp_path / "backend" / "data" / "outputs",
        storage_backend_mode="cos",
        storage_temp_dir=tmp_path / "backend" / "data" / "tmp_storage",
    )
    settings.storage_temp_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(storage, "settings", settings)
    monkeypatch.setattr(storage, "_get_storage_backend", lambda: _FakeBackend())

    stored_path = storage.persist_task_output_directory(
        task_id="task-1",
        local_output_dir=output_dir,
        delete_local=False,
    )

    manifest = json.loads((output_dir / "storage_manifest.json").read_text(encoding="utf-8"))

    assert stored_path == "data/outputs/task-1"
    assert manifest["translated_pdf"] == "paper/paper_translated.pdf"
    assert manifest["terminology_csv"] == "terminology_table.csv"
    assert manifest["logs"] == ["paper/paper.log"]
    assert manifest["translated_source_archive"] == "_downloads/translated_source.zip"
    assert "data/outputs/task-1/storage_manifest.json" in uploaded
    assert "data/outputs/task-1/_downloads/translated_source.zip" in uploaded
