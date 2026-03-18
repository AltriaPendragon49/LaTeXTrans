# Why
- Day 1 must freeze the community domain model before APIs, pages, and interactions start moving in parallel.
- The two source planning documents already define the minimum object set, but they are not yet captured as an executable OpenSpec change.
- A foundation change is needed so later daily changes can inherit one schema, one permission matrix, and one page inventory without risking production drift.

## What Changes
- Define the MVP paper-first data contract for `papers`, `paper_assets`, `paper_likes`, `paper_favorites`, `comments`, `reports`, `moderation_actions`, `notifications`, `user_roles`, and `user_bans`.
- Define baseline RLS boundaries for end users, admins, and service role writes.
- Freeze the page boundary for `/`, `/paper/:paperId`, `/submit`, and `/admin/moderation` as the execution contract for Days 2-10.
- Apply additive-only SQL migrations for the new community tables to the existing Supabase project via MCP, without modifying `public.translation_tasks` or `public.user_settings`.
- Add a repo-side SQL contract test so the OpenSpec, migration files, and remote schema remain aligned.

## Impact
- Adds capability `community-schema-foundation`.
- Unblocks `add-community-day-02-paper-intake-and-feed-api` through `add-community-day-10-demo-assets-and-week3-backlog`.
- Changes the production schema by adding new community tables, indexes, helper functions, and RLS policies only for newly introduced tables.
- Preserves existing translation runtime tables unchanged and keeps `translation_tasks` integration as soft references for later daily changes.
