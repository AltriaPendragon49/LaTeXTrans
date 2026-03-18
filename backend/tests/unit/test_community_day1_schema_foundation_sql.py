from pathlib import Path


MIGRATION_DIR = Path("backend/migrations")
FILES = {
    "papers": MIGRATION_DIR / "20260318_create_papers_and_assets.sql",
    "interactions": MIGRATION_DIR / "20260318_create_interaction_tables.sql",
    "moderation": MIGRATION_DIR / "20260318_create_moderation_tables.sql",
    "refinements": MIGRATION_DIR / "20260318_refine_day1_policy_and_index_guards.sql",
}


def _normalized_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_day1_migration_files_exist():
    for path in FILES.values():
        assert path.exists(), f"expected migration file to exist: {path}"


def test_day1_declares_all_required_tables():
    combined = "\n".join(_normalized_sql(path) for path in FILES.values())

    required_tables = [
        "create table if not exists public.papers",
        "create table if not exists public.paper_assets",
        "create table if not exists public.paper_likes",
        "create table if not exists public.paper_favorites",
        "create table if not exists public.comments",
        "create table if not exists public.reports",
        "create table if not exists public.moderation_actions",
        "create table if not exists public.notifications",
        "create table if not exists public.user_roles",
        "create table if not exists public.user_bans",
    ]

    for table_stmt in required_tables:
        assert table_stmt in combined


def test_day1_declares_key_columns_and_constraints():
    papers_sql = _normalized_sql(FILES["papers"])
    interactions_sql = _normalized_sql(FILES["interactions"])
    moderation_sql = _normalized_sql(FILES["moderation"])

    assert "source text not null check (source in ('upload', 'arxiv'))" in papers_sql
    assert "visibility text not null default 'public' check (visibility in ('public', 'hidden'))" in papers_sql
    assert "status text not null default 'draft' check (status in ('draft', 'published', 'removed'))" in papers_sql
    assert "trans_status text not null default 'not_started'" in papers_sql
    assert "authors jsonb not null default '[]'::jsonb" in papers_sql
    assert "categories text[] not null default '{}'::text[]" in papers_sql
    assert "primary key (paper_id, user_id)" in interactions_sql
    assert "status text not null default 'visible' check (status in ('visible', 'hidden', 'deleted'))" in interactions_sql
    assert "target_type text not null check (target_type in ('paper', 'comment'))" in moderation_sql
    assert "action_type text not null check (action_type in ('hide', 'unhide', 'ban_user', 'dismiss_report', 'resolve_report'))" in moderation_sql
    assert "role text not null check (role in ('admin', 'moderator'))" in moderation_sql


def test_day1_declares_required_indexes():
    combined = "\n".join(_normalized_sql(path) for path in FILES.values())

    required_indexes = [
        "create unique index if not exists papers_arxiv_id_unique_idx",
        "create index if not exists papers_created_at_desc_idx",
        "create index if not exists papers_visibility_status_created_at_idx",
        "create index if not exists papers_trans_status_created_at_idx",
        "create index if not exists papers_created_by_idx",
        "create index if not exists paper_assets_paper_latest_idx",
        "create index if not exists paper_assets_paper_id_idx",
        "create index if not exists paper_likes_user_id_idx",
        "create index if not exists paper_favorites_user_id_idx",
        "create index if not exists comments_paper_created_at_idx",
        "create index if not exists comments_user_id_idx",
        "create index if not exists reports_status_created_at_idx",
        "create index if not exists reports_reported_by_idx",
        "create index if not exists notifications_user_created_at_idx",
        "create index if not exists user_bans_user_id_idx",
        "create index if not exists comments_parent_id_idx",
        "create index if not exists user_bans_created_by_idx",
    ]

    for index_stmt in required_indexes:
        assert index_stmt in combined


def test_day1_enables_rls_on_all_new_tables():
    combined = "\n".join(_normalized_sql(path) for path in FILES.values())

    for table_name in [
        "public.papers",
        "public.paper_assets",
        "public.paper_likes",
        "public.paper_favorites",
        "public.comments",
        "public.reports",
        "public.moderation_actions",
        "public.notifications",
        "public.user_roles",
        "public.user_bans",
    ]:
        assert f"alter table {table_name} enable row level security;" in combined


def test_day1_declares_helper_functions_and_policies():
    combined = "\n".join(_normalized_sql(path) for path in FILES.values())

    required_fragments = [
        "create or replace function public.current_user_is_admin()",
        "create or replace function public.current_user_is_banned()",
        "create policy papers_public_read_anon",
        "create policy papers_select_authenticated",
        "create policy papers_admin_update_all",
        "create policy paper_assets_admin_read_all",
        "create policy paper_likes_select_own",
        "create policy paper_likes_insert_own",
        "create policy paper_likes_delete_own",
        "create policy paper_favorites_select_own",
        "create policy paper_favorites_insert_own",
        "create policy paper_favorites_delete_own",
        "create policy comments_public_read_anon",
        "create policy comments_select_authenticated",
        "create policy comments_insert_own",
        "create policy comments_update_authenticated",
        "create policy comments_delete_own",
        "create policy reports_select_authenticated",
        "create policy reports_insert_own",
        "create policy reports_admin_update_all",
        "create policy moderation_actions_admin_all",
        "create policy notifications_select_own",
        "create policy notifications_update_read_at_own",
        "create policy user_roles_select_authenticated",
        "create policy user_roles_admin_insert_all",
        "create policy user_roles_admin_update_all",
        "create policy user_roles_admin_delete_all",
        "create policy user_bans_admin_manage_all",
    ]

    for fragment in required_fragments:
        assert fragment in combined
