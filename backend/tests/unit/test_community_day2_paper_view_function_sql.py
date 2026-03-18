from pathlib import Path


MIGRATION_PATH = Path("backend/migrations/20260318_add_increment_paper_view_count_fn.sql")


def _normalized_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8").lower()


def test_day2_view_counter_function_migration_exists():
    assert MIGRATION_PATH.exists()


def test_day2_view_counter_function_is_atomic_rpc_contract():
    sql = _normalized_sql()

    assert "create or replace function public.increment_paper_view_count" in sql
    assert "returns table (view_count integer)" in sql
    assert "security definer" in sql
    assert "set search_path = ''" in sql
    assert "update public.papers" in sql
    assert "set view_count = public.papers.view_count + 1" in sql
    assert "status <> 'removed'" in sql
