from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.db import db_connection, get_database_dialect

USER_SETTINGS_DEFAULTS: dict[str, Any] = {
    "default_source_language": "en",
    "default_target_language": "zh",
    "translation_mode": "full",
    "compile_strategy": "auto",
    "translation_model": None,
    "generate_glossary": True,
    "use_author_api": True,
    "custom_base_url": None,
    "custom_api_key_encrypted": None,
    "default_formatting": None,
}

_USER_SETTINGS_COLUMNS = tuple(USER_SETTINGS_DEFAULTS.keys())
_JSON_COLUMNS = {"default_formatting"}
_BOOLEAN_COLUMNS = {"generate_glossary", "use_author_api"}


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


def _decode_json(value: Any) -> Any:
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


class UserSettingsRepository:
    def _normalize_settings_row(self, row: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if row is None:
            return None

        normalized = dict(USER_SETTINGS_DEFAULTS)
        for column in _USER_SETTINGS_COLUMNS:
            value = row.get(column)
            if column in _JSON_COLUMNS:
                normalized[column] = _decode_json(value)
            elif column in _BOOLEAN_COLUMNS and value is not None:
                normalized[column] = bool(value)
            else:
                normalized[column] = value
        return normalized

    def _serialize_updates(self, updates: dict[str, Any]) -> dict[str, Any]:
        serialized: dict[str, Any] = {}
        for key, value in updates.items():
            if key not in _USER_SETTINGS_COLUMNS:
                continue
            if key in _JSON_COLUMNS:
                serialized[key] = None if value is None else json.dumps(value)
            else:
                serialized[key] = value
        return serialized

    def get_user_settings(self, user_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(_USER_SETTINGS_COLUMNS)
                    + f" from user_settings where user_id = {_placeholder(0)} limit 1"
                ),
                (user_id,),
            )
            return self._normalize_settings_row(_fetchone(cursor))

    def upsert_user_settings(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        serialized_updates = self._serialize_updates(updates)
        now = _utc_now_naive()

        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select "
                    + ", ".join(_USER_SETTINGS_COLUMNS)
                    + f" from user_settings where user_id = {_placeholder(0)} limit 1"
                ),
                (user_id,),
            )
            existing = _fetchone(cursor)

            if existing is None:
                insert_payload = dict(USER_SETTINGS_DEFAULTS)
                insert_payload.update(serialized_updates)
                insert_columns = ("user_id", *_USER_SETTINGS_COLUMNS, "updated_at")
                insert_values = (user_id, *(insert_payload[column] for column in _USER_SETTINGS_COLUMNS), now)
                placeholders = ", ".join(_placeholder(index) for index in range(len(insert_columns)))
                cursor.execute(
                    (
                        "insert into user_settings ("
                        + ", ".join(insert_columns)
                        + f") values ({placeholders})"
                    ),
                    insert_values,
                )
            elif serialized_updates:
                update_columns = (*serialized_updates.keys(), "updated_at")
                assignments = ", ".join(
                    f"{column} = {_placeholder(index)}"
                    for index, column in enumerate(update_columns)
                )
                values = (*serialized_updates.values(), now, user_id)
                cursor.execute(
                    (
                        f"update user_settings set {assignments} "
                        f"where user_id = {_placeholder(len(values) - 1)}"
                    ),
                    values,
                )

        saved = self.get_user_settings(user_id)
        return saved or dict(USER_SETTINGS_DEFAULTS)
