from __future__ import annotations

from pathlib import Path
import tarfile

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


def test_sync_complete_assets_uses_db_asset_records_and_updates_markdown(tmp_path: Path) -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import sync_core_pool_complete_assets

    complete_path = tmp_path / "complete.md"
    complete_path.write_text("1111.11111\n", encoding="utf-8")

    asset_records = [
        {
            "paper_id": "paper-live",
            "arxiv_id": "2503.23674",
            "asset_type": "source_archive",
            "storage_backend": "object_storage",
            "file_path": "latextrans-prod/data/community_papers/paper-live/source/main.tex",
            "file_name": "main.tex",
        },
        {
            "paper_id": "paper-live",
            "arxiv_id": "2503.23674",
            "asset_type": "preview_html",
            "storage_backend": "object_storage",
            "file_path": "latextrans-prod/data/community_papers/paper-live/preview/preview.html",
            "file_name": "preview.html",
        },
        {
            "paper_id": "paper-live",
            "arxiv_id": "2503.23674",
            "asset_type": "translated_pdf",
            "storage_backend": "object_storage",
            "file_path": "latextrans-prod/data/community_papers/paper-live/translated/2503.23674-zh.pdf",
            "file_name": "2503.23674-zh.pdf",
        },
        {
            "paper_id": "paper-partial",
            "arxiv_id": "2501.00001",
            "asset_type": "source_archive",
            "storage_backend": "object_storage",
            "file_path": "latextrans-prod/data/community_papers/paper-partial/source/main.tex",
            "file_name": "main.tex",
        },
    ]
    payloads = {
        "latextrans-prod/data/community_papers/paper-live/source/main.tex": b"\\section{demo}",
        "latextrans-prod/data/community_papers/paper-live/preview/preview.html": b"<html>preview</html>",
        "latextrans-prod/data/community_papers/paper-live/translated/2503.23674-zh.pdf": b"%PDF-1.4",
        "latextrans-prod/data/community_papers/paper-partial/source/main.tex": b"partial",
    }
    backend = _FakeStorageBackend(
        refs_by_prefix={},
        payloads=payloads,
    )

    report = sync_core_pool_complete_assets(
        storage_backend=backend,
        complete_path=complete_path,
        destination_root=tmp_path / "community_papers",
        asset_records=asset_records,
    )

    item = report["items"][0]
    assert item["arxiv_id"] == "2503.23674"
    assert item["status"] == "downloaded"
    assert item["matched_prefix"] == "paper-live"
    assert report["discovered"] == 1
    assert (tmp_path / "community_papers" / "2503.23674" / "source" / "main.tex").read_text(encoding="utf-8") == "\\section{demo}"
    assert (tmp_path / "community_papers" / "2503.23674" / "preview" / "preview.html").read_text(encoding="utf-8") == "<html>preview</html>"
    assert (tmp_path / "community_papers" / "2503.23674" / "translated" / "2503.23674-zh.pdf").read_bytes() == b"%PDF-1.4"
    assert complete_path.read_text(encoding="utf-8") == "2503.23674\n"


def test_sync_complete_assets_marks_conflicts_without_downloading(tmp_path: Path) -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import sync_core_pool_complete_assets

    complete_path = tmp_path / "complete.md"
    complete_path.write_text("", encoding="utf-8")

    asset_records = [
        {
            "paper_id": paper_id,
            "arxiv_id": "2503.23674",
            "asset_type": asset_type,
            "storage_backend": "object_storage",
            "file_path": f"latextrans-prod/data/community_papers/{paper_id}/{asset_type}/asset.bin",
            "file_name": "asset.bin",
        }
        for paper_id in ("paper-a", "paper-b")
        for asset_type in ("source_archive", "preview_html", "translated_pdf")
    ]
    backend = _FakeStorageBackend(
        refs_by_prefix={},
        payloads={
            str(row["file_path"]): b"bytes"
            for row in asset_records
        },
    )

    report = sync_core_pool_complete_assets(
        storage_backend=backend,
        complete_path=complete_path,
        destination_root=tmp_path / "community_papers",
        asset_records=asset_records,
    )

    item = report["items"][0]
    assert item["status"] == "conflict"
    assert sorted(item["conflict_prefixes"]) == [
        "paper-a",
        "paper-b",
    ]
    assert backend.downloaded == []


