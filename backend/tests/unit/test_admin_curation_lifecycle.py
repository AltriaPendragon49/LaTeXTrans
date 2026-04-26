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
        self.deleted_job_ids: list[str] = []

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

    def delete_curation_job(self, job_id: str):
        self.deleted_job_ids.append(job_id)
        return 1


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


def test_wait_for_task_terminal_state_reports_admission_timeout_before_processing(monkeypatch):
    sleep_calls: list[int] = []

    class _Repo:
        def get_task(self, _task_id: str):
            return {"task_id": "task-admission", "status": "queued", "progress": 0}

    async def _fake_sleep(_seconds: int):
        sleep_calls.append(1)

    async def _fake_run_db_blocking(operation):
        return operation()

    monkeypatch.setattr(paper_service, "ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS", 3)
    monkeypatch.setattr(paper_service, "ADMIN_CURATION_ADMISSION_TIMEOUT_SECONDS", 3, raising=False)
    monkeypatch.setattr(paper_service, "ADMIN_CURATION_EXECUTION_TIMEOUT_SECONDS", 2, raising=False)
    monkeypatch.setattr(paper_service.task_manager, "get_task", lambda _task_id: None)
    monkeypatch.setattr(paper_service, "_get_translation_task_repository", lambda: _Repo())
    monkeypatch.setattr(paper_service, "run_db_blocking", _fake_run_db_blocking)
    monkeypatch.setattr(paper_service.asyncio, "sleep", _fake_sleep)

    try:
        asyncio.run(paper_service._wait_for_task_terminal_state("task-admission"))
    except Exception as exc:
        assert getattr(exc, "timeout_reason", None) == "admission_timeout"
    else:
        raise AssertionError("expected admission-stage timeout")

    assert len(sleep_calls) == 3


def test_wait_for_task_terminal_state_reports_execution_timeout_after_processing(monkeypatch):
    sleep_calls: list[int] = []
    states = iter(
        [
            {"task_id": "task-execution", "status": "queued", "progress": 0},
            {"task_id": "task-execution", "status": "processing", "progress": 15},
            {"task_id": "task-execution", "status": "processing", "progress": 25},
        ]
    )

    class _Repo:
        def get_task(self, _task_id: str):
            try:
                return next(states)
            except StopIteration:
                return {"task_id": "task-execution", "status": "processing", "progress": 25}

    async def _fake_sleep(_seconds: int):
        sleep_calls.append(1)

    async def _fake_run_db_blocking(operation):
        return operation()

    monkeypatch.setattr(paper_service, "ADMIN_CURATION_TASK_WAIT_TIMEOUT_SECONDS", 4)
    monkeypatch.setattr(paper_service, "ADMIN_CURATION_ADMISSION_TIMEOUT_SECONDS", 4, raising=False)
    monkeypatch.setattr(paper_service, "ADMIN_CURATION_EXECUTION_TIMEOUT_SECONDS", 2, raising=False)
    monkeypatch.setattr(paper_service.task_manager, "get_task", lambda _task_id: None)
    monkeypatch.setattr(paper_service, "_get_translation_task_repository", lambda: _Repo())
    monkeypatch.setattr(paper_service, "run_db_blocking", _fake_run_db_blocking)
    monkeypatch.setattr(paper_service.asyncio, "sleep", _fake_sleep)

    try:
        asyncio.run(paper_service._wait_for_task_terminal_state("task-execution"))
    except Exception as exc:
        assert getattr(exc, "timeout_reason", None) == "execution_timeout"
    else:
        raise AssertionError("expected execution-stage timeout")

    assert len(sleep_calls) >= 2


def test_cleanup_failed_admin_curation_artifacts_preserves_task_artifacts(monkeypatch, tmp_path):
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
    assert deleted_task_ids == []
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
            "terminal_reason": "task_execution_timeout",
            "timeout_reason": "execution_timeout",
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
    assert repository.job["terminal_reason"] == "task_execution_timeout"
    assert repository.job["timeout_reason"] == "execution_timeout"


