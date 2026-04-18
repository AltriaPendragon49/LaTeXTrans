import asyncio
from pathlib import Path

from fastapi import HTTPException

from backend.app.repositories.community_paper_repository import CommunityPaperRepository
from backend.app.services import paper_service


class _FakeCursor:
    def __init__(self) -> None:
        self.sql = ""
        self.params = ()

    def execute(self, sql, params) -> None:
        self.sql = sql
        self.params = params

    def fetchall(self):
        return []


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeRepository:
    def __init__(self, job: dict):
        self.job = dict(job)
        self.updates: list[dict] = []
        self.deleted_translation_tasks: list[list[str]] = []
        self.deleted_paper_rows: list[tuple[str, list[str]]] = []

    def get_curation_job(self, _job_id: str):
        return dict(self.job)

    def update_curation_job(self, _job_id: str, updates: dict):
        self.job.update(updates)
        self.updates.append(dict(updates))
        return dict(self.job)

    def delete_translation_tasks(self, task_ids: list[str]):
        self.deleted_translation_tasks.append(list(task_ids))
        return len(task_ids)

    def delete_rows_for_papers(self, table_name: str, paper_ids: list[str]):
        self.deleted_paper_rows.append((table_name, list(paper_ids)))
        return len(paper_ids)


def test_list_pending_curation_jobs_only_includes_resumable_in_progress_statuses(monkeypatch):
    cursor = _FakeCursor()

    monkeypatch.setattr(
        "backend.app.repositories.community_paper_repository.db_connection",
        lambda *args, **kwargs: _FakeConnection(cursor),
        raising=False,
    )

    repository = CommunityPaperRepository()
    repository.list_pending_curation_jobs()

    assert cursor.params == ("queued", "processing", "translating", "publishing")


def test_serialize_curation_batch_status_treats_retry_as_failed():
    assert paper_service._serialize_curation_batch_status([{"status": "retry"}]) == "failed"


def test_wait_for_task_terminal_state_uses_30_minute_timeout_budget(monkeypatch):
    sleep_calls: list[int] = []

    async def _fake_sleep(_seconds: int):
        sleep_calls.append(1)

    monkeypatch.setattr(paper_service.task_manager, "get_task", lambda _task_id: None)
    monkeypatch.setattr(paper_service.asyncio, "sleep", _fake_sleep)

    try:
        asyncio.run(paper_service._wait_for_task_terminal_state("task-timeout"))
    except TimeoutError as exc:
        assert "task-timeout" in str(exc)
    else:
        raise AssertionError("expected timeout after bounded wait budget")

    assert len(sleep_calls) == 1800


def test_cleanup_failed_admin_curation_artifacts_removes_placeholder_paper_and_task_artifacts(monkeypatch, tmp_path):
    repository = _FakeRepository({"job_id": "job-1"})
    task_id = "task-new"
    paper_id = "paper-new"
    uploads_dir = tmp_path / "uploads"
    failed_tasks_dir = tmp_path / "failed_tasks"
    source_dir = uploads_dir / task_id
    failed_dir = failed_tasks_dir / task_id
    source_dir.mkdir(parents=True)
    failed_dir.mkdir(parents=True)

    deleted_task_ids: list[str] = []

    async def _run_local(operation):
        return operation()

    async def _fetch_paper(_paper_id: str):
        return {"id": paper_id, "status": "curating", "visibility": "private"}

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", _fetch_paper)
    monkeypatch.setattr(paper_service.settings, "uploads_dir", uploads_dir)
    monkeypatch.setattr(paper_service.settings, "failed_tasks_dir", failed_tasks_dir)
    monkeypatch.setattr(
        paper_service.task_manager,
        "delete_task_full",
        lambda candidate_task_id: deleted_task_ids.append(candidate_task_id) or {"success": True, "deleted_dirs": [], "errors": []},
    )

    result = asyncio.run(
        paper_service._cleanup_failed_admin_curation_artifacts(
            repository=repository,
            job={
                "paper_id": paper_id,
                "task_id": task_id,
                "source_type": "upload",
                "source_path": str(source_dir),
            },
            translated_task_id=task_id,
            cancel_running_task=False,
        )
    )

    assert result["errors"] == []
    assert deleted_task_ids == [task_id]
    assert repository.deleted_translation_tasks == []
    assert ("papers", [paper_id]) in repository.deleted_paper_rows
    assert ("paper_assets", [paper_id]) in repository.deleted_paper_rows
    assert source_dir.exists()
    assert failed_dir.exists()
    assert result["failed_artifact_path"] == str(failed_dir).replace("\\", "/")
    assert result["artifact_storage_backend"] == "local_disk"


