from pathlib import Path


MIGRATION_PATH = Path("backend/migrations_mysql/20260421_0008_community_paper_engagement.sql")


def _normalized_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8").lower()


def test_mysql_engagement_migration_exists() -> None:
    assert MIGRATION_PATH.exists()


def test_mysql_engagement_migration_declares_required_tables() -> None:
    sql = _normalized_sql()
    required_fragments = [
        "create table if not exists favorite_folders",
        "create table if not exists favorite_folder_papers",
        "create table if not exists paper_daily_views",
    ]
    for fragment in required_fragments:
        assert fragment in sql


def test_mysql_engagement_migration_declares_uniques_indexes_and_foreign_keys() -> None:
    sql = _normalized_sql()
    required_fragments = [
        "unique key uq_favorite_folders_user_name (user_id, name)",
        "unique key uq_favorite_folder_papers_folder_paper (folder_id, paper_id)",
        "unique key uq_paper_daily_views_dedupe (paper_id, view_date, principal_type, principal_key)",
        "key idx_favorite_folders_user_updated (user_id, updated_at)",
        "key idx_favorite_folder_papers_paper_id (paper_id)",
        "key idx_paper_daily_views_lookup (paper_id, view_date)",
        "constraint fk_favorite_folders_user_id",
        "constraint fk_favorite_folder_papers_folder_id",
        "constraint fk_favorite_folder_papers_paper_id",
        "constraint fk_paper_daily_views_paper_id",
    ]
    for fragment in required_fragments:
        assert fragment in sql
