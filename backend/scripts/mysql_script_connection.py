from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from backend.app.core.config import get_settings
from backend.app.db import db_connection


def resolve_mysql_script_config() -> dict[str, object] | None:
    settings = get_settings()
    host = str(settings.mysql_host or "").strip()
    user = str(settings.mysql_user or "").strip()
    database = str(settings.mysql_database or "").strip()
    password = str(settings.mysql_password or "")

    if not any([host, user, database, password, settings.mysql_port, settings.mysql_connect_timeout]):
        return None

    missing = [name for name, value in [("MYSQL_HOST", host), ("MYSQL_USER", user), ("MYSQL_DATABASE", database)] if not value]
    if missing:
        missing_names = ", ".join(missing)
        raise RuntimeError(
            "Dedicated MySQL script env is incomplete. "
            f"Set {missing_names}, or clear MYSQL_* and rely on DATABASE_URL."
        )

    return {
        "host": host,
        "port": int(settings.mysql_port or 3306),
        "user": user,
        "password": password,
        "database": database,
        "connect_timeout": int(settings.mysql_connect_timeout or 10),
    }


def describe_mysql_script_target() -> str:
    mysql_config = resolve_mysql_script_config()
    if mysql_config is None:
        return "configured DATABASE_URL"
    return (
        f"MYSQL_* env {mysql_config['user']}@{mysql_config['host']}:"
        f"{mysql_config['port']}/{mysql_config['database']}"
    )


@contextmanager
def mysql_script_connection(*, commit: bool = False) -> Iterator[object]:
    mysql_config = resolve_mysql_script_config()
    if mysql_config is None:
        with db_connection(commit=commit) as connection:
            yield connection
        return

    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise RuntimeError("PyMySQL is required for MySQL-backed script connections.") from exc

    connection = pymysql.connect(
        host=str(mysql_config["host"]),
        port=int(mysql_config["port"]),
        user=str(mysql_config["user"]),
        password=str(mysql_config["password"]),
        database=str(mysql_config["database"]),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=int(mysql_config["connect_timeout"]),
    )
    try:
        yield connection
        if commit:
            connection.commit()
    except Exception:
        if commit:
            connection.rollback()
        raise
    finally:
        connection.close()