def test_cleanup_failed_admin_curation_artifacts_keeps_existing_published_paper(monkeypatch, tmp_path):
    repository = _FakeRepository({"job_id": "job-1"})
    task_id = "task-existing"
    failed_tasks_dir = tmp_path / "failed_tasks"
    failed_dir = failed_tasks_dir / task_id
    failed_dir.mkdir(parents=True)

    async def _run_local(operation):
        return operation()

    async def _fetch_paper(_paper_id: str):
        return {"id": "paper-live", "status": "published", "visibility": "public"}

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(paper_service, "_fetch_paper_by_id", _fetch_paper)
    monkeypatch.setattr(paper_service.settings, "failed_tasks_dir", failed_tasks_dir)
    monkeypatch.setattr(
        paper_service.task_manager,
        "delete_task_full",
        lambda _task_id: {"success": True, "deleted_dirs": [], "errors": []},
    )

    asyncio.run(
        paper_service._cleanup_failed_admin_curation_artifacts(
            repository=repository,
            job={"paper_id": "paper-live", "task_id": task_id, "source_type": "arxiv", "source_path": None},
            translated_task_id=task_id,
            cancel_running_task=False,
        )
    )

    assert repository.deleted_translation_tasks == []
    assert repository.deleted_paper_rows == []
    assert failed_dir.exists()


def test_mark_admin_curation_job_failed_persists_retained_failure_metadata(monkeypatch):
    repository = _FakeRepository({"job_id": "job-1", "status": "publishing"})

    async def _run_local(operation):
        return operation()

    async def _cleanup_failed(**_kwargs):
        return {
            "deleted_paths": [],
            "errors": [],
            "failed_artifact_path": "failed_tasks/task-1",
            "artifact_storage_backend": "object_storage",
            "terminal_task_status": "failed_compilation",
        }

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(paper_service, "_cleanup_failed_admin_curation_artifacts", _cleanup_failed)

    asyncio.run(
        paper_service._mark_admin_curation_job_failed(
            repository=repository,
            job_id="job-1",
            job={"task_id": "task-1"},
            translated_task_id="task-1",
            failure_message="compile failed",
            cancel_running_task=False,
        )
    )

    assert repository.job["status"] == "failed"
    assert repository.job["error"] == "compile failed"
    assert repository.job["failed_artifact_path"] == "failed_tasks/task-1"
    assert repository.job["artifact_storage_backend"] == "object_storage"
    assert repository.job["terminal_task_status"] == "failed_compilation"


def test_run_curation_job_reuses_existing_arxiv_translation_task(monkeypatch):
    repository = _FakeRepository(
        {
            "job_id": "job-1",
            "paper_id": "paper-1",
            "source_type": "arxiv",
            "arxiv_id": "2406.15882",
            "task_id": "task-existing",
            "source_language": "en",
            "target_language": "zh",
            "created_by": "admin-1",
            "status": "publishing",
        }
    )
    publish_calls: list[str] = []

    async def _run_local(operation):
        return operation()

    async def _resolve_context(_user_id: str):
        return {"user_id": "admin-1", "is_admin": True, "roles": ["admin"]}

    async def _fetch_metadata(_arxiv_id: str):
        return {"title": "Paper", "authors": [], "categories": [], "abstract_raw": "abstract"}

    async def _wait_for_terminal(_task_id: str):
        return {"status": "completed"}

    async def _publish_job(*, translated_task_id: str, **_kwargs):
        publish_calls.append(translated_task_id)
        return {"id": "paper-1"}

    async def _unexpected_start(**_kwargs):
        raise AssertionError("existing task should be reused instead of starting a new arXiv translation")

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: repository)
    monkeypatch.setattr(paper_service, "resolve_submitter_context_by_user_id", _resolve_context)
    monkeypatch.setattr(paper_service, "_fetch_arxiv_metadata", _fetch_metadata)
    monkeypatch.setattr(paper_service, "_wait_for_task_terminal_state", _wait_for_terminal)
    monkeypatch.setattr(paper_service, "_publish_admin_curation_job", _publish_job)
    monkeypatch.setattr(paper_service, "_start_arxiv_paper_translation", _unexpected_start)

    asyncio.run(paper_service._run_curation_job("job-1"))

    assert publish_calls == ["task-existing"]
    assert repository.job["status"] == "completed"
    assert repository.job["paper_id"] == "paper-1"


