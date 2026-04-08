"""Database helpers for local auth/MySQL-backed persistence."""

from backend.app.db.connection import DatabaseUnavailableError, db_connection, get_database_dialect

__all__ = ["DatabaseUnavailableError", "db_connection", "get_database_dialect"]
