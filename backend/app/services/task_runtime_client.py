from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict

import httpx
from fastapi import HTTPException, Request, status

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

INTERNAL_TASK_CANCEL_ACTION = "task.cancel"


def _runtime_secret() -> str:
    settings = get_settings()
    raw_keys = str(getattr(settings, "auth_jwt_keys", "") or "").strip()
    for item in raw_keys.split(","):
        _version, sep, secret = item.partition(":")
        if sep and secret.strip():
            return secret.strip()
    return raw_keys or "change-me-local-dev-secret"


def _signature_payload(
    *,
    action: str,
    task_id: str,
    timestamp: str,
    terminal_reason: str,
) -> str:
    return "\n".join([action, task_id, timestamp, terminal_reason])


def _sign_internal_request(
    *,
    action: str,
    task_id: str,
    timestamp: str,
    terminal_reason: str,
) -> str:
    payload = _signature_payload(
        action=action,
        task_id=task_id,
        timestamp=timestamp,
        terminal_reason=terminal_reason,
    )
    return hmac.new(_runtime_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_internal_task_runtime_request(
    *,
    request: Request,
    task_id: str,
    action: str,
    terminal_reason: str,
) -> None:
    timestamp = str(request.headers.get("x-latextrans-runtime-timestamp") or "").strip()
    signature = str(request.headers.get("x-latextrans-runtime-signature") or "").strip()
    if not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing internal runtime signature")

    try:
        timestamp_value = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal runtime timestamp") from exc

    max_age = max(int(getattr(get_settings(), "internal_runtime_request_max_age_seconds", 60) or 60), 1)
    if abs(int(time.time()) - timestamp_value) > max_age:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired internal runtime signature")

    expected = _sign_internal_request(
        action=action,
        task_id=task_id,
        timestamp=timestamp,
        terminal_reason=terminal_reason,
    )
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal runtime signature")


def should_signal_worker_runtime() -> bool:
    role = str(getattr(get_settings(), "backend_runtime_role", "all") or "all").strip().lower()
    return role == "web"


def worker_cancel_signal_failed(result: Dict[str, Any]) -> bool:
    return should_signal_worker_runtime() and (
        not bool(result.get("sent"))
        or bool(result.get("error"))
    )


async def request_worker_task_cancel(
    task_id: str,
    *,
    terminal_reason: str = "task_deleted",
    timeout_seconds: float = 5.0,
) -> Dict[str, Any]:
    normalized_task_id = str(task_id or "").strip()
    if not normalized_task_id:
        return {"sent": False, "reason": "empty_task_id"}
    if not should_signal_worker_runtime():
        return {"sent": False, "reason": "runtime_role_not_web"}

    settings = get_settings()
    base_url = str(getattr(settings, "worker_runtime_api_base_url", "") or "").strip().rstrip("/")
    if not base_url:
        return {"sent": False, "reason": "worker_runtime_api_base_url_empty"}

    timestamp = str(int(time.time()))
    signature = _sign_internal_request(
        action=INTERNAL_TASK_CANCEL_ACTION,
        task_id=normalized_task_id,
        timestamp=timestamp,
        terminal_reason=terminal_reason,
    )
    url = f"{base_url}/internal/task/{normalized_task_id}/cancel"
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                url,
                params={"terminal_reason": terminal_reason},
                headers={
                    "x-latextrans-runtime-timestamp": timestamp,
                    "x-latextrans-runtime-signature": signature,
                },
            )
        if response.status_code == 404:
            return {"sent": True, "status_code": 404, "cancelled": False}
        response.raise_for_status()
        payload = response.json()
        return {"sent": True, "status_code": response.status_code, **payload}
    except Exception as exc:
        logger.warning("Failed to signal worker runtime cancellation for task %s: %s", normalized_task_id, exc)
        return {"sent": False, "error": str(exc)}
