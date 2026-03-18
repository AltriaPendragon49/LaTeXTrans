## 1. OpenSpec And Design
- [x] 1.1 Update `proposal.md` to reflect additive-only Supabase MCP execution on the main project.
- [x] 1.2 Add `design.md` with schema, RLS, migration-order, and rollback constraints.
- [x] 1.3 Expand the Day 1 delta spec to freeze entity inventory, indexes, RLS boundaries, and page boundaries.

## 2. SQL Migrations
- [x] 2.1 Add `backend/migrations/20260318_create_papers_and_assets.sql` for `papers`, `paper_assets`, indexes, and baseline RLS.
- [x] 2.2 Add `backend/migrations/20260318_create_interaction_tables.sql` for likes, favorites, comments, indexes, and self-owned interaction policies.
- [x] 2.3 Add `backend/migrations/20260318_create_moderation_tables.sql` for reports, moderation, notifications, roles, bans, helper functions, and admin policies.
- [x] 2.4 Add a follow-up additive migration for advisor-driven index and policy refinements on newly created Day 1 tables only.

## 3. Repository Validation
- [x] 3.1 Add `backend/tests/unit/test_community_day1_schema_foundation_sql.py` to verify tables, indexes, helper functions, and RLS declarations.
- [x] 3.2 Run `pytest backend/tests/unit/test_community_day1_schema_foundation_sql.py`.
- [x] 3.3 Run `openspec validate add-community-day-01-schema-rls-foundation --strict --no-interactive`.

## 4. Supabase MCP Application
- [x] 4.1 Verify the target project state before applying Day 1 migrations.
- [x] 4.2 Apply the papers/assets migration to Supabase.
- [x] 4.3 Apply the interaction migration to Supabase.
- [x] 4.4 Apply the moderation migration to Supabase.
- [x] 4.5 Verify remote tables, indexes, policies, and migration registration with Supabase MCP.
- [x] 4.6 Run Supabase security and performance advisors for the new schema.

## 5. Status Sync
- [x] 5.1 Mark every completed task in this checklist.
- [x] 5.2 Update `texts/社区打造十天OpenSpec执行索引.md` only after repository validation and Supabase verification are complete.
