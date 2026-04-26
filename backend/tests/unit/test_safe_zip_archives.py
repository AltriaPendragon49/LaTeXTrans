from __future__ import annotations

import os
import zipfile
from pathlib import Path

from backend.app.services import paper_service, task_artifact_storage


def test_archive_directory_for_storage_clamps_pre_1980_timestamps(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    old_file = source / "paper.tex"
    old_file.write_text("hello", encoding="utf-8")
    os.utime(old_file, (0, 0))

    monkeypatch.setattr(paper_service.settings, "storage_temp_dir", tmp_path / "tmp")

    archive_path = paper_service._archive_directory_for_storage(source_path=source, task_id="task-1")

    with zipfile.ZipFile(archive_path) as archive:
        info = archive.getinfo("source/paper.tex")
    assert info.date_time >= (1980, 1, 1, 0, 0, 0)


def test_translated_source_archive_clamps_pre_1980_timestamps(tmp_path: Path) -> None:
    source_file = tmp_path / "main.tex"
    source_file.write_text("hello", encoding="utf-8")
    os.utime(source_file, (0, 0))

    relative = task_artifact_storage._create_translated_source_archive(tmp_path)

    assert relative == task_artifact_storage.TRANSLATED_SOURCE_ARCHIVE_RELATIVE_PATH
    with zipfile.ZipFile(tmp_path / relative) as archive:
        info = archive.getinfo("main.tex")
    assert info.date_time >= (1980, 1, 1, 0, 0, 0)
