## Purpose

This rollout note defines the local-first migration window, rollback triggers, and backup expectations for replacing Supabase runtime dependencies with NiuTrans-backed auth and MySQL persistence.

Detailed importer execution and backout guidance for this change is maintained in `docs/import-source-rollout-backout.md`.

## Migration Window

The rollout window for this change is the local validation phase only.

- perform migration against a local MySQL instance
- run migration in `dry-run` mode first
- capture validation output before any write mode import
- switch local runtime to MySQL-backed auth and persistence only after schema setup and import validation both pass

Recommended local sequence:

1. Export or snapshot current local working state
2. Run schema migrations
3. Run migration `dry-run`
4. Review mapping and path-validation reports
5. Run migration write mode
6. Start backend and frontend against local MySQL
7. Execute local acceptance checks

## Data Backup

Backups are mandatory before write-mode migration.

- create a MySQL dump or snapshot before each write-mode import attempt
- preserve the source export used for the run
- preserve local file directories referenced by migrated rows, especially task outputs and community paper assets
- store migration logs and validation reports alongside the backup set for that run

Minimum backup set:

- local MySQL pre-import dump
- Supabase source export snapshot
- local asset directories or a filesystem snapshot

## Rollback Trigger

Rollback should happen immediately if any of the following occurs during local validation:

- imported row counts diverge from expected counts without an explained exception set
- ownership mapping is incorrect for authenticated history, settings, or community-agent data
- critical file-path references fail for migrated paper assets or task outputs
- login succeeds upstream but local session issuance or bootstrap is inconsistent
- protected routes allow unauthorized access or deny authorized access due to policy errors

## Rollback Procedure

1. Stop local services that point at the migrated MySQL state.
2. Restore MySQL from the most recent pre-import dump or snapshot.
3. Revert local runtime env to the last known-good configuration if needed.
4. Fix mapping, policy, or schema issues.
5. Re-run migration in `dry-run` mode before the next write-mode attempt.

## Exit Criteria For Local Rollout

The local migration window can be considered complete only when:

- auth bootstrap works with local JWT/session handling
- guest translation still works
- authenticated history and settings work
- community paper display and community-agent persistence work
- migration verification reports pass without unresolved critical issues
