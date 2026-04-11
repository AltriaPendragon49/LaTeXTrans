from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.db import DatabaseUnavailableError, db_connection, get_database_dialect

PAPER_COLUMNS = (
    "id",
    "created_by",
    "source",
    "arxiv_id",
    "title",
    "authors",
    "categories",
    "abstract_raw",
    "abstract_translated",
    "visibility",
    "status",
    "community_status",
    "trans_status",
    "trans_latest_task_id",
    "trans_latest_asset_pdf_id",
    "community_selected_task_id",
    "community_selected_asset_id",
    "like_count",
    "favorite_count",
    "comment_count",
    "view_count",
    "download_count",
    "official_published_at",
    "created_at",
    "updated_at",
)

PAPER_ASSET_COLUMNS = (
    "id",
    "paper_id",
    "task_id",
    "asset_type",
    "storage_backend",
    "file_path",
    "file_name",
    "mime_type",
    "is_latest",
    "created_at",
)

STRUCTURED_INSIGHT_COLUMNS = (
    "paper_id",
    "section_key",
    "content",
    "status",
    "updated_at",
)

CURATION_JOB_COLUMNS = (
    "job_id",
    "batch_id",
    "paper_id",
    "source_type",
    "arxiv_id",
    "original_filename",
    "source_path",
    "task_id",
    "source_language",
    "target_language",
    "status",
    "error",
    "created_by",
    "created_at",
    "updated_at",
)

DELETE_JOB_COLUMNS = (
    "job_id",
    "paper_id",
    "status",
    "attempt_count",
    "last_error",
    "created_by",
    "created_at",
    "updated_at",
)

_PAPER_JSON_COLUMNS = {"authors", "categories"}
_DELETE_JOB_INT_COLUMNS = {"attempt_count"}
_PAPER_INT_COLUMNS = {
    "like_count",
    "favorite_count",
    "comment_count",
    "view_count",
    "download_count",
}


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _placeholder(_index: int) -> str:
    return "?" if get_database_dialect() == "sqlite" else "%s"


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


def _decode_json_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return list(parsed) if isinstance(parsed, list) else []
    return []


