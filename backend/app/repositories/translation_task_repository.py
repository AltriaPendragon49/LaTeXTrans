from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.db import db_connection, get_database_dialect

TRANSLATION_TASK_COLUMNS = (
    "task_id",
    "user_id",
    "source_type",
    "arxiv_id",
    "status",
    "stage",
    "progress",
    "message",
    "error",
    "detail_code",
    "source_language",
    "target_language",
    "translation_mode",
    "compile_strategy",
    "translation_model",
    "config_hash",
    "source_path",
    "output_path",
    "formatting",
    "generate_glossary",
    "use_author_api",
    "email_notification",
    "created_at",
    "completed_at",
)

_JSON_COLUMNS = {"formatting"}
_BOOLEAN_COLUMNS = {"generate_glossary", "use_author_api", "email_notification"}


def _utc_now_naive() -> datetime:
    """获取当前UTC时间，去除时区信息和微秒。"""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _placeholder(_index: int) -> str:
    """根据数据库方言返回对应的参数占位符（SQLite: ?，MySQL: %s）。"""
    return "?" if get_database_dialect() == "sqlite" else "%s"


def _placeholders(count: int) -> str:
    """生成指定数量的参数占位符，用逗号分隔。"""
    return ", ".join(_placeholder(index) for index in range(count))


def _fetchone(cursor) -> Optional[dict[str, Any]]:
    """从游标获取一行数据并转换为字典格式返回。"""
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {key: row[key] for key in row.keys()}


def _fetchall(cursor) -> list[dict[str, Any]]:
    """从游标获取所有行数据并转换为字典列表返回。"""
    rows = cursor.fetchall() or []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(dict(row))
        else:
            normalized.append({key: row[key] for key in row.keys()})
    return normalized


def _decode_json(value: Any) -> Any:
    """将存储的JSON数据解码为Python对象。"""
    if value in (None, ""):
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode()
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


