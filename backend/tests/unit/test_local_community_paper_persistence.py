import asyncio
import sqlite3
from pathlib import Path

import pytest

from backend.app.core.config import get_settings
from backend.app.db import DatabaseUnavailableError
from backend.app.services import paper_service


def _create_sqlite_schema(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
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
              like_count integer not null default 0,
              favorite_count integer not null default 0,
              comment_count integer not null default 0,
              view_count integer not null default 0,
              download_count integer not null default 0,
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
              is_latest integer not null default 1,
              created_at text not null
            );

            create table paper_likes (
              paper_id text not null,
              user_id text not null
            );

            create table paper_favorites (
              paper_id text not null,
              user_id text not null
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def _insert_public_paper(database_path: Path, *, view_count: int = 2) -> None:
    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute(
            """
            insert into papers (
              id, created_by, source, arxiv_id, title, authors, categories,
              abstract_raw, abstract_translated, visibility, status,
              community_status, trans_status, trans_latest_task_id,
              trans_latest_asset_pdf_id, community_selected_task_id,
              community_selected_asset_id, like_count, favorite_count,
              comment_count, view_count, download_count, official_published_at,
              created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "paper-local-1",
                "usr-local-1",
                "arxiv",
                "2501.12345",
                "Local persistence paper",
                '["Alice","Bob"]',
                '["cs.CL"]',
                "Raw abstract",
                "Translated abstract",
                "public",
                "published",
                "official",
                "completed",
                "task-local-1",
                None,
                "task-local-1",
                "asset-preview-1",
                1,
                0,
                0,
                view_count,
                0,
                "2026-04-09T10:00:00Z",
                "2026-04-09T09:00:00Z",
                "2026-04-09T10:00:00Z",
            ),
        )
        connection.execute(
            """
            insert into paper_assets (
              id, paper_id, task_id, asset_type, storage_backend,
              file_path, file_name, mime_type, is_latest, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "asset-preview-1",
                "paper-local-1",
                "task-local-1",
                "preview_html",
                "local_disk",
                "data/community_papers/paper-local-1/preview.html",
                "preview.html",
                "text/html",
                1,
                "2026-04-09T10:00:00Z",
            ),
        )
        connection.commit()
    finally:
        connection.close()


def test_list_papers_reads_from_local_database_when_supabase_client_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "community-papers.db"
    _create_sqlite_schema(database_path)
    _insert_public_paper(database_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path.resolve()}")
    monkeypatch.setattr(paper_service.settings, "community_baseline_seed_path", None)
    monkeypatch.setattr(paper_service, "get_supabase_admin_client", lambda: None)

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert result["total"] == 1
    assert result["source_mode"] == "database"
    assert result["items"][0]["id"] == "paper-local-1"
    assert result["items"][0]["latest_asset"]["asset_type"] == "preview_html"


def test_record_view_increments_local_database_when_supabase_client_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "community-papers.db"
    _create_sqlite_schema(database_path)
    _insert_public_paper(database_path, view_count=2)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path.resolve()}")
    monkeypatch.setattr(paper_service, "get_supabase_admin_client", lambda: None)

    result = asyncio.run(paper_service.record_community_paper_view(paper_id="paper-local-1"))

    assert result == {"paper_id": "paper-local-1", "view_count": 3}

    connection = sqlite3.connect(str(database_path))
    try:
        row = connection.execute(
            "select view_count from papers where id = ?",
            ("paper-local-1",),
        ).fetchone()
    finally:
        connection.close()

    assert row is not None
    assert row[0] == 3


def test_list_papers_uses_baseline_seed_without_supabase_runtime_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase_calls = {"count": 0}

    class _UnavailableRepository:
        def list_public_papers(self):
            raise DatabaseUnavailableError("local database unavailable")

    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: _UnavailableRepository())
    monkeypatch.setattr(
        paper_service,
        "_load_baseline_seed_rows",
        lambda: [
            {
                "id": "paper-seed-1",
                "source": "arxiv",
                "arxiv_id": "2501.54321",
                "title": "Seed fallback paper",
                "authors": [],
                "categories": [],
                "abstract_raw": "Seed abstract",
                "abstract_translated": None,
                "visibility": "public",
                "status": "published",
                "community_status": "official",
                "trans_status": "completed",
                "trans_latest_task_id": None,
                "trans_latest_asset_pdf_id": None,
                "community_selected_task_id": None,
                "community_selected_asset_id": None,
                "like_count": 0,
                "favorite_count": 0,
                "comment_count": 0,
                "view_count": 0,
                "download_count": 0,
                "official_published_at": "2026-04-09T10:00:00Z",
                "created_at": "2026-04-09T09:00:00Z",
                "updated_at": "2026-04-09T10:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        paper_service,
        "get_supabase_admin_client",
        lambda: supabase_calls.__setitem__("count", supabase_calls["count"] + 1),
    )
    monkeypatch.setattr(
        paper_service,
        "_fetch_asset_maps_for_papers",
        lambda _paper_ids: asyncio.sleep(0, result={}),
    )

    result = asyncio.run(paper_service.list_community_papers(sort="latest"))

    assert result["total"] == 1
    assert result["source_mode"] == "baseline_seed"
    assert result["items"][0]["id"] == "paper-seed-1"
    assert supabase_calls["count"] == 0