class CommunityPaperRepository:
    def _normalize_paper_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if row is None:
            return None

        normalized = dict(row)
        for column in PAPER_COLUMNS:
            value = normalized.get(column)
            if column in _PAPER_JSON_COLUMNS:
                normalized[column] = _decode_json_list(value)
            elif column in _PAPER_INT_COLUMNS and value is not None:
                normalized[column] = int(value)
            else:
                normalized[column] = value
        return normalized

    def _normalize_asset_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if row is None:
            return None
        normalized = dict(row)
        normalized["is_latest"] = bool(normalized.get("is_latest"))
        return normalized

    def _serialize_paper_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        serialized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in PAPER_COLUMNS:
                continue
            if key in _PAPER_JSON_COLUMNS:
                serialized[key] = json.dumps(list(value or []), ensure_ascii=False)
            elif key in _PAPER_INT_COLUMNS and value is not None:
                serialized[key] = int(value)
            else:
                serialized[key] = value
        return serialized

    def _serialize_asset_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        serialized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in PAPER_ASSET_COLUMNS:
                continue
            if key == "is_latest" and value is not None:
                serialized[key] = bool(value)
            else:
                serialized[key] = value
        return serialized

    def _normalize_structured_insight_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if row is None:
            return None

        normalized = dict(row)
        for column in STRUCTURED_INSIGHT_COLUMNS:
            normalized[column] = normalized.get(column)
        return normalized

    def _serialize_structured_insight_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        serialized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in STRUCTURED_INSIGHT_COLUMNS:
                continue
            serialized[key] = value
        return serialized

    def _normalize_curation_job_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        return dict(row) if row is not None else None

    def _serialize_curation_job_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in payload.items() if key in CURATION_JOB_COLUMNS}

    def _normalize_delete_job_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if row is None:
            return None
        normalized = dict(row)
        for column in DELETE_JOB_COLUMNS:
            value = normalized.get(column)
            if column in _DELETE_JOB_INT_COLUMNS and value is not None:
                normalized[column] = int(value)
            else:
                normalized[column] = value
        return normalized

    def _serialize_delete_job_updates(self, payload: dict[str, Any]) -> dict[str, Any]:
        serialized: dict[str, Any] = {}
        for key, value in payload.items():
            if key not in DELETE_JOB_COLUMNS:
                continue
            if key in _DELETE_JOB_INT_COLUMNS and value is not None:
                serialized[key] = int(value)
            else:
                serialized[key] = value
        return serialized

    def get_paper_by_id(self, paper_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_COLUMNS)
                    + f" from papers where id = {_placeholder(0)} limit 1"
                ),
                (paper_id,),
            )
            return self._normalize_paper_row(_fetchone(cursor))

    def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_COLUMNS)
                    + f" from papers where arxiv_id = {_placeholder(0)} limit 1"
                ),
                (arxiv_id,),
            )
            return self._normalize_paper_row(_fetchone(cursor))

    def get_paper_by_title(
        self,
        *,
        title: str,
        source: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            params: list[Any] = [title, "removed"]
            sql = (
                "select "
                + ", ".join(PAPER_COLUMNS)
                + f" from papers where title = {_placeholder(0)} and status <> {_placeholder(1)}"
            )
            if source:
                sql += f" and source = {_placeholder(2)}"
                params.append(source)
            sql += " limit 1"
            cursor.execute(sql, tuple(params))
            return self._normalize_paper_row(_fetchone(cursor))

    def list_public_papers(self) -> list[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_COLUMNS)
                    + " from papers where visibility = "
                    + _placeholder(0)
                    + " and status <> "
                    + _placeholder(1)
                ),
                ("public", "removed"),
            )
            return [
                normalized
                for normalized in (self._normalize_paper_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def insert_paper(self, payload: dict[str, Any]) -> dict[str, Any]:
        serialized = self._serialize_paper_updates(payload)
        if "id" not in serialized:
            raise ValueError("paper id is required")
        columns = tuple(column for column in PAPER_COLUMNS if column in serialized)
        placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "insert into papers ("
                    + ", ".join(columns)
                    + f") values ({placeholders})"
                ),
                tuple(serialized[column] for column in columns),
            )
        return self.get_paper_by_id(str(serialized["id"])) or dict(payload)

    def update_paper(self, paper_id: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        serialized = self._serialize_paper_updates(updates)
        if not serialized:
            return self.get_paper_by_id(paper_id)

        assignments = ", ".join(
            f"{column} = {_placeholder(index)}"
            for index, column in enumerate(serialized.keys())
        )
        values = [serialized[column] for column in serialized.keys()]
        values.append(paper_id)
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    f"update papers set {assignments} "
                    f"where id = {_placeholder(len(values) - 1)}"
                ),
                tuple(values),
            )
            if cursor.rowcount <= 0:
                return None
        return self.get_paper_by_id(paper_id)

    def list_latest_assets_for_paper(self, paper_id: str) -> list[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_ASSET_COLUMNS)
                    + " from paper_assets where paper_id = "
                    + _placeholder(0)
                    + " and is_latest = "
                    + _placeholder(1)
                    + " order by created_at desc"
                ),
                (paper_id, True),
            )
            return [
                normalized
                for normalized in (self._normalize_asset_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_latest_assets_for_papers(self, paper_ids: list[str]) -> list[dict[str, Any]]:
        normalized_ids = [str(paper_id or "").strip() for paper_id in paper_ids if str(paper_id or "").strip()]
        if not normalized_ids:
            return []
        with db_connection() as connection:
            cursor = connection.cursor()
            placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_ASSET_COLUMNS)
                    + " from paper_assets where paper_id in ("
                    + placeholders
                    + ") and is_latest = "
                    + _placeholder(len(normalized_ids))
                    + " order by created_at desc"
                ),
                (*normalized_ids, True),
            )
            return [
                normalized
                for normalized in (self._normalize_asset_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def upsert_latest_asset(
        self,
        *,
        paper_id: str,
        task_id: Optional[str],
        asset_type: str,
        file_path: str,
        file_name: str,
        mime_type: str,
        storage_backend: str = "local_disk",
        asset_id: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> dict[str, Any]:
        normalized_asset_id = str(asset_id or "").strip() or f"{paper_id}:{asset_type}:{task_id or 'none'}"
        normalized_created_at = created_at or _utc_now_naive().isoformat()

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update paper_assets set is_latest = "
                    + _placeholder(0)
                    + " where paper_id = "
                    + _placeholder(1)
                    + " and asset_type = "
                    + _placeholder(2)
                ),
                (False, paper_id, asset_type),
            )

            existing = None
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_ASSET_COLUMNS)
                    + f" from paper_assets where id = {_placeholder(0)} limit 1"
                ),
                (normalized_asset_id,),
            )
            existing = _fetchone(cursor)
            payload = {
                "id": normalized_asset_id,
                "paper_id": paper_id,
                "task_id": task_id,
                "asset_type": asset_type,
                "storage_backend": storage_backend,
                "file_path": file_path,
                "file_name": file_name,
                "mime_type": mime_type,
                "is_latest": True,
                "created_at": normalized_created_at,
            }
            serialized = self._serialize_asset_updates(payload)
            if existing is None:
                columns = tuple(column for column in PAPER_ASSET_COLUMNS if column in serialized)
                placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
                cursor.execute(
                    (
                        "insert into paper_assets ("
                        + ", ".join(columns)
                        + f") values ({placeholders})"
                    ),
                    tuple(serialized[column] for column in columns),
                )
            else:
                assignments = ", ".join(
                    f"{column} = {_placeholder(index)}"
                    for index, column in enumerate(
                        column for column in PAPER_ASSET_COLUMNS if column != "id" and column in serialized
                    )
                )
                update_columns = [column for column in PAPER_ASSET_COLUMNS if column != "id" and column in serialized]
                values = [serialized[column] for column in update_columns]
                values.append(normalized_asset_id)
                cursor.execute(
                    (
                        f"update paper_assets set {assignments} "
                        f"where id = {_placeholder(len(values) - 1)}"
                    ),
                    tuple(values),
                )

        for row in self.list_latest_assets_for_paper(paper_id):
            if str(row.get("asset_type") or "") == asset_type:
                return row
        return payload

    def list_structured_insight_sections(self, paper_id: str) -> list[dict[str, Any]]:
        try:
            with db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    (
                        "select "
                        + ", ".join(STRUCTURED_INSIGHT_COLUMNS)
                        + " from community_structured_insights where paper_id = "
                        + _placeholder(0)
                        + " order by updated_at asc, section_key asc"
                    ),
                    (paper_id,),
                )
                return [
                    normalized
                    for normalized in (
                        self._normalize_structured_insight_row(row) for row in _fetchall(cursor)
                    )
                    if normalized is not None
                ]
        except Exception:
            return []

    def upsert_structured_insight_section(self, payload: dict[str, Any]) -> dict[str, Any]:
        serialized = self._serialize_structured_insight_updates(payload)
        paper_id = str(serialized.get("paper_id") or "").strip()
        section_key = str(serialized.get("section_key") or "").strip()
        if not paper_id or not section_key:
            raise ValueError("paper_id and section_key are required")

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "delete from community_structured_insights where paper_id = "
                    + _placeholder(0)
                    + " and section_key = "
                    + _placeholder(1)
                ),
                (paper_id, section_key),
            )
            columns = tuple(column for column in STRUCTURED_INSIGHT_COLUMNS if column in serialized)
            placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
            cursor.execute(
                (
                    "insert into community_structured_insights ("
                    + ", ".join(columns)
                    + f") values ({placeholders})"
                ),
                tuple(serialized[column] for column in columns),
            )

        rows = self.list_structured_insight_sections(paper_id)
        for row in rows:
            if str(row.get("section_key") or "") == section_key:
                return row
        return payload

    def insert_curation_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        serialized = self._serialize_curation_job_updates(payload)
        job_id = str(serialized.get("job_id") or "").strip()
        if not job_id:
            raise ValueError("job_id is required")

        columns = tuple(column for column in CURATION_JOB_COLUMNS if column in serialized)
        placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "insert into community_curation_jobs ("
                    + ", ".join(columns)
                    + f") values ({placeholders})"
                ),
                tuple(serialized[column] for column in columns),
            )
        return self.get_curation_job(job_id) or dict(payload)

    def get_curation_job(self, job_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(CURATION_JOB_COLUMNS)
                    + " from community_curation_jobs where job_id = "
                    + _placeholder(0)
                    + " limit 1"
                ),
                (job_id,),
            )
            return self._normalize_curation_job_row(_fetchone(cursor))

    def update_curation_job(self, job_id: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        serialized = self._serialize_curation_job_updates(updates)
        if not serialized:
            return self.get_curation_job(job_id)

        assignments = ", ".join(
            f"{column} = {_placeholder(index)}"
            for index, column in enumerate(serialized.keys())
        )
        values = [serialized[column] for column in serialized.keys()]
        values.append(job_id)
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    f"update community_curation_jobs set {assignments} "
                    f"where job_id = {_placeholder(len(values) - 1)}"
                ),
                tuple(values),
            )
            if cursor.rowcount <= 0:
                return None
        return self.get_curation_job(job_id)

    def list_curation_jobs_for_batch(self, batch_id: str) -> list[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(CURATION_JOB_COLUMNS)
                    + " from community_curation_jobs where batch_id = "
                    + _placeholder(0)
                    + " order by created_at asc, job_id asc"
                ),
                (batch_id,),
            )
            return [
                normalized
                for normalized in (self._normalize_curation_job_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_pending_curation_jobs(self) -> list[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(CURATION_JOB_COLUMNS)
                    + " from community_curation_jobs where status in ("
                    + _placeholder(0)
                    + ", "
                    + _placeholder(1)
                    + ", "
                    + _placeholder(2)
                    + ") order by created_at asc"
                ),
                ("queued", "processing", "retry"),
            )
            return [
                normalized
                for normalized in (self._normalize_curation_job_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def insert_delete_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        serialized = self._serialize_delete_job_updates(payload)
        job_id = str(serialized.get("job_id") or "").strip()
        if not job_id:
            raise ValueError("job_id is required")

        columns = tuple(column for column in DELETE_JOB_COLUMNS if column in serialized)
        placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "insert into community_delete_jobs ("
                    + ", ".join(columns)
                    + f") values ({placeholders})"
                ),
                tuple(serialized[column] for column in columns),
            )
        return self.get_delete_job(job_id) or dict(payload)

    def get_delete_job(self, job_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(DELETE_JOB_COLUMNS)
                    + " from community_delete_jobs where job_id = "
                    + _placeholder(0)
                    + " limit 1"
                ),
                (job_id,),
            )
            return self._normalize_delete_job_row(_fetchone(cursor))

    def get_delete_job_by_paper_id(self, paper_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(DELETE_JOB_COLUMNS)
                    + " from community_delete_jobs where paper_id = "
                    + _placeholder(0)
                    + " order by created_at desc limit 1"
                ),
                (paper_id,),
            )
            return self._normalize_delete_job_row(_fetchone(cursor))

    def update_delete_job(self, job_id: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        serialized = self._serialize_delete_job_updates(updates)
        if not serialized:
            return self.get_delete_job(job_id)

        assignments = ", ".join(
            f"{column} = {_placeholder(index)}"
            for index, column in enumerate(serialized.keys())
        )
        values = [serialized[column] for column in serialized.keys()]
        values.append(job_id)
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    f"update community_delete_jobs set {assignments} "
                    f"where job_id = {_placeholder(len(values) - 1)}"
                ),
                tuple(values),
            )
            if cursor.rowcount <= 0:
                return None
        return self.get_delete_job(job_id)

    def list_pending_delete_jobs(self) -> list[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(DELETE_JOB_COLUMNS)
                    + " from community_delete_jobs where status in ("
                    + _placeholder(0)
                    + ", "
                    + _placeholder(1)
                    + ", "
                    + _placeholder(2)
                    + ") order by created_at asc"
                ),
                ("queued", "running", "retry"),
            )
            return [
                normalized
                for normalized in (self._normalize_delete_job_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def get_viewer_state(self, paper_ids: list[str], *, user_id: str) -> dict[str, dict[str, bool]]:
        normalized_ids = [str(paper_id or "").strip() for paper_id in paper_ids if str(paper_id or "").strip()]
        default_state = {
            paper_id: {"liked": False, "favorited": False}
            for paper_id in normalized_ids
        }
        if not normalized_ids or not user_id:
            return default_state

        try:
            with db_connection() as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index + 1) for index in range(len(normalized_ids)))
                cursor.execute(
                    (
                        "select paper_id from paper_likes where user_id = "
                        + _placeholder(0)
                        + " and paper_id in ("
                        + placeholders
                        + ")"
                    ),
                    (user_id, *normalized_ids),
                )
                liked_ids = {
                    str(row.get("paper_id") or "").strip()
                    for row in _fetchall(cursor)
                    if str(row.get("paper_id") or "").strip()
                }
                cursor.execute(
                    (
                        "select paper_id from paper_favorites where user_id = "
                        + _placeholder(0)
                        + " and paper_id in ("
                        + placeholders
                        + ")"
                    ),
                    (user_id, *normalized_ids),
                )
                favorited_ids = {
                    str(row.get("paper_id") or "").strip()
                    for row in _fetchall(cursor)
                    if str(row.get("paper_id") or "").strip()
                }
        except Exception:
            return default_state

        for paper_id in normalized_ids:
            default_state[paper_id] = {
                "liked": paper_id in liked_ids,
                "favorited": paper_id in favorited_ids,
            }
        return default_state

    def increment_view_count(self, paper_id: str) -> Optional[int]:
        return self._increment_counter(paper_id, "view_count")

    def increment_download_count(self, paper_id: str) -> Optional[int]:
        return self._increment_counter(paper_id, "download_count")

    def _increment_counter(self, paper_id: str, column: str) -> Optional[int]:
        if column not in {"view_count", "download_count"}:
            raise ValueError(f"unsupported counter column: {column}")

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    f"update papers set {column} = coalesce({column}, 0) + 1, "
                    f"updated_at = {_placeholder(0)} where id = {_placeholder(1)}"
                ),
                (_utc_now_naive().isoformat(), paper_id),
            )
            if cursor.rowcount <= 0:
                return None
            cursor.execute(
                f"select {column} from papers where id = {_placeholder(0)} limit 1",
                (paper_id,),
            )
            row = _fetchone(cursor)
        if row is None:
            return None
        value = row.get(column)
        return int(value) if value is not None else 0

    def mark_translation_failed_by_task(self, task_id: str) -> int:
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            return 0

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update papers set trans_status = "
                    + _placeholder(0)
                    + ", updated_at = "
                    + _placeholder(1)
                    + " where community_selected_task_id = "
                    + _placeholder(2)
                    + " and trans_status in ("
                    + _placeholder(3)
                    + ", "
                    + _placeholder(4)
                    + ")"
                ),
                ("failed", _utc_now_naive().isoformat(), normalized_task_id, "queued", "processing"),
            )
            return int(cursor.rowcount or 0)

    def list_inflight_translation_papers(self) -> list[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_COLUMNS)
                    + " from papers where trans_status in ("
                    + _placeholder(0)
                    + ", "
                    + _placeholder(1)
                    + ")"
                ),
                ("queued", "processing"),
            )
            return [
                normalized
                for normalized in (self._normalize_paper_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_purgeable_non_success_papers(self, statuses: list[str]) -> list[dict[str, Any]]:
        normalized_statuses = [str(status or "").strip() for status in statuses if str(status or "").strip()]
        if not normalized_statuses:
            return []
        placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_statuses)))
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(PAPER_COLUMNS)
                    + " from papers where trans_status in ("
                    + placeholders
                    + ")"
                ),
                tuple(normalized_statuses),
            )
            return [
                normalized
                for normalized in (self._normalize_paper_row(row) for row in _fetchall(cursor))
                if normalized is not None
            ]

    def list_asset_task_ids_for_papers(self, paper_ids: list[str]) -> list[str]:
        normalized_ids = [str(paper_id or "").strip() for paper_id in paper_ids if str(paper_id or "").strip()]
        if not normalized_ids:
            return []
        placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select task_id from paper_assets where paper_id in ("
                    + placeholders
                    + ")"
                ),
                tuple(normalized_ids),
            )
            return [
                str(row.get("task_id") or "").strip()
                for row in _fetchall(cursor)
                if str(row.get("task_id") or "").strip()
            ]

    def list_comment_ids_for_papers(self, paper_ids: list[str]) -> list[str]:
        normalized_ids = [str(paper_id or "").strip() for paper_id in paper_ids if str(paper_id or "").strip()]
        if not normalized_ids:
            return []
        try:
            with db_connection() as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
                cursor.execute(
                    (
                        "select id from comments where paper_id in ("
                        + placeholders
                        + ")"
                    ),
                    tuple(normalized_ids),
                )
                return [
                    str(row.get("id") or "").strip()
                    for row in _fetchall(cursor)
                    if str(row.get("id") or "").strip()
                ]
        except Exception:
            return []

    def list_report_ids_for_targets(self, *, target_type: str, target_ids: list[str]) -> list[str]:
        normalized_ids = [str(target_id or "").strip() for target_id in target_ids if str(target_id or "").strip()]
        if not normalized_ids:
            return []
        try:
            with db_connection() as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index + 1) for index in range(len(normalized_ids)))
                cursor.execute(
                    (
                        "select id from reports where target_type = "
                        + _placeholder(0)
                        + " and target_id in ("
                        + placeholders
                        + ")"
                    ),
                    (target_type, *normalized_ids),
                )
                return [
                    str(row.get("id") or "").strip()
                    for row in _fetchall(cursor)
                    if str(row.get("id") or "").strip()
                ]
        except Exception:
            return []

    def delete_rows_by_ids(self, table_name: str, *, id_column: str, row_ids: list[str]) -> int:
        if table_name not in {"reports", "moderation_actions"}:
            raise ValueError(f"unsupported cleanup table: {table_name}")
        normalized_ids = [str(row_id or "").strip() for row_id in row_ids if str(row_id or "").strip()]
        if not normalized_ids:
            return 0
        try:
            with db_connection(commit=True) as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
                cursor.execute(
                    f"delete from {table_name} where {id_column} in ({placeholders})",
                    tuple(normalized_ids),
                )
                return int(cursor.rowcount or 0)
        except Exception:
            return 0

    def delete_rows_for_papers(self, table_name: str, paper_ids: list[str]) -> int:
        if table_name not in {
            "comments",
            "paper_assets",
            "paper_likes",
            "paper_favorites",
            "community_structured_insights",
            "papers",
        }:
            raise ValueError(f"unsupported cleanup table: {table_name}")
        normalized_ids = [str(paper_id or "").strip() for paper_id in paper_ids if str(paper_id or "").strip()]
        if not normalized_ids:
            return 0
        try:
            with db_connection(commit=True) as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
                cursor.execute(
                    f"delete from {table_name} where paper_id in ({placeholders})"
                    if table_name != "papers"
                    else f"delete from papers where id in ({placeholders})",
                    tuple(normalized_ids),
                )
                return int(cursor.rowcount or 0)
        except Exception:
            return 0

    def delete_translation_tasks(self, task_ids: list[str]) -> int:
        normalized_ids = [str(task_id or "").strip() for task_id in task_ids if str(task_id or "").strip()]
        if not normalized_ids:
            return 0
        try:
            with db_connection(commit=True) as connection:
                cursor = connection.cursor()
                placeholders = ", ".join(_placeholder(index) for index in range(len(normalized_ids)))
                cursor.execute(
                    "delete from translation_tasks where task_id in (" + placeholders + ")",
                    tuple(normalized_ids),
                )
                return int(cursor.rowcount or 0)
        except Exception:
            return 0


__all__ = [
    "CommunityPaperRepository",
    "PAPER_COLUMNS",
    "PAPER_ASSET_COLUMNS",
    "DatabaseUnavailableError",
]
