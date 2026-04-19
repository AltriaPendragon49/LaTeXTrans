from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_last_pressure_write_at = 0.0


def get_runtime_role() -> str:
    return str(getattr(get_settings(), "backend_runtime_role", "all") or "all").strip().lower()


def web_runtime_enabled() -> bool:
    return get_runtime_role() in {"all", "web"}


def background_runtime_enabled() -> bool:
    return get_runtime_role() in {"all", "worker"}


def admin_job_execution_enabled() -> bool:
    return background_runtime_enabled()


def _frontend_pressure_signal_path() -> Path:
    settings = get_settings()
    signal_dir = Path(settings.storage_temp_dir) / "runtime_pressure"
    signal_dir.mkdir(parents=True, exist_ok=True)
    return signal_dir / "frontend_pressure.json"


def record_frontend_pressure() -> None:
    global _last_pressure_write_at

    settings = get_settings()
    now = time.time()
    min_interval = max(0.1, float(getattr(settings, "frontend_pressure_write_interval_seconds", 1.0) or 1.0))
    if now - _last_pressure_write_at < min_interval:
        return

    signal_path = _frontend_pressure_signal_path()
    payload = {
        "timestamp": now,
        "runtime_role": get_runtime_role(),
    }
    try:
        signal_path.write_text(json.dumps(payload), encoding="utf-8")
        _last_pressure_write_at = now
    except Exception as exc:
        logger.debug("Failed to persist frontend pressure heartbeat: %s", exc)


def _read_frontend_pressure_timestamp() -> Optional[float]:
    signal_path = _frontend_pressure_signal_path()
    if not signal_path.exists():
        return None

    try:
        payload = json.loads(signal_path.read_text(encoding="utf-8"))
        timestamp = payload.get("timestamp")
        return float(timestamp) if timestamp is not None else None
    except Exception:
        try:
            return signal_path.stat().st_mtime
        except Exception:
            return None


def has_recent_frontend_pressure() -> bool:
    settings = get_settings()
    timestamp = _read_frontend_pressure_timestamp()
    if timestamp is None:
        return False
    grace = max(0.0, float(getattr(settings, "frontend_pressure_grace_seconds", 15.0) or 15.0))
    return (time.time() - timestamp) <= grace


def backfill_start_blocked_by_frontend_pressure() -> bool:
    return background_runtime_enabled() and get_runtime_role() == "worker" and has_recent_frontend_pressure()


def apply_worker_process_priority() -> None:
    if get_runtime_role() != "worker":
        return

    increment = int(getattr(get_settings(), "worker_process_nice_increment", 10) or 0)
    if increment <= 0 or not hasattr(os, "nice"):
        return

    try:
        os.nice(increment)
    except Exception as exc:
        logger.debug("Failed to adjust worker niceness: %s", exc)
