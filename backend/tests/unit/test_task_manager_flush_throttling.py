"""
TDD Tests: TaskManager Supabase Flush Throttling + Coalescing

Design under test:
  - Semantic transitions (status/stage VALUE CHANGE) -> immediate flush
  - Repeated same status+stage (pure progress tick) -> throttled
  - Value-only updates within FLUSH_INTERVAL -> NO flush
  - Value-only updates after FLUSH_INTERVAL -> flush
  - Terminal states always flush
  - update_task must never block on slow DB
  - SupabaseFlusher coalesces rapid updates: last-write-wins per task_id

Run with:
    pytest backend/tests/unit/test_task_manager_flush_throttling.py -v
"""

import os
import time
import threading
from typing import List, Tuple

import pytest

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services.task_manager import TaskManager, FLUSH_INTERVAL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task_manager(monkeypatch) -> Tuple[TaskManager, List]:
    """Return a TaskManager with a recorder replacing _persist_task_update."""
    flush_calls: List[Tuple[str, dict]] = []

    monkeypatch.setattr(
        "backend.app.services.task_manager.get_supabase_admin_client",
        lambda: None,
    )
    tm = TaskManager()
    tm._persist_task_update = lambda task_id, updates: flush_calls.append(
        (task_id, dict(updates))
    )
    return tm, flush_calls


def _drain(tm: TaskManager) -> None:
    """Wait for all pending flusher work to complete using the flusher's drain()."""
    tm._flusher.drain(timeout=2.0)


def _create_auth_task(tm: TaskManager, user_id: str = "user-1") -> str:
    return tm.create_task(source_type="upload", user_id=user_id)


# ---------------------------------------------------------------------------
# Test 1: progress-only within FLUSH_INTERVAL -> NO flush
# ---------------------------------------------------------------------------

def test_progress_only_within_interval_does_not_flush(monkeypatch):
    """Rapid progress updates within FLUSH_INTERVAL must not trigger DB writes."""
    tm, flush_calls = _make_task_manager(monkeypatch)
    task_id = _create_auth_task(tm)

    for pct in range(5, 50, 5):
        tm.update_task(task_id, progress=pct, message=f"Parsing {pct}%")

    _drain(tm)
    assert len(flush_calls) <= 1, (
        f"Expected <=1 flush for rapid progress updates, got {len(flush_calls)}"
    )


# ---------------------------------------------------------------------------
# Test 2: status VALUE CHANGE -> immediate flush
# ---------------------------------------------------------------------------

def test_status_value_change_triggers_immediate_flush(monkeypatch):
    """Changing status to a different value must trigger an immediate flush."""
    tm, flush_calls = _make_task_manager(monkeypatch)
    task_id = _create_auth_task(tm)

    before = len(flush_calls)
    tm.update_task(task_id, status="processing")
    _drain(tm)
    assert len(flush_calls) > before, "status value change must trigger flush"
    assert "status" in flush_calls[-1][1]


# ---------------------------------------------------------------------------
# Test 3: stage VALUE CHANGE -> immediate flush
# ---------------------------------------------------------------------------

def test_stage_value_change_triggers_immediate_flush(monkeypatch):
    """Changing stage to a different value must trigger an immediate flush."""
    tm, flush_calls = _make_task_manager(monkeypatch)
    task_id = _create_auth_task(tm)

    before = len(flush_calls)
    tm.update_task(task_id, stage="translating")
    _drain(tm)
    assert len(flush_calls) > before, "stage value change must trigger flush"
    assert "stage" in flush_calls[-1][1]


# ---------------------------------------------------------------------------
# Test 4: repeated same status+stage -> throttled (THE CRITICAL CASE)
# ---------------------------------------------------------------------------

def test_repeated_same_status_stage_is_throttled(monkeypatch):
    """
    create_progress_callback sends status=processing + stage=translating on
    every progress tick without changing values.  These must be throttled.
    This is the exact pattern that produced the PATCH storm in production.
    """
    tm, flush_calls = _make_task_manager(monkeypatch)
    task_id = _create_auth_task(tm)

    # First call: real value changes (pending->processing, idle->translating)
    tm.update_task(task_id, status="processing", stage="translating", progress=10)
    _drain(tm)
    initial_flushes = len(flush_calls)
    assert initial_flushes >= 1, "First transition must flush"

    # 10 rapid progress ticks with SAME status+stage (no value change)
    for pct in range(15, 65, 5):
        tm.update_task(
            task_id,
            status="processing",   # same as before
            stage="translating",   # same as before
            progress=pct,
            message=f"Translating {pct}%",
        )

    _drain(tm)
    additional = len(flush_calls) - initial_flushes
    assert additional <= 1, (
        f"Expected <=1 throttled flush for 10 rapid ticks with same status+stage, "
        f"got {additional}. PATCH storm not fixed!"
    )


# ---------------------------------------------------------------------------
# Test 5: progress after FLUSH_INTERVAL -> flush (time-throttle expiry)
# ---------------------------------------------------------------------------

def test_progress_after_flush_interval_triggers_flush(monkeypatch):
    """After FLUSH_INTERVAL has elapsed, a progress update must flush."""
    tm, flush_calls = _make_task_manager(monkeypatch)
    task_id = _create_auth_task(tm)

    with tm._lock:
        tm._tasks[task_id]["_last_flush_time"] = time.monotonic() - (FLUSH_INTERVAL + 1.0)

    before = len(flush_calls)
    tm.update_task(task_id, progress=42, message="tick after interval")
    _drain(tm)
    assert len(flush_calls) > before, "progress after FLUSH_INTERVAL must flush"


