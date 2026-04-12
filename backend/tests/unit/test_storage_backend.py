from pathlib import Path

import pytest

from backend.app.services.storage_backend import (
    LocalDiskStorageBackend,
    StoredObjectRef,
    build_storage_backend,
)


def test_local_disk_backend_round_trips_relative_object_key(tmp_path: Path) -> None:
    backend = LocalDiskStorageBackend(root=tmp_path)
    source = tmp_path / "cache" / "preview.html"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("<article>preview</article>", encoding="utf-8")

    stored = backend.put_file(
        local_path=source,
        object_key="community/paper-1/preview/preview.html",
        content_type="text/html",
        delete_local=False,
    )

    assert isinstance(stored, StoredObjectRef)
    assert stored.storage_backend == "local_disk"
    assert stored.object_key == "community/paper-1/preview/preview.html"
    assert backend.resolve_local_path(stored).read_text(encoding="utf-8") == "<article>preview</article>"


def test_local_disk_backend_rejects_escape_object_keys(tmp_path: Path) -> None:
    backend = LocalDiskStorageBackend(root=tmp_path)
    source = tmp_path / "cache" / "preview.html"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError):
        backend.put_file(
            local_path=source,
            object_key="../etc/password",
            content_type="text/plain",
            delete_local=False,
        )

    with pytest.raises(ValueError):
        backend.put_file(
            local_path=source,
            object_key="/absolute/path",
            content_type="text/plain",
            delete_local=False,
        )

    with pytest.raises(ValueError):
        backend.put_file(
            local_path=source,
            object_key="C:/absolute/path",
            content_type="text/plain",
            delete_local=False,
        )


def test_local_disk_backend_deletes_source_when_requested(tmp_path: Path) -> None:
    backend = LocalDiskStorageBackend(root=tmp_path)
    source = tmp_path / "cache" / "temporary.txt"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("temp", encoding="utf-8")

    backend.put_file(
        local_path=source,
        object_key="paper/asset.txt",
        content_type="text/plain",
        delete_local=True,
    )

    assert not source.exists()


def test_storage_backend_factory_rejects_incomplete_cos_config(tmp_path: Path) -> None:
    class DummySettings:
        storage_backend_mode = "cos"
        storage_temp_dir = tmp_path
        cos_bucket = None
        cos_region = "ap-guangzhou"
        cos_secret_id = None
        cos_secret_key = None
        cos_base_prefix = "paperx"

    with pytest.raises(ValueError) as exc:
        build_storage_backend(DummySettings())

    assert "COS" in str(exc.value)
