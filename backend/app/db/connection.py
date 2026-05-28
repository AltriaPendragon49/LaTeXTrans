"""数据库连接模块，支持 MySQL 和 SQLite 两种数据库方言"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator, Literal
from urllib.parse import parse_qs, urlparse

from backend.app.core.config import get_settings

# 数据库类型
DatabaseDialect = Literal["mysql", "sqlite"]


class DatabaseUnavailableError(RuntimeError):
    """当需要本地持久化但数据库未配置时抛出"""


def get_database_dialect() -> DatabaseDialect:
    """从 DATABASE_URL 判断当前使用的数据库方言（mysql 或 sqlite）"""
    database_url = str(get_settings().database_url or "").strip()
    if database_url.startswith("sqlite://"):
        return "sqlite"
    return "mysql"


@contextmanager
def db_connection(*, commit: bool = False) -> Iterator[object]:
    """创建数据库连接的上下文管理器，自动处理事务提交/回滚和连接关闭

    参数：
        commit: 是否在退出时自动提交事务

    生成：
        数据库连接对象（sqlite3.Connection 或 pymysql.Connection）

    抛出：
        DatabaseUnavailableError: 如果 DATABASE_URL 未配置或 PyMySQL 未安装
    """
    settings = get_settings()
    database_url = str(settings.database_url or "").strip()
    if not database_url:
        raise DatabaseUnavailableError("DATABASE_URL is not configured")

    parsed = urlparse(database_url)
    dialect = get_database_dialect()

    if dialect == "sqlite":
        sqlite_path = parsed.path or ""
        # 处理 Windows 路径（如 /C:/... 的 URL 格式）
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
    except ImportError as exc:  # pragma: no cover - 取决于本地环境
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