def test_sync_complete_assets_supports_local_disk_asset_records(tmp_path: Path) -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import sync_core_pool_complete_assets

    complete_path = tmp_path / "complete.md"
    source_root = tmp_path / "server_backend"
    for relative_path, content in {
        "data/community_papers/paper-local/source/2506.06941.zip": b"zip",
        "data/community_papers/paper-local/preview/preview.html": b"<html>local</html>",
        "data/community_papers/paper-local/translated/zh.pdf": b"%PDF-1.4",
    }.items():
        path = source_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    class _LocalBackend:
        def resolve_local_path(self, ref: StoredObjectRef) -> Path:
            return source_root / ref.object_key

        def download_file(self, *, object_key: str, local_path: Path) -> Path:
            source = source_root / object_key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                raise PermissionError(str(source))
            local_path.write_bytes(source.read_bytes())
            return local_path

    asset_records = [
        {
            "paper_id": "paper-local",
            "arxiv_id": "2506.06941",
            "asset_type": asset_type,
            "storage_backend": "local_disk",
            "file_path": file_path,
            "file_name": file_name,
        }
        for asset_type, file_path, file_name in [
            ("source_archive", "data/community_papers/paper-local/source/2506.06941.zip", "2506.06941.zip"),
            ("preview_html", "data/community_papers/paper-local/preview/preview.html", "preview.html"),
            ("translated_pdf", "data/community_papers/paper-local/translated/zh.pdf", "zh.pdf"),
        ]
    ]

    report = sync_core_pool_complete_assets(
        storage_backends={"local_disk": _LocalBackend()},  # type: ignore[dict-item]
        complete_path=complete_path,
        destination_root=tmp_path / "community_papers",
        asset_records=asset_records,
    )

    assert report["downloaded"] == 1
    assert complete_path.read_text(encoding="utf-8") == "2506.06941\n"
    assert (tmp_path / "community_papers" / "2506.06941" / "source" / "2506.06941.zip").read_bytes() == b"zip"
    assert (tmp_path / "community_papers" / "2506.06941" / "preview" / "preview.html").read_text(encoding="utf-8") == "<html>local</html>"
    assert (tmp_path / "community_papers" / "2506.06941" / "translated" / "zh.pdf").read_bytes() == b"%PDF-1.4"


