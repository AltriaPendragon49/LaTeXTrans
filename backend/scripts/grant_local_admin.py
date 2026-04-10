from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.scripts.mysql_script_connection import describe_mysql_script_target, mysql_script_connection


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _fetch_target_user(*, user_id: str | None, external_user_id: str | None, email: str | None) -> dict[str, object] | None:
    with mysql_script_connection(commit=False) as connection:
        cursor = connection.cursor()
        if user_id:
            cursor.execute(
                "select id, external_provider, external_user_id, email from users where id = %s limit 1",
                (user_id,),
            )
            return cursor.fetchone()
        if external_user_id:
            cursor.execute(
                (
                    "select id, external_provider, external_user_id, email "
                    "from users where external_provider = %s and external_user_id = %s limit 1"
                ),
                ("niutrans", external_user_id),
            )
            return cursor.fetchone()
        if email:
            cursor.execute(
                "select id, external_provider, external_user_id, email from users where email = %s limit 1",
                (email,),
            )
            return cursor.fetchone()
    return None


def grant_local_admin(*, user_id: str | None, external_user_id: str | None, email: str | None) -> None:
    target_user = _fetch_target_user(user_id=user_id, external_user_id=external_user_id, email=email)
    if not target_user:
        raise SystemExit(
            "Target local user was not found. Sign in once first so the local auth user record exists, "
            "then rerun this script."
        )

    with mysql_script_connection(commit=True) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "select role from user_roles where user_id = %s and role = %s limit 1",
            (target_user["id"], "admin"),
        )
        existing = cursor.fetchone()
        if existing:
            print(
                f"User {target_user['id']} already has admin role "
                f"(external_user_id={target_user.get('external_user_id')})."
            )
            return

        cursor.execute(
            "insert into user_roles (user_id, role, created_at) values (%s, %s, %s)",
            (target_user["id"], "admin", _utc_now_naive()),
        )

    print(
        f"Granted admin role to user {target_user['id']} "
        f"(external_user_id={target_user.get('external_user_id')}, email={target_user.get('email')})."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Grant a persistent local admin role in MySQL-backed auth.")
    parser.add_argument("--user-id", help="Local user id, for example usr_xxx.")
    parser.add_argument("--external-user-id", help="External NiuTrans user id, for example 458470.")
    parser.add_argument("--email", help="Local user email when available in users table.")
    args = parser.parse_args()

    supplied = [value for value in [args.user_id, args.external_user_id, args.email] if value]
    if len(supplied) != 1:
        raise SystemExit("Provide exactly one of --user-id, --external-user-id, or --email.")

    print(f"Using {describe_mysql_script_target()} for admin grant")
    grant_local_admin(
        user_id=args.user_id,
        external_user_id=args.external_user_id,
        email=args.email,
    )


if __name__ == "__main__":
    main()
