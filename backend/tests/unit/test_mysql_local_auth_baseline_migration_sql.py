from pathlib import Path


MIGRATION_PATH = Path("backend/migrations_mysql/20260409_0001_local_auth_mysql.sql")


def _normalized_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8").lower()


def test_mysql_baseline_migration_exists() -> None:
    assert MIGRATION_PATH.exists()


def test_mysql_baseline_declares_required_tables() -> None:
    sql = _normalized_sql()
    required_fragments = [
        "create table if not exists users",
        "create table if not exists user_roles",
        "create table if not exists auth_sessions",
        "create table if not exists user_settings",
        "create table if not exists translation_tasks",
        "create table if not exists papers",
        "create table if not exists paper_assets",
        "create table if not exists paper_likes",
        "create table if not exists paper_favorites",
        "create table if not exists comments",
        "create table if not exists reports",
        "create table if not exists moderation_actions",
        "create table if not exists community_agent_conversations",
        "create table if not exists community_agent_runs",
        "create table if not exists community_agent_events",
    ]
    for fragment in required_fragments:
        assert fragment in sql


def test_mysql_baseline_declares_key_uniques_indexes_and_foreign_keys() -> None:
    sql = _normalized_sql()
    required_fragments = [
        "unique key uq_users_provider_external (external_provider, external_user_id)",
        "key idx_auth_sessions_user_status (user_id, status)",
        "key idx_translation_tasks_user_created (user_id, created_at)",
        "key idx_papers_visibility_status_created (visibility, status, created_at)",
        "key idx_paper_assets_paper_type_latest (paper_id, asset_type, is_latest, created_at)",
        "key idx_paper_likes_user_id_paper_id (user_id, paper_id)",
        "key idx_paper_favorites_user_id_paper_id (user_id, paper_id)",
        "key idx_comments_paper_created (paper_id, created_at)",
        "key idx_reports_target_status_created (target_type, target_id, status, created_at)",
        "key idx_moderation_actions_report_id_created (report_id, created_at)",
        "key idx_community_agent_conversations_user_updated (user_id, updated_at)",
        "unique key uq_community_agent_events_run_sequence (run_id, sequence_no)",
        "constraint fk_auth_sessions_user_id",
        "constraint fk_translation_tasks_user_id",
        "constraint fk_paper_assets_paper_id",
        "constraint fk_reports_paper_id",
        "constraint fk_moderation_actions_report_id",
        "constraint fk_community_agent_events_run_id",
    ]
    for fragment in required_fragments:
        assert fragment in sql