def test_cleanup_failed_admin_curation_artifacts_requests_terminal_timeout_cancellation(monkeypatch):
    repository = _FakeRepository({"job_id": "job-1"})
    cancel_calls: list[dict] = []

    async def _run_local(operation):
        return operation()

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(
        paper_service.task_manager,
        "cancel_task",
        lambda task_id, **kwargs: cancel_calls.append({"task_id": task_id, **kwargs}) or True,
    )
    monkeypatch.setattr(paper_service.task_manager, "get_task", lambda _task_id: None)
    monkeypatch.setattr(
        paper_service.task_manager,
        "delete_task_full",
        lambda _task_id: {"success": True, "deleted_dirs": [], "errors": []},
    )

    asyncio.run(
        paper_service._cleanup_failed_admin_curation_artifacts(
            repository=repository,
            job={"paper_id": None, "task_id": "task-timeout"},
            translated_task_id="task-timeout",
            cancel_running_task=True,
            terminal_reason="task_execution_timeout",
            timeout_reason="execution_timeout",
        )
    )

    assert cancel_calls == [
        {
            "task_id": "task-timeout",
            "terminal_reason": "task_execution_timeout",
            "timeout_reason": "execution_timeout",
        }
    ]


def test_run_curation_job_disables_terminology_table_for_admin_intake(monkeypatch):
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
    captured: dict[str, Any] = {}

    async def _run_local(operation):
        return operation()

    async def _resolve_context(_user_id: str):
        return {"user_id": "admin-1", "is_admin": True, "roles": ["admin"]}

    async def _fetch_metadata(_arxiv_id: str):
        return {"title": "Paper", "authors": [], "categories": [], "abstract_raw": "abstract"}

    async def _start_arxiv_translation(**kwargs):
        request = kwargs["request"]
        captured["generate_terminology_table"] = request.advanced_config.generate_terminology_table
        captured["community_production_translation"] = request.advanced_config.community_production_translation
        return {"task_id": "task-new"}

    async def _wait_for_terminal(_task_id: str):
        return {"status": "failed", "error": "stop"}

    async def _mark_failed(**_kwargs):
        return None

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: repository)
    monkeypatch.setattr(paper_service, "resolve_submitter_context_by_user_id", _resolve_context)
    monkeypatch.setattr(paper_service, "_fetch_arxiv_metadata", _fetch_metadata)
    monkeypatch.setattr(paper_service, "_start_arxiv_paper_translation", _start_arxiv_translation)
    monkeypatch.setattr(paper_service, "_wait_for_task_terminal_state", _wait_for_terminal)
    monkeypatch.setattr(paper_service, "_mark_admin_curation_job_failed", _mark_failed)

    asyncio.run(paper_service._run_curation_job("job-1"))

    assert captured["generate_terminology_table"] is False
    assert captured["community_production_translation"] is True


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


def test_run_curation_job_keeps_existing_arxiv_task_in_translating_until_publish(monkeypatch):
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
            "status": "queued",
        }
    )
    publish_seen_statuses: list[str] = []

    async def _run_local(operation):
        return operation()

    async def _resolve_context(_user_id: str):
        return {"user_id": "admin-1", "is_admin": True, "roles": ["admin"]}

    async def _fetch_metadata(_arxiv_id: str):
        return {"title": "Paper", "authors": [], "categories": [], "abstract_raw": "abstract"}

    async def _wait_for_terminal(_task_id: str):
        assert repository.job["status"] == "translating"
        return {"status": "completed"}

    async def _publish_job(*, translated_task_id: str, **_kwargs):
        publish_seen_statuses.append(repository.job["status"])
        assert translated_task_id == "task-existing"
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

    assert publish_seen_statuses == ["publishing"]
    assert repository.updates[0]["status"] == "processing"
    assert repository.updates[1]["status"] == "translating"
    assert repository.updates[2]["status"] == "publishing"


