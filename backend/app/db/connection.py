from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator, Literal
from urllib.parse import parse_qs, urlparse

from backend.app.core.config import get_settings

DatabaseDialect = Literal["mysql", "sqlite"]


class DatabaseUnavailableError(RuntimeError):
    """Raised when local persistence is required but not configured."""


def get_database_dialect() -> DatabaseDialect:
    database_url = str(get_settings().database_url or "").strip()
    if database_url.startswith("sqlite://"):
        return "sqlite"
    return "mysql"


@contextmanager
def db_connection(*, commit: bool = False) -> Iterator[object]:
    settings = get_settings()
    database_url = str(settings.database_url or "").strip()
    if not database_url:
        raise DatabaseUnavailableError("DATABASE_URL is not configured")

    parsed = urlparse(database_url)
    dialect = get_database_dialect()

    if dialect == "sqlite":
        sqlite_path = parsed.path or ""
        if sqlite_path.startswith("/") and sqlite_path[2:3] == ":":
            sqlite_path = sqlite_path[1:]
        if not sqlite_path:
            sqlite_path = ":memory:"

        connection = sqlite3.connect(sqlite_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
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
        return

    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise DatabaseUnavailableError(
            "PyMySQL is required for MySQL-backed local auth. Install backend requirements first."
        ) from exc

    query = parse_qs(parsed.query or "")
    connect_timeout = int((query.get("connect_timeout") or ["10"])[0])
    connection = pymysql.connect(
        host=parsed.hostname or "127.0.0.1",
        port=int(parsed.port or 3306),
        user=parsed.username or "",
        password=parsed.password or "",
        database=(parsed.path or "/").lstrip("/"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=connect_timeout,
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
