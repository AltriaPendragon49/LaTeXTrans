import asyncio
import sqlite3
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.app.core.config import get_settings
from backend.app.services import paper_service


def _create_schema(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            create table users (
              id text primary key
            );

            create table user_roles (
              user_id text not null,
              role text not null,
              created_at text not null,
              primary key (user_id, role)
            );

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
            """
        )
        connection.commit()
    finally:
        connection.close()


def _insert_user_roles(database_path: Path, user_id: str, roles: list[str]) -> None:
    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute("insert into users (id) values (?)", (user_id,))
        for role in roles:
            connection.execute(
                "insert into user_roles (user_id, role, created_at) values (?, ?, ?)",
                (user_id, role, "2026-04-09T10:00:00Z"),
            )
        connection.commit()
    finally:
        connection.close()


def _insert_paper_row(database_path: Path, *, paper_id: str = "paper-local-1") -> None:
    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute(
            """
            insert into papers (
              id, created_by, source, arxiv_id, title, authors, categories,
              abstract_raw, abstract_translated, visibility, status, community_status,
              trans_status, trans_latest_task_id, trans_latest_asset_pdf_id,
              community_selected_task_id, community_selected_asset_id, like_count,
              favorite_count, comment_count, view_count, download_count,
              official_published_at, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                "usr-local-1",
                "arxiv",
                "2501.00001",
                "Original title",
                '["Alice"]',
                '["cs.CL"]',
                "Raw abstract",
                "Translated abstract",
                "public",
                "published",
                "official",
                "not_started",
                None,
                None,
                None,
                None,
                0,
                0,
                0,
                0,
                0,
                None,
                "2026-04-09T10:00:00Z",
                "2026-04-09T10:00:00Z",
            ),
        )
        connection.commit()
    finally:
        connection.close()


def test_resolve_submitter_context_by_user_id_reads_local_roles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "community-papers.db"
    _create_schema(database_path)
    _insert_user_roles(database_path, "usr-admin", ["user", "admin", "moderator"])

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path.resolve()}")

    result = asyncio.run(paper_service.resolve_submitter_context_by_user_id("usr-admin"))

    assert result["user_id"] == "usr-admin"
    assert result["roles"] == ["admin", "moderator"]
    assert result["is_admin"] is True


def test_resolve_submitter_context_by_user_id_without_database_uses_local_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", "")

    result = asyncio.run(paper_service.resolve_submitter_context_by_user_id("usr-1"))

    assert result == {"user_id": "usr-1", "roles": [], "is_admin": False}


def test_insert_paper_without_database_returns_service_unavailable_without_local_database_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", "")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            paper_service._insert_paper(
                {
                    "id": "paper-cutover-1",
                    "source": "upload",
                    "title": "Cutover",
                    "visibility": "public",
                    "status": "published",
                    "community_status": "official",
                    "trans_status": "not_started",
                }
            )
        )

    assert exc_info.value.status_code == 503


def test_update_paper_without_database_returns_service_unavailable_without_local_database_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", "")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(paper_service._update_paper("paper-1", {"title": "Updated"}))

    assert exc_info.value.status_code == 503


def test_upsert_latest_asset_without_database_returns_service_unavailable_without_local_database_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", "")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            paper_service._upsert_latest_asset(
                paper_id="paper-1",
                task_id="task-1",
                asset_type="translated_pdf",
                file_path="data/community_papers/paper-1/paper.pdf",
            )
        )

    assert exc_info.value.status_code == 503


def test_update_and_asset_upsert_use_local_repository(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "community-papers.db"
    _create_schema(database_path)
    _insert_paper_row(database_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path.resolve()}")

    updated = asyncio.run(paper_service._update_paper("paper-local-1", {"title": "Updated title"}))
    asset = asyncio.run(
        paper_service._upsert_latest_asset(
            paper_id="paper-local-1",
            task_id="task-2",
            asset_type="preview_html",
            file_path="data/community_papers/paper-local-1/preview-v2.html",
        )
    )

    assert updated["title"] == "Updated title"
    assert asset["paper_id"] == "paper-local-1"
    assert asset["asset_type"] == "preview_html"
    assert asset["is_latest"] is True



