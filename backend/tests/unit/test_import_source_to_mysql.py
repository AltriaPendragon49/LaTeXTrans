from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

from backend.app.core.config import get_settings
from backend.app.services import paper_service
from backend.scripts.import_source_to_mysql import run_import


ENTITIES = (
    "users",
    "user_roles",
    "user_settings",
    "translation_tasks",
    "papers",
    "paper_assets",
    "community_agent_conversations",
    "community_agent_runs",
    "community_agent_events",
)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_exports(export_dir: Path, payload_by_entity: dict[str, list[dict]]) -> None:
    for entity in ENTITIES:
        _write_json(export_dir / f"{entity}.json", payload_by_entity.get(entity, []))


def _create_sqlite_schema(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            create table users (
              id text primary key,
              external_provider text not null,
              external_user_id text not null,
              email text null,
              display_name text null,
              token_version integer not null,
              status text not null,
              created_at text not null,
              updated_at text not null
            );
            create table user_roles (
              user_id text not null,
              role text not null,
              created_at text not null,
              primary key (user_id, role)
            );
            create table user_settings (
              user_id text primary key,
              default_source_language text not null,
              default_target_language text not null,
              translation_mode text not null,
              compile_strategy text not null,
              translation_model text null,
              generate_glossary integer not null,
              use_author_api integer not null,
              custom_base_url text null,
              custom_api_key_encrypted text null,
              default_formatting text null,
              updated_at text not null
            );
            create table translation_tasks (
              task_id text primary key,
              user_id text null,
              source_type text not null,
              arxiv_id text null,
              status text not null,
              stage text null,
              progress integer not null,
              message text null,
              error text null,
              detail_code text null,
              source_language text not null,
              target_language text not null,
              translation_mode text not null,
              compile_strategy text not null,
              translation_model text null,
              config_hash text null,
              source_path text null,
              output_path text null,
              formatting text null,
              generate_glossary integer not null,
              use_author_api integer not null,
              email_notification integer not null,
              created_at text not null,
              completed_at text null
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
            create table community_agent_conversations (
              conversation_id text not null,
              user_id text not null,
              title text not null,
              created_at text not null,
              updated_at text not null,
              turns text not null,
              primary key (conversation_id, user_id)
            );
            create table community_agent_runs (
              run_id text primary key,
              user_id text null,
              conversation_id text null,
              status text not null,
              intent text not null,
              mode text not null,
              message text null,
              summary text null,
              error text null,
              report text null,
              created_at text not null,
              updated_at text not null,
              completed_at text null
            );
            create table community_agent_events (
              id integer primary key autoincrement,
              run_id text not null,
              sequence_no integer not null,
              event_type text not null,
              payload text not null,
              created_at text not null,
              unique (run_id, sequence_no)
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def _payload(asset_path: str) -> dict[str, list[dict]]:
    return {
        "users": [{"id": "usr_1", "external_provider": "niutrans", "external_user_id": 179017, "email": "alice@example.com", "display_name": "Alice", "token_version": "2", "status": "active", "created_at": "2026-04-10T09:00:00+08:00", "updated_at": "2026-04-10T09:30:00+08:00"}],
        "user_roles": [{"user_id": "usr_1", "role": "admin", "created_at": "2026-04-10T01:05:00Z"}],
        "user_settings": [{"user_id": "usr_1", "default_source_language": "en", "default_target_language": "zh", "translation_mode": "full", "compile_strategy": "auto", "translation_model": "gpt-local", "generate_glossary": "false", "use_author_api": "true", "default_formatting": {"line_spacing": 1.2}, "updated_at": "2026-04-10T01:05:00Z"}],
        "translation_tasks": [{"task_id": "task_1", "user_id": "usr_1", "source_type": "arxiv", "arxiv_id": "2501.00001", "status": "completed", "stage": "done", "progress": "100", "message": "done", "source_language": "en", "target_language": "zh", "translation_mode": "full", "compile_strategy": "auto", "translation_model": "gpt-local", "config_hash": "cfg_1", "source_path": "data/uploads/task_1", "output_path": "data/outputs/task_1", "formatting": {"font_size": 12}, "generate_glossary": "1", "use_author_api": 0, "email_notification": "true", "created_at": "2026-04-10T01:06:00Z", "completed_at": "2026-04-10T01:07:00Z"}],
        "papers": [{"id": "paper_1", "created_by": "usr_1", "source": "arxiv", "arxiv_id": "2501.00001", "title": "Demo", "authors": [{"name": "Alice"}], "categories": ["cs.CL"], "abstract_raw": "raw", "abstract_translated": "trans", "visibility": "public", "status": "published", "community_status": "active", "trans_status": "success", "trans_latest_task_id": "task_1", "community_selected_task_id": "task_1", "like_count": "3", "favorite_count": 2, "comment_count": "1", "view_count": 15, "download_count": "5", "official_published_at": "2026-04-10T01:08:00Z", "created_at": "2026-04-10T01:08:00Z", "updated_at": "2026-04-10T01:09:00Z"}],
        "paper_assets": [{"id": "asset_1", "paper_id": "paper_1", "task_id": "task_1", "asset_type": "translated_pdf", "storage_backend": "local_disk", "file_path": asset_path, "file_name": "", "mime_type": "", "is_latest": "true", "created_at": "2026-04-10T01:09:00Z"}],
        "community_agent_conversations": [{"id": "conv_1", "user_id": "usr_1", "title": "Chat 1", "created_at": "2026-04-10T01:10:00Z", "updated_at": "2026-04-10T01:10:30Z", "turns": [{"id": "turn_1", "role": "user", "content": "hello"}]}],
        "community_agent_runs": [{"run_id": "run_1", "user_id": "usr_1", "conversation_id": "conv_1", "status": "completed", "intent": "answer", "mode": "chat", "message": "ok", "summary": "done", "report": {"status": "ok"}, "created_at": "2026-04-10T01:11:00Z", "updated_at": "2026-04-10T01:12:00Z", "completed_at": "2026-04-10T01:12:00Z"}],
        "community_agent_events": [{"run_id": "run_1", "sequence_no": "1", "event_type": "status", "payload": {"type": "status", "sequence": 1, "data": {"status": "completed"}}, "created_at": "2026-04-10T01:11:30Z"}],
    }


def test_run_import_dry_run_reports_counts_and_missing_assets(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    existing_asset = tmp_path / "assets" / "present.pdf"
    existing_asset.parent.mkdir(parents=True, exist_ok=True)
    existing_asset.write_bytes(b"%PDF-1.4")
    missing_asset = tmp_path / "assets" / "missing.pdf"

    payload = _payload(str(existing_asset))
    payload["paper_assets"].append({"id": "asset_missing", "paper_id": "paper_1", "task_id": "task_1", "asset_type": "source_pdf", "storage_backend": "local_disk", "file_path": str(missing_asset), "file_name": "missing.pdf", "mime_type": "application/pdf", "is_latest": True, "created_at": "2026-04-10T01:09:30Z"})
    _write_exports(export_dir, payload)

    report = run_import(input_dir=export_dir, dry_run=True, asset_root=tmp_path)

    assert report["dry_run"] is True
    assert report["entities"]["users"]["source_rows"] == 1
    assert report["entities"]["paper_assets"]["source_rows"] == 2
    assert report["entities"]["paper_assets"]["missing_assets"] == 1
    assert report["missing_assets"][0]["entity"] == "paper_assets"
    assert "missing.pdf" in report["missing_assets"][0]["path"]


def test_run_import_write_mode_upserts_rows_and_normalizes_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database_path = tmp_path / "importer.db"
    export_dir = tmp_path / "exports"
    asset_file = tmp_path / "assets" / "paper_1.pdf"
    asset_file.parent.mkdir(parents=True, exist_ok=True)
    asset_file.write_bytes(b"%PDF-1.4")

    _create_sqlite_schema(database_path)
    _write_exports(export_dir, _payload(str(asset_file)))
    monkeypatch.setattr(get_settings(), "database_url", f"sqlite:///{database_path}")

    report = run_import(input_dir=export_dir, dry_run=False, asset_root=tmp_path)

    assert report["errors"] == []
    assert report["entities"]["users"]["inserted"] == 1
    assert report["entities"]["community_agent_events"]["inserted"] == 1

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        user_row = connection.execute("select external_user_id, token_version from users where id = ?", ("usr_1",)).fetchone()
        settings_row = connection.execute("select generate_glossary, use_author_api, default_formatting from user_settings where user_id = ?", ("usr_1",)).fetchone()
        task_row = connection.execute("select progress, formatting, email_notification from translation_tasks where task_id = ?", ("task_1",)).fetchone()
        asset_row = connection.execute("select file_name, mime_type, is_latest from paper_assets where id = ?", ("asset_1",)).fetchone()
        event_row = connection.execute("select sequence_no, event_type, payload from community_agent_events where run_id = ?", ("run_1",)).fetchone()
    finally:
        connection.close()

    assert user_row["external_user_id"] == "179017"
    assert user_row["token_version"] == 2
    assert settings_row["generate_glossary"] == 0
    assert settings_row["use_author_api"] == 1
    assert json.loads(settings_row["default_formatting"])["line_spacing"] == 1.2
    assert task_row["progress"] == 100
    assert json.loads(task_row["formatting"])["font_size"] == 12
    assert task_row["email_notification"] == 1
    assert asset_row["file_name"] == "paper_1.pdf"
    assert asset_row["mime_type"] == "application/pdf"
    assert asset_row["is_latest"] == 1
    assert event_row["sequence_no"] == 1
    assert event_row["event_type"] == "status"
    assert json.loads(event_row["payload"])["data"]["status"] == "completed"


def test_run_import_is_repeatable_and_reports_updates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    database_path = tmp_path / "repeatable.db"
    export_dir = tmp_path / "exports"
    asset_file = tmp_path / "assets" / "paper_1.pdf"
    asset_file.parent.mkdir(parents=True, exist_ok=True)
    asset_file.write_bytes(b"%PDF-1.4")

    _create_sqlite_schema(database_path)
    payload = _payload(str(asset_file))
    _write_exports(export_dir, payload)
    monkeypatch.setattr(get_settings(), "database_url", f"sqlite:///{database_path}")

    first_report = run_import(input_dir=export_dir, dry_run=False, asset_root=tmp_path)
    assert first_report["entities"]["users"]["inserted"] == 1
    assert first_report["entities"]["users"]["updated"] == 0

    payload["users"][0]["display_name"] = "Alice Updated"
    _write_exports(export_dir, payload)

    second_report = run_import(input_dir=export_dir, dry_run=False, asset_root=tmp_path)
    assert second_report["entities"]["users"]["inserted"] == 0
    assert second_report["entities"]["users"]["updated"] == 1

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        user_row = connection.execute("select display_name from users where id = ?", ("usr_1",)).fetchone()
    finally:
        connection.close()

    assert user_row["display_name"] == "Alice Updated"


def test_imported_paper_rows_are_visible_through_service_read_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "service-read.db"
    export_dir = tmp_path / "exports"
    asset_file = tmp_path / "assets" / "paper_1.pdf"
    asset_file.parent.mkdir(parents=True, exist_ok=True)
    asset_file.write_bytes(b"%PDF-1.4")

    payload = _payload(str(asset_file))
    payload["papers"][0]["abstract_translated"] = "杩欐槸瀵煎叆鍚庣殑涓枃鎽樿"
    payload["papers"][0]["community_status"] = "official"
    payload["papers"][0]["trans_status"] = "completed"

    _create_sqlite_schema(database_path)
    _write_exports(export_dir, payload)

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    monkeypatch.setattr(paper_service.settings, "database_url", f"sqlite:///{database_path}")
    monkeypatch.setattr(paper_service.settings, "community_baseline_seed_path", None)

    report = run_import(input_dir=export_dir, dry_run=False, asset_root=tmp_path)
    assert report["errors"] == []

    async def _identity_paper(row, asset_map=None):
        del asset_map
        return row

    async def _empty_viewer_state(_paper_ids, user_id=None):
        del user_id
        return {"paper_1": {"liked": False, "favorited": False}}

    async def _no_source_html(_arxiv_id: str):
        return None

    monkeypatch.setattr(paper_service, "_hydrate_arxiv_metadata_if_needed", _identity_paper)
    monkeypatch.setattr(paper_service, "_hydrate_translated_abstract_if_needed", _identity_paper)
    monkeypatch.setattr(paper_service, "_fetch_viewer_state", _empty_viewer_state)
    monkeypatch.setattr(paper_service, "_fetch_sanitized_arxiv_html", _no_source_html)

    listing = asyncio.run(paper_service.list_community_papers(sort="latest"))
    detail = asyncio.run(paper_service.get_community_paper_detail(paper_id="paper_1"))

    assert listing["source_mode"] == "database"
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == "paper_1"
    assert detail["paper"]["id"] == "paper_1"
    assert detail["paper"]["latest_asset"]["id"] == "asset_1"
    assert detail["reader"]["translated"]["kind"] == "translated_pdf"


