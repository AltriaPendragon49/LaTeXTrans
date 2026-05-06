from pathlib import Path


MIGRATION_PATH = Path("backend/migrations_mysql/20260507_0011_daily_translation_quotas.sql")


def _normalized_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8").lower()


def test_daily_translation_quota_migration_exists() -> None:
    assert MIGRATION_PATH.exists()


def test_daily_translation_quota_migration_declares_quota_and_balance_tables() -> None:
    sql = _normalized_sql()
    required_fragments = [
        "create table if not exists user_daily_quotas",
        "quota_type varchar(64) not null",
        "quota_date date not null",
        "limit_count int not null",
        "used_count int not null default 0",
        "primary key (user_id, quota_type, quota_date)",
        "key idx_user_daily_quotas_date_type (quota_date, quota_type)",
        "constraint fk_user_daily_quotas_user_id",
        "create table if not exists niutrans_balance_snapshots",
        "unused_num_integral int null",
        "status varchar(32) not null",
        "source varchar(32) not null",
        "primary key (user_id)",
        "constraint fk_niutrans_balance_snapshots_user_id",
    ]
    for fragment in required_fragments:
        assert fragment in sql


def test_daily_translation_quota_migration_has_used_count_guard() -> None:
    sql = _normalized_sql()

    assert "constraint chk_user_daily_quotas_nonnegative" in sql
    assert "used_count >= 0" in sql
    assert "limit_count >= 0" in sql
