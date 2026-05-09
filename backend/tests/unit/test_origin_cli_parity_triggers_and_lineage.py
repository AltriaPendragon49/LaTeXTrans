import asyncio
import json
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.api.routes import translate as translate_route
from backend.app.models.config_models import (
    AdvancedConfig,
    ORIGIN_CLI_PARITY_MODE,
)


class _CapturingQueue:
    def __init__(self):
        self.enqueued = []

    def get_user_active_count(self, _user_id):
        return 0

    async def enqueue(self, task_id, factory, user_id, token_hash, **kwargs):
        self.enqueued.append(
            {
                "task_id": task_id,
                "factory": factory,
                "user_id": user_id,
                "token_hash": token_hash,
                "kwargs": kwargs,
            }
        )


class _RouteTaskManager:
    def __init__(self, task):
        self.task = dict(task)
        self.updates = []
        self.created = []

    def is_cancelled(self, _task_id):
        return False

    def get_task(self, _task_id):
        return dict(self.task)

    def update_task(self, task_id, **kwargs):
        self.updates.append((task_id, dict(kwargs)))
        self.task.update(kwargs)
        return True

    def begin_task_attempt(self, _task_id):
        return 1

    def create_progress_callback(self, _task_id, **_kwargs):
        return None

    def persist_task_if_needed(self, _task_id):
        return True

    def create_task(self, **kwargs):
        task_id = f"created-{len(self.created) + 1}"
        self.created.append((task_id, dict(kwargs)))
        self.task = {
            "task_id": task_id,
            "source_type": kwargs.get("source_type"),
            "arxiv_id": kwargs.get("arxiv_id"),
            "source_path": kwargs.get("source_path"),
            "source_available": bool(kwargs.get("source_path")),
            "status": "pending",
        }
        return task_id


class _CoordinatorProbe:
    configs = []

    def __init__(self, *, config, project_dir, output_dir, on_progress=None):
        self.config = dict(config)
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.on_progress = on_progress
        self.__class__.configs.append(dict(config))

    async def workflow_latextrans_async(self):
        pdf_path = os.path.join(self.output_dir, "translated.pdf")
        with open(pdf_path, "wb") as handle:
            handle.write(b"%PDF")
        return {"status": "completed", "pdf_path": pdf_path}


def _assert_origin_cli_parity_config(config):
    assert config["translation_core_mode"] == ORIGIN_CLI_PARITY_MODE
    assert config["origin_cli_parity_single_kernel_lineage"] is True
    assert config["enable_legacy_translation_core"] is True
    assert config["generate_terminology"] is False
    assert config["generate_terminology_table"] is False


@pytest.mark.parametrize(
    ("source_type", "arxiv_id"),
    [
        ("upload", None),
        ("arxiv", "2501.00001"),
    ],
)
def test_shared_translate_route_factory_reaches_coordinator_with_parity_config(
    monkeypatch, tmp_path, source_type, arxiv_id
):
    source_dir = tmp_path / f"{source_type}-source"
    source_dir.mkdir()
    (source_dir / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}Hi\\end{document}",
        encoding="utf-8",
    )
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()

    manager = _RouteTaskManager(
        {
            "task_id": f"{source_type}-task",
            "source_type": source_type,
            "arxiv_id": arxiv_id,
            "source_path": str(source_dir),
            "source_available": True,
            "status": "pending",
        }
    )
    queue = _CapturingQueue()
    _CoordinatorProbe.configs = []

    async def _fake_build_llm_config_async(_advanced_config, _user_id):
        return {"api_key": f"{source_type}-secret", "model": "fake-model"}

    monkeypatch.setattr(translate_route, "task_manager", manager)
    monkeypatch.setattr(translate_route, "get_task_queue", lambda: queue)
    monkeypatch.setattr(translate_route.settings, "outputs_dir", outputs_dir)
    monkeypatch.setattr(translate_route, "find_reusable_output", lambda *_args, **_kwargs: asyncio.sleep(0, result=None))
    monkeypatch.setattr(translate_route, "build_llm_config_async", _fake_build_llm_config_async)
    monkeypatch.setattr(translate_route, "get_arxiv_category", lambda _ids: {"2501.00001": ["cs.CL"]})
    monkeypatch.setattr(translate_route, "capture_task_config", lambda **_kwargs: None)
    monkeypatch.setattr(translate_route, "CoordinatorAgent", _CoordinatorProbe)

    request = translate_route.TranslateRequest(
        source_language="en",
        target_language="zh",
        advanced_config=AdvancedConfig(
            translation_core_mode="modern",
            translation_mode="quick_scan",
            compile_strategy="xelatex",
            generate_terminology_table=True,
        ),
    )

    response = asyncio.run(
        translate_route.start_translation(
            task_id=f"{source_type}-task",
            request=request,
            credentials=None,
            current_user=None,
        )
    )
    assert response.status == "queued"
    assert len(queue.enqueued) == 1

    asyncio.run(queue.enqueued[0]["factory"]())

    assert len(_CoordinatorProbe.configs) == 1
    _assert_origin_cli_parity_config(_CoordinatorProbe.configs[0])
    metadata_update = next(payload for _task_id, payload in manager.updates if "advanced_config" in payload)
    assert metadata_update["advanced_config"]["translation_mode"] == "full"
    assert metadata_update["advanced_config"]["compile_strategy"] == "auto"
    expected_hash = translate_route.compute_config_hash(
        arxiv_id=arxiv_id,
        source_language="en",
        target_language="zh",
        translation_mode="full",
        compile_strategy="auto",
        source_path=str(source_dir),
        formatting=None,
    )
    assert metadata_update["config_hash"] == expected_hash