def test_run_curation_job_keeps_new_arxiv_task_in_translating_until_publish(monkeypatch):
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
    publish_seen_statuses: list[str] = []

    async def _run_local(operation):
        return operation()

    async def _resolve_context(_user_id: str):
        return {"user_id": "admin-1", "is_admin": True, "roles": ["admin"]}

    async def _fetch_metadata(_arxiv_id: str):
        return {"title": "Paper", "authors": [], "categories": [], "abstract_raw": "abstract"}

    async def _start_arxiv_translation(**_kwargs):
        return {"task_id": "task-new"}

    async def _wait_for_terminal(_task_id: str):
        assert _task_id == "task-new"
        assert repository.job["status"] == "translating"
        return {"status": "completed"}

    async def _publish_job(*, translated_task_id: str, **_kwargs):
        publish_seen_statuses.append(repository.job["status"])
        assert translated_task_id == "task-new"
        return {"id": "paper-1"}

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: repository)
    monkeypatch.setattr(paper_service, "resolve_submitter_context_by_user_id", _resolve_context)
    monkeypatch.setattr(paper_service, "_fetch_arxiv_metadata", _fetch_metadata)
    monkeypatch.setattr(paper_service, "_start_arxiv_paper_translation", _start_arxiv_translation)
    monkeypatch.setattr(paper_service, "_wait_for_task_terminal_state", _wait_for_terminal)
    monkeypatch.setattr(paper_service, "_publish_admin_curation_job", _publish_job)

    asyncio.run(paper_service._run_curation_job("job-1"))

    assert publish_seen_statuses == ["publishing"]
    assert repository.updates[0]["status"] == "processing"
    assert repository.updates[1]["status"] == "translating"
    assert repository.updates[2]["status"] == "translating"
    assert repository.updates[2]["task_id"] == "task-new"
    assert repository.updates[3]["status"] == "publishing"


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
        return {
            "api_key": "system-key",
            "pool_routing_key": "system-pool:test",
            "pool_members": [
                {
                    "member_id": "account-1",
                    "base_url": "https://example.test/v1/chat/completions",
                    "api_key": "key-1",
                    "account_id": "account-1",
                    "quota_scope": "account",
                },
                {
                    "member_id": "account-2",
                    "base_url": "https://example.test/v1/chat/completions",
                    "api_key": "key-2",
                    "account_id": "account-2",
                    "quota_scope": "account",
                },
                {
                    "member_id": "account-3",
                    "base_url": "https://example.test/v1/chat/completions",
                    "api_key": "key-3",
                    "account_id": "account-3",
                    "quota_scope": "account",
                    "reserve": True,
                },
            ],
            "reserve_count": 1,
            "default_member_concurrency": 1,
        }

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
    assert created["download_and_enqueue"]["llm_capacity"] == 2


def test_start_arxiv_paper_translation_preserves_community_production_flag(monkeypatch):
    created: dict[str, object] = {}

    class _TaskManager:
        def create_task(self, **kwargs):
            return "task-admin-backfill"

        def update_task(self, task_id, **kwargs):
            return True

        def persist_task_if_needed(self, task_id):
            return True

    def _fake_create_task(coro):
        coro.close()
        return None

    def _fake_download_and_enqueue(**kwargs):
        created["advanced_config"] = kwargs["advanced_config"]

        async def _noop():
            return None

        return _noop()

    async def _fake_build_llm_config_async(*_args, **_kwargs):
        return {"api_key": "system-key", "pool_routing_key": "system-pool:test"}

    request = paper_service.translate_route.TranslateRequest(
        source_language="en",
        target_language="zh",
    )
    request.advanced_config.community_production_translation = True

    monkeypatch.setattr(paper_service, "task_manager", _TaskManager())
    monkeypatch.setattr(paper_service.asyncio, "create_task", _fake_create_task)
    monkeypatch.setattr(paper_service.translate_route, "_download_and_enqueue", _fake_download_and_enqueue)
    monkeypatch.setattr(
        paper_service.translate_route,
        "build_llm_config_async",
        _fake_build_llm_config_async,
    )

    asyncio.run(
        paper_service._start_arxiv_paper_translation(
            paper={"source": "arxiv", "arxiv_id": "2312.00752"},
            request=request,
            context={"user_id": "admin-1", "is_admin": True, "roles": ["admin"]},
        )
    )

    assert created["advanced_config"].community_production_translation is True


def test_run_curation_job_marks_timeout_as_failed_and_cancels_running_translation(monkeypatch):
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