def test_start_arxiv_paper_translation_routes_admin_curation_into_backfill_lane(monkeypatch):
    created: dict[str, object] = {}

    class _TaskManager:
        def create_task(self, **kwargs):
            created["create_task"] = kwargs
            return "task-admin-backfill"

        def update_task(self, task_id, **kwargs):
            created["update_task"] = (task_id, kwargs)
            return True

        def persist_task_if_needed(self, task_id):
            created["persist_task"] = task_id
            return True

    def _fake_create_task(coro):
        coro.close()
        return None

    def _fake_download_and_enqueue(**kwargs):
        created["download_and_enqueue"] = kwargs

        async def _noop():
            return None

        return _noop()

    async def _fake_build_llm_config_async(*_args, **_kwargs):
        return {"api_key": "system-key", "pool_routing_key": "system-pool:test"}

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(paper_service.asyncio, "create_task", _fake_create_task)
    monkeypatch.setattr(paper_service.translate_route, "_download_and_enqueue", _fake_download_and_enqueue)
    monkeypatch.setattr(
        paper_service.translate_route,
        "build_llm_config_async",
        _fake_build_llm_config_async,
    )

    result = asyncio.run(
        paper_service._start_arxiv_paper_translation(
            paper={"source": "arxiv", "arxiv_id": "2312.00752"},
            request=paper_service.translate_route.TranslateRequest(
                source_language="en",
                target_language="zh",
            ),
            context={"user_id": "admin-1", "is_admin": True, "roles": ["admin"]},
        )
    )

    assert result == {"task_id": "task-admin-backfill", "status": "queued"}
    assert created["persist_task"] == "task-admin-backfill"
    assert created["download_and_enqueue"]["lane"] == "backfill"


def test_run_curation_job_marks_timeout_as_failed_without_automatic_retry(monkeypatch):
    repository = _FakeRepository(
        {
            "job_id": "job-1",
            "paper_id": "paper-1",
            "source_type": "arxiv",
            "arxiv_id": "2406.15882",
            "task_id": None,
            "source_language": "en",
            "target_language": "zh",
            "created_by": "admin-1",
            "status": "queued",
        }
    )
    async def _run_local(operation):
        return operation()

    async def _resolve_context(_user_id: str):
        return {"user_id": "admin-1", "is_admin": True, "roles": ["admin"]}

    async def _fetch_metadata(_arxiv_id: str):
        return {"title": "Paper", "authors": [], "categories": [], "abstract_raw": "abstract"}

    async def _start_translation(**_kwargs):
        return {"task_id": "task-new", "status": "queued"}

    async def _timeout_wait(_task_id: str):
        raise TimeoutError("Timed out waiting for task task-new")

    cleanup_calls: list[tuple[str, bool]] = []

    async def _cleanup_failed(*, translated_task_id: str, cancel_running_task: bool, **_kwargs):
        cleanup_calls.append((translated_task_id, cancel_running_task))
        return {"errors": []}

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: repository)
    monkeypatch.setattr(paper_service.task_manager, "get_task", lambda _task_id: None)
    monkeypatch.setattr(paper_service, "resolve_submitter_context_by_user_id", _resolve_context)
    monkeypatch.setattr(paper_service, "_fetch_arxiv_metadata", _fetch_metadata)
    monkeypatch.setattr(paper_service, "_start_arxiv_paper_translation", _start_translation)
    monkeypatch.setattr(paper_service, "_wait_for_task_terminal_state", _timeout_wait)
    monkeypatch.setattr(paper_service, "_cleanup_failed_admin_curation_artifacts", _cleanup_failed)

    asyncio.run(paper_service._run_curation_job("job-1"))

    assert repository.job["task_id"] == "task-new"
    assert repository.job["status"] == "failed"
    assert "Timed out waiting for task task-new" in str(repository.job["error"])
    assert cleanup_calls == [("task-new", True)]


def test_batch_delete_admin_curation_jobs_reports_successes_and_failures(monkeypatch):
    async def _delete_admin_curation_job(*, job_id: str, current_user: dict):
        assert current_user["id"] == "admin-1"
        if job_id == "job-2":
            raise HTTPException(status_code=404, detail="Curation job not found")
        return {
            "job_id": job_id,
            "paper_id": None if job_id == "job-1" else "paper-3",
            "status": "failed" if job_id == "job-1" else "completed",
        }

    monkeypatch.setattr(paper_service, "delete_admin_curation_job", _delete_admin_curation_job)

    result = asyncio.run(
        paper_service.batch_delete_admin_curation_jobs(
            job_ids=["job-1", "job-2", "job-3"],
            current_user={"id": "admin-1", "roles": ["admin"]},
        )
    )

    assert result["deleted_count"] == 2
    assert result["failed_count"] == 1
    assert [item["job_id"] for item in result["deleted"]] == ["job-1", "job-3"]
    assert result["failed"] == [
        {
            "job_id": "job-2",
            "status_code": 404,
            "detail": "Curation job not found",
        }
    ]
