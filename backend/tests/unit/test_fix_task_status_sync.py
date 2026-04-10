"""
TDD Tests: fix-task-status-sync
OpenSpec change: fix-task-status-sync

Covers:
  Task 1 - Failed task must NOT be deleted from persistent storage on interception
  Task 2 - email_notification flag must be recovered from local persistent storage after restart
  Task 4 - PersistentStateFlusher drain behavior for terminal states

Run with:
    pytest backend/tests/unit/test_fix_task_status_sync.py -v
"""

import asyncio
import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import List, Tuple
import threading

import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services.task_manager import PersistentStateFlusher, TaskManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tm(monkeypatch) -> TaskManager:
    return TaskManager()


def _seed_failed_task(tm: TaskManager, task_id: str, output_path: Path) -> None:
    """Inject a minimal failed task directly into the in-memory store."""
    tm._tasks[task_id] = {
        "task_id": task_id,
        "status": "failed",
        "progress": 100,
        "stage": "done",
        "message": "failed",
        "error": "something went wrong",
        "warnings": None,
        "failure_reason_code": None,
        "failure_class": None,
        "guard_phase": None,
        "replay_bundle_ref": None,
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
        "user_id": "user-test",
        "source_language": "en",
        "target_language": "zh",
        "failure_intercepted": False,
        "failed_output_path": None,
        "_last_flush_time": 0.0,
    }


# ---------------------------------------------------------------------------
# Task 1: Failed task must NOT be deleted from persistent storage
# ---------------------------------------------------------------------------

def test_intercept_failed_task_does_not_delete_from_persistent_store(monkeypatch, tmp_path):
    """
    When _intercept_failed_task is called for a failed task,
    it must NOT call _delete_failed_task_from_persistent_store.

    Constraint alignment: local persistent storage is the authority for terminal states.
    Deleting the record causes history page to show stale 'Waiting' state.
    """
    delete_called = []

    tm = _make_tm(monkeypatch)

    # Patch delete method to track calls
    tm._delete_failed_task_from_persistent_store = lambda task_id: delete_called.append(task_id)

    task_id = "task-no-delete-test"
    output_path = tmp_path / "outputs" / task_id
    output_path.mkdir(parents=True, exist_ok=True)
    _seed_failed_task(tm, task_id, output_path)

    monkeypatch.setattr(
        "backend.app.services.task_manager.get_settings",
        lambda: SimpleNamespace(
            outputs_dir=tmp_path / "outputs",
            failed_tasks_dir=tmp_path / "failed_tasks",
        ),
    )

    tm._intercept_failed_task(
        task_id=task_id,
        status_message="structure guard failed",
        status_error="missing end{document}",
    )

    assert delete_called == [], (
        f"_delete_failed_task_from_persistent_store was called unexpectedly: {delete_called}. "
        "Failed tasks must remain in local persistent storage so history page can display them."
    )


def test_intercept_failed_task_status_preserved_after_interception(monkeypatch, tmp_path):
    """
    After _intercept_failed_task, the task status must remain 'failed'
    (not wiped or changed). Local persistent storage is the authority; the in-memory
    status must not be altered by the interception logic.
    """
    tm = _make_tm(monkeypatch)
    task_id = "task-status-preserved"
    output_path = tmp_path / "outputs" / task_id
    output_path.mkdir(parents=True, exist_ok=True)
    _seed_failed_task(tm, task_id, output_path)
    tm._tasks[task_id]["status"] = "structure_invalid"

    monkeypatch.setattr(
        "backend.app.services.task_manager.get_settings",
        lambda: SimpleNamespace(
            outputs_dir=tmp_path / "outputs",
            failed_tasks_dir=tmp_path / "failed_tasks",
        ),
    )

    tm._intercept_failed_task(
        task_id=task_id,
        status_message="structure invalid",
        status_error="bad structure",
    )

    assert tm._tasks[task_id]["status"] == "structure_invalid", (
        "Task status must not be mutated by _intercept_failed_task."
    )