def test_delete_admin_curation_job_cancels_queued_translation_before_deleting_task(monkeypatch):
    repository = _FakeRepository(
        {
            "job_id": "job-queued",
            "paper_id": "paper-placeholder",
            "published_paper_id": None,
            "task_id": "task-queued",
            "source_type": "arxiv",
            "source_path": None,
            "status": "translating",
        }
    )
    events: list[tuple] = []

    async def _run_local(operation):
        return operation()

    async def _cancel_curation_job_task_if_running(job_id: str):
        events.append(("cancel_curation_job", job_id))
        return True

    async def _delete_placeholder(*, repository, paper_id: str):
        events.append(("delete_placeholder", paper_id))
        return ["papers"]

    async def _request_worker_task_cancel(task_id: str, **kwargs):
        events.append(("worker_cancel", task_id, kwargs))
        return {"sent": True, "cancelled": True}

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: repository)
    monkeypatch.setattr(
        paper_service,
        "_cancel_curation_job_task_if_running",
        _cancel_curation_job_task_if_running,
    )
    monkeypatch.setattr(
        paper_service,
        "_delete_placeholder_curation_paper_if_present",
        _delete_placeholder,
    )
    monkeypatch.setattr(
        paper_service,
        "request_worker_task_cancel",
        _request_worker_task_cancel,
    )
    monkeypatch.setattr(
        paper_service.task_manager,
        "cancel_task",
        lambda task_id, **kwargs: events.append(("cancel_task", task_id, kwargs)) or True,
    )
    monkeypatch.setattr(
        paper_service.task_manager,
        "delete_task_full",
        lambda task_id: events.append(("delete_task_full", task_id))
        or {"success": True, "deleted_dirs": [], "errors": []},
    )

    result = asyncio.run(
        paper_service.delete_admin_curation_job(
            job_id="job-queued",
            current_user={"id": "admin-1", "roles": ["admin"]},
        )
    )

    assert result["job_id"] == "job-queued"
    assert events[:4] == [
        ("cancel_curation_job", "job-queued"),
        ("worker_cancel", "task-queued", {"terminal_reason": "admin_curation_deleted"}),
        ("cancel_task", "task-queued", {"terminal_reason": "admin_curation_deleted"}),
        ("delete_task_full", "task-queued"),
    ]
    assert repository.deleted_translation_tasks == [["task-queued"]]
    assert repository.deleted_job_ids == ["job-queued"]


def test_list_curation_jobs_for_arxiv_id_orders_created_jobs(monkeypatch):
    cursor = _FakeCursor()

    monkeypatch.setattr(
        "backend.app.repositories.community_paper_repository.db_connection",
        lambda *args, **kwargs: _FakeConnection(cursor),
        raising=False,
    )

    repository = CommunityPaperRepository()
    repository.list_curation_jobs_for_arxiv_id("2504.07439")

    assert "from community_curation_jobs where arxiv_id =" in cursor.sql
    assert "order by created_at asc, job_id asc" in cursor.sql
    assert cursor.params == ("2504.07439",)


def test_submit_admin_arxiv_curation_batch_resets_existing_completed_arxiv_history(monkeypatch):
    class _BatchRepository:
        def __init__(self) -> None:
            self.inserted_payloads: list[dict] = []
            self.deleted_job_ids: list[str] = []

        def list_curation_jobs_for_arxiv_id(self, arxiv_id: str):
            assert arxiv_id == "2504.07439"
            return [
                {
                    "job_id": "job-old-completed",
                    "paper_id": "paper-old",
                    "published_paper_id": "paper-old",
                    "task_id": "task-old",
                    "source_type": "arxiv",
                    "arxiv_id": arxiv_id,
                    "status": "completed",
                }
            ]

        def insert_curation_job(self, payload: dict):
            stored = dict(payload)
            self.inserted_payloads.append(stored)
            return stored

        def delete_curation_job(self, job_id: str):
            self.deleted_job_ids.append(job_id)
            return 1

    repository = _BatchRepository()
    hard_deleted_paper_ids: list[str] = []
    scheduled_job_ids: list[str] = []

    async def _run_local(operation):
        return operation()

    async def _fetch_paper_by_arxiv_id(arxiv_id: str):
        assert arxiv_id == "2504.07439"
        return {"id": "paper-old", "arxiv_id": arxiv_id}

    async def _hard_delete_paper_records(*, repository, paper_id: str):
        assert repository is not None
        hard_deleted_paper_ids.append(paper_id)

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: repository)
    monkeypatch.setattr(paper_service, "_fetch_paper_by_arxiv_id", _fetch_paper_by_arxiv_id)
    monkeypatch.setattr(paper_service, "_hard_delete_paper_records", _hard_delete_paper_records)
    monkeypatch.setattr(paper_service, "_schedule_curation_job", lambda job_id: scheduled_job_ids.append(job_id))

    result = asyncio.run(
        paper_service.submit_admin_arxiv_curation_batch(
            arxiv_ids=["2504.07439"],
            current_user={"id": "admin-1", "roles": ["admin"]},
        )
    )

    assert hard_deleted_paper_ids == ["paper-old"]
    assert repository.deleted_job_ids == ["job-old-completed"]
    assert result["items"][0]["paper_id"] != "paper-old"
    assert scheduled_job_ids == [result["items"][0]["job_id"]]


