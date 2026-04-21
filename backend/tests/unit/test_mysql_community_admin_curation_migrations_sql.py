from pathlib import Path


CURATION_MIGRATION = Path("backend/migrations_mysql/20260411_0002_community_admin_curation_flow.sql")
ASSET_ID_EXPANSION_MIGRATION = Path("backend/migrations_mysql/20260411_0003_expand_paper_asset_id_columns.sql")
CONTENT_BACKFILL_MIGRATION = Path("backend/migrations_mysql/20260411_0004_add_content_column_to_community_structured_insights.sql")
SIMILAR_RECOMMENDATIONS_MIGRATION = Path("backend/migrations_mysql/20260412_0005_add_community_similar_recommendations.sql")
RETENTION_MIGRATION = Path("backend/migrations_mysql/20260419_0006_admin_curation_retention_fields.sql")
TERMINAL_REASON_MIGRATION = Path("backend/migrations_mysql/20260421_0007_admin_curation_terminal_reasons.sql")


def _normalized_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_mysql_admin_curation_migration_declares_required_tables() -> None:
    sql = _normalized_sql(CURATION_MIGRATION)
    required_fragments = [
        "create table if not exists community_structured_insights",
        "create table if not exists community_curation_jobs",
        "create table if not exists community_delete_jobs",
        "content mediumtext null",
    ]
    for fragment in required_fragments:
        assert fragment in sql
    assert "summary_en" not in sql
    assert "summary_zh" not in sql
    assert "bullets_en" not in sql
    assert "bullets_zh" not in sql
    assert "body_en" not in sql
    assert "body_zh" not in sql


def test_mysql_asset_id_expansion_migration_exists_and_alters_columns() -> None:
    assert ASSET_ID_EXPANSION_MIGRATION.exists()
    sql = _normalized_sql(ASSET_ID_EXPANSION_MIGRATION)
    assert "modify column trans_latest_asset_pdf_id varchar(255) null" in sql
    assert "modify column community_selected_asset_id varchar(255) null" in sql


def test_mysql_structured_insight_content_backfill_migration_exists_and_is_idempotent() -> None:
    assert CONTENT_BACKFILL_MIGRATION.exists()
    sql = _normalized_sql(CONTENT_BACKFILL_MIGRATION)
    assert "information_schema.columns" in sql
    assert "table_name = 'community_structured_insights'" in sql
    assert "column_name = 'content'" in sql
    assert "alter table community_structured_insights add column content mediumtext null after section_key" in sql


def test_mysql_similar_recommendations_migration_exists_and_declares_required_columns() -> None:
    assert SIMILAR_RECOMMENDATIONS_MIGRATION.exists()
    sql = _normalized_sql(SIMILAR_RECOMMENDATIONS_MIGRATION)
    assert "create table if not exists community_similar_recommendations" in sql
    assert "paper_id varchar(64) not null" in sql
    assert "position int not null" in sql
    assert "abstract mediumtext not null" in sql
    assert "community_paper_id varchar(64) null" in sql
    assert "foreign key (paper_id) references papers(id)" in sql


def test_mysql_admin_curation_retention_migration_exists_and_declares_required_columns() -> None:
    assert RETENTION_MIGRATION.exists()
    sql = _normalized_sql(RETENTION_MIGRATION)
    assert "alter table community_curation_jobs" in sql
    assert "terminal_task_status varchar(32) null" in sql
    assert "failed_artifact_path text null" in sql
    assert "artifact_storage_backend varchar(32) null" in sql
    assert "published_paper_id varchar(64) null" in sql


def test_mysql_admin_curation_terminal_reason_migration_exists_and_declares_required_columns() -> None:
    assert TERMINAL_REASON_MIGRATION.exists()
    sql = _normalized_sql(TERMINAL_REASON_MIGRATION)
    assert "table_name = 'community_curation_jobs'" in sql
    assert "column_name = 'terminal_reason'" in sql
    assert "column_name = 'timeout_reason'" in sql
    assert "alter table community_curation_jobs add column terminal_reason varchar(64) null after terminal_task_status" in sql
    assert "alter table community_curation_jobs add column timeout_reason varchar(64) null after terminal_reason" in sql
