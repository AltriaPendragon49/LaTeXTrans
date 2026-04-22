from pathlib import Path


MIGRATION_PATH = Path("backend/migrations_mysql/20260422_0009_add_arxiv_published_at.sql")


def test_mysql_arxiv_published_at_migration_exists() -> None:
    assert MIGRATION_PATH.exists()


def test_mysql_arxiv_published_at_migration_adds_paper_column() -> None:
    sql = MIGRATION_PATH.read_text(encoding="utf-8").lower()
    assert "information_schema.columns" in sql
    assert "table_name = 'papers'" in sql
    assert "column_name = 'arxiv_published_at'" in sql
    assert "alter table papers add column arxiv_published_at datetime null after official_published_at" in sql
