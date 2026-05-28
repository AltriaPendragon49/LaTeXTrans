from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from backend.app.core.config import get_settings
from backend.app.db import db_connection, get_database_dialect


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


class AuthRepository:
    """认证相关的数据访问层，负责用户、会话和API密钥的增删改查操作。"""

    def __init__(self) -> None:
        """初始化认证仓库，加载应用配置信息。"""
        self._settings = get_settings()

    def _ensure_admin_role_if_seeded(self, cursor, *, user_id: str, external_user_id: str) -> None:
        """如果外部用户ID在预配置的管理员列表中，则确保该用户拥有admin角色。"""
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
        """根据用户ID获取用户信息及其角色列表。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id, external_provider, external_user_id, login_identifier, email, display_name, token_version, status "
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
        login_identifier: Optional[str],
        email: Optional[str],
        display_name: Optional[str],
    ) -> dict[str, Any]:
        """根据外部提供商信息查找用户，如果不存在则创建新用户并返回。"""
        now = _utc_now_naive()
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "select id, external_provider, external_user_id, login_identifier, email, display_name, token_version, status "
                    f"from users where external_provider = {_placeholder(0)} and external_user_id = {_placeholder(1)} limit 1"
                ),
                (external_provider, external_user_id),
            )
            existing = _fetchone(cursor)
            if existing is None:
                user_id = f"usr_{uuid4().hex}"
                cursor.execute(
                    (
                        "insert into users (id, external_provider, external_user_id, login_identifier, email, display_name, token_version, status, created_at, updated_at) "
                        f"values ({_placeholders(10)})"
                    ),
                    (
                        user_id,
                        external_provider,
                        external_user_id,
                        login_identifier,
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
                    "login_identifier": login_identifier,
                    "email": email,
                    "display_name": display_name,
                    "token_version": 1,
                    "status": "active",
                    "roles": roles,
                }

            cursor.execute(
                (
                    "update users set login_identifier = "
                    f"{_placeholder(0)}, email = {_placeholder(1)}, display_name = {_placeholder(2)}, updated_at = {_placeholder(3)} "
                    f"where id = {_placeholder(4)}"
                ),
                (login_identifier, email, display_name, now, existing["id"]),
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
            existing["login_identifier"] = login_identifier
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
        """为用户创建一个新的认证会话并返回会话ID。"""
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
        """根据会话ID获取当前有效的会话信息，已撤销或非活跃状态的会话返回None。"""
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
        """更新会话的最后活跃时间。"""
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
        """撤销指定的认证会话。"""
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update auth_sessions set status = "
                    f"{_placeholder(0)}, revoked_at = {_placeholder(1)} where id = {_placeholder(2)}"
                ),
                ("revoked", _utc_now_naive(), session_id),
            )

    def store_encrypted_apikey(self, user_id: str, encrypted_apikey: Optional[str]) -> None:
        """存储用户的加密API密钥。"""
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            cursor.execute(
                (
                    "update users set encrypted_apikey = "
                    f"{_placeholder(0)}, updated_at = {_placeholder(1)} where id = {_placeholder(2)}"
                ),
                (encrypted_apikey, _utc_now_naive(), user_id),
            )

    def get_encrypted_apikey(self, user_id: str) -> Optional[str]:
        """获取用户的加密API密钥。"""
        with db_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"select encrypted_apikey from users where id = {_placeholder(0)} limit 1",
                (user_id,),
            )
            row = _fetchone(cursor)
            if row is None:
                return None
            return row.get("encrypted_apikey")
