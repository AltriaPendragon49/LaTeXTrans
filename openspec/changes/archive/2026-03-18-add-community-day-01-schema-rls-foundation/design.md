# Day 1 Community Schema/RLS Technical Design

## Summary
Day 1 establishes the database foundation for the 10-day community rollout on the existing Supabase project `LaTeXTrans` (`ebfojcotiztnjmxbktta`). The change is additive-only: it introduces new community tables, indexes, RLS policies, and helper functions while leaving the existing translation tables untouched.

This design intentionally freezes the paper-first data model before Day 2 APIs and Day 3+ UI changes begin. It uses repository migrations as the source of truth and applies the same SQL to Supabase through MCP so local artifacts and the deployed schema do not drift.

## Constraints
- The target Supabase project is the production/main project, not a development branch.
- Existing tables `public.translation_tasks` and `public.user_settings` must not be altered.
- Only additive operations are allowed:
  - `create table if not exists`
  - `create index if not exists`
  - `create or replace function`
  - `drop policy if exists` followed by `create policy`
- New tables may be adjusted by later migrations, but no destructive rollback is planned for this change.
- The change defines schema and permission foundations only. It does not add community API routes, frontend routes, or counter-maintenance triggers.

## Existing Database Baseline
The target project currently exposes only these application-facing `public` tables for the relevant domain:
- `public.translation_tasks`
- `public.user_settings`

Remote migration history already includes the task metadata and settings migrations required by the current translation product. Day 1 must remain compatible with this baseline and avoid coupling itself to existing production rows.

## Data Model
### `public.papers`
Purpose:
- Canonical community object for uploaded or arXiv-imported papers
- Stable anchor for later feed, detail, translation, and interaction APIs

Key columns:
- Identity and source: `id`, `source`, `arxiv_id`
- Content summary: `title`, `authors`, `categories`, `abstract_raw`, `abstract_translated`
- Governance and state: `visibility`, `status`, `trans_status`
- Ownership and integration: `created_by`, `trans_latest_task_id`, `trans_latest_asset_pdf_id`
- Denormalized counters: `like_count`, `favorite_count`, `comment_count`, `view_count`, `download_count`
- Audit timestamps: `created_at`, `updated_at`

Compatibility:
- `trans_latest_task_id` remains a soft text reference to the existing `translation_tasks.task_id`.
- `trans_latest_asset_pdf_id` is introduced as a nullable future pointer without enforcing an initial FK in Day 1.

### `public.paper_assets`
Purpose:
- Canonical storage metadata for source archives and translated/preview assets

Key columns:
- Identity and linkage: `id`, `paper_id`, `task_id`
- Asset metadata: `asset_type`, `storage_backend`, `file_path`, `file_name`, `mime_type`
- Current-version marker: `is_latest`
- Audit timestamp: `created_at`

### `public.paper_likes`
Purpose:
- One-row-per-user-per-paper like relation

### `public.paper_favorites`
Purpose:
- One-row-per-user-per-paper favorite relation

### `public.comments`
Purpose:
- Flat or threaded comments scoped to a paper

Key columns:
- Identity and linkage: `id`, `paper_id`, `user_id`, `parent_id`
- Content and moderation state: `content`, `status`
- Audit timestamps: `created_at`, `updated_at`

### `public.reports`
Purpose:
- User-submitted moderation reports for papers or comments

### `public.moderation_actions`
Purpose:
- Immutable moderation audit trail for hide/unhide/ban/report actions

### `public.notifications`
Purpose:
- Minimal notification queue for later day changes

### `public.user_roles`
Purpose:
- Database-level source of truth for admin/moderator privileges

### `public.user_bans`
Purpose:
- Active or expiring user bans used by moderation and future write guards

## Index Plan
The design includes indexes for:
- feed reads (`papers_created_at_desc_idx`, `papers_visibility_status_created_at_idx`, `papers_trans_status_created_at_idx`)
- ownership filters (`papers_created_by_idx`, `paper_likes_user_id_idx`, `paper_favorites_user_id_idx`, `comments_user_id_idx`, `reports_reported_by_idx`, `notifications_user_created_at_idx`, `user_bans_user_id_idx`)
- FK access and cascades (`paper_assets_paper_id_idx`, `paper_assets_paper_latest_idx`, `comments_paper_created_at_idx`)
- uniqueness and filtered lookup (`papers_arxiv_id_unique_idx`)

