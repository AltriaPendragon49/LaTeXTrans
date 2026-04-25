from __future__ import annotations

from pathlib import Path

from backend.app.services.storage_backend import StoredObjectRef


class _FakeStorageBackend:
    def __init__(self, refs_by_prefix: dict[str, list[StoredObjectRef]], payloads: dict[str, bytes]) -> None:
        self._refs_by_prefix = refs_by_prefix
        self._payloads = payloads
        self.downloaded: list[tuple[str, Path]] = []

    def list_files(self, *, prefix: str) -> list[StoredObjectRef]:
        return list(self._refs_by_prefix.get(prefix, []))

    def download_file(self, *, object_key: str, local_path: Path) -> Path:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(self._payloads[object_key])
        self.downloaded.append((object_key, local_path))
        return local_path


def test_parse_complete_arxiv_ids_ignores_headers_and_notes() -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import parse_complete_arxiv_ids

    markdown = """
2506.01622
2503.23674

4-24-6.18：
"""

    assert parse_complete_arxiv_ids(markdown) == ["2506.01622", "2503.23674"]


def test_sync_complete_assets_downloads_into_arxiv_id_directory(tmp_path: Path) -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import sync_core_pool_complete_assets

    complete_path = tmp_path / "complete.md"
    complete_path.write_text("2503.23674\n", encoding="utf-8")

    refs = [
        StoredObjectRef(storage_backend="object_storage", object_key="latextrans-prod/data/community_papers/2503.23674/source/main.tex"),
        StoredObjectRef(storage_backend="object_storage", object_key="latextrans-prod/data/community_papers/2503.23674/preview/preview.html"),
        StoredObjectRef(storage_backend="object_storage", object_key="latextrans-prod/data/community_papers/2503.23674/translated/2503.23674-zh.pdf"),
    ]
    payloads = {
        "latextrans-prod/data/community_papers/2503.23674/source/main.tex": b"\\section{demo}",
        "latextrans-prod/data/community_papers/2503.23674/preview/preview.html": b"<html>preview</html>",
        "latextrans-prod/data/community_papers/2503.23674/translated/2503.23674-zh.pdf": b"%PDF-1.4",
    }
    backend = _FakeStorageBackend(
        refs_by_prefix={
            "data/community_papers/2503.23674": refs,
            "data/community_papers": refs,
        },
        payloads=payloads,
    )

    report = sync_core_pool_complete_assets(
        storage_backend=backend,
        complete_path=complete_path,
        destination_root=tmp_path / "community_papers",
    )

    item = report["items"][0]
    assert item["arxiv_id"] == "2503.23674"
    assert item["status"] == "downloaded"
    assert item["matched_prefix"] == "latextrans-prod/data/community_papers/2503.23674"
    assert (tmp_path / "community_papers" / "2503.23674" / "source" / "main.tex").read_text(encoding="utf-8") == "\\section{demo}"
    assert (tmp_path / "community_papers" / "2503.23674" / "preview" / "preview.html").read_text(encoding="utf-8") == "<html>preview</html>"
    assert (tmp_path / "community_papers" / "2503.23674" / "translated" / "2503.23674-zh.pdf").read_bytes() == b"%PDF-1.4"


def test_sync_complete_assets_marks_conflicts_without_downloading(tmp_path: Path) -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import sync_core_pool_complete_assets

    complete_path = tmp_path / "complete.md"
    complete_path.write_text("2503.23674\n", encoding="utf-8")

    refs = [
        StoredObjectRef(storage_backend="object_storage", object_key="latextrans-prod/data/community_papers/paper-a/translated/2503.23674-zh.pdf"),
        StoredObjectRef(storage_backend="object_storage", object_key="latextrans-prod/data/community_papers/paper-b/translated/2503.23674-zh.pdf"),
    ]
    backend = _FakeStorageBackend(
        refs_by_prefix={
            "data/community_papers/2503.23674": [],
            "data/community_papers": refs,
        },
        payloads={
            "latextrans-prod/data/community_papers/paper-a/translated/2503.23674-zh.pdf": b"%PDF-1.4",
            "latextrans-prod/data/community_papers/paper-b/translated/2503.23674-zh.pdf": b"%PDF-1.4",
        },
    )

    report = sync_core_pool_complete_assets(
        storage_backend=backend,
        complete_path=complete_path,
        destination_root=tmp_path / "community_papers",
    )

    item = report["items"][0]
    assert item["status"] == "conflict"
    assert sorted(item["conflict_prefixes"]) == [
        "latextrans-prod/data/community_papers/paper-a",
        "latextrans-prod/data/community_papers/paper-b",
    ]
    assert backend.downloaded == []