# ---------------------------------------------------------------------------
# Test 6: terminal states always flush
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("terminal_status", [
    "completed",
    "failed",
    "failed_compilation",
    "structure_invalid",
    "completed_with_warnings",
])
def test_terminal_status_always_flushes(monkeypatch, terminal_status):
    """Terminal status is always a value change and must always flush."""
    tm, flush_calls = _make_task_manager(monkeypatch)
    task_id = _create_auth_task(tm)

    tm.update_task(task_id, status="processing")
    _drain(tm)
    with tm._lock:
        tm._tasks[task_id]["_last_flush_time"] = time.monotonic()

    before = len(flush_calls)
    tm.update_task(task_id, status=terminal_status, progress=100)
    _drain(tm)
    assert len(flush_calls) > before, f"Terminal '{terminal_status}' must flush"


# ---------------------------------------------------------------------------
# Test 7: update_task must not block on slow DB
# ---------------------------------------------------------------------------

def test_update_task_does_not_block_on_slow_db(monkeypatch):
    """Slow DB writer must not block update_task (non-blocking guarantee)."""
    monkeypatch.setattr(
        "backend.app.services.task_manager.get_supabase_admin_client",
        lambda: None,
    )
    tm = TaskManager()
    tm._persist_task_update = lambda tid, upd: time.sleep(1.0)
    task_id = _create_auth_task(tm)

    start = time.monotonic()
    tm.update_task(task_id, status="processing")
    elapsed = time.monotonic() - start
    assert elapsed < 0.5, f"update_task blocked {elapsed:.3f}s, must be <0.5s"


# ---------------------------------------------------------------------------
# Test 8: guest tasks never flush
# ---------------------------------------------------------------------------

def test_guest_task_never_flushes(monkeypatch):
    """Tasks without user_id must never reach _persist_task_update."""
    tm, flush_calls = _make_task_manager(monkeypatch)
    task_id = tm.create_task(source_type="upload")  # no user_id

    tm.update_task(task_id, status="processing")
    tm.update_task(task_id, progress=50)
    tm.update_task(task_id, status="completed", progress=100)
    _drain(tm)
    assert flush_calls == [], f"Guest task must never flush, got: {flush_calls}"


# ---------------------------------------------------------------------------
# Test 9: coalescing — multiple rapid enqueues for same task -> 1 write
# ---------------------------------------------------------------------------

def test_coalescing_reduces_writes_for_same_task(monkeypatch):
    """
    When many updates are enqueued before the flusher thread wakes,
    they should be coalesced into a single Supabase write (last-write-wins).
    """
    tm, flush_calls = _make_task_manager(monkeypatch)
    task_id = _create_auth_task(tm)

    # Simulate a semantic transition first so flusher is "cold"
    tm.update_task(task_id, status="processing", stage="translating", progress=10)
    _drain(tm)
    initial = len(flush_calls)

    # Blast many updates after FLUSH_INTERVAL (to ensure they'd each qualify)
    with tm._lock:
        tm._tasks[task_id]["_last_flush_time"] = time.monotonic() - (FLUSH_INTERVAL + 10)

    # Pause flusher by making writer very slow, so all enqueues pile up
    barrier = threading.Barrier(2)
    released = threading.Event()
    original_writer = tm._persist_task_update

    def _gating_writer(task_id, updates):
        # First write: wait at barrier so we can enqueue more before it returns
        barrier.wait(timeout=2.0)
        released.wait(timeout=2.0)
        original_writer(task_id, updates)

    tm._persist_task_update = _gating_writer

    # Enqueue first item to start the blocked writer
    tm.update_task(task_id, status="processing", stage="translating", progress=30, message="A")
    barrier.wait(timeout=2.0)  # writer is now blocked inside _gating_writer

    # Enqueue more while writer is blocked — these should coalesce
    for i, pct in enumerate(range(40, 80, 10)):
        with tm._lock:
            tm._tasks[task_id]["_last_flush_time"] = time.monotonic() - (FLUSH_INTERVAL + 10)
        tm.update_task(task_id, status="processing", stage="translating", progress=pct, message=f"step-{i}")

    released.set()  # unblock writer
    tm._persist_task_update = original_writer  # restore for subsequent writes
    _drain(tm)

    total_new = len(flush_calls) - initial
    # With coalescing, the 4 additional enqueues should be 1 write (or at most 2)
    assert total_new <= 3, (
        f"Expected coalescing to reduce 5 enqueues to <=3 writes, got {total_new}"
    )


# ---------------------------------------------------------------------------
# Test 10: drain() is a no-op when nothing is pending
# ---------------------------------------------------------------------------

def test_drain_is_noop_when_idle(monkeypatch):
    """drain() should return immediately if nothing is pending."""
    tm, _ = _make_task_manager(monkeypatch)
    start = time.monotonic()
    tm._flusher.drain(timeout=0.5)
    elapsed = time.monotonic() - start
    assert elapsed < 0.1, f"drain() on idle flusher took {elapsed:.3f}s, expected instant"