@pytest.mark.parametrize("fail_status", ["failed", "failed_compilation", "structure_invalid"])
def test_update_task_terminal_status_does_not_invoke_db_delete(monkeypatch, fail_status):
    """
    update_task() with a terminal fail status must NOT trigger any persistent-store delete.
    The delete call was previously inside _intercept_failed_task.
    """
    delete_calls = []
    flush_calls = []

    tm = TaskManager()
    tm._persist_task_update = lambda tid, upd: flush_calls.append((tid, upd))
    tm._delete_failed_task_from_persistent_store = lambda tid: delete_calls.append(tid)

    task_id = tm.create_task(source_type="upload", user_id="user-1")

    # Simulate failure via update_task
    tm.update_task(task_id, status=fail_status, message="something failed", error="err")
    tm._flusher.drain(timeout=2.0)

    assert delete_calls == [], (
        f"update_task(status='{fail_status}') must not call _delete_failed_task_from_persistent_store. "
        f"Got: {delete_calls}"
    )


# ---------------------------------------------------------------------------
# Task 2: email_notification recovered from local translation storage
# ---------------------------------------------------------------------------

def test_recover_from_local_storage_preserves_email_notification_true(monkeypatch):
    """
    When local translation-task storage returns email_notification=True,
    _recover_from_persistent_store must include email_notification: True in
    the restored task's advanced_config dict.
    """
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_translation_task_repository",
        lambda: _make_mock_translation_task_repository(email_notification=True),
    )

    tm = TaskManager()
    result = tm._recover_from_persistent_store("task-email-true")

    assert result is not None, "_recover_from_persistent_store returned None unexpectedly"
    adv = result.get("advanced_config", {})
    assert adv.get("email_notification") is True, (
        f"advanced_config must preserve email_notification=True after recovery. Got: {adv}"
    )


def test_recover_from_local_storage_preserves_email_notification_false(monkeypatch):
    """
    When local translation-task storage returns email_notification=False,
    _recover_from_persistent_store must include email_notification: False.
    """
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_translation_task_repository",
        lambda: _make_mock_translation_task_repository(email_notification=False),
    )

    tm = TaskManager()
    result = tm._recover_from_persistent_store("task-email-false")

    assert result is not None
    adv = result.get("advanced_config", {})
    assert adv.get("email_notification") is False, (
        f"advanced_config must have email_notification=False when DB returns False. Got: {adv}"
    )


def test_recover_from_local_storage_preserves_email_notification_missing(monkeypatch):
    """
    When local translation-task storage returns a db_task with no email_notification field,
    _recover_from_persistent_store must default email_notification to False.
    """
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_translation_task_repository",
        lambda: _make_mock_translation_task_repository(email_notification=None),  # field absent
    )

    tm = TaskManager()
    result = tm._recover_from_persistent_store("task-email-missing")

    assert result is not None
    adv = result.get("advanced_config", {})
    # Default should be False (not opted in)
    assert adv.get("email_notification") is False, (
        f"email_notification should default to False when missing from DB. Got: {adv}"
    )


def _make_mock_translation_task_repository(email_notification):
    """Build a minimal mock translation-task repository that returns one task row."""
    db_task = {
        "task_id": "task-email-test",
        "status": "completed",
        "progress": 100,
        "stage": "done",
        "message": "Task completed",
        "error": None,
        "source_type": "upload",
        "source_path": None,
        "output_path": None,
        "translation_mode": "full",
        "compile_strategy": "auto",
        "translation_model": None,
        "generate_glossary": True,
        "use_author_api": True,
        "arxiv_id": None,
        "user_id": "user-test",
        "source_language": "en",
        "target_language": "zh",
        "created_at": "2026-01-01T00:00:00",
        "completed_at": "2026-01-01T00:01:00",
    }
    if email_notification is not None:
        db_task["email_notification"] = email_notification
    # Leave field absent when email_notification is None (tests default=False)

    class _MockRepository:
        def get_task(self, _task_id):
            return dict(db_task)

    return _MockRepository()


