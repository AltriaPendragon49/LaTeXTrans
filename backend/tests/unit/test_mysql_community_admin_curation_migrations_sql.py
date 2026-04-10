from pathlib import Path


CURATION_MIGRATION = Path("backend/migrations_mysql/20260411_0002_community_admin_curation_flow.sql")
ASSET_ID_EXPANSION_MIGRATION = Path("backend/migrations_mysql/20260411_0003_expand_paper_asset_id_columns.sql")


def _normalized_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_mysql_admin_curation_migration_declares_required_tables() -> None:
    sql = _normalized_sql(CURATION_MIGRATION)
    required_fragments = [
        "create table if not exists community_structured_insights",
        "create table if not exists community_curation_jobs",
        "create table if not exists community_delete_jobs",
    ]
    for fragment in required_fragments:
        assert fragment in sql


def test_mysql_asset_id_expansion_migration_exists_and_alters_columns() -> None:
    assert ASSET_ID_EXPANSION_MIGRATION.exists()
    sql = _normalized_sql(ASSET_ID_EXPANSION_MIGRATION)
    assert "modify column trans_latest_asset_pdf_id varchar(255) null" in sql
    assert "modify column community_selected_asset_id varchar(255) null" in sql
