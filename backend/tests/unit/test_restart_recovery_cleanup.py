import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

import backend.app.main as main_module
from backend.app.api.routes import translate as translate_route
from backend.app.models.config_models import AdvancedConfig


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


def test_reset_stale_community_tasks_purges_all_related_records(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ENABLE_STALE_PAPER_PURGE", "true")
    community_root = tmp_path / "community_papers"
    community_root.mkdir(parents=True, exist_ok=True)
    (community_root / "paper-1").mkdir()

    deleted = {
        "tables": [],
        "task_ids": [],
    }

    paper_rows = [
        {
            "id": "paper-1",
            "trans_latest_task_id": "task-latest",
            "community_selected_task_id": "task-community",
            "visibility": "private",
            "status": "draft",
        }
    ]
    asset_rows = [
        {"task_id": "task-latest"},
        {"task_id": "task-source"},
        {"task_id": None},
    ]
    comment_rows = [{"id": "comment-1"}]
    report_rows = [{"id": "report-paper"}, {"id": "report-comment"}]

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

        if query.table_name == "paper_assets" and query.mode == "select":
            return asset_rows

        if query.table_name == "comments" and query.mode == "select":
            return comment_rows

        if query.table_name == "reports" and query.mode == "select":
            return report_rows

        if query.mode == "delete":
            deleted["tables"].append(
                (query.table_name, tuple(query.filters), query.payload)
            )
            return [{"ok": True}]

        if query.mode == "update":
            return []

        return []

    class _FakeTaskManager:
        def delete_task_full(self, task_id: str):
            deleted["task_ids"].append(task_id)
            return {"success": True, "deleted_dirs": [f"/tmp/{task_id}"], "errors": []}

    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            supabase_service_role_key="service-role",
            supabase_url="https://example.supabase.co",
            community_papers_dir=community_root,
        ),
    )
    monkeypatch.setattr(
        "backend.app.core.supabase_client.create_supabase_admin_client",
        lambda: _FakeSupabaseClient(handler),
    )
    monkeypatch.setattr(
        main_module,
        "get_task_manager",
        lambda: _FakeTaskManager(),
        raising=False,
    )

    result = asyncio.run(main_module.reset_stale_community_tasks())

    deleted_tables = [table for table, _filters, _payload in deleted["tables"]]
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
            supabase_service_role_key="service-role",
            supabase_url="https://example.supabase.co",
            community_papers_dir=community_root,
        ),
    )
    monkeypatch.setattr(
        "backend.app.core.supabase_client.create_supabase_admin_client",
        lambda: _FakeSupabaseClient(handler),
    )
    monkeypatch.setattr(main_module, "get_task_manager", lambda: _FakeTaskManager(), raising=False)

    result = asyncio.run(main_module.reset_stale_community_tasks())

    assert result.get("purged_records", 0) == 0
    assert (community_root / "paper-public").exists()
    assert not deleted["tables"]


def test_fail_interrupted_translation_tasks_marks_failed_and_cleans_artifacts(monkeypatch):
    affected_papers = [{"id": "paper-1"}]
    stale_papers = [{"id": "paper-2", "community_selected_task_id": "task-run"}]
    updates = []
    deleted_task_ids = []
    fake_repo = _FakeTranslationTaskRepository(
        active_ids=["task-run", "task-download"],
        status_map={"task-run": "failed"},
    )

    def handler(query: _FakeQuery):
        if query.table_name == "papers" and query.mode == "select":
            if query.columns == "id":
                return affected_papers
            if query.columns == "id, community_selected_task_id":
                return stale_papers
        if query.mode == "update":
            updates.append((query.table_name, query.payload, tuple(query.filters)))
            return [{"ok": True}]
        return []

    class _FakeTaskManager:
        def delete_task_full(self, task_id: str):
            deleted_task_ids.append(task_id)
            return {"success": True, "deleted_dirs": [f"/tmp/{task_id}"], "errors": []}

    monkeypatch.setattr(
        "backend.app.core.supabase_client.create_supabase_admin_client",
        lambda: _FakeSupabaseClient(handler),
    )
    monkeypatch.setattr(main_module, "get_task_manager", lambda: _FakeTaskManager(), raising=False)
    monkeypatch.setattr(main_module, "get_translation_task_repository", lambda: fake_repo)
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            supabase_service_role_key="service-role",
            supabase_url="https://example.supabase.co",
        ),
    )

    result = asyncio.run(main_module.fail_interrupted_translation_tasks())

    assert result["failed_tasks"] == 2
    assert result["updated_papers"] == 2
    assert set(deleted_task_ids) == {"task-run", "task-download"}
    assert fake_repo.updated_batches
    batch_task_ids, batch_payload = fake_repo.updated_batches[-1]
    assert set(batch_task_ids) == {"task-run", "task-download"}
    assert batch_payload["status"] == "failed"
    assert batch_payload["detail_code"] == "task_interrupted_restart"
    assert any(table == "papers" for table, _payload, _filters in updates)


def test_fail_interrupted_translation_tasks_marks_local_rows_without_supabase(monkeypatch):
    deleted_task_ids = []
    fake_repo = _FakeTranslationTaskRepository(active_ids=["task-run"])

    class _FakeTaskManager:
        def delete_task_full(self, task_id: str):
            deleted_task_ids.append(task_id)
            return {"success": True, "deleted_dirs": [f"/tmp/{task_id}"], "errors": []}

    monkeypatch.setattr(main_module, "get_task_manager", lambda: _FakeTaskManager(), raising=False)
    monkeypatch.setattr(main_module, "get_translation_task_repository", lambda: fake_repo)
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            supabase_service_role_key="",
            supabase_url="",
        ),
    )

    result = asyncio.run(main_module.fail_interrupted_translation_tasks())

    assert result["failed_tasks"] == 1
    assert result["updated_papers"] == 0
    assert result["cleaned_task_artifacts"] == 1
    assert deleted_task_ids == ["task-run"]
    assert fake_repo.updated_batches
    assert fake_repo.updated_batches[-1][1]["status"] == "failed"


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