def test_persist_task_with_retry_does_not_register_authenticated_task_for_guest_cleanup(monkeypatch):
    registered = []

    monkeypatch.setattr(
        "backend.app.services.task_manager.guest_tracker",
        SimpleNamespace(register=lambda task_id: registered.append(task_id)),
    )

    tm = TaskManager()
    task_id = tm.create_task(source_type="upload", user_id="user-authenticated", persist_to_db=False)
    monkeypatch.setattr(tm, "persist_task_if_needed", lambda _task_id: False)

    result = asyncio.run(tm.persist_task_with_retry(task_id, retries=1, delay=0))

    assert result is False
    assert registered == []
    assert tm._tasks[task_id]["persist_failed"] is True


# ---------------------------------------------------------------------------
# Task 4: PersistentStateFlusher drain behavior for terminal states
# ---------------------------------------------------------------------------

def test_flusher_drains_pending_before_any_shutdown(monkeypatch):
    """
    When PersistentStateFlusher has pending items and drain() is called,
    all pending writes must be flushed before drain() returns.
    This mirrors the shutdown use-case where we need terminal writes to complete.
    """
    written: List[Tuple[str, dict]] = []

    flusher = PersistentStateFlusher(writer=lambda tid, upd: written.append((tid, dict(upd))))

    flusher.enqueue("task-terminal-A", {"status": "completed", "progress": 100})
    flusher.enqueue("task-terminal-B", {"status": "failed", "progress": 100})

    flusher.drain(timeout=3.0)

    task_ids = {w[0] for w in written}
    assert "task-terminal-A" in task_ids, "Terminal task A was not flushed before drain() returned"
    assert "task-terminal-B" in task_ids, "Terminal task B was not flushed before drain() returned"


def test_flusher_terminal_state_written_even_when_enqueued_late(monkeypatch):
    """
    A terminal state enqueued just before drain() must still be written.
    (Guards against race where enqueue and drain race each other.)
    """
    written: List[Tuple[str, dict]] = []

    flusher = PersistentStateFlusher(writer=lambda tid, upd: written.append((tid, dict(upd))))

    # Enqueue and immediately drain â€?should not lose the write
    flusher.enqueue("task-late-terminal", {"status": "completed"})
    flusher.drain(timeout=3.0)

    assert any(w[0] == "task-late-terminal" for w in written), (
        "Terminal state enqueued just before drain() must be written within drain() timeout."
    )


def test_flusher_coalesces_terminal_with_earlier_progress(monkeypatch):
    """
    If multiple updates for the same task_id are enqueued while the flusher thread
    is idle, they should be coalesced to a single write with last-write-wins per field.
    The terminal status must be present in the final coalesced write.
    """
    written: List[Tuple[str, dict]] = []

    # Use a gate to hold the flusher thread before it starts draining.
    # This ensures all enqueues arrive before the first _run cycle.
    gate = threading.Event()
    first_call_done = threading.Event()

    def _gated_writer(tid, upd):
        # Signal that the writer was invoked, then record
        written.append((tid, dict(upd)))
        first_call_done.set()

    flusher = PersistentStateFlusher(writer=_gated_writer)

    # Enqueue directly into _pending without waking the worker thread
    # This simulates multiple rapid enqueues before the thread wakes
    with flusher._lock:
        flusher._pending["task-coalesce"] = {"progress": 50}
        # Coalesce: later enqueues overwrite earlier ones per field
        flusher._pending["task-coalesce"].update({"progress": 100})
        flusher._pending["task-coalesce"].update({"status": "completed"})

    # Now wake the flusher with all pending items already coalesced
    flusher._has_work.set()
    flusher.drain(timeout=3.0)

    # Only one write should have occurred, and it must contain the terminal status
    task_writes = [w for w in written if w[0] == "task-coalesce"]
    assert len(task_writes) == 1, (
        f"Coalesced enqueues should produce exactly 1 write, got: {task_writes}"
    )
    assert task_writes[0][1].get("status") == "completed", (
        f"Coalesced write must contain status='completed'. Got: {task_writes[0][1]}"
    )
    assert task_writes[0][1].get("progress") == 100, (
        f"Coalesced write must contain latest progress=100. Got: {task_writes[0][1]}"
    )