This follows Supabase/Postgres guidance to index RLS filter columns and foreign keys.

## RLS and Authorization Model
### General rules
- Enable RLS on every new `public` table.
- Use `(select auth.uid())` inside policies to align with Supabase performance guidance.
- Use `security definer` helper functions for complex role and ban checks.
- Reserve protected-object writes for service role or authenticated admins only.

### End-user write boundaries
- Users can write only self-owned interaction records:
  - `paper_likes`
  - `paper_favorites`
  - `comments`
  - `reports`
- Users can read only their own `notifications`, `reports`, and `user_roles`.
- Users cannot directly insert or update `papers`, `paper_assets`, `moderation_actions`, or `user_bans`.

### Admin boundaries
- Admin/moderator status is determined from `public.user_roles`.
- Admins can:
  - read and update all `reports`
  - read and update all `comments`
  - read and update all `papers`
  - manage `moderation_actions`, `user_roles`, and `user_bans`
- Admin checks use `public.current_user_is_admin()`.

### Service-role boundaries
- Service role writes bypass RLS for protected flows such as:
  - paper creation and protected field updates
  - asset registration
  - moderation writes
  - notification fan-out

## Helper Functions
### `public.current_user_is_admin()`
Implementation:
- `security definer`
- `stable`
- `search_path = ''`
- Returns `true` when `(select auth.uid())` has role `admin` or `moderator` in `public.user_roles`

### `public.current_user_is_banned()`
Implementation:
- `security definer`
- `stable`
- `search_path = ''`
- Returns `true` when `(select auth.uid())` has an active row in `public.user_bans` whose `expires_at` is null or in the future

## Migration Layout
### `backend/migrations/20260318_create_papers_and_assets.sql`
Creates:
- `public.papers`
- `public.paper_assets`
- indexes for both tables
- baseline RLS enablement
- public read policy for `papers`

### `backend/migrations/20260318_create_interaction_tables.sql`
Creates:
- `public.paper_likes`
- `public.paper_favorites`
- `public.comments`
- indexes for these tables
- baseline RLS enablement
- self-owned user policies and public comment-read policy

### `backend/migrations/20260318_create_moderation_tables.sql`
Creates:
- `public.reports`
- `public.moderation_actions`
- `public.notifications`
- `public.user_roles`
- `public.user_bans`
- indexes for these tables
- helper functions
- RLS enablement
- admin/self policies
- admin expansion policies on `papers`, `comments`, and `reports`

### `backend/migrations/20260318_refine_day1_policy_and_index_guards.sql`
Creates only additive refinements on Day 1 tables:
- missing FK indexes discovered by advisors
- a minimal admin read policy for `paper_assets`
- consolidated authenticated policies to reduce multiple-permissive-policy warnings on `papers`, `comments`, `reports`, and `user_roles`

## MCP Application Order
Apply the migrations to Supabase in this order:
1. `create_papers_and_assets_day1`
2. `create_interaction_tables_day1`
3. `create_moderation_tables_day1`
4. `refine_day1_policy_and_index_guards`

## Verification Strategy
### Repository-side
- Add a dedicated SQL contract test that reads the migration files and asserts:
  - required tables are declared
  - required indexes are present
  - required helper functions are present
  - required policies and `enable row level security` statements exist
- Run `pytest backend/tests/unit/test_community_day1_schema_foundation_sql.py`
- Run `openspec validate add-community-day-01-schema-rls-foundation --strict --no-interactive`

### Supabase-side
- Use MCP `apply_migration` for each SQL file
- Verify table metadata with `list_tables`
- Verify indexes and policies with `execute_sql`
- Verify migration registration with `list_migrations`
- Run advisors:
  - `security`
  - `performance`

## Rollback and Failure Handling
- There is no destructive rollback in this change because it targets the main project.
- If one migration fails:
  - stop the sequence immediately
  - inspect created objects
  - fix the SQL in repo
  - apply only additive follow-up changes to the newly created objects
- Existing translation tables are never part of rollback scope.

## Out of Scope
- Day 2 paper APIs
- Day 3/4 frontend route wiring
- counters or view/download triggers
- backfill from `translation_tasks`
- storage bucket changes
- notification delivery logic
