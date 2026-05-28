from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from backend.app.db import db_connection, get_database_dialect


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _placeholder(_index: int) -> str:
    return "?" if get_database_dialect() == "sqlite" else "%s"


def _placeholders(count: int) -> str:
    return ", ".join(_placeholder(index) for index in range(count))


def _fetchone(cursor) -> Optional[dict[str, Any]]:
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {key: row[key] for key in row.keys()}


def _fetchall(cursor) -> list[dict[str, Any]]:
    rows = cursor.fetchall() or []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(dict(row))
        else:
            normalized.append({key: row[key] for key in row.keys()})
    return normalized


class PdfDirectTaskRepository:
    def create_task(
        self,
        *,
        user_id: str,
        upstream_file_no: str,
        file_name: str,
        file_size_kb: Optional[int] = None,
        page_num: Optional[int] = None,
    ) -> dict[str, Any]:
        now = _utc_now_naive()
        task_id = f"pdf_{uuid4().hex}"
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "insert into pdf_direct_tasks "
                    "(id, user_id, upstream_file_no, file_name, file_size_kb, page_num, "
                    "trans_status, status, created_at, updated_at) "
                    f"values ({_placeholders(10)})"
                ),
                (task_id, user_id, upstream_file_no, file_name, file_size_kb, page_num, 101, "active", now, now),
            )
        return self.get_task_by_id(task_id)

    def get_task_by_id(self, task_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id, user_id, upstream_file_no, file_name, file_size_kb, page_num, "
                    "progress, trans_status, trans_failure_cause, trans_failure_code, "
                    "cos_artifact_key, status, created_at, updated_at, completed_at "
                    f"from pdf_direct_tasks where id = {_placeholder(0)} limit 1"
                ),
                (task_id,),
            )
            return _fetchone(cursor)

    def get_task_by_id_and_user(self, task_id: str, user_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id, user_id, upstream_file_no, file_name, file_size_kb, page_num, "
                    "progress, trans_status, trans_failure_cause, trans_failure_code, "
                    "cos_artifact_key, status, created_at, updated_at, completed_at "
                    f"from pdf_direct_tasks where id = {_placeholder(0)} and user_id = {_placeholder(1)} limit 1"
                ),
                (task_id, user_id),
            )
            return _fetchone(cursor)

    def list_tasks_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id, user_id, upstream_file_no, file_name, file_size_kb, page_num, "
                    "progress, trans_status, trans_failure_cause, trans_failure_code, "
                    "cos_artifact_key, status, created_at, updated_at, completed_at "
                    f"from pdf_direct_tasks where user_id = {_placeholder(0)} "
                    "order by created_at desc"
                ),
                (user_id,),
            )
            return _fetchall(cursor)

    def update_task_status(
        self,
        *,
        task_id: str,
        trans_status: int,
        progress: Optional[float] = None,
        trans_failure_cause: Optional[str] = None,
        trans_failure_code: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        now = _utc_now_naive()
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update pdf_direct_tasks set "
                    f"trans_status = {_placeholder(0)}, "
                    f"progress = {_placeholder(1)}, "
                    f"trans_failure_cause = {_placeholder(2)}, "
                    f"trans_failure_code = {_placeholder(3)}, "
                    f"updated_at = {_placeholder(4)} "
                    f"where id = {_placeholder(5)}"
                ),
                (trans_status, progress, trans_failure_cause, trans_failure_code, now, task_id),
            )
            if trans_status in (104, 105, 106):
                cursor.execute(
                    f"update pdf_direct_tasks set completed_at = {_placeholder(0)} where id = {_placeholder(1)}",
                    (now, task_id),
                )
        return self.get_task_by_id(task_id)

    def set_cos_artifact_key(self, task_id: str, cos_artifact_key: str) -> None:
        now = _utc_now_naive()
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update pdf_direct_tasks set "
                    f"cos_artifact_key = {_placeholder(0)}, updated_at = {_placeholder(1)} "
                    f"where id = {_placeholder(2)}"
                ),
                (cos_artifact_key, now, task_id),
            )

    def find_stale_processing_tasks(self, timeout_seconds: float) -> list[dict[str, Any]]:
        """Find tasks stuck in processing state (103) beyond timeout_seconds since last update."""
        if timeout_seconds <= 0:
            return []
        from datetime import timedelta
        cutoff = _utc_now_naive() - timedelta(seconds=timeout_seconds)
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id, user_id, upstream_file_no, file_name, file_size_kb, page_num, "
                    "progress, trans_status, trans_failure_cause, trans_failure_code, "
                    "cos_artifact_key, status, created_at, updated_at, completed_at "
                    "from pdf_direct_tasks "
                    f"where trans_status = 103 and status = 'active' "
                    f"and updated_at < {_placeholder(0)}"
                ),
                (cutoff,),
            )
            return _fetchall(cursor)

    def fail_stale_task(
        self, task_id: str, failure_cause: str = "translation timed out"
    ) -> Optional[dict[str, Any]]:
        now = _utc_now_naive()
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update pdf_direct_tasks set "
                    f"trans_status = 106, "
                    f"trans_failure_cause = {_placeholder(0)}, "
                    f"completed_at = {_placeholder(1)}, "
                    f"updated_at = {_placeholder(1)} "
                    f"where id = {_placeholder(2)} and trans_status = 103"
                ),
                (failure_cause, now, task_id),
            )
        return self.get_task_by_id(task_id)

    def mark_expired(self, task_id: str) -> None:
        now = _utc_now_naive()
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update pdf_direct_tasks set "
                    f"status = 'expired', updated_at = {_placeholder(0)} "
                    f"where id = {_placeholder(1)}"
                ),
                (now, task_id),
            )
