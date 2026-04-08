from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from backend.app.core.config import get_settings
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


class AuthRepository:
    def __init__(self) -> None:
        self._settings = get_settings()

    def _ensure_admin_role_if_seeded(self, cursor, *, user_id: str, external_user_id: str) -> None:
        if external_user_id not in self._settings.local_admin_external_user_ids:
            return

        cursor.execute(
            f"select role from user_roles where user_id = {_placeholder(0)} and role = {_placeholder(1)}",
            (user_id, "admin"),
        )
        if cursor.fetchone():
            return

        cursor.execute(
            (
                "insert into user_roles (user_id, role, created_at) "
                f"values ({_placeholders(3)})"
            ),
            (user_id, "admin", _utc_now_naive()),
        )

    def get_user_by_id(self, user_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id, external_provider, external_user_id, email, display_name, token_version, status "
                    f"from users where id = {_placeholder(0)} limit 1"
                ),
                (user_id,),
            )
            user = _fetchone(cursor)
            if user is None:
                return None

            cursor.execute(
                f"select role from user_roles where user_id = {_placeholder(0)} order by role asc",
                (user_id,),
            )
            user["roles"] = [row["role"] for row in _fetchall(cursor)]
            return user

    def get_or_create_user(
        self,
        *,
        external_provider: str,
        external_user_id: str,
        email: Optional[str],
        display_name: Optional[str],
    ) -> dict[str, Any]:
        now = _utc_now_naive()
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id, external_provider, external_user_id, email, display_name, token_version, status "
                    f"from users where external_provider = {_placeholder(0)} and external_user_id = {_placeholder(1)} limit 1"
                ),
                (external_provider, external_user_id),
            )
            existing = _fetchone(cursor)
            if existing is None:
                user_id = f"usr_{uuid4().hex}"
                cursor.execute(
                    (
                        "insert into users (id, external_provider, external_user_id, email, display_name, token_version, status, created_at, updated_at) "
                        f"values ({_placeholders(9)})"
                    ),
                    (
                        user_id,
                        external_provider,
                        external_user_id,
                        email,
                        display_name,
                        1,
                        "active",
                        now,
                        now,
                    ),
                )
                cursor.execute(
                    (
                        "insert into user_roles (user_id, role, created_at) "
                        f"values ({_placeholders(3)})"
                    ),
                    (user_id, "user", now),
                )
                self._ensure_admin_role_if_seeded(
                    cursor,
                    user_id=user_id,
                    external_user_id=external_user_id,
                )
                roles = ["user"]
                if external_user_id in self._settings.local_admin_external_user_ids:
                    roles.append("admin")
                return {
                    "id": user_id,
                    "external_provider": external_provider,
                    "external_user_id": external_user_id,
                    "email": email,
                    "display_name": display_name,
                    "token_version": 1,
                    "status": "active",
                    "roles": roles,
                }

            cursor.execute(
                (
                    "update users set email = "
                    f"{_placeholder(0)}, display_name = {_placeholder(1)}, updated_at = {_placeholder(2)} "
                    f"where id = {_placeholder(3)}"
                ),
                (email, display_name, now, existing["id"]),
            )
            self._ensure_admin_role_if_seeded(
                cursor,
                user_id=existing["id"],
                external_user_id=external_user_id,
            )
            cursor.execute(
                f"select role from user_roles where user_id = {_placeholder(0)} order by role asc",
                (existing["id"],),
            )
            existing["roles"] = [row["role"] for row in _fetchall(cursor)]
            existing["email"] = email
            existing["display_name"] = display_name
            return existing

    def create_session(
        self,
        *,
        user_id: str,
        expires_at: datetime,
        client_ip: Optional[str],
        user_agent: Optional[str],
    ) -> str:
        session_id = f"ses_{uuid4().hex}"
        issued_at = _utc_now_naive()
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "insert into auth_sessions (id, user_id, status, issued_at, expires_at, revoked_at, last_seen_at, client_ip, user_agent) "
                    f"values ({_placeholders(9)})"
                ),
                (
                    session_id,
                    user_id,
                    "active",
                    issued_at,
                    expires_at.replace(tzinfo=None, microsecond=0),
                    None,
                    issued_at,
                    client_ip,
                    user_agent,
                ),
            )
        return session_id

    def get_active_session(self, session_id: str) -> Optional[dict[str, Any]]:
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id, user_id, status, issued_at, expires_at, revoked_at, last_seen_at, client_ip, user_agent "
                    f"from auth_sessions where id = {_placeholder(0)} limit 1"
                ),
                (session_id,),
            )
            session = _fetchone(cursor)
            if session is None:
                return None
            if session.get("status") != "active" or session.get("revoked_at") is not None:
                return None
            return session

    def mark_session_seen(self, session_id: str) -> None:
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update auth_sessions set last_seen_at = "
                    f"{_placeholder(0)} where id = {_placeholder(1)}"
                ),
                (_utc_now_naive(), session_id),
            )

    def revoke_session(self, session_id: str) -> None:
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update auth_sessions set status = "
                    f"{_placeholder(0)}, revoked_at = {_placeholder(1)} where id = {_placeholder(2)}"
                ),
                ("revoked", _utc_now_naive(), session_id),
            )