def test_batch_download_and_enqueue_factory_reaches_coordinator_with_parity_config(
    monkeypatch, tmp_path
):
    downloaded_source = tmp_path / "downloaded-arxiv"
    downloaded_source.mkdir()
    (downloaded_source / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}Batch\\end{document}",
        encoding="utf-8",
    )
    outputs_dir = tmp_path / "outputs"
    uploads_dir = tmp_path / "uploads"
    outputs_dir.mkdir()
    uploads_dir.mkdir()

    manager = _RouteTaskManager(
        {
            "task_id": "batch-task",
            "source_type": "arxiv",
            "arxiv_id": "2501.00002",
            "source_path": None,
            "source_available": False,
            "status": "pending",
        }
    )
    queue = _CapturingQueue()
    _CoordinatorProbe.configs = []

    async def _fake_build_llm_config_async(_advanced_config, _user_id):
        return {"api_key": "batch-secret", "model": "fake-model"}

    monkeypatch.setattr(translate_route, "task_manager", manager)
    monkeypatch.setattr(translate_route.settings, "outputs_dir", outputs_dir)
    monkeypatch.setattr(translate_route.settings, "uploads_dir", uploads_dir)
    monkeypatch.setattr(translate_route, "batch_download_arxiv_tex", lambda *_args: [str(downloaded_source)])
    monkeypatch.setattr(translate_route, "find_reusable_output", lambda *_args, **_kwargs: asyncio.sleep(0, result=None))
    monkeypatch.setattr(translate_route, "build_llm_config_async", _fake_build_llm_config_async)
    monkeypatch.setattr(translate_route, "get_arxiv_category", lambda _ids: {"2501.00002": ["cs.CL"]})
    monkeypatch.setattr(translate_route, "capture_task_config", lambda **_kwargs: None)
    monkeypatch.setattr(translate_route, "CoordinatorAgent", _CoordinatorProbe)
    monkeypatch.setattr(
        translate_route.task_artifact_storage,
        "persist_task_directory",
        lambda local_dir, **_kwargs: str(local_dir),
    )

    asyncio.run(
        translate_route._download_and_enqueue(
            task_id="batch-task",
            arxiv_id="2501.00002",
            user_id="user-1",
            source_language="en",
            target_language="zh",
            advanced_config=AdvancedConfig(translation_core_mode="modern"),
            tq=queue,
            token_hash="token-hash",
            llm_capacity=3,
        )
    )
    assert len(queue.enqueued) == 1

    asyncio.run(queue.enqueued[0]["factory"]())

    assert len(_CoordinatorProbe.configs) == 1
    _assert_origin_cli_parity_config(_CoordinatorProbe.configs[0])


