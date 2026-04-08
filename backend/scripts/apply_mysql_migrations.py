from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.db import db_connection


def _load_sql_files(migrations_dir: Path) -> list[Path]:
    return sorted(path for path in migrations_dir.glob("*.sql") if path.is_file())


def apply_migrations(*, dry_run: bool = False) -> None:
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations_mysql"
    sql_files = _load_sql_files(migrations_dir)
    if not sql_files:
        print(f"No MySQL migration files found in {migrations_dir}")
        return

    for sql_file in sql_files:
        sql = sql_file.read_text(encoding="utf-8").strip()
        if not sql:
            continue
        print(f"Applying {sql_file.name}")
        if dry_run:
            continue
        with db_connection(commit=True) as connection:
            cursor = connection.cursor()
            for statement in [part.strip() for part in sql.split(";") if part.strip()]:
                cursor.execute(statement)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply local MySQL migrations.")
    parser.add_argument("--dry-run", action="store_true", help="Print migration order without executing SQL.")
    args = parser.parse_args()
    apply_migrations(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