class TranslationTaskRepository:
    """翻译任务数据访问层，管理翻译任务的增删改查、分页列表及批量操作。"""

    def _normalize_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """将数据库行数据标准化为统一的翻译任务记录格式。"""
        if row is None:
            return None

        normalized = dict(row)
        for column in TRANSLATION_TASK_COLUMNS:
            value = normalized.get(column)
            if column in _JSON_COLUMNS:
                normalized[column] = _decode_json(value)
            elif column in _BOOLEAN_COLUMNS and value is not None:
                normalized[column] = bool(value)
            else:
                normalized[column] = value
        return normalized

    def _serialize_updates(self, updates: dict[str, Any]) -> dict[str, Any]:
        """将更新载荷序列化为适合数据库存储的格式。"""
        serialized: dict[str, Any] = {}
        for key, value in updates.items():
            if key not in TRANSLATION_TASK_COLUMNS:
                continue
            if key in _JSON_COLUMNS:
                serialized[key] = None if value is None else json.dumps(value)
            elif key in _BOOLEAN_COLUMNS and value is not None:
                serialized[key] = bool(value)
            else:
                serialized[key] = value
        return serialized

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        """根据任务ID获取翻译任务记录。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(TRANSLATION_TASK_COLUMNS)
                    + f" from translation_tasks where task_id = {_placeholder(0)} limit 1"
                ),
                (task_id,),
            )
            return self._normalize_row(_fetchone(cursor))

    def list_tasks_for_user(
        self,
        user_id: str,
        *,
        page: int,
        page_size: int,
        status_filter: Optional[str],
    ) -> tuple[list[dict[str, Any]], int]:
        """分页获取指定用户的翻译任务列表，支持按状态过滤。"""
        offset = (page - 1) * page_size
        where_clause = f"user_id = {_placeholder(0)}"
        params: list[Any] = [user_id]
        if status_filter:
            where_clause += f" and status = {_placeholder(len(params))}"
            params.append(status_filter)

        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(TRANSLATION_TASK_COLUMNS)
                    + f" from translation_tasks where {where_clause} "
                    "order by created_at desc "
                    f"limit {_placeholder(len(params))} offset {_placeholder(len(params) + 1)}"
                ),
                (*params, page_size, offset),
            )
            tasks = [self._normalize_row(row) for row in _fetchall(cursor)]

            cursor.execute(
                f"select count(*) as total from translation_tasks where {where_clause}",
                tuple(params),
            )
            count_row = _fetchone(cursor) or {"total": 0}
            return [task for task in tasks if task is not None], int(count_row.get("total") or 0)

    def get_task_for_user(self, user_id: str, task_id: str) -> Optional[dict[str, Any]]:
        """获取指定用户的单个翻译任务记录。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(TRANSLATION_TASK_COLUMNS)
                    + f" from translation_tasks where user_id = {_placeholder(0)} and task_id = {_placeholder(1)} limit 1"
                ),
                (user_id, task_id),
            )
            return self._normalize_row(_fetchone(cursor))

    def list_task_ids_by_status(self, statuses: list[str]) -> list[str]:
        """根据状态列表获取对应的任务ID列表。"""
        normalized_statuses = [str(status or "").strip() for status in statuses if str(status or "").strip()]
        if not normalized_statuses:
            return []

        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select task_id from translation_tasks where status in ("
                    + _placeholders(len(normalized_statuses))
                    + ") order by created_at desc"
                ),
                tuple(normalized_statuses),
            )
            return [
                str(row.get("task_id") or "").strip()
                for row in _fetchall(cursor)
                if str(row.get("task_id") or "").strip()
            ]

    def list_existing_task_ids(self, task_ids: list[str]) -> list[str]:
        """从给定的任务ID列表中筛选出数据库中实际存在的任务ID。"""
        normalized_task_ids = [str(task_id or "").strip() for task_id in task_ids if str(task_id or "").strip()]
        if not normalized_task_ids:
            return []

        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select task_id from translation_tasks where task_id in ("
                    + _placeholders(len(normalized_task_ids))
                    + ")"
                ),
                tuple(normalized_task_ids),
            )
            return [
                str(row.get("task_id") or "").strip()
                for row in _fetchall(cursor)
                if str(row.get("task_id") or "").strip()
            ]

    def list_task_statuses(self, task_ids: list[str]) -> dict[str, str]:
        """批量获取多个任务ID对应的状态字典。"""
        normalized_task_ids = [str(task_id or "").strip() for task_id in task_ids if str(task_id or "").strip()]
        if not normalized_task_ids:
            return {}

        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select task_id, status from translation_tasks where task_id in ("
                    + _placeholders(len(normalized_task_ids))
                    + ")"
                ),
                tuple(normalized_task_ids),
            )
            return {
                str(row.get("task_id") or "").strip(): str(row.get("status") or "").strip()
                for row in _fetchall(cursor)
                if str(row.get("task_id") or "").strip()
            }

    def insert_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        """插入一条新的翻译任务记录。"""
        serialized = self._serialize_updates(payload)
        columns = tuple(column for column in TRANSLATION_TASK_COLUMNS if column in serialized)
        placeholders = ", ".join(_placeholder(index) for index in range(len(columns)))
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "insert into translation_tasks ("
                    + ", ".join(columns)
                    + f") values ({placeholders})"
                ),
                tuple(serialized[column] for column in columns),
            )
        return self.get_task(str(payload["task_id"])) or dict(payload)

    def update_task(self, task_id: str, updates: dict[str, Any]) -> bool:
        """更新指定翻译任务记录，返回是否更新成功。"""
        serialized = self._serialize_updates(updates)
        if not serialized:
            return self.get_task(task_id) is not None

        assignments = ", ".join(
            f"{column} = {_placeholder(index)}"
            for index, column in enumerate(serialized.keys())
        )
        values = [serialized[column] for column in serialized.keys()]
        values.append(task_id)

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    f"update translation_tasks set {assignments} "
                    f"where task_id = {_placeholder(len(values) - 1)}"
                ),
                tuple(values),
            )
            return cursor.rowcount > 0

    def update_tasks(self, task_ids: list[str], updates: dict[str, Any]) -> int:
        """批量更新多个翻译任务记录，返回受影响的行数。"""
        normalized_task_ids = [str(task_id or "").strip() for task_id in task_ids if str(task_id or "").strip()]
        if not normalized_task_ids:
            return 0

        serialized = self._serialize_updates(updates)
        if not serialized:
            return len(self.list_existing_task_ids(normalized_task_ids))

        assignments = ", ".join(
            f"{column} = {_placeholder(index)}"
            for index, column in enumerate(serialized.keys())
        )
        where_offset = len(serialized)
        values = [serialized[column] for column in serialized.keys()]
        values.extend(normalized_task_ids)

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    f"update translation_tasks set {assignments} "
                    "where task_id in ("
                    + ", ".join(_placeholder(where_offset + index) for index in range(len(normalized_task_ids)))
                    + ")"
                ),
                tuple(values),
            )
            return int(cursor.rowcount or 0)

    def upsert_task(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """创建或更新翻译任务记录（存在则更新，不存在则插入）。"""
        existing = self.get_task(task_id)
        if existing is None:
            return self.insert_task(payload)
        self.update_task(task_id, payload)
        return self.get_task(task_id) or dict(payload)

    def delete_task_for_user(self, user_id: str, task_id: str) -> bool:
        """删除指定用户的翻译任务记录，返回是否删除成功。"""
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "delete from translation_tasks "
                    f"where user_id = {_placeholder(0)} and task_id = {_placeholder(1)}"
                ),
                (user_id, task_id),
            )
            return cursor.rowcount > 0

    def delete_task(self, task_id: str) -> bool:
        """根据任务ID删除翻译任务记录（不校验用户归属），返回是否删除成功。"""
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "delete from translation_tasks "
                    f"where task_id = {_placeholder(0)}"
                ),
                (task_id,),
            )
            return cursor.rowcount > 0

    def find_reusable_completed_task(
        self,
        config_hash: str,
        *,
        exclude_task_id: str,
    ) -> Optional[dict[str, Any]]:
        """查找具有相同配置哈希且已完成的可复用翻译任务，用于避免重复翻译。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(TRANSLATION_TASK_COLUMNS)
                    + " from translation_tasks "
                    f"where config_hash = {_placeholder(0)} "
                    f"and status in ({_placeholder(1)}, {_placeholder(2)}) "
                    f"and task_id <> {_placeholder(3)} "
                    "order by completed_at desc, created_at desc limit 1"
                ),
                (config_hash, "completed", "completed_with_warnings", exclude_task_id),
            )
            return self._normalize_row(_fetchone(cursor))
