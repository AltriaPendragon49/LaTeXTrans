from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.scripts.mysql_script_connection import (
    describe_mysql_script_target,
    mysql_script_connection,
    resolve_mysql_script_config,
)


def _load_sql_files(migrations_dir: Path) -> list[Path]:
    return sorted(path for path in migrations_dir.glob("*.sql") if path.is_file())


def apply_migrations(*, dry_run: bool = False) -> None:
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations_mysql"
    sql_files = _load_sql_files(migrations_dir)
    if not sql_files:
        print(f"No MySQL migration files found in {migrations_dir}")
        return

    if resolve_mysql_script_config() is not None:
        print(f"Using dedicated {describe_mysql_script_target()} for migration connection")
    else:
        print(f"Using {describe_mysql_script_target()} for migration connection")

    for sql_file in sql_files:
        sql = sql_file.read_text(encoding="utf-8").strip()
        if not sql:
            continue
        print(f"Applying {sql_file.name}")
        if dry_run:
            continue
        with mysql_script_connection(commit=True) as connection:
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
