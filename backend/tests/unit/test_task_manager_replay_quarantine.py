import json
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services.task_manager import TaskManager


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed_task_manager_task(tm: TaskManager, task_id: str, output_path: Path, replay_bundle_ref: str, *, status: str = "failed"):
    tm._tasks[task_id] = {
        "task_id": task_id,
        "status": status,
        "progress": 100,
        "stage": "done",
        "message": "failed",
        "error": "err",
        "warnings": None,
        "failure_reason_code": None,
        "failure_class": None,
        "guard_phase": None,
        "replay_bundle_ref": replay_bundle_ref,
        "evidence_chain_broken": False,
        "source_available": True,
        "created_at": "2026-01-01T00:00:00",
        "completed_at": "2026-01-01T00:01:00",
        "source_type": "upload",
        "source_path": None,
        "output_path": str(output_path),
        "advanced_config": None,
        "latex_validation": None,
        "arxiv_id": None,
        "user_id": None,
        "source_language": "en",
        "target_language": "zh",
        "failure_intercepted": False,
        "failed_output_path": None,
    }


def test_quarantine_rewrites_replay_refs_in_scoped_domain(monkeypatch, tmp_path):
    outputs_dir = tmp_path / "outputs"
    failed_dir = tmp_path / "failed_tasks"
    task_id = "task_rewrite_ok"
    old_root = outputs_dir / task_id
    bundle_dir = old_root / "zh_paper"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    main_tex = bundle_dir / "main.tex"
    main_tex.write_text(r"\documentclass{article}", encoding="utf-8")
    replay_path = bundle_dir / "replay_bundle.json"
    _write_json(
        replay_path,
        {
            "main_tex_path": str(main_tex),
            "figure_path": str(bundle_dir / "figures" / "a.pdf"),
        },
    )
    task_log = bundle_dir / "task_log.json"
    _write_json(
        task_log,
        [
            {
                "timestamp": "2026-01-01T00:00:00",
                "event": "structure_invalid_aborted",
                "replay_bundle_ref": str(replay_path),
            }
        ],
    )

    tm = TaskManager()
    _seed_task_manager_task(tm, task_id, old_root, str(replay_path))

    monkeypatch.setattr(
        "backend.app.services.task_manager.get_settings",
        lambda: SimpleNamespace(outputs_dir=outputs_dir, failed_tasks_dir=failed_dir),
    )
    monkeypatch.setattr("backend.app.services.task_manager.get_supabase_admin_client", lambda: None)

    tm._intercept_failed_task(task_id, status_message="failed", status_error="failed")

    task = tm._tasks[task_id]
    assert task["output_path"].startswith(str(failed_dir))
    assert task["replay_bundle_ref"].startswith(str(failed_dir))
    assert Path(task["replay_bundle_ref"]).exists()

    rewritten_bundle = json.loads(Path(task["replay_bundle_ref"]).read_text(encoding="utf-8"))
    assert rewritten_bundle["main_tex_path"].startswith(str(failed_dir))
    assert Path(rewritten_bundle["main_tex_path"]).exists()


def test_quarantine_rewrite_idempotent(monkeypatch, tmp_path):
    outputs_dir = tmp_path / "outputs"
    failed_dir = tmp_path / "failed_tasks"
    task_id = "task_idempotent"
    old_root = outputs_dir / task_id
    new_root = failed_dir / task_id
    bundle_dir = new_root / "zh_paper"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    main_tex = bundle_dir / "main.tex"
    main_tex.write_text("main", encoding="utf-8")
    replay_path = bundle_dir / "replay_bundle.json"
    _write_json(replay_path, {"main_tex_path": str(main_tex)})
    task_log = bundle_dir / "task_log.json"
    _write_json(task_log, [{"event": "x", "replay_bundle_ref": str(replay_path)}])

    tm = TaskManager()
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_settings",
        lambda: SimpleNamespace(outputs_dir=outputs_dir, failed_tasks_dir=failed_dir),
    )

    payload = {"replay_bundle_ref": str(replay_path)}
    tm._rewrite_replay_evidence_after_quarantine(
        task_id=task_id,
        task_snapshot=payload,
        old_task_root=old_root,
        new_task_root=new_root,
    )
    first_task_log_bytes = task_log.read_bytes()
    first_bundle_bytes = replay_path.read_bytes()

    tm._rewrite_replay_evidence_after_quarantine(
        task_id=task_id,
        task_snapshot=payload,
        old_task_root=old_root,
        new_task_root=new_root,
    )
    assert task_log.read_bytes() == first_task_log_bytes
    assert replay_path.read_bytes() == first_bundle_bytes


