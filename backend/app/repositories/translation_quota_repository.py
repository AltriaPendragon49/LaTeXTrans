from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

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


class TranslationQuotaRepository:
    def ensure_daily_quota(
        self,
        *,
        user_id: str,
        quota_type: str,
        quota_date: str,
        limit_count: int,
    ) -> dict[str, Any]:
        now = _utc_now_naive()
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            self._ensure_daily_quota_row(
                cursor,
                user_id=user_id,
                quota_type=quota_type,
                quota_date=quota_date,
                limit_count=limit_count,
                now=now,
            )
            return self._select_daily_quota_row(
                cursor,
                user_id=user_id,
                quota_type=quota_type,
                quota_date=quota_date,
            )

    def reserve_daily_quota(
        self,
        *,
        user_id: str,
        quota_type: str,
        quota_date: str,
        requested_count: int,
        limit_count: int,
    ) -> tuple[bool, dict[str, Any]]:
        now = _utc_now_naive()
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            self._ensure_daily_quota_row(
                cursor,
                user_id=user_id,
                quota_type=quota_type,
                quota_date=quota_date,
                limit_count=limit_count,
                now=now,
            )
            update_sql = (
                "update user_daily_quotas "
                f"set used_count = used_count + {_placeholder(0)}, "
                f"limit_count = {_placeholder(1)}, updated_at = {_placeholder(2)} "
                f"where user_id = {_placeholder(3)} "
                f"and quota_type = {_placeholder(4)} "
                f"and quota_date = {_placeholder(5)} "
                f"and used_count + {_placeholder(6)} <= {_placeholder(7)}"
            )
            cursor.execute(
                update_sql,
                (
                    requested_count,
                    limit_count,
                    now,
                    user_id,
                    quota_type,
                    quota_date,
                    requested_count,
                    limit_count,
                ),
            )
            accepted = int(cursor.rowcount or 0) > 0
            row = self._select_daily_quota_row(
                cursor,
                user_id=user_id,
                quota_type=quota_type,
                quota_date=quota_date,
            )
            return accepted, row

    def release_daily_quota(
        self,
        *,
        user_id: str,
        quota_type: str,
        quota_date: str,
        count: int,
        limit_count: int,
    ) -> dict[str, Any]:
        now = _utc_now_naive()
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            self._ensure_daily_quota_row(
                cursor,
                user_id=user_id,
                quota_type=quota_type,
                quota_date=quota_date,
                limit_count=limit_count,
                now=now,
            )
            clamp_fn = "max" if get_database_dialect() == "sqlite" else "greatest"
            cursor.execute(
                (
                    "update user_daily_quotas "
                    f"set used_count = {clamp_fn}(0, used_count - {_placeholder(0)}), "
                    f"limit_count = {_placeholder(1)}, updated_at = {_placeholder(2)} "
                    f"where user_id = {_placeholder(3)} "
                    f"and quota_type = {_placeholder(4)} "
                    f"and quota_date = {_placeholder(5)}"
                ),
                (count, limit_count, now, user_id, quota_type, quota_date),
            )
            return self._select_daily_quota_row(
                cursor,
                user_id=user_id,
                quota_type=quota_type,
                quota_date=quota_date,
            )

    def upsert_pdf_direct_snapshot(
        self,
        *,
        user_id: str,
        unused_num_integral: Optional[int],
        status: str,
        source: str,
        fetched_at: Optional[datetime],
    ) -> dict[str, Any]:
        now = _utc_now_naive()
        fetched_value = _to_naive_utc(fetched_at) if fetched_at is not None else None
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"select user_id from niutrans_balance_snapshots where user_id = {_placeholder(0)}",
                (user_id,),
            )
            if _fetchone(cursor):
                cursor.execute(
                    (
                        "update niutrans_balance_snapshots "
                        f"set unused_num_integral = {_placeholder(0)}, "
                        f"status = {_placeholder(1)}, source = {_placeholder(2)}, "
                        f"fetched_at = {_placeholder(3)}, updated_at = {_placeholder(4)} "
                        f"where user_id = {_placeholder(5)}"
                    ),
                    (unused_num_integral, status, source, fetched_value, now, user_id),
                )
            else:
                cursor.execute(
                    (
                        "insert into niutrans_balance_snapshots "
                        "(user_id, unused_num_integral, status, source, fetched_at, updated_at) "
                        f"values ({_placeholders(6)})"
                    ),
                    (user_id, unused_num_integral, status, source, fetched_value, now),
                )
            return self.get_pdf_direct_snapshot_for_user_with_cursor(cursor, user_id)

    def get_pdf_direct_snapshot_for_user(self, user_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            return self.get_pdf_direct_snapshot_for_user_with_cursor(cursor, user_id)

    def get_pdf_direct_snapshot_for_user_with_cursor(self, cursor, user_id: str) -> Optional[dict[str, Any]]:
        cursor.execute(
            (
                "select user_id, unused_num_integral, status, source, fetched_at, updated_at "
                f"from niutrans_balance_snapshots where user_id = {_placeholder(0)} limit 1"
            ),
            (user_id,),
        )
        return _fetchone(cursor)

    def _ensure_daily_quota_row(
        self,
        cursor,
        *,
        user_id: str,
        quota_type: str,
        quota_date: str,
        limit_count: int,
        now: datetime,
    ) -> None:
        dialect = get_database_dialect()
        if dialect == "sqlite":
            cursor.execute(
                (
                    "insert or ignore into user_daily_quotas "
                    "(user_id, quota_type, quota_date, limit_count, used_count, created_at, updated_at) "
                    f"values ({_placeholders(7)})"
                ),
                (user_id, quota_type, quota_date, limit_count, 0, now, now),
            )
        else:
            cursor.execute(
                (
                    "insert ignore into user_daily_quotas "
                    "(user_id, quota_type, quota_date, limit_count, used_count, created_at, updated_at) "
                    f"values ({_placeholders(7)})"
                ),
                (user_id, quota_type, quota_date, limit_count, 0, now, now),
            )
        cursor.execute(
            (
                "update user_daily_quotas "
                f"set limit_count = {_placeholder(0)}, updated_at = {_placeholder(1)} "
                f"where user_id = {_placeholder(2)} "
                f"and quota_type = {_placeholder(3)} "
                f"and quota_date = {_placeholder(4)}"
            ),
            (limit_count, now, user_id, quota_type, quota_date),
        )

    def _select_daily_quota_row(
        self,
        cursor,
        *,
        user_id: str,
        quota_type: str,
        quota_date: str,
    ) -> dict[str, Any]:
        cursor.execute(
            (
                "select user_id, quota_type, quota_date, limit_count, used_count, created_at, updated_at "
                f"from user_daily_quotas where user_id = {_placeholder(0)} "
                f"and quota_type = {_placeholder(1)} "
                f"and quota_date = {_placeholder(2)} limit 1"
            ),
            (user_id, quota_type, quota_date),
        )
        row = _fetchone(cursor)
        if row is None:
            raise RuntimeError("daily quota row was not created")
        return row


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(microsecond=0)
    return value.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)
