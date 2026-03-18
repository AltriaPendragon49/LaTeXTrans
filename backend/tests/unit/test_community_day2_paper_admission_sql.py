from pathlib import Path


MIGRATION_PATH = Path("backend/migrations/20260318_add_paper_community_admission_fields.sql")


def _normalized_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8").lower()


def test_day2_paper_admission_migration_exists():
    assert MIGRATION_PATH.exists()


def test_day2_paper_admission_declares_required_columns_and_indexes():
    sql = _normalized_sql()

    assert "alter table public.papers" in sql
    assert "add column if not exists community_status text not null default 'user_fallback'" in sql
    assert "check (community_status in ('official', 'user_fallback'))" in sql
    assert "add column if not exists community_selected_task_id text;" in sql
    assert "add column if not exists community_selected_asset_id uuid;" in sql
    assert "add column if not exists official_published_at timestamp with time zone;" in sql
    assert "create index if not exists papers_community_status_created_at_idx" in sql
    assert "create index if not exists papers_official_published_at_idx" in sql


def test_day2_paper_admission_does_not_touch_existing_history_tables():
    sql = _normalized_sql()

    assert "translation_tasks" not in sql
    assert "user_settings" not in sql