def test_sync_complete_assets_copies_local_disk_source_directory(tmp_path: Path) -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import sync_core_pool_complete_assets

    complete_path = tmp_path / "complete.md"
    source_root = tmp_path / "server_backend"
    source_dir = source_root / "data/community_papers/paper-dir/source/2203.09191"
    source_dir.mkdir(parents=True)
    (source_dir / "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
    for relative_path, content in {
        "data/community_papers/paper-dir/preview/preview.html": b"<html>dir</html>",
        "data/community_papers/paper-dir/translated/zh.pdf": b"%PDF-1.4",
    }.items():
        path = source_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    class _LocalBackend:
        def resolve_local_path(self, ref: StoredObjectRef) -> Path:
            return source_root / ref.object_key

        def download_file(self, *, object_key: str, local_path: Path) -> Path:
            source = source_root / object_key
            if source.is_dir():
                raise PermissionError(str(source))
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(source.read_bytes())
            return local_path

    asset_records = [
        {
            "paper_id": "paper-dir",
            "arxiv_id": "2203.09191",
            "asset_type": asset_type,
            "storage_backend": "local_disk",
            "file_path": file_path,
            "file_name": file_name,
        }
        for asset_type, file_path, file_name in [
            ("source_archive", "data/community_papers/paper-dir/source/2203.09191", "2203.09191"),
            ("preview_html", "data/community_papers/paper-dir/preview/preview.html", "preview.html"),
            ("translated_pdf", "data/community_papers/paper-dir/translated/zh.pdf", "zh.pdf"),
        ]
    ]

    report = sync_core_pool_complete_assets(
        storage_backends={"local_disk": _LocalBackend()},  # type: ignore[dict-item]
        complete_path=complete_path,
        destination_root=tmp_path / "community_papers",
        asset_records=asset_records,
    )

    assert report["downloaded"] == 1
    copied_source = tmp_path / "community_papers" / "2203.09191" / "source" / "2203.09191" / "main.tex"
    assert copied_source.read_text(encoding="utf-8") == "\\documentclass{article}"


def test_sync_complete_assets_reports_missing_local_asset_and_continues(tmp_path: Path) -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import sync_core_pool_complete_assets

    complete_path = tmp_path / "complete.md"
    source_root = tmp_path / "server_backend"
    existing_source = source_root / "data/community_papers/paper-ok/source/ok.zip"
    existing_source.parent.mkdir(parents=True, exist_ok=True)
    existing_source.write_bytes(b"zip")
    for relative_path, content in {
        "data/community_papers/paper-ok/preview/preview.html": b"<html>ok</html>",
        "data/community_papers/paper-ok/translated/zh.pdf": b"%PDF-1.4",
    }.items():
        path = source_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    class _LocalBackend:
        def resolve_local_path(self, ref: StoredObjectRef) -> Path:
            return source_root / ref.object_key

        def download_file(self, *, object_key: str, local_path: Path) -> Path:
            source = source_root / object_key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(source.read_bytes())
            return local_path

    def rows(paper_id: str, arxiv_id: str, missing: bool) -> list[dict[str, str]]:
        source_path = (
            f"data/community_papers/{paper_id}/source/missing.zip"
            if missing
            else f"data/community_papers/{paper_id}/source/ok.zip"
        )
        return [
            {
                "paper_id": paper_id,
                "arxiv_id": arxiv_id,
                "asset_type": asset_type,
                "storage_backend": "local_disk",
                "file_path": file_path,
                "file_name": file_name,
            }
            for asset_type, file_path, file_name in [
                ("source_archive", source_path, Path(source_path).name),
                ("preview_html", f"data/community_papers/{paper_id}/preview/preview.html", "preview.html"),
                ("translated_pdf", f"data/community_papers/{paper_id}/translated/zh.pdf", "zh.pdf"),
            ]
        ]

    asset_records = rows("paper-missing", "2203.09191", True) + rows("paper-ok", "2506.06941", False)

    report = sync_core_pool_complete_assets(
        storage_backends={"local_disk": _LocalBackend()},  # type: ignore[dict-item]
        complete_path=complete_path,
        destination_root=tmp_path / "community_papers",
        asset_records=asset_records,
    )

    assert report["failed"] == 1
    assert report["downloaded"] == 1
    assert report["complete_updated"] is True
    assert [item["status"] for item in report["items"]] == ["failed", "downloaded"]
    assert complete_path.read_text(encoding="utf-8") == "2506.06941\n"


def test_sync_complete_assets_does_not_overwrite_complete_when_all_items_fail(tmp_path: Path) -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import sync_core_pool_complete_assets

    complete_path = tmp_path / "complete.md"
    complete_path.write_text("keep-me\n", encoding="utf-8")
    source_root = tmp_path / "server_backend"

    class _LocalBackend:
        def resolve_local_path(self, ref: StoredObjectRef) -> Path:
            return source_root / ref.object_key

        def download_file(self, *, object_key: str, local_path: Path) -> Path:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            return local_path.write_bytes((source_root / object_key).read_bytes())  # type: ignore[return-value]

    asset_records = [
        {
            "paper_id": "paper-missing",
            "arxiv_id": "2203.09191",
            "asset_type": asset_type,
            "storage_backend": "local_disk",
            "file_path": f"data/community_papers/paper-missing/{group}/{file_name}",
            "file_name": file_name,
        }
        for asset_type, group, file_name in [
            ("source_archive", "source", "missing.zip"),
            ("preview_html", "preview", "preview.html"),
            ("translated_pdf", "translated", "zh.pdf"),
        ]
    ]

    report = sync_core_pool_complete_assets(
        storage_backends={"local_disk": _LocalBackend()},  # type: ignore[dict-item]
        complete_path=complete_path,
        destination_root=tmp_path / "community_papers",
        asset_records=asset_records,
    )

    assert report["failed"] == 1
    assert report["complete_updated"] is False
    assert complete_path.read_text(encoding="utf-8") == "keep-me\n"


def test_targeted_sync_does_not_overwrite_complete_report(tmp_path: Path) -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import sync_core_pool_complete_assets

    complete_path = tmp_path / "complete.md"
    complete_path.write_text("keep-existing\n", encoding="utf-8")
    asset_records = [
        {
            "paper_id": "paper-live",
            "arxiv_id": "2503.23674",
            "asset_type": asset_type,
            "storage_backend": "object_storage",
            "file_path": f"latextrans-prod/data/community_papers/paper-live/{asset_type}/asset.bin",
            "file_name": "asset.bin",
        }
        for asset_type in ("source_archive", "preview_html", "translated_pdf")
    ]
    backend = _FakeStorageBackend(
        refs_by_prefix={},
        payloads={str(row["file_path"]): b"bytes" for row in asset_records},
    )

    report = sync_core_pool_complete_assets(
        storage_backend=backend,
        complete_path=complete_path,
        destination_root=tmp_path / "community_papers",
        asset_records=asset_records,
        limit=1,
    )

    assert report["downloaded"] == 1
    assert report["complete_updated"] is False
    assert complete_path.read_text(encoding="utf-8") == "keep-existing\n"


def test_parse_remote_server_credentials_redacts_secret_fields() -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import parse_remote_server_credentials

    credentials = parse_remote_server_credentials(
        """
服务器: 82.156.76.218
用户: ubuntu
密码: top-secret
"""
    )

    assert credentials.host == "82.156.76.218"
    assert credentials.username == "ubuntu"
    assert credentials.password == "top-secret"
    assert "top-secret" not in credentials.safe_summary()


def test_build_remote_sync_command_runs_current_script_in_backend_container() -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import build_remote_sync_command

    command = build_remote_sync_command(
        container_name="latextrans-backend",
        complete_path="/app/backend/arxiv_id/core_pool/complete.md",
        destination_root="/app/backend/data/community_papers",
        arxiv_ids=["2506.06941"],
        limit=10,
        force=True,
    )

    assert command.startswith("docker exec -i -w /app latextrans-backend python -")
    assert "--complete-path /app/backend/arxiv_id/core_pool/complete.md" in command
    assert "--destination-root /app/backend/data/community_papers" in command
    assert "--arxiv-id 2506.06941" in command
    assert "--limit 10" in command
    assert "--force" in command
    assert "--remote-pull-and-clean" not in command


def test_safe_extract_tar_rejects_path_traversal(tmp_path: Path) -> None:
    from backend.scripts.sync_core_pool_complete_from_cos import safe_extract_tar

    archive_path = tmp_path / "bad.tar.gz"
    payload = tmp_path / "payload.txt"
    payload.write_text("oops", encoding="utf-8")
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(payload, arcname="../escape.txt")

    with tarfile.open(archive_path, "r:gz") as archive:
        try:
            safe_extract_tar(archive, tmp_path / "out")
        except ValueError as exc:
            assert "Unsafe archive member" in str(exc)
        else:
            raise AssertionError("Expected unsafe archive member to be rejected")
