import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

import backend.app.main as main_module
from backend.app.api.routes import translate as translate_route
from backend.app.models.config_models import AdvancedConfig
from backend.app.services import task_manager
from backend.app.services.task_manager import clear_cached_runtime_artifacts


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client, table_name: str):
        self.client = client
        self.table_name = table_name
        self.mode = "select"
        self.columns = None
        self.filters = []
        self.payload = None

    def select(self, columns: str):
        self.mode = "select"
        self.columns = columns
        return self

    def delete(self):
        self.mode = "delete"
        return self

    def update(self, payload):
        self.mode = "update"
        self.payload = payload
        return self

    def eq(self, key, value):
        self.filters.append(("eq", key, value))
        return self

    def in_(self, key, values):
        self.filters.append(("in", key, tuple(values)))
        return self

    def is_(self, key, value):
        self.filters.append(("is", key, value))
        return self

    def execute(self):
        return self.client.execute(self)


class _FakeSupabaseClient:
    def __init__(self, handler):
        self.handler = handler

    def table(self, table_name: str):
        return _FakeQuery(self, table_name)

    def execute(self, query: _FakeQuery):
        return _Result(self.handler(query))


class _FakeTranslationTaskRepository:
    def __init__(
        self,
        *,
        active_ids=None,
        existing_ids=None,
        status_map=None,
        update_rowcount=None,
    ):
        self.active_ids = list(active_ids or [])
        self.existing_ids = set(existing_ids or [])
        self.status_map = dict(status_map or {})
        self.update_rowcount = update_rowcount
        self.updated_batches = []
        self.status_queries = []
        self.existing_queries = []

    def list_task_ids_by_status(self, _statuses):
        return list(self.active_ids)

    def update_tasks(self, task_ids, updates):
        self.updated_batches.append((tuple(task_ids), dict(updates)))
        if self.update_rowcount is not None:
            return self.update_rowcount
        return len(task_ids)

    def list_task_statuses(self, task_ids):
        self.status_queries.append(tuple(task_ids))
        return {
            task_id: self.status_map[task_id]
            for task_id in task_ids
            if task_id in self.status_map
        }

    def list_existing_task_ids(self, task_ids):
        self.existing_queries.append(tuple(task_ids))
        return [task_id for task_id in task_ids if task_id in self.existing_ids]


