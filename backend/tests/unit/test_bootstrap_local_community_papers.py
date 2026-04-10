from __future__ import annotations

import json
from pathlib import Path

from backend.scripts.bootstrap_local_community_papers import bootstrap_local_community_papers
from backend.app.core.config import get_settings


def _create_sqlite_schema(database_path: Path) -> None:
    import sqlite3

    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            create table papers (
              id text primary key,
              created_by text null,
              source text not null,
              arxiv_id text null,
              title text not null,
              authors text null,
              categories text null,
              abstract_raw text null,
              abstract_translated text null,
              visibility text not null,
              status text not null,
              community_status text not null,
              trans_status text not null,
              trans_latest_task_id text null,
              trans_latest_asset_pdf_id text null,
              community_selected_task_id text null,
              community_selected_asset_id text null,
              like_count integer not null,
              favorite_count integer not null,
              comment_count integer not null,
              view_count integer not null,
              download_count integer not null,
              official_published_at text null,
              created_at text not null,
              updated_at text not null
            );
            create table paper_assets (
              id text primary key,
              paper_id text not null,
              task_id text null,
              asset_type text not null,
              storage_backend text not null,
              file_path text not null,
              file_name text not null,
              mime_type text not null,
              is_latest integer not null,
              created_at text not null
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_bootstrap_local_community_papers_registers_on_disk_assets(monkeypatch, tmp_path: Path) -> None:
    paper_dir = tmp_path / "community_papers" / "paper-live"
    source_dir = paper_dir / "source" / "2501.12345"
    preview_dir = paper_dir / "preview"
    translated_dir = paper_dir / "translated"
    source_dir.mkdir(parents=True)
    preview_dir.mkdir(parents=True)
    translated_dir.mkdir(parents=True)

    (source_dir / "main.tex").write_text("\\section{Demo}", encoding="utf-8")
    (preview_dir / "preview.html").write_text("<html><body>这是一个中文预览，用于验证翻译内容�?/body></html>", encoding="utf-8")
    (translated_dir / "2501.12345-zh.pdf").write_bytes(b"%PDF-1.4")

    database_path = tmp_path / "community.db"
    _create_sqlite_schema(database_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    monkeypatch.setattr(settings, "base_dir", tmp_path)
    monkeypatch.setattr(settings, "community_papers_dir", tmp_path / "community_papers")
    monkeypatch.setattr(
        "backend.scripts.bootstrap_local_community_papers._metadata_for",
        lambda arxiv_id: {
            "title": f"Title for {arxiv_id}",
            "authors": ["Alice", "Bob"],
            "categories": ["cs.CL"],
            "abstract_raw": "Demo abstract",
        },
    )

    report = bootstrap_local_community_papers(dry_run=False)

    assert report["discovered"] == 1
    assert report["inserted"] == 1
    assert report["updated"] == 0

    import sqlite3

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        paper = connection.execute("select * from papers where id = ?", ("paper-live",)).fetchone()
        assets = connection.execute(
            "select asset_type, file_name, file_path from paper_assets where paper_id = ? order by asset_type",
            ("paper-live",),
        ).fetchall()
    finally:
        connection.close()

    assert paper is not None
    assert paper["arxiv_id"] == "2501.12345"
    assert paper["title"] == "Title for 2501.12345"
    assert paper["trans_status"] == "completed"
    assert paper["community_selected_asset_id"] == "paper-live:preview_html"
    assert {row["asset_type"] for row in assets} == {"preview_html", "source_archive", "translated_pdf"}
    assert {row["asset_type"]: row["file_path"] for row in assets} == {
        "preview_html": "community_papers/paper-live/preview/preview.html",
        "source_archive": "community_papers/paper-live/source/2501.12345",
        "translated_pdf": "community_papers/paper-live/translated/2501.12345-zh.pdf",
    }