def test_community_existing_task_bridge_calls_shared_translate_route(monkeypatch):
    from backend.app.services import paper_service

    captured = {}

    async def _fake_start_translation(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(task_id=kwargs["task_id"], status="queued")

    request = translate_route.TranslateRequest(
        source_language="en",
        target_language="zh",
        advanced_config=AdvancedConfig(translation_core_mode="modern"),
    )

    monkeypatch.setattr(paper_service.translate_route, "start_translation", _fake_start_translation)

    result = asyncio.run(
        paper_service._enqueue_existing_task_translation(
            task_id="community-upload-task",
            request=request,
            credentials=None,
            current_user={"id": "user-1"},
        )
    )

    assert result == {"task_id": "community-upload-task", "status": "queued"}
    assert captured["task_id"] == "community-upload-task"
    assert captured["request"] is request


def test_community_arxiv_bridge_uses_batch_download_enqueue_entrypoint(monkeypatch):
    from backend.app.services import paper_service

    manager = _RouteTaskManager(
        {
            "task_id": "unused",
            "source_type": "arxiv",
            "arxiv_id": "2501.00003",
            "source_available": False,
            "status": "pending",
        }
    )
    captured = {}
    scheduled = []

    async def _fake_build_llm_config_async(_advanced_config, _user_id):
        return {"api_key": "community-secret"}

    def _fake_download_and_enqueue(**kwargs):
        captured.update(kwargs)
        return asyncio.sleep(0)

    def _fake_create_task(coro):
        scheduled.append(coro)
        coro.close()
        return None

    monkeypatch.setattr(paper_service, "task_manager", manager)
    monkeypatch.setattr(paper_service.translate_route, "build_llm_config_async", _fake_build_llm_config_async)
    monkeypatch.setattr(paper_service.translate_route, "_download_and_enqueue", _fake_download_and_enqueue)
    monkeypatch.setattr(paper_service.asyncio, "create_task", _fake_create_task)
    monkeypatch.setattr(paper_service, "get_task_queue", lambda: None)

    request = translate_route.TranslateRequest(
        source_language="en",
        target_language="zh",
        advanced_config=AdvancedConfig(translation_core_mode="modern"),
    )
    result = asyncio.run(
        paper_service._start_arxiv_paper_translation(
            paper={"source": "arxiv", "arxiv_id": "2501.00003"},
            request=request,
            context={"user_id": "user-1"},
        )
    )

    assert result == {"task_id": "created-1", "status": "queued"}
    assert captured["task_id"] == "created-1"
    assert captured["advanced_config"] is not request.advanced_config
    assert captured["advanced_config"].translation_core_mode == ORIGIN_CLI_PARITY_MODE
    assert captured["advanced_config"].translation_mode == "full"
    assert captured["advanced_config"].compile_strategy == "auto"
    assert captured["advanced_config"].generate_terminology_table is False
    assert captured["lane"] == "backfill"


def test_community_source_archive_bridge_preserves_submitter_user_context(
    monkeypatch, tmp_path
):
    from backend.app.services import paper_service

    source_dir = tmp_path / "community-source"
    source_dir.mkdir()
    (source_dir / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}Community source\\end{document}",
        encoding="utf-8",
    )
    manager = _RouteTaskManager(
        {
            "task_id": "seed-task",
            "source_type": "upload",
            "source_path": str(source_dir),
            "source_available": True,
            "status": "pending",
        }
    )
    captured = {}

    async def _fake_ensure_public_paper(_paper_id):
        return {
            "id": "paper-source-archive",
            "source": "upload",
            "arxiv_id": None,
            "trans_status": "source_ready",
            "community_status": "official",
        }

    async def _fake_fetch_asset_map_for_paper(**_kwargs):
        return {
            "source_archive": {
                "file_path": str(source_dir),
            }
        }

    async def _fake_resolve_submitter_context_by_user_id(user_id):
        return {"user_id": user_id, "roles": ["member"], "is_admin": False}

    async def _fake_enqueue_existing_task_translation(**kwargs):
        captured.update(kwargs)
        return {"task_id": kwargs["task_id"], "status": "queued"}

    async def _fake_update_paper(_paper_id, payload):
        return payload

    def _fake_create_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(paper_service, "_ensure_public_paper", _fake_ensure_public_paper)
    monkeypatch.setattr(paper_service, "_fetch_asset_map_for_paper", _fake_fetch_asset_map_for_paper)
    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context_by_user_id",
        _fake_resolve_submitter_context_by_user_id,
    )
    monkeypatch.setattr(
        paper_service,
        "_enqueue_existing_task_translation",
        _fake_enqueue_existing_task_translation,
    )
    monkeypatch.setattr(paper_service, "_update_paper", _fake_update_paper)
    monkeypatch.setattr(paper_service, "_resolve_storage_path", lambda path: source_dir)
    monkeypatch.setattr(paper_service, "task_manager", manager)
    monkeypatch.setattr(paper_service.asyncio, "create_task", _fake_create_task)

    request = translate_route.TranslateRequest(
        source_language="en",
        target_language="zh",
        advanced_config=AdvancedConfig(translation_core_mode="modern"),
    )
    result = asyncio.run(
        paper_service.start_paper_translation(
            paper_id="paper-source-archive",
            request=request,
            credentials=None,
            submitter_user_id="submitter-1",
        )
    )

    assert result["status"] == "queued"
    assert captured["request"].advanced_config.translation_core_mode == ORIGIN_CLI_PARITY_MODE
    assert captured["current_user"]["id"] == "submitter-1"


