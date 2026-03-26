from pathlib import Path


MIGRATION_PATH = Path("backend/migrations/20260326_create_community_content_pool_foundation.sql")


def _normalized_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8").lower()


def test_content_pool_foundation_migration_exists() -> None:
    assert MIGRATION_PATH.exists()


def test_content_pool_foundation_declares_candidate_and_job_tables() -> None:
    sql = _normalized_sql()

    assert "create table if not exists public.community_content_pool_candidates" in sql
    assert "create unique index if not exists community_content_pool_candidates_arxiv_id_idx" in sql
    assert "create table if not exists public.community_content_pool_jobs" in sql
    assert "create index if not exists community_content_pool_jobs_status_idx" in sql


def test_content_pool_foundation_declares_event_log_for_replayability() -> None:
    sql = _normalized_sql()

    assert "create table if not exists public.community_content_pool_job_events" in sql
    assert "payload jsonb not null default '{}'::jsonb" in sql
    assert "stage text not null" in sql
