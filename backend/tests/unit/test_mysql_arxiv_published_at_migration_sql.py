from pathlib import Path


MIGRATION_PATH = Path("backend/migrations_mysql/20260422_0009_add_arxiv_published_at.sql")


def test_mysql_arxiv_published_at_migration_exists() -> None:
    assert MIGRATION_PATH.exists()


def test_mysql_arxiv_published_at_migration_adds_paper_column() -> None:
    sql = MIGRATION_PATH.read_text(encoding="utf-8").lower()
    assert "alter table papers" in sql
    assert "add column if not exists arxiv_published_at datetime null" in sql
