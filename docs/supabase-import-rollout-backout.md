# Supabase Export Import Rollout and Backout

## Scope

This note covers local migration/import runs using:

- `backend/scripts/import_supabase_to_mysql.py`
- Supabase-exported JSON row files
- local MySQL or SQLite target schema

Covered entities in this slice:

- `users`
- `user_roles`
- `user_settings`
- `translation_tasks`
- `papers`
- `paper_assets`
- `community_agent_conversations`
- `community_agent_runs`
- `community_agent_events`

## Rollout Steps

1. Prepare export files in one directory (for example `users.json`, `papers.json`).
2. Back up current local database.
3. Run dry-run first:
   `python backend/scripts/import_supabase_to_mysql.py --input-dir <export_dir> --dry-run --report-json <report_path>`
4. Review report for:
   - parse/validation errors
   - skipped rows
   - missing `paper_assets` file paths
5. Fix input issues, then run write mode:
   `python backend/scripts/import_supabase_to_mysql.py --input-dir <export_dir> --report-json <report_path> --fail-on-error`
6. Re-run the same command if needed; importer is upsert-based and repeatable.

## Backout Triggers

Back out immediately when any of the following happens:

- import report contains unresolved errors in write mode
- entity counts are unexpectedly lower than source counts
- key ownership fields are wrong (`user_id`, `created_by`, conversation ownership)
- critical `paper_assets` paths are missing and block expected local reading flows

## Backout Procedure

1. Stop services that use the migrated database.
2. Restore the pre-import backup.
3. Fix mapping/input data issues based on the report.
4. Re-run dry-run and confirm report quality before the next write run.

## Verification Checklist

- dry-run report archived with the run timestamp
- write-mode report archived with the run timestamp
- no unresolved row-level errors
- expected row visibility in history/settings/community flows
- missing asset report reviewed and triaged