def test_quarantine_non_target_paths_unchanged(monkeypatch, tmp_path):
    outputs_dir = tmp_path / "outputs"
    failed_dir = tmp_path / "failed_tasks"
    task_id = "task_non_target"
    old_root = outputs_dir / task_id
    bundle_dir = old_root / "zh_paper"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    main_tex = bundle_dir / "main.tex"
    main_tex.write_text("main", encoding="utf-8")
    replay_path = bundle_dir / "replay_bundle.json"
    untouched_windows = r"C:\third_party\external\bundle.json"
    untouched_other = str((tmp_path / "external" / "foo.txt").resolve())
    _write_json(
        replay_path,
        {
            "main_tex_path": str(main_tex),
            "external_ref": untouched_windows,
            "external_path": untouched_other,
        },
    )
    _write_json(
        bundle_dir / "task_log.json",
        [{"event": "x", "replay_bundle_ref": str(replay_path)}],
    )

    tm = TaskManager()
    _seed_task_manager_task(tm, task_id, old_root, str(replay_path))
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_settings",
        lambda: SimpleNamespace(outputs_dir=outputs_dir, failed_tasks_dir=failed_dir),
    )
    monkeypatch.setattr("backend.app.services.task_manager.get_supabase_admin_client", lambda: None)

    tm._intercept_failed_task(task_id, status_message="failed", status_error="failed")
    rewritten = json.loads(Path(tm._tasks[task_id]["replay_bundle_ref"]).read_text(encoding="utf-8"))
    assert rewritten["external_ref"] == untouched_windows
    assert rewritten["external_path"] == untouched_other


def test_evidence_chain_broken_flag_warning_without_status_mutation(monkeypatch, tmp_path):
    outputs_dir = tmp_path / "outputs"
    failed_dir = tmp_path / "failed_tasks"
    task_id = "task_broken"
    old_root = outputs_dir / task_id
    bundle_dir = old_root / "zh_paper"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    replay_path = bundle_dir / "replay_bundle.json"
    missing_main = bundle_dir / "missing_main.tex"
    _write_json(replay_path, {"main_tex_path": str(missing_main)})
    _write_json(
        bundle_dir / "task_log.json",
        [{"event": "x", "replay_bundle_ref": str(replay_path)}],
    )

    tm = TaskManager()
    _seed_task_manager_task(tm, task_id, old_root, str(replay_path), status="failed_compilation")

    monkeypatch.setattr(
        "backend.app.services.task_manager.get_settings",
        lambda: SimpleNamespace(outputs_dir=outputs_dir, failed_tasks_dir=failed_dir),
    )
    monkeypatch.setattr("backend.app.services.task_manager.get_supabase_admin_client", lambda: None)

    tm._intercept_failed_task(task_id, status_message="failed_compilation", status_error="compile failed")

    task = tm._tasks[task_id]
    assert task["status"] == "failed_compilation"
    assert task["evidence_chain_broken"] is True

    task_log_path = Path(task["output_path"]) / "zh_paper" / "task_log.json"
    events = json.loads(task_log_path.read_text(encoding="utf-8"))
    assert any(e.get("event") == "evidence_chain_warning" for e in events)