def _create_local_cleanup_schema(database_path: Path) -> None:
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

            create table comments (
              id text primary key,
              paper_id text not null
            );

            create table reports (
              id text primary key,
              target_type text not null,
              target_id text not null,
              status text not null default 'open',
              created_at text not null
            );

            create table moderation_actions (
              id text primary key,
              report_id text not null,
              action_type text not null,
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


def _seed_local_cleanup_rows(database_path: Path) -> None:
    connection = sqlite3.connect(str(database_path))
    try:
        cursor = connection.cursor()
        cursor.execute(
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
                "paper-local-purge",
                "usr-local-1",
                "upload",
                None,
                "Local draft paper",
                "[]",
                "[]",
                "raw",
                None,
                "private",
                "draft",
                "user_fallback",
                "processing",
                "task-latest",
                None,
                "task-community",
                None,
                0,
                0,
                0,
                0,
                0,
                None,
                "2026-04-09T09:00:00",
                "2026-04-09T09:00:00",
            ),
        )
        cursor.execute(
            """
            insert into paper_assets (
              id, paper_id, task_id, asset_type, storage_backend,
              file_path, file_name, mime_type, is_latest, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "asset-source-1",
                "paper-local-purge",
                "task-source",
                "source_archive",
                "local_disk",
                "data/community_papers/paper-local-purge/source.zip",
                "source.zip",
                "application/zip",
                1,
                "2026-04-09T09:01:00",
            ),
        )
        cursor.execute(
            "insert into comments (id, paper_id) values (?, ?)",
            ("comment-local-1", "paper-local-purge"),
        )
        cursor.execute(
            """
            insert into reports (id, target_type, target_id, status, created_at)
            values (?, ?, ?, ?, ?)
            """,
            ("report-paper-1", "paper", "paper-local-purge", "open", "2026-04-09T09:02:00"),
        )
        cursor.execute(
            """
            insert into reports (id, target_type, target_id, status, created_at)
            values (?, ?, ?, ?, ?)
            """,
            ("report-comment-1", "comment", "comment-local-1", "open", "2026-04-09T09:03:00"),
        )
        cursor.execute(
            """
            insert into moderation_actions (id, report_id, action_type, created_at)
            values (?, ?, ?, ?)
            """,
            ("action-report-1", "report-paper-1", "dismiss", "2026-04-09T09:04:00"),
        )
        cursor.execute(
            """
            insert into moderation_actions (id, report_id, action_type, created_at)
            values (?, ?, ?, ?)
            """,
            ("action-report-2", "report-comment-1", "dismiss", "2026-04-09T09:05:00"),
        )
        cursor.execute(
            "insert into paper_likes (paper_id, user_id) values (?, ?)",
            ("paper-local-purge", "usr-local-1"),
        )
        cursor.execute(
            "insert into paper_favorites (paper_id, user_id) values (?, ?)",
            ("paper-local-purge", "usr-local-1"),
        )
        connection.commit()
    finally:
        connection.close()


def test_reset_stale_community_tasks_purges_all_related_records(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ENABLE_STALE_PAPER_PURGE", "true")
    community_root = tmp_path / "community_papers"
    community_root.mkdir(parents=True, exist_ok=True)
    (community_root / "paper-1").mkdir()

    deleted = {
        "tables": [],
        "task_ids": [],
    }

    class _FakeCommunityRepository:
        def list_purgeable_non_success_papers(self, _statuses):
            return [
                {
                    "id": "paper-1",
                    "trans_latest_task_id": "task-latest",
                    "community_selected_task_id": "task-community",
                    "visibility": "private",
                    "status": "draft",
                }
            ]

        def list_asset_task_ids_for_papers(self, _paper_ids):
            return ["task-source"]

        def list_comment_ids_for_papers(self, _paper_ids):
            return ["comment-1"]

        def list_report_ids_for_targets(self, *, target_type, target_ids):
            if target_type == "paper" and list(target_ids) == ["paper-1"]:
                return ["report-paper"]
            if target_type == "comment" and list(target_ids) == ["comment-1"]:
                return ["report-comment"]
            return []

        def delete_rows_by_ids(self, table_name, *, id_column, row_ids):
            deleted["tables"].append((table_name, id_column, tuple(row_ids)))

        def delete_rows_for_papers(self, table_name, paper_ids):
            deleted["tables"].append((table_name, "paper_id", tuple(paper_ids)))

        def delete_translation_tasks(self, task_ids):
            deleted["tables"].append(("translation_tasks", "task_id", tuple(task_ids)))

    class _FakeTaskManager:
        def delete_task_full(self, task_id: str):
            deleted["task_ids"].append(task_id)
            return {"success": True, "deleted_dirs": [f"/tmp/{task_id}"], "errors": []}

    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            migration_source_service_role_key="service-role",
            migration_source_url="https://example.import-source.local",
            community_papers_dir=community_root,
        ),
    )
    monkeypatch.setattr(main_module, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(
        main_module,
        "get_task_manager",
        lambda: _FakeTaskManager(),
        raising=False,
    )

    result = asyncio.run(main_module.reset_stale_community_tasks())

    deleted_tables = [table for table, _column, _row_ids in deleted["tables"]]
    assert result["purged_records"] == 1
    assert set(deleted["task_ids"]) == {"task-community", "task-latest", "task-source"}
    assert not (community_root / "paper-1").exists()
    assert "comments" in deleted_tables
    assert "reports" in deleted_tables
    assert "moderation_actions" in deleted_tables
    assert "paper_assets" in deleted_tables
    assert "paper_likes" in deleted_tables
    assert "paper_favorites" in deleted_tables
    assert "translation_tasks" in deleted_tables
    assert "papers" in deleted_tables


def test_reset_stale_community_tasks_keeps_public_papers_even_if_non_success(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ENABLE_STALE_PAPER_PURGE", "true")
    community_root = tmp_path / "community_papers"
    community_root.mkdir(parents=True, exist_ok=True)
    (community_root / "paper-public").mkdir()

    deleted = {"tables": []}
    paper_rows = [
        {
            "id": "paper-public",
            "trans_latest_task_id": "task-public",
            "community_selected_task_id": "task-public",
            "visibility": "public",
            "status": "published",
        }
    ]

    def handler(query: _FakeQuery):
        if query.table_name == "papers" and query.mode == "select":
            if (
                (
                    "in",
                    "trans_status",
                    ("not_started", "queued", "processing", "failed", "failed_compilation", "structure_invalid"),
                )
                in query.filters
            ):
                return paper_rows
        if query.mode == "delete":
            deleted["tables"].append(query.table_name)
            return [{"ok": True}]
        return []

    class _FakeTaskManager:
        def delete_task_full(self, task_id: str):
            return {"success": True, "deleted_dirs": [f"/tmp/{task_id}"], "errors": []}

    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            migration_source_service_role_key="service-role",
            migration_source_url="https://example.import-source.local",
            community_papers_dir=community_root,
        ),
    )
    monkeypatch.setattr(main_module, "get_task_manager", lambda: _FakeTaskManager(), raising=False)

    result = asyncio.run(main_module.reset_stale_community_tasks())

    assert result.get("purged_records", 0) == 0
    assert (community_root / "paper-public").exists()
    assert not deleted["tables"]


def test_reset_stale_community_tasks_uses_local_repository_in_local_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    community_root = tmp_path / "community_papers"
    community_root.mkdir(parents=True, exist_ok=True)
    (community_root / "paper-local-purge").mkdir()
    database_path = tmp_path / "community-cleanup.db"
    _create_local_cleanup_schema(database_path)
    _seed_local_cleanup_rows(database_path)

    deleted_task_ids = []

    class _FakeTaskManager:
        def delete_task_full(self, task_id: str):
            deleted_task_ids.append(task_id)
            return {"success": True, "deleted_dirs": [f"/tmp/{task_id}"], "errors": []}

    settings = main_module.get_settings()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path.resolve()}")
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            migration_source_service_role_key="",
            migration_source_url="",
            community_papers_dir=community_root,
        ),
    )
    monkeypatch.setattr(main_module, "get_task_manager", lambda: _FakeTaskManager(), raising=False)

    result = asyncio.run(main_module.reset_stale_community_tasks())

    assert result["purged_records"] == 1
    assert result["deleted_folders"] == 1
    assert set(deleted_task_ids) == {"task-community", "task-latest", "task-source"}
    assert not (community_root / "paper-local-purge").exists()

    connection = sqlite3.connect(str(database_path))
    try:
        paper_count = connection.execute("select count(*) from papers").fetchone()[0]
        asset_count = connection.execute("select count(*) from paper_assets").fetchone()[0]
        comment_count = connection.execute("select count(*) from comments").fetchone()[0]
        report_count = connection.execute("select count(*) from reports").fetchone()[0]
        moderation_action_count = connection.execute("select count(*) from moderation_actions").fetchone()[0]
        like_count = connection.execute("select count(*) from paper_likes").fetchone()[0]
        favorite_count = connection.execute("select count(*) from paper_favorites").fetchone()[0]
    finally:
        connection.close()

    assert paper_count == 0
    assert asset_count == 0
    assert comment_count == 0
    assert report_count == 0
    assert moderation_action_count == 0
    assert like_count == 0
    assert favorite_count == 0


def test_reset_stale_community_tasks_skips_when_local_repository_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    community_root = tmp_path / "community_papers"
    community_root.mkdir(parents=True, exist_ok=True)
    legacy_client_calls = {"count": 0}

    class _UnavailableCommunityRepository:
        def list_purgeable_non_success_papers(self, _statuses):
            raise main_module.DatabaseUnavailableError("local database unavailable")

    monkeypatch.setenv("ENABLE_STALE_PAPER_PURGE", "true")
    monkeypatch.setattr(main_module, "get_community_paper_repository", lambda: _UnavailableCommunityRepository())
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            migration_source_service_role_key="service-role",
            migration_source_url="https://example.import-source.local",
            community_papers_dir=community_root,
        ),
    )

    result = asyncio.run(main_module.reset_stale_community_tasks())

    assert result.get("purged_records", 0) == 0
    assert result["errors"]
    assert legacy_client_calls["count"] == 0


def test_fail_interrupted_translation_tasks_marks_failed_and_cleans_artifacts(monkeypatch):
    deleted_task_ids = []
    fake_repo = _FakeTranslationTaskRepository(
        active_ids=["task-run", "task-download"],
        status_map={"task-run": "failed"},
    )
    marked_task_ids = []

    class _FakeTaskManager:
        def delete_task_full(self, task_id: str):
            deleted_task_ids.append(task_id)
            return {"success": True, "deleted_dirs": [f"/tmp/{task_id}"], "errors": []}

    class _FakeCommunityRepository:
        def list_inflight_translation_papers(self):
            return []

    async def _fake_mark_paper_translation_failed_by_task(task_id: str):
        marked_task_ids.append(task_id)
        return 1

    monkeypatch.setattr(main_module, "get_community_paper_repository", lambda: _FakeCommunityRepository())
    monkeypatch.setattr(main_module, "get_task_manager", lambda: _FakeTaskManager(), raising=False)
    monkeypatch.setattr(main_module, "get_translation_task_repository", lambda: fake_repo)
    monkeypatch.setattr(
        "backend.app.services.paper_service.mark_paper_translation_failed_by_task",
        _fake_mark_paper_translation_failed_by_task,
    )
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            migration_source_service_role_key="service-role",
            migration_source_url="https://example.import-source.local",
        ),
    )

    result = asyncio.run(main_module.fail_interrupted_translation_tasks())

    assert result["failed_tasks"] == 2
    assert result["updated_papers"] == 2
    assert set(deleted_task_ids) == {"task-run", "task-download"}
    assert marked_task_ids == ["task-run", "task-download"]
    assert fake_repo.updated_batches
    batch_task_ids, batch_payload = fake_repo.updated_batches[-1]
    assert set(batch_task_ids) == {"task-run", "task-download"}
    assert batch_payload["status"] == "failed"
    assert batch_payload["detail_code"] == "task_interrupted_restart"


def test_fail_interrupted_translation_tasks_marks_local_rows_in_local_mode(monkeypatch):
    deleted_task_ids = []
    fake_repo = _FakeTranslationTaskRepository(active_ids=["task-run"])
    marked_task_ids = []

    class _FakeTaskManager:
        def delete_task_full(self, task_id: str):
            deleted_task_ids.append(task_id)
            return {"success": True, "deleted_dirs": [f"/tmp/{task_id}"], "errors": []}

    async def _fake_mark_paper_translation_failed_by_task(task_id: str):
        marked_task_ids.append(task_id)
        return 1

    monkeypatch.setattr(main_module, "get_task_manager", lambda: _FakeTaskManager(), raising=False)
    monkeypatch.setattr(main_module, "get_translation_task_repository", lambda: fake_repo)
    monkeypatch.setattr(
        "backend.app.services.paper_service.mark_paper_translation_failed_by_task",
        _fake_mark_paper_translation_failed_by_task,
    )
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            migration_source_service_role_key="",
            migration_source_url="",
        ),
    )

    result = asyncio.run(main_module.fail_interrupted_translation_tasks())

    assert result["failed_tasks"] == 1
    assert result["updated_papers"] == 1
    assert result["cleaned_task_artifacts"] == 1
    assert deleted_task_ids == ["task-run"]
    assert marked_task_ids == ["task-run"]
    assert fake_repo.updated_batches
    assert fake_repo.updated_batches[-1][1]["status"] == "failed"


def test_fail_interrupted_translation_tasks_prefers_local_paper_reconciliation_even_with_legacy_migration_env_present(
    monkeypatch,
):
    deleted_task_ids = []
    marked_task_ids = []
    fake_repo = _FakeTranslationTaskRepository(
        active_ids=["task-run", "task-download"],
        status_map={"task-run": "failed", "task-stale": "failed"},
    )

    class _FakeTaskManager:
        def delete_task_full(self, task_id: str):
            deleted_task_ids.append(task_id)
            return {"success": True, "deleted_dirs": [f"/tmp/{task_id}"], "errors": []}

    class _FakeCommunityPaperRepository:
        def list_inflight_translation_papers(self):
            return [
                {"id": "paper-1", "community_selected_task_id": "task-run"},
                {"id": "paper-2", "community_selected_task_id": "task-stale"},
                {"id": "paper-3", "community_selected_task_id": "task-ok"},
            ]

    async def _fake_mark_paper_translation_failed_by_task(task_id: str):
        marked_task_ids.append(task_id)
        return 1 if task_id in {"task-run", "task-stale"} else 0

    def _unexpected_legacy_admin_client():
        raise AssertionError("Legacy admin client should not be used during local restart failover")

    monkeypatch.setattr(main_module, "get_task_manager", lambda: _FakeTaskManager(), raising=False)
    monkeypatch.setattr(main_module, "get_translation_task_repository", lambda: fake_repo)
    monkeypatch.setattr(main_module, "get_community_paper_repository", lambda: _FakeCommunityPaperRepository())
    monkeypatch.setattr(
        "backend.app.services.paper_service.mark_paper_translation_failed_by_task",
        _fake_mark_paper_translation_failed_by_task,
    )
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            migration_source_service_role_key="service-role",
            migration_source_url="https://example.import-source.local",
        ),
    )

    result = asyncio.run(main_module.fail_interrupted_translation_tasks())

    assert result["failed_tasks"] == 2
    assert result["updated_papers"] == 2
    assert set(deleted_task_ids) == {"task-run", "task-download"}
    assert marked_task_ids.count("task-run") == 1
    assert marked_task_ids.count("task-stale") == 1
    assert "task-download" in marked_task_ids
    assert fake_repo.status_queries
    assert set(fake_repo.status_queries[-1]) == {"task-run", "task-stale", "task-ok"}


def test_startup_orphan_cleanup_uses_local_translation_task_repository(monkeypatch, tmp_path: Path):
    outputs_dir = tmp_path / "outputs"
    terms_dir = tmp_path / "data" / "terms"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    terms_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / "task-orphan").mkdir()
    (terms_dir / "task-keep").mkdir()

    fake_repo = _FakeTranslationTaskRepository(existing_ids=["task-keep"])

    class _FakeTaskQueue:
        def __init__(self, *args, **kwargs):
            pass

        async def initialize(self):
            return None

    async def _fake_failover():
        return {}

    async def _fake_reset():
        return {}

    async def _fake_sleep(_seconds: float):
        raise asyncio.CancelledError()

    async def _run() -> None:
        monkeypatch.setattr(main_module, "fail_interrupted_translation_tasks", _fake_failover)
        monkeypatch.setattr(main_module, "reset_stale_community_tasks", _fake_reset)
        monkeypatch.setattr(main_module, "get_translation_task_repository", lambda: fake_repo)
        monkeypatch.setattr(main_module.asyncio, "sleep", _fake_sleep)
        monkeypatch.setattr(
            "backend.app.services.task_manager.TaskQueue",
            _FakeTaskQueue,
        )
        monkeypatch.setattr(
            main_module,
            "settings",
            SimpleNamespace(
                app_name="LaTexTrans",
                version="test",
                data_dir=tmp_path / "data",
                outputs_dir=outputs_dir,
                guest_task_ttl_hours=0,
                max_concurrent_translations=1,
                llm_model="gpt-test",
                cors_origins=["http://localhost:3000"],
            ),
        )

        await main_module.startup_event()
        with pytest.raises(asyncio.CancelledError):
            await main_module.app.state.cleanup_task

    asyncio.run(_run())

    assert fake_repo.existing_queries
    assert set(fake_repo.existing_queries[0]) == {"task-orphan", "task-keep"}
    assert not (outputs_dir / "task-orphan").exists()
    assert (terms_dir / "task-keep").exists()


def test_clear_cached_runtime_artifacts_removes_existing_file_and_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    outputs_dir = tmp_path / "outputs"
    staging_dir = tmp_path / "tmp_storage"
    monkeypatch.setattr(
        task_manager,
        "get_settings",
        lambda: SimpleNamespace(outputs_dir=outputs_dir, storage_temp_dir=staging_dir),
    )

    file_path = outputs_dir / "task-1" / "translated.pdf"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("pdf", encoding="utf-8")
    preview_dir = staging_dir / "task-1" / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    (preview_dir / "preview.html").write_text("<article>preview</article>", encoding="utf-8")

    cleared = clear_cached_runtime_artifacts("task-1", [file_path, preview_dir])

    assert str(file_path) in cleared
    assert str(preview_dir) in cleared
    assert not file_path.exists()
    assert not preview_dir.exists()


def test_clear_cached_runtime_artifacts_skips_paths_outside_allowed_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    outputs_dir = tmp_path / "outputs"
    staging_dir = tmp_path / "tmp_storage"
    outside_dir = tmp_path / "outside"
    monkeypatch.setattr(
        task_manager,
        "get_settings",
        lambda: SimpleNamespace(outputs_dir=outputs_dir, storage_temp_dir=staging_dir),
    )

    inside_file = outputs_dir / "task-1" / "inside.txt"
    inside_file.parent.mkdir(parents=True, exist_ok=True)
    inside_file.write_text("inside", encoding="utf-8")

    outside_file = outside_dir / "leak.txt"
    outside_file.parent.mkdir(parents=True, exist_ok=True)
    outside_file.write_text("outside", encoding="utf-8")

    cleared = clear_cached_runtime_artifacts("task-1", [inside_file, outside_file])

    assert str(inside_file) in cleared
    assert str(outside_file) not in cleared
    assert not inside_file.exists()
    assert outside_file.exists()


def test_startup_web_role_skips_background_recovery_and_cleanup_loops(monkeypatch, tmp_path: Path):
    calls = {"failover": 0, "reset": 0, "resume_curation": 0, "resume_delete": 0}

    class _FakeTaskQueue:
        def __init__(self, *args, **kwargs):
            pass

        async def initialize(self):
            return None

    async def _fake_failover():
        calls["failover"] += 1
        return {}

    async def _fake_reset():
        calls["reset"] += 1
        return {}

    async def _fake_resume_curation():
        calls["resume_curation"] += 1
        return {}

    async def _fake_resume_delete():
        calls["resume_delete"] += 1
        return {}

    async def _run() -> None:
        monkeypatch.setattr(main_module, "fail_interrupted_translation_tasks", _fake_failover)
        monkeypatch.setattr(main_module, "reset_stale_community_tasks", _fake_reset)
        monkeypatch.setattr(
            "backend.app.services.paper_service.resume_pending_admin_curation_jobs",
            _fake_resume_curation,
        )
        monkeypatch.setattr(
            "backend.app.services.paper_service.resume_pending_delete_jobs",
            _fake_resume_delete,
        )
        monkeypatch.setattr(
            "backend.app.services.task_manager.TaskQueue",
            _FakeTaskQueue,
        )
        monkeypatch.setattr(
            main_module,
            "settings",
            SimpleNamespace(
                app_name="LaTexTrans",
                version="test",
                data_dir=tmp_path / "data",
                outputs_dir=tmp_path / "data" / "outputs",
                guest_task_ttl_hours=0,
                max_concurrent_translations=1,
                llm_model="gpt-test",
                cors_origins=["http://localhost:3000"],
                backend_runtime_role="web",
            ),
        )

        await main_module.startup_event()
        assert getattr(main_module.app.state, "cleanup_task", None) is None
        assert getattr(main_module.app.state, "admin_job_poll_task", None) is None
        await main_module.shutdown_event()

    asyncio.run(_run())

    assert calls == {
        "failover": 0,
        "reset": 0,
        "resume_curation": 0,
        "resume_delete": 0,
    }


def test_startup_worker_role_runs_failover_and_admin_poll_without_stale_cleanup(monkeypatch, tmp_path: Path):
    calls = {"failover": 0, "reset": 0, "resume_curation": 0, "resume_delete": 0}

    class _FakeTaskQueue:
        def __init__(self, *args, **kwargs):
            pass

        async def initialize(self):
            return None

    async def _fake_failover():
        calls["failover"] += 1
        return {}

    async def _fake_reset():
        calls["reset"] += 1
        return {}

    async def _fake_resume_curation():
        calls["resume_curation"] += 1
        return {}

    async def _fake_resume_delete():
        calls["resume_delete"] += 1
        return {}

    async def _fake_sleep(_seconds: float):
        raise asyncio.CancelledError()

    async def _run() -> None:
        monkeypatch.setattr(main_module, "fail_interrupted_translation_tasks", _fake_failover)
        monkeypatch.setattr(main_module, "reset_stale_community_tasks", _fake_reset)
        monkeypatch.setattr(main_module.asyncio, "sleep", _fake_sleep)
        monkeypatch.setattr(
            "backend.app.services.paper_service.resume_pending_admin_curation_jobs",
            _fake_resume_curation,
        )
        monkeypatch.setattr(
            "backend.app.services.paper_service.resume_pending_delete_jobs",
            _fake_resume_delete,
        )
        monkeypatch.setattr(
            "backend.app.services.task_manager.TaskQueue",
            _FakeTaskQueue,
        )
        monkeypatch.setattr(
            main_module,
            "settings",
            SimpleNamespace(
                app_name="LaTexTrans",
                version="test",
                data_dir=tmp_path / "data",
                outputs_dir=tmp_path / "data" / "outputs",
                guest_task_ttl_hours=0,
                max_concurrent_translations=1,
                llm_model="gpt-test",
                cors_origins=["http://localhost:3000"],
                backend_runtime_role="worker",
                admin_job_poll_interval_seconds=1,
            ),
        )

        await main_module.startup_event()
        with pytest.raises(asyncio.CancelledError):
            await main_module.app.state.admin_job_poll_task
        await main_module.shutdown_event()

    asyncio.run(_run())

    assert calls["failover"] == 1
    assert calls["reset"] == 0
    assert calls["resume_curation"] == 1
    assert calls["resume_delete"] == 1


def test_run_translation_persists_failed_state_on_cancel(monkeypatch, tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    main_tex = source_dir / "main.tex"
    main_tex.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")

    updates = []
    marked_failed_tasks = []

    class _FakeTaskManager:
        def is_cancelled(self, task_id: str) -> bool:
            return False

        def get_task(self, task_id: str):
            return {
                "task_id": task_id,
                "source_path": str(source_dir),
                "source_type": "upload",
                "arxiv_id": None,
                "advanced_config": {},
            }

        def update_task(self, task_id: str, **kwargs):
            updates.append((task_id, kwargs))
            return True

    monkeypatch.setattr(translate_route, "task_manager", _FakeTaskManager())
    monkeypatch.setattr(translate_route, "settings", SimpleNamespace(outputs_dir=tmp_path / "outputs"))
    monkeypatch.setattr(translate_route, "is_runtime_shutting_down", lambda: True)
    monkeypatch.setattr(
        "backend.app.services.paper_service.mark_paper_translation_failed_by_task",
        lambda task_id: asyncio.sleep(0, result=marked_failed_tasks.append(task_id) or 1),
    )
    monkeypatch.setattr(
        translate_route,
        "find_main_tex_file",
        lambda _path: (_ for _ in ()).throw(asyncio.CancelledError()),
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            translate_route.run_translation(
                task_id="task-cancelled",
                target_language="zh",
                source_language="en",
                advanced_config=AdvancedConfig(),
                user_id="user-1",
            )
        )

    failed_updates = [payload for task_id, payload in updates if task_id == "task-cancelled" and payload.get("status") == "failed"]
    assert failed_updates, "cancelled translation should persist a failed state after restart interruption"
    assert failed_updates[-1].get("detail_code") == "task_interrupted_restart"
    assert marked_failed_tasks == ["task-cancelled"]


def test_run_translation_runtime_cancel_does_not_mark_restart_failure(monkeypatch, tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    main_tex = source_dir / "main.tex"
    main_tex.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")

    updates = []
    marked_failed_tasks = []

    class _FakeTaskManager:
        def is_cancelled(self, task_id: str) -> bool:
            return False

        def get_task(self, task_id: str):
            return {
                "task_id": task_id,
                "source_path": str(source_dir),
                "source_type": "upload",
                "arxiv_id": None,
                "advanced_config": {},
            }

        def update_task(self, task_id: str, **kwargs):
            updates.append((task_id, kwargs))
            return True

    monkeypatch.setattr(translate_route, "task_manager", _FakeTaskManager())
    monkeypatch.setattr(translate_route, "settings", SimpleNamespace(outputs_dir=tmp_path / "outputs"))
    monkeypatch.setattr(translate_route, "is_runtime_shutting_down", lambda: False)
    monkeypatch.setattr(
        "backend.app.services.paper_service.mark_paper_translation_failed_by_task",
        lambda task_id: asyncio.sleep(0, result=marked_failed_tasks.append(task_id) or 1),
    )
    monkeypatch.setattr(
        translate_route,
        "find_main_tex_file",
        lambda _path: (_ for _ in ()).throw(asyncio.CancelledError()),
    )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            translate_route.run_translation(
                task_id="task-runtime-cancelled",
                target_language="zh",
                source_language="en",
                advanced_config=AdvancedConfig(),
                user_id="user-1",
            )
        )

    failed_updates = [
        payload
        for task_id, payload in updates
        if task_id == "task-runtime-cancelled" and payload.get("status") == "failed"
    ]
    assert not failed_updates, "runtime cancellation should not be mislabeled as restart interruption"
    assert marked_failed_tasks == []


@pytest.mark.parametrize(
    ("workflow_status", "expected_task_status"),
    [
        ("failed_compilation", "failed_compilation"),
        ("structure_invalid", "structure_invalid"),
    ],
)
def test_run_translation_terminal_failure_syncs_paper_status(
    monkeypatch,
    tmp_path: Path,
    workflow_status: str,
    expected_task_status: str,
):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    main_tex = source_dir / "main.tex"
    main_tex.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")

    updates = []
    marked_failed_tasks = []

    class _FakeTaskManager:
        def is_cancelled(self, task_id: str) -> bool:
            return False

        def get_task(self, task_id: str):
            return {
                "task_id": task_id,
                "source_path": str(source_dir),
                "source_type": "upload",
                "arxiv_id": None,
                "advanced_config": {},
            }

        def update_task(self, task_id: str, **kwargs):
            updates.append((task_id, kwargs))
            return True

        def create_progress_callback(self, _task_id: str):
            def _callback(_progress: int, _message: str):
                return None

            return _callback

    class _FakeCoordinator:
        def __init__(self, *args, **kwargs):
            pass

        async def workflow_latextrans_async(self):
            return {
                "status": workflow_status,
                "error_summary": "fixture failure",
                "warnings": None,
                "pdf_path": None,
            }

    async def _fake_find_reusable_output(_config_hash: str, _task_id: str):
        return None

    async def _fake_mark_failed(task_id: str):
        marked_failed_tasks.append(task_id)
        return 1

    monkeypatch.setattr(translate_route, "task_manager", _FakeTaskManager())
    monkeypatch.setattr(
        translate_route,
        "settings",
        SimpleNamespace(
            outputs_dir=tmp_path / "outputs",
            uploads_dir=tmp_path / "uploads",
            llm_max_concurrent_requests=1,
            model_context_tokens=32000,
            prompt_reserve_tokens=4096,
            enable_compile_first_structural_fallback=False,
            enable_post_compile_target_language_fallback=False,
            structural_fallback_ratio_cap=0.0,
            structural_fallback_cap_mode="soft",
        ),
    )
    monkeypatch.setattr(translate_route, "find_main_tex_file", lambda _path: main_tex)
    monkeypatch.setattr(translate_route, "find_reusable_output", _fake_find_reusable_output)
    monkeypatch.setattr(translate_route, "build_llm_config_async", lambda *_args, **_kwargs: asyncio.sleep(0, result={}))
    monkeypatch.setattr(translate_route, "capture_task_config", lambda **_kwargs: None)
    monkeypatch.setattr(translate_route, "CoordinatorAgent", _FakeCoordinator)
    monkeypatch.setattr(
        "backend.app.services.paper_service.mark_paper_translation_failed_by_task",
        _fake_mark_failed,
    )

    asyncio.run(
        translate_route.run_translation(
            task_id="task-terminal-failure",
            target_language="zh",
            source_language="en",
            advanced_config=AdvancedConfig(),
            user_id="user-1",
        )
    )

    terminal_updates = [
        payload
        for task_id, payload in updates
        if task_id == "task-terminal-failure" and payload.get("status") == expected_task_status
    ]
    assert terminal_updates, f"translation should persist {expected_task_status} status"
    assert marked_failed_tasks == ["task-terminal-failure"]