def test_submit_admin_arxiv_curation_batch_resets_existing_failed_arxiv_history(monkeypatch):
    class _BatchRepository:
        def __init__(self) -> None:
            self.inserted_payloads: list[dict] = []
            self.deleted_job_ids: list[str] = []
            self.deleted_translation_tasks: list[list[str]] = []

        def list_curation_jobs_for_arxiv_id(self, arxiv_id: str):
            assert arxiv_id == "2504.07439"
            return [
                {
                    "job_id": "job-old-failed",
                    "paper_id": "paper-failed",
                    "published_paper_id": None,
                    "task_id": "task-failed",
                    "source_type": "arxiv",
                    "arxiv_id": arxiv_id,
                    "status": "failed",
                    "failed_artifact_path": "failed_tasks/task-failed",
                    "artifact_storage_backend": "object_storage",
                }
            ]

        def insert_curation_job(self, payload: dict):
            stored = dict(payload)
            self.inserted_payloads.append(stored)
            return stored

        def delete_translation_tasks(self, task_ids: list[str]):
            self.deleted_translation_tasks.append(list(task_ids))
            return len(task_ids)

        def delete_curation_job(self, job_id: str):
            self.deleted_job_ids.append(job_id)
            return 1

    repository = _BatchRepository()
    deleted_task_ids: list[str] = []
    task_events: list[tuple[str, str]] = []
    deleted_failed_artifacts: list[tuple[str, str | None]] = []
    deleted_placeholder_papers: list[str] = []

    async def _run_local(operation):
        return operation()

    async def _fetch_paper_by_arxiv_id(arxiv_id: str):
        assert arxiv_id == "2504.07439"
        return None

    async def _delete_placeholder(*, repository, paper_id: str):
        deleted_placeholder_papers.append(paper_id)
        return ["papers"]

    monkeypatch.setattr(paper_service, "_run_local_repo", _run_local)
    monkeypatch.setattr(paper_service, "get_community_paper_repository", lambda: repository)
    monkeypatch.setattr(paper_service, "_fetch_paper_by_arxiv_id", _fetch_paper_by_arxiv_id)
    monkeypatch.setattr(
        paper_service,
        "_delete_retained_failed_artifact",
        lambda *, failed_artifact_path, artifact_storage_backend: deleted_failed_artifacts.append(
            (failed_artifact_path, artifact_storage_backend)
        )
        or [failed_artifact_path],
    )
    monkeypatch.setattr(
        paper_service.task_manager,
        "delete_task_full",
        lambda task_id: deleted_task_ids.append(task_id)
        or task_events.append(("delete", task_id))
        or {"success": True, "deleted_dirs": [], "errors": []},
    )
    monkeypatch.setattr(
        paper_service.task_manager,
        "cancel_task",
        lambda task_id, **_kwargs: task_events.append(("cancel", task_id)) or True,
    )
    monkeypatch.setattr(paper_service, "_delete_placeholder_curation_paper_if_present", _delete_placeholder)
    monkeypatch.setattr(paper_service, "_schedule_curation_job", lambda _job_id: None)

    result = asyncio.run(
        paper_service.submit_admin_arxiv_curation_batch(
            arxiv_ids=["2504.07439"],
            current_user={"id": "admin-1", "roles": ["admin"]},
        )
    )

    assert deleted_failed_artifacts == [("failed_tasks/task-failed", "object_storage")]
    assert task_events == [("cancel", "task-failed"), ("delete", "task-failed")]
    assert deleted_task_ids == ["task-failed"]
    assert repository.deleted_translation_tasks == [["task-failed"]]
    assert deleted_placeholder_papers == ["paper-failed"]
    assert repository.deleted_job_ids == ["job-old-failed"]
    assert result["items"][0]["paper_id"] != "paper-failed"
