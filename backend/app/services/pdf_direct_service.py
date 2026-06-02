from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from backend.app.core.config import get_settings
from backend.app.core.encryption import decrypt_api_key
from backend.app.repositories.auth_repository import AuthRepository
from backend.app.repositories.pdf_direct_task_repository import PdfDirectTaskRepository
from backend.app.repositories.translation_quota_repository import TranslationQuotaRepository
from backend.app.services.storage_backend import build_storage_backend

logger = logging.getLogger(__name__)

# Upstream transStatus constants
TRANS_STATUS_NOT_STARTED = 101
TRANS_STATUS_PROCESSING = 103
TRANS_STATUS_CANCELED = 104
TRANS_STATUS_COMPLETED = 105
TRANS_STATUS_FAILED = 106

# Product error codes
PDF_DIRECT_CREDIT_INSUFFICIENT = "PDF_DIRECT_CREDIT_INSUFFICIENT"
PDF_DIRECT_CREDENTIAL_UNAVAILABLE = "PDF_DIRECT_CREDENTIAL_UNAVAILABLE"
PDF_DIRECT_VALIDATION_ERROR = "PDF_DIRECT_VALIDATION_ERROR"
PDF_DIRECT_LIMIT_ERROR = "PDF_DIRECT_LIMIT_ERROR"
PDF_DIRECT_RETRYABLE_ERROR = "PDF_DIRECT_RETRYABLE_ERROR"
PDF_DIRECT_AUTH_ERROR = "PDF_DIRECT_AUTH_ERROR"
PDF_DIRECT_NOT_FOUND = "PDF_DIRECT_NOT_FOUND"
PDF_DIRECT_NOT_READY = "PDF_DIRECT_NOT_READY"
PDF_DIRECT_DISABLED = "PDF_DIRECT_DISABLED"

# Upstream error → product error mapping
CREDIT_INSUFFICIENT_CODES = {20017, 110019, 110020, 20002}
FILE_VALIDATION_CODES = {20004, 210011, 110024, 110025, 110029, 110013, 110014, 110007}
FILE_LIMIT_CODES = {20005, 210013, 210014, 210015}
RETRYABLE_CODES = {20022, 22001, 110000}
AUTH_ERROR_CODES = {21000, 20006}
NOT_FOUND_CODES = {20003, 110021, 110011}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_millis() -> str:
    return str(int(time.time() * 1000))


def _generate_auth_str(params: dict[str, str], apikey: str) -> str:
    """Generate NiuTrans document API auth string per documented rules.

    1. Include apikey + all non-empty parameters sorted by ASCII parameter name
    2. Exclude authStr and file fields
    3. MD5 the joined key=value string
    """
    signing_params: dict[str, str] = {}
    for key, value in params.items():
        if key in ("authStr", "file"):
            continue
        if value:
            signing_params[key] = value
    signing_params["apikey"] = apikey

    sorted_keys = sorted(signing_params.keys())
    param_str = "&".join(f"{k}={signing_params[k]}" for k in sorted_keys)
    return hashlib.md5(param_str.encode("utf-8")).hexdigest()


class PdfDirectServiceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, extra: Optional[dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.extra = extra or {}


class PdfDirectService:
    def __init__(
        self,
        *,
        task_repo: Optional[PdfDirectTaskRepository] = None,
        auth_repo: Optional[AuthRepository] = None,
        quota_repo: Optional[TranslationQuotaRepository] = None,
    ) -> None:
        self._settings = get_settings()
        self._task_repo = task_repo or PdfDirectTaskRepository()
        self._auth_repo = auth_repo or AuthRepository()
        self._quota_repo = quota_repo or TranslationQuotaRepository()

    @property
    def _enabled(self) -> bool:
        return bool(
            self._settings.pdf_direct_translation_enabled
            and self._settings.niutrans_doc_api_app_id
            and self._settings.niutrans_doc_api_base_url
        )

    def _check_enabled(self) -> None:
        if not self._enabled:
            raise PdfDirectServiceError(
                PDF_DIRECT_DISABLED,
                "PDF direct translation is not available.",
                status_code=503,
            )

    def _get_user_apikey(self, user_id: str) -> str:
        encrypted = self._auth_repo.get_encrypted_apikey(user_id)
        if not encrypted:
            raise PdfDirectServiceError(
                PDF_DIRECT_CREDENTIAL_UNAVAILABLE,
                "Your NiuTrans API credentials are not available. Please re-login.",
                status_code=401,
            )
        apikey = decrypt_api_key(encrypted)
        if not apikey:
            raise PdfDirectServiceError(
                PDF_DIRECT_CREDENTIAL_UNAVAILABLE,
                "Your NiuTrans API credentials are not available. Please re-login.",
                status_code=401,
            )
        return apikey

    def _map_upstream_error(self, upstream_code: int, upstream_msg: str) -> PdfDirectServiceError:
        if upstream_code in CREDIT_INSUFFICIENT_CODES:
            return PdfDirectServiceError(
                PDF_DIRECT_CREDIT_INSUFFICIENT,
                "Insufficient PDF direct translation credits.",
                status_code=402,
                extra={
                    "upstream_code": upstream_code,
                    "upstream_message": upstream_msg,
                    "account_url": "https://niutrans.com/",
                },
            )
        if upstream_code in FILE_VALIDATION_CODES:
            return PdfDirectServiceError(
                PDF_DIRECT_VALIDATION_ERROR,
                f"File validation failed: {upstream_msg}",
                status_code=400,
                extra={"upstream_code": upstream_code, "upstream_message": upstream_msg},
            )
        if upstream_code in FILE_LIMIT_CODES:
            return PdfDirectServiceError(
                PDF_DIRECT_LIMIT_ERROR,
                f"File exceeds limits: {upstream_msg}",
                status_code=400,
                extra={"upstream_code": upstream_code, "upstream_message": upstream_msg},
            )
        if upstream_code in RETRYABLE_CODES:
            return PdfDirectServiceError(
                PDF_DIRECT_RETRYABLE_ERROR,
                "Service is busy, please retry shortly.",
                status_code=503,
                extra={"upstream_code": upstream_code, "upstream_message": upstream_msg},
            )
        if upstream_code in AUTH_ERROR_CODES:
            return PdfDirectServiceError(
                PDF_DIRECT_AUTH_ERROR,
                "Authentication failed with upstream translation service.",
                status_code=401,
                extra={"upstream_code": upstream_code, "upstream_message": upstream_msg},
            )
        if upstream_code in NOT_FOUND_CODES:
            return PdfDirectServiceError(
                PDF_DIRECT_NOT_FOUND,
                "File not found or expired.",
                status_code=404,
                extra={"upstream_code": upstream_code, "upstream_message": upstream_msg},
            )
        return PdfDirectServiceError(
            "PDF_DIRECT_UPSTREAM_ERROR",
            f"Upstream error ({upstream_code}): {upstream_msg}",
            status_code=502,
            extra={"upstream_code": upstream_code, "upstream_message": upstream_msg},
        )

    def _build_signed_params(self, apikey: str, **extra_params) -> dict[str, str]:
        params: dict[str, str] = {
            "appId": self._settings.niutrans_doc_api_app_id or "",
            "timestamp": _now_millis(),
        }
        for key, value in extra_params.items():
            if value:
                params[key] = str(value)
        params["authStr"] = _generate_auth_str(params, apikey)
        return params

    async def upload_and_get_page_num(
        self,
        *,
        user_id: str,
        file_content: bytes,
        file_name: str,
    ) -> dict[str, Any]:
        self._check_enabled()
        apikey = self._get_user_apikey(user_id)

        params = self._build_signed_params(apikey)
        url = f"{self._settings.niutrans_doc_api_base_url}/paperUploadAndGetPageNum"

        timeout = httpx.Timeout(60.0, connect=15.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    data=params,
                    files={"file": (file_name, file_content, "application/pdf")},
                )
        except httpx.HTTPError as exc:
            raise PdfDirectServiceError(
                PDF_DIRECT_RETRYABLE_ERROR,
                "Upstream translation service is unavailable.",
                status_code=503,
            ) from exc

        payload = response.json() if response.text else {}
        upstream_code = payload.get("code")

        if isinstance(upstream_code, int) and upstream_code not in (0, 200):
            raise self._map_upstream_error(upstream_code, str(payload.get("msg", "")))

        if response.status_code >= 500:
            raise PdfDirectServiceError(
                PDF_DIRECT_RETRYABLE_ERROR,
                "Upstream translation service error.",
                status_code=503,
            )

        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        upstream_file_no = str(data.get("fileNo") or "")
        page_num = data.get("pageNum")

        if not upstream_file_no:
            raise PdfDirectServiceError(
                "PDF_DIRECT_UPSTREAM_ERROR",
                "Upstream did not return a file number.",
                status_code=502,
            )

        task = self._task_repo.create_task(
            user_id=user_id,
            upstream_file_no=upstream_file_no,
            file_name=file_name,
            file_size_kb=len(file_content) // 1024 if file_content else None,
            page_num=page_num,
        )
        self._refresh_balance_snapshot(user_id)
        return self._task_to_response(task)

    async def start_translation(self, *, user_id: str, task_id: str) -> dict[str, Any]:
        self._check_enabled()
        apikey = self._get_user_apikey(user_id)

        task = self._task_repo.get_task_by_id_and_user(task_id, user_id)
        if task is None:
            raise PdfDirectServiceError(PDF_DIRECT_NOT_FOUND, "Task not found.", status_code=404)

        params = self._build_signed_params(
            apikey,
            fileNo=task["upstream_file_no"],
            **{"from": "en", "to": "zh"},
        )
        url = f"{self._settings.niutrans_doc_api_base_url}/transPaperFile"

        timeout = httpx.Timeout(30.0, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    data=params,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.HTTPError as exc:
            raise PdfDirectServiceError(
                PDF_DIRECT_RETRYABLE_ERROR,
                "Upstream translation service is unavailable.",
                status_code=503,
            ) from exc

        payload = response.json() if response.text else {}
        upstream_code = payload.get("code")

        if isinstance(upstream_code, int) and upstream_code not in (0, 200):
            raise self._map_upstream_error(upstream_code, str(payload.get("msg", "")))

        self._task_repo.update_task_status(task_id=task_id, trans_status=TRANS_STATUS_PROCESSING, progress=0.0)
        self._refresh_balance_snapshot(user_id)
        return self._task_to_response(self._task_repo.get_task_by_id(task_id))

    async def get_task_status(self, *, user_id: str, task_id: str) -> dict[str, Any]:
        task = self._task_repo.get_task_by_id_and_user(task_id, user_id)
        if task is None:
            raise PdfDirectServiceError(PDF_DIRECT_NOT_FOUND, "Task not found.", status_code=404)
        return self._task_to_response(task)

    async def poll_upstream_status(self, *, user_id: str, task_id: str) -> dict[str, Any]:
        self._check_enabled()
        apikey = self._get_user_apikey(user_id)

        task = self._task_repo.get_task_by_id_and_user(task_id, user_id)
        if task is None:
            raise PdfDirectServiceError(PDF_DIRECT_NOT_FOUND, "Task not found.", status_code=404)

        # Check for task timeout
        if task["trans_status"] == TRANS_STATUS_PROCESSING:
            timeout = self._settings.pipeline_timeout_seconds
            if timeout > 0 and task.get("updated_at"):
                updated_at = task["updated_at"]
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at)
                if isinstance(updated_at, datetime) and updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                if isinstance(updated_at, datetime):
                    elapsed = (_now_utc() - updated_at).total_seconds()
                    if elapsed > timeout:
                        self._task_repo.fail_stale_task(task_id, "translation timed out")
                        self._refresh_balance_snapshot(user_id)
                        updated = self._task_repo.get_task_by_id(task_id)
                        return self._task_to_response(updated)

        params = self._build_signed_params(apikey, fileNo=task["upstream_file_no"])
        url = f"{self._settings.niutrans_doc_api_base_url}/getInfo"
        query_string = urlencode(params)

        timeout = httpx.Timeout(15.0, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{url}?{query_string}")
        except httpx.HTTPError as exc:
            raise PdfDirectServiceError(
                PDF_DIRECT_RETRYABLE_ERROR,
                "Upstream translation service is unavailable.",
                status_code=503,
            ) from exc

        payload = response.json() if response.text else {}
        upstream_code = payload.get("code")
        if isinstance(upstream_code, int) and upstream_code not in (0, 200):
            raise self._map_upstream_error(upstream_code, str(payload.get("msg", "")))

        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        trans_status = data.get("transStatus", task["trans_status"])
        progress = data.get("progress")
        trans_failure_cause = data.get("transFailureCause")
        trans_failure_code = data.get("transFailureCode")

        self._task_repo.update_task_status(
            task_id=task_id,
            trans_status=trans_status,
            progress=progress,
            trans_failure_cause=trans_failure_cause,
            trans_failure_code=trans_failure_code,
        )

        updated_task = self._task_repo.get_task_by_id(task_id)

        if trans_status == TRANS_STATUS_COMPLETED and not updated_task.get("cos_artifact_key"):
            await self._cache_translated_pdf_to_cos(user_id, apikey, updated_task)

        if trans_status in (TRANS_STATUS_COMPLETED, TRANS_STATUS_CANCELED, TRANS_STATUS_FAILED):
            self._refresh_balance_snapshot(user_id)

        return self._task_to_response(updated_task)

    async def cancel_task(self, *, user_id: str, task_id: str) -> dict[str, Any]:
        self._check_enabled()
        apikey = self._get_user_apikey(user_id)

        task = self._task_repo.get_task_by_id_and_user(task_id, user_id)
        if task is None:
            raise PdfDirectServiceError(PDF_DIRECT_NOT_FOUND, "Task not found.", status_code=404)

        if task["trans_status"] not in (TRANS_STATUS_NOT_STARTED, TRANS_STATUS_PROCESSING):
            raise PdfDirectServiceError(
                "PDF_DIRECT_CANCEL_NOT_ALLOWED",
                "Task cannot be canceled in its current state.",
                status_code=400,
            )

        params = self._build_signed_params(apikey, fileNo=task["upstream_file_no"])
        url = f"{self._settings.niutrans_doc_api_base_url}/interrupt"

        timeout = httpx.Timeout(15.0, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    data=params,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.HTTPError as exc:
            raise PdfDirectServiceError(
                PDF_DIRECT_RETRYABLE_ERROR,
                "Upstream translation service is unavailable.",
                status_code=503,
            ) from exc

        payload = response.json() if response.text else {}
        upstream_code = payload.get("code")
        if isinstance(upstream_code, int) and upstream_code not in (0, 200):
            raise self._map_upstream_error(upstream_code, str(payload.get("msg", "")))

        self._task_repo.update_task_status(task_id=task_id, trans_status=TRANS_STATUS_CANCELED)
        self._refresh_balance_snapshot(user_id)
        return self._task_to_response(self._task_repo.get_task_by_id(task_id))

    async def download_translated_pdf(self, *, user_id: str, task_id: str) -> tuple[bytes, str]:
        self._check_enabled()
        apikey = self._get_user_apikey(user_id)

        task = self._task_repo.get_task_by_id_and_user(task_id, user_id)
        if task is None:
            raise PdfDirectServiceError(PDF_DIRECT_NOT_FOUND, "Task not found.", status_code=404)

        if task["trans_status"] != TRANS_STATUS_COMPLETED:
            raise PdfDirectServiceError(
                PDF_DIRECT_NOT_READY,
                "Translated PDF is not ready for download.",
                status_code=400,
            )

        params = self._build_signed_params(apikey, fileNo=task["upstream_file_no"], type="1")
        url = f"{self._settings.niutrans_doc_api_base_url}/download"
        query_string = urlencode(params)

        timeout = httpx.Timeout(120.0, connect=15.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{url}?{query_string}")
        except httpx.HTTPError as exc:
            raise PdfDirectServiceError(
                PDF_DIRECT_RETRYABLE_ERROR,
                "Upstream translation service is unavailable.",
                status_code=503,
            ) from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
                upstream_code = payload.get("code")
                raise self._map_upstream_error(upstream_code or response.status_code, str(payload.get("msg", "")))
            except (ValueError, PdfDirectServiceError):
                if isinstance(response.json() if response.text else {}, dict):
                    payload = response.json()
                    upstream_code = payload.get("code")
                    if upstream_code:
                        raise self._map_upstream_error(upstream_code, str(payload.get("msg", "")))
                raise PdfDirectServiceError(
                    "PDF_DIRECT_DOWNLOAD_FAILED",
                    "Failed to download translated PDF.",
                    status_code=502,
                )

        content_type = response.headers.get("content-type", "application/pdf")
        return response.content, content_type

    async def _cache_translated_pdf_to_cos(self, user_id: str, apikey: str, task: dict[str, Any]) -> None:
        try:
            pdf_content, _ = await self._download_from_upstream(apikey, task["upstream_file_no"])
        except Exception:
            logger.exception("Failed to download translated PDF for COS caching (task=%s)", task["id"])
            return

        try:
            from pathlib import Path as _Path
            from backend.app.core.config import get_settings as _get_settings

            _settings = _get_settings()
            storage = build_storage_backend(_settings)
            tmp_dir = _settings.storage_temp_dir
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = tmp_dir / f"pdf_direct_{task['id']}.pdf"
            tmp_path.write_bytes(pdf_content)

            cos_key = f"{_settings.cos_base_prefix}/pdf-direct/{user_id}/{task['upstream_file_no']}/translated.pdf"
            storage.put_file(
                local_path=tmp_path,
                object_key=cos_key,
                content_type="application/pdf",
                delete_local=True,
            )
            self._task_repo.set_cos_artifact_key(task["id"], cos_key)
            logger.info("Cached translated PDF to COS: %s", cos_key)
        except Exception:
            logger.exception("Failed to upload translated PDF to COS (task=%s)", task["id"])

    async def _download_from_upstream(self, apikey: str, file_no: str) -> tuple[bytes, str]:
        params = self._build_signed_params(apikey, fileNo=file_no, type="1")
        url = f"{self._settings.niutrans_doc_api_base_url}/download"
        query_string = urlencode(params)
        timeout = httpx.Timeout(120.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{url}?{query_string}")
            if response.status_code >= 400:
                raise PdfDirectServiceError(
                    "PDF_DIRECT_DOWNLOAD_FAILED",
                    "Failed to download translated PDF from upstream.",
                    status_code=502,
                )
            content_type = response.headers.get("content-type", "application/pdf")
            return response.content, content_type

    def _refresh_balance_snapshot(self, user_id: str) -> None:
        """Placeholder: balance is refreshed at login and after terminal operations.

        Full re-fetch from upstream getUserInfo requires the upstream login token,
        which is not persisted. Balance snapshots are primarily maintained at login time.
        """
        pass

    @staticmethod
    def _task_to_response(task: Optional[dict[str, Any]]) -> dict[str, Any]:
        if task is None:
            return {}
        return {
            "task_id": task["id"],
            "user_id": task["user_id"],
            "upstream_file_no": task.get("upstream_file_no"),
            "file_name": task.get("file_name"),
            "file_size_kb": task.get("file_size_kb"),
            "page_num": task.get("page_num"),
            "progress": task.get("progress"),
            "trans_status": task.get("trans_status"),
            "trans_failure_cause": task.get("trans_failure_cause"),
            "trans_failure_code": task.get("trans_failure_code"),
            "status": task.get("status"),
            "has_artifact": bool(task.get("cos_artifact_key")),
            "created_at": _serialize_datetime(task.get("created_at")),
            "updated_at": _serialize_datetime(task.get("updated_at")),
            "completed_at": _serialize_datetime(task.get("completed_at")),
        }


def _serialize_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return raw
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