def test_content_pool_and_community_agent_start_translation_delegate_with_parity_request(
    monkeypatch,
):
    from backend.app.services import community_content_pool_service
    from backend.app.services.community_agent.skills.start_translation_kernel import (
        StartTranslationKernelSkill,
    )

    captured_requests = []

    async def _fake_start_paper_translation(**kwargs):
        captured_requests.append(kwargs["request"])
        return {"paper_id": kwargs["paper_id"], "task_id": "task-shared", "status": "queued"}

    async def _fake_detail(**_kwargs):
        return {"reader": {"state": "source_ready"}, "paper": {}}

    monkeypatch.setattr(community_content_pool_service.paper_service, "start_paper_translation", _fake_start_paper_translation)
    monkeypatch.setattr(community_content_pool_service.paper_service, "get_community_paper_detail", _fake_detail)

    content_pool_result = asyncio.run(
        community_content_pool_service._default_start_translation("paper-1")
    )

    runtime_state = SimpleNamespace(context={"user_id": "user-1"})
    skill = StartTranslationKernelSkill()
    skill_result = asyncio.run(
        skill.execute({"paper_id": "paper-2", "source_language": "en", "target_language": "zh"}, runtime_state)
    )

    assert content_pool_result["status"] == "queued"
    assert skill_result["status"] == "queued"
    assert len(captured_requests) == 2
    assert all(request.advanced_config.translation_core_mode == ORIGIN_CLI_PARITY_MODE for request in captured_requests)


@pytest.mark.parametrize("entrypoint", ["content_pool", "community_agent"])
def test_content_pool_and_community_agent_entrypoints_reach_coordinator_with_parity_config(
    monkeypatch,
    tmp_path,
    entrypoint,
):
    from backend.app.services import community_content_pool_service, paper_service
    from backend.app.services.community_agent.skills.start_translation_kernel import (
        StartTranslationKernelSkill,
    )

    downloaded_source = tmp_path / f"{entrypoint}-downloaded-source"
    downloaded_source.mkdir()
    (downloaded_source / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}Community\\end{document}",
        encoding="utf-8",
    )
    outputs_dir = tmp_path / f"{entrypoint}-outputs"
    uploads_dir = tmp_path / f"{entrypoint}-uploads"
    outputs_dir.mkdir()
    uploads_dir.mkdir()

    manager = _RouteTaskManager(
        {
            "task_id": "seed-task",
            "source_type": "arxiv",
            "arxiv_id": "2501.00004",
            "source_path": None,
            "source_available": False,
            "status": "pending",
        }
    )
    queue = _CapturingQueue()
    scheduled = []
    _CoordinatorProbe.configs = []

    async def _fake_ensure_public_paper(_paper_id):
        return {
            "id": "paper-shared",
            "source": "arxiv",
            "arxiv_id": "2501.00004",
            "trans_status": "source_ready",
            "community_status": "official",
        }

    async def _fake_fetch_asset_map_for_paper(**_kwargs):
        return {}

    async def _fake_update_paper(_paper_id, payload):
        return payload

    async def _fake_watch_task_and_sync_asset(**_kwargs):
        return None

    async def _fake_get_community_paper_detail(**_kwargs):
        return {"reader": {"state": "source_ready"}, "paper": {}}

    async def _fake_resolve_submitter_context_by_user_id(user_id):
        return {"user_id": user_id, "roles": [], "is_admin": False}

    async def _fake_build_llm_config_async(_advanced_config, _user_id):
        return {"api_key": f"{entrypoint}-secret", "model": "fake-model"}

    def _capture_create_task(coro):
        scheduled.append(coro)
        return None

    async def _drain_scheduled():
        for coro in list(scheduled):
            await coro

    monkeypatch.setattr(paper_service, "_ensure_public_paper", _fake_ensure_public_paper)
    monkeypatch.setattr(paper_service, "_fetch_asset_map_for_paper", _fake_fetch_asset_map_for_paper)
    monkeypatch.setattr(paper_service, "_update_paper", _fake_update_paper)
    monkeypatch.setattr(paper_service, "_watch_task_and_sync_asset", _fake_watch_task_and_sync_asset)
    monkeypatch.setattr(paper_service, "get_community_paper_detail", _fake_get_community_paper_detail)
    monkeypatch.setattr(
        paper_service,
        "resolve_submitter_context_by_user_id",
        _fake_resolve_submitter_context_by_user_id,
    )
    monkeypatch.setattr(paper_service, "task_manager", manager)
    monkeypatch.setattr(paper_service, "get_task_queue", lambda: queue)
    monkeypatch.setattr(paper_service.asyncio, "create_task", _capture_create_task)
    monkeypatch.setattr(translate_route, "task_manager", manager)
    monkeypatch.setattr(translate_route.settings, "outputs_dir", outputs_dir)
    monkeypatch.setattr(translate_route.settings, "uploads_dir", uploads_dir)
    monkeypatch.setattr(translate_route, "batch_download_arxiv_tex", lambda *_args: [str(downloaded_source)])
    monkeypatch.setattr(translate_route, "find_reusable_output", lambda *_args, **_kwargs: asyncio.sleep(0, result=None))
    monkeypatch.setattr(translate_route, "build_llm_config_async", _fake_build_llm_config_async)
    monkeypatch.setattr(translate_route, "get_arxiv_category", lambda _ids: {"2501.00004": ["cs.CL"]})
    monkeypatch.setattr(translate_route, "capture_task_config", lambda **_kwargs: None)
    monkeypatch.setattr(translate_route, "CoordinatorAgent", _CoordinatorProbe)
    monkeypatch.setattr(
        translate_route.task_artifact_storage,
        "persist_task_directory",
        lambda local_dir, **_kwargs: str(local_dir),
    )

    if entrypoint == "content_pool":
        result = asyncio.run(community_content_pool_service._default_start_translation("paper-shared"))
    else:
        runtime_state = SimpleNamespace(context={"user_id": "user-agent"})
        result = asyncio.run(
            StartTranslationKernelSkill().execute(
                {"paper_id": "paper-shared", "source_language": "en", "target_language": "zh"},
                runtime_state,
            )
        )

    assert result["status"] == "queued"
    asyncio.run(_drain_scheduled())
    assert len(queue.enqueued) == 1

    asyncio.run(queue.enqueued[0]["factory"]())

    assert len(_CoordinatorProbe.configs) == 1
    _assert_origin_cli_parity_config(_CoordinatorProbe.configs[0])


