## 1. Migration Tooling
- [x] 1.1 Add a dry-run-first operator script that inventories local production assets, current MySQL rows, and COS objects.
- [x] 1.2 Generate a migration manifest with upload targets, DB updates, orphan COS deletions, same-key conflicts, and local cleanup candidates.
- [x] 1.3 Add output-manifest backfill for historical ordinary-task output directories.
- [x] 1.4 Add idempotent upload support that skips same-size existing COS objects and reports size mismatches.
- [x] 1.5 Add guarded execution modes for COS orphan deletion, DB pointer updates, and local cleanup.
- [x] 1.6 Add tests for path normalization, manifest generation, output manifest backfill, and DB update planning.
- [x] 1.7 Update `backend/file.md` for any new backend production script.

## 2. Pre-Cutover Production Preparation
- [x] 2.1 Confirm maintenance window approval.
- [x] 2.2 Free minimal disk headroom using only approved disposable files or caches.
- [x] 2.3 Capture current disk, service, env, MySQL, and COS audit snapshots.
- [x] 2.4 Back up affected MySQL tables.

## 3. Cutover Execution
- [x] 3.1 Pause production writes by stopping worker and backend write traffic.
- [x] 3.2 Run migration dry-run and review manifest totals.
- [x] 3.3 Delete final-manifest-excluded COS orphan objects.
- [x] 3.4 Upload local durable assets to COS.
- [x] 3.5 Verify uploaded COS object counts and sizes.
- [x] 3.6 Apply MySQL pointer updates.
- [x] 3.7 Configure production backend and worker for `STORAGE_BACKEND_MODE=cos`.
- [x] 3.8 Restart services and confirm health.

## 4. Verification And Cleanup
- [x] 4.1 Verify representative public community paper list/detail/preview/PDF/source routes.
- [x] 4.2 Verify representative ordinary task PDF/source/log/terminology routes.
- [x] 4.3 Clear or remove migrated local asset directories according to the manifest.
- [x] 4.4 Repeat verification after local asset cleanup.
- [x] 4.5 Capture final disk usage, COS totals, DB storage-backend counts, and health checks.
- [x] 4.6 Archive or attach the final migration report.