def test_origin_cli_parity_production_path_has_single_kernel_lineage(monkeypatch, tmp_path):
    import backend.app.services.agents.langgraph_orchestrator as orch_mod

    project_dir = tmp_path / "paper"
    project_dir.mkdir()
    (project_dir / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}lineage\\end{document}",
        encoding="utf-8",
    )
    output_root = tmp_path / "out"
    output_root.mkdir()

    class Parser:
        def __init__(self, *args, **kwargs):
            pass

        async def execute(self):
            return None

    class Translator:
        noop_sections = []
        payload_invariant_sections = []
        c1_retry_enforced_once = False

        def __init__(self, *args, **kwargs):
            self.trans_mode = kwargs.get("trans_mode", 0)

        async def execute(self, *args, **kwargs):
            return None

    class Validator:
        code_like_filtered_bare_tokens = 0

        def __init__(self, *args, **kwargs):
            pass

        def execute(self, *args, **kwargs):
            return []

    class Generator:
        def __init__(self, *args, **kwargs):
            pass

        async def execute_async(self):
            pdf_path = tmp_path / "paper.pdf"
            pdf_path.write_bytes(b"%PDF")
            return {"status": "completed", "pdf_path": str(pdf_path), "engine": "pdflatex"}

    monkeypatch.setattr(orch_mod, "ParserAgent", Parser)
    monkeypatch.setattr(orch_mod, "TranslatorAgent", Translator)
    monkeypatch.setattr(orch_mod, "ValidatorAgent", Validator)
    monkeypatch.setattr(orch_mod, "GeneratorAgent", Generator)

    result = asyncio.run(
        orch_mod.run_pipeline(
            config={"translation_core_mode": "modern", "target_language": "zh", "task_id": "lineage-task"},
            project_dir=str(project_dir),
            output_dir=str(output_root),
        )
    )

    assert result["status"] == "completed"
    transed_project_dir = output_root / "zh_paper"
    task_log = json.loads((transed_project_dir / "task_log.json").read_text(encoding="utf-8"))
    task_started = next(entry for entry in task_log if entry["event"] == "task_started")
    _assert_origin_cli_parity_config(task_started["config"])

    audit_entries = [
        json.loads(line)
        for line in (transed_project_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected_entries = [
        entry for entry in audit_entries if entry["event"] == "origin_cli_parity_kernel_selected"
    ]
    assert len(selected_entries) == 1
    assert selected_entries[0]["payload"]["single_kernel_lineage"] is True

    serialized_audit = json.dumps(audit_entries, sort_keys=True)
    assert "modern_kernel_selected" not in serialized_audit
    assert "shadow_kernel" not in serialized_audit
    assert "dual_result" not in serialized_audit
    assert "dual_output" not in serialized_audit
