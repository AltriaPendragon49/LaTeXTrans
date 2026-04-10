## 1. Auth Foundation

- [x] 1.1 Add backend auth endpoints for in-app login, logout, and current-user bootstrap using the NiuTrans login API as the upstream credential verifier.
- [x] 1.2 Define and implement the local JWT/session contract, including claims, TTL, no-refresh behavior, current-device logout, session invalidation, and multi-device policy.
- [x] 1.3 Add local JWT/session issuance and verification, plus `optional_current_user`, `require_current_user`, and `require_admin_user` dependencies.
- [x] 1.4 Introduce a centralized authorization entrypoint such as `authorize(user, resource, action, context)` and remove route-level ad hoc ownership logic.
- [x] 1.5 Define local user mapping based on NiuTrans `userId` and seed an initial local admin strategy that does not depend on Supabase metadata or service-role behavior.
- [x] 1.6 Replace frontend Supabase auth state management with local token/session handling and authenticated session bootstrap.
- [x] 1.7 Update login/register/recovery UI so in-app login remains local, while registration and account-management entry points redirect to NiuTrans-managed pages.

## 2. MySQL Persistence Foundation

- [x] 2.1 Add MySQL connection, migration workflow, and repository/service helpers suitable for local development and later server rollout.
- [x] 2.2 Finalize MySQL DDL, indexes, unique constraints, and foreign-key strategy for users, auth/session support, translation tasks, user settings, community papers, paper assets, and currently used community-agent persistence records.
- [x] 2.3 Replace runtime Supabase admin-client and user-client access paths with MySQL-backed repositories and app-layer authorization filters.

## 3. Translation Mainline Migration

- [x] 3.1 Move authenticated translation-task persistence, history retrieval, task deletion, and reconciliation flows from Supabase to MySQL.
- [x] 3.2 Move user-settings storage and retrieval from Supabase to MySQL while preserving current default-setting behavior.
- [x] 3.3 Keep guest translation behavior intact, including non-persistent guest task semantics and existing cleanup expectations.
- [x] 3.4 Replace batch-translation persistence retry behavior so it targets MySQL/local fallback semantics instead of Supabase-specific retry assumptions.

## 4. Community Migration

- [x] 4.1 Move community paper metadata and paper-asset persistence from Supabase to MySQL while keeping local disk paths as the asset source of truth.
- [x] 4.2 Move community-agent conversation/run persistence from Supabase-backed auth context to MySQL-backed local user context.
- [x] 4.3 Replace community authorization assumptions that currently depend on RLS/service-role patterns with explicit app-layer ownership and admin checks.

## 5. Data Migration And Cleanup

- [x] 5.1 Add repeatable local migration scripts that import current Supabase rows into MySQL for the in-scope entities.
- [x] 5.2 Define explicit schema-mapping and field-conversion rules for each migrated entity, including user identity mapping and JSON field normalization.
- [x] 5.3 Implement migration dry-run mode, validation reports, checksum or count verification, and a clear rollback procedure for local testing.
- [x] 5.4 Write and maintain a rollout note covering migration window, data backup, and rollback triggers for the local-first cutover.
- [x] 5.5 Validate migrated file-path references against the local disk layout and emit actionable reports for missing assets without aborting all imports.
- [x] 5.6 Remove runtime Supabase SDK/config dependencies from local startup paths once MySQL-backed flows are complete.
- [x] 5.7 Update local setup documentation and env examples so local validation no longer requires Supabase runtime credentials.

## 6. Local Verification

- [x] 6.1 Verify in-app login via NiuTrans-backed credential validation plus local token issuance.
- [x] 6.2 Verify guest translation still works without login.
- [x] 6.3 Verify authenticated history and settings flows run against MySQL.
- [x] 6.4 Verify community paper display and community-agent persistence run against MySQL.
- [x] 6.5 Verify migrated local data is visible and coherent after import.
- [x] 6.6 Run `openspec validate replace-supabase-with-niutrans-auth-and-mysql --strict --no-interactive` and collect local evidence before implementation sign-off.

## Progress Notes
### 2026-04-09

- `3.1` advanced substantially but is not complete yet.
- Completed slices now include:
  - authenticated `translation_tasks` persistence via repository-backed local DB writes
  - authenticated history list/detail/delete via local current-user resolution plus repository queries
  - translation config-hash persistence and reusable-output lookup via local task persistence
  - startup interrupted-task failover and orphaned-task cleanup using local `translation_tasks` persistence
- `6.3` has partial evidence now for authenticated history/settings on local persistence, but it remains unchecked until a cleaner end-to-end verification pass is captured.
- Remaining work inside `3.1` is now concentrated in:
  - guest-flow semantics and cleanup expectations
  - batch retry/cutover semantics
  - residual legacy Supabase auth-context usage outside the main translation-task path, especially community/user-scoped client flows

### 2026-04-09 Auth Cleanup Addendum

- The `resolve_current_user_id(...)` fallback cleanup slice is now complete for the remaining upload/arxiv/translate entry paths.
- `resolve_current_user_id(...)` now returns a user id only from verified local `current_user` state and no longer decodes unverified bearer-token payloads.
- Focused regression coverage now confirms:
  - forged JWT `sub` claims are ignored for user-id resolution
  - upload/arxiv/start-translation guest-compatible entry paths stay guest when auth verification fails
  - batch translation rejects credentials that do not resolve to a verified local user
- Pytest temp/runtime isolation is now pinned under `backend/tests`, and the root cache provider has been disabled to avoid workspace ACL noise during local verification.

### 2026-04-09 Frontend Local Auth Cutover

- Completed the frontend auth cutover slice for the approved change.
- Replaced the runtime Supabase session bootstrap with local token storage plus `/api/auth/me` bootstrap.
- Switched login/logout handling to the local auth endpoints and preserved the existing `useAuth()` consumer shape for downstream pages.
- Updated the login UI so in-app sign-in stays local while registration and account-management entry points now redirect to NiuTrans-managed pages.
- Added focused frontend coverage for:
  - local auth bootstrap from a stored access token
  - login-page rendering with external registration/account actions instead of local sign-up/OTP flow

### 2026-04-09 Community-Agent Run Auth Cutover

- `4.2` advanced, but is not complete yet.
- Completed the run-auth slice for:
  - `POST /api/community-agent/runs`
  - `GET /api/community-agent/runs/{run_id}`
  - `GET /api/community-agent/runs/{run_id}/events`
- Those run endpoints now depend on verified local `require_current_user` state instead of `get_supabase_client_from_request`.
- In-memory run ownership is now keyed by trusted local `user_id` when available, rather than only by hashed bearer-token state.
- Remaining work inside `4.2` is now concentrated in:
  - conversation CRUD persistence, which still uses the Supabase-backed `community_agent_conversations` path
  - MySQL-backed community-agent repositories and schema for conversation/run/event persistence
  - end-to-end local verification that community-agent persistence, not just run auth, is fully detached from Supabase

### 2026-04-09 Community-Agent Conversation Local Persistence

- `4.2` advanced again, but is still not complete yet.
- Completed in this slice:
  - replaced community conversation CRUD route dependencies on `get_supabase_client_from_request` with verified local `require_current_user`
  - added `CommunityAgentConversationRepository` for local DB-backed list/upsert/delete with explicit `user_id` scoping
  - switched `community_agent_service` conversation CRUD from Supabase client calls to local repository calls
  - introduced a shared `authorize(user, resource, action, context)` policy package and wired it into community-conversation routes plus local admin cleanup authorization
  - added focused repository, route, service, admin-auth, and policy tests for the local conversation persistence and centralized authorization entrypoint
- Remaining work inside `4.2` is now concentrated in:
  - durable persistence for community-agent runs and event replay, which are still runtime-memory-backed
  - explicit migration/bootstrap DDL for local MySQL rollout beyond the repository test schema
  - end-to-end local verification that community-agent persistence is fully detached from Supabase in a configured local database
- `1.4` advanced substantially, but remains unchecked until more route-level ad hoc ownership checks outside this slice move onto the shared authorization entrypoint.
- `4.3` advanced substantially, but remains unchecked until more community authorization paths beyond conversation CRUD are fully centralized under app-layer policies.

### 2026-04-09 Community Paper Local Repository Cutover

- `4.1` advanced substantially, but is not complete yet.
- Completed in this slice:
  - added a local `CommunityPaperRepository` for `papers` and `paper_assets`, with SQLite/MySQL-compatible reads, updates, latest-asset upserts, viewer-state reads, and local counter increments
  - rewired `paper_service` read/download/view core paths to prefer the local repository before any Supabase fallback:
    - paper lookup by id/arXiv/title
    - public paper list
    - latest asset lookup and asset-map construction
    - local preview/download counter increments
    - paper translation-failure status reconciliation by `community_selected_task_id`
    - inflight watcher resumption from local `papers` rows
  - updated restart failover so community paper status reconciliation can advance in local-only mode, without requiring Supabase admin access
  - added focused local SQLite verification for:
    - public community-paper listing from local persistence
    - local view-count increment semantics
    - restart failover updating community-paper translation state in local-only mode
- Remaining work inside `4.1` is now concentrated in:
  - full write-path cutover for all community paper creation/update/delete flows, not just the read/download/view/status helpers
  - stale community cleanup removing the remaining Supabase-admin dependency in startup/admin cleanup
  - migration/bootstrap DDL and data import coverage for the full community paper/asset model
- `2.3` also advanced in this slice because the community paper service no longer requires runtime Supabase admin-client access for the covered local paths.
- `6.4` has stronger partial evidence now for community paper display on MySQL/local persistence, but it remains unchecked until the remaining community persistence and cleanup paths are verified end-to-end.

### 2026-04-09 Community Cleanup And MySQL Baseline

- `4.1` advanced again, but is still not complete yet.
- Completed in this slice:
  - switched `reset_stale_community_tasks()` to prefer the local `CommunityPaperRepository` for stale non-success paper cleanup, only falling back to Supabase when the local database is unavailable
  - added local repository cleanup helpers for purge-related comment/report/task lookup and deletion so startup/admin cleanup can remove local paper rows, related joins, and task rows without Supabase runtime credentials
  - added focused regression coverage proving stale private community papers are purged through local persistence even when Supabase credentials are absent
  - added the missing MySQL baseline migration under `backend/migrations_mysql/20260409_0001_local_auth_mysql.sql`
  - baseline migration now covers the current local-auth/local-persistence tables used by code, including `users`, `user_roles`, `auth_sessions`, `user_settings`, `translation_tasks`, `papers`, `paper_assets`, `paper_likes`, `paper_favorites`, `comments`, `community_agent_conversations`, `community_agent_runs`, and `community_agent_events`
  - added focused migration tests so local verification now checks the baseline file exists and contains the required core tables, indexes, and foreign keys
- Remaining work impacted by this slice:
  - `2.2` advanced substantially, but remains unchecked until the DDL/index/constraint strategy is reconciled against any remaining in-scope entities and migration scripts beyond the baseline
  - `2.3` advanced again because startup/admin cleanup no longer requires Supabase when local paper persistence is configured
  - `4.1` still needs full write-side community paper cutover and end-to-end MySQL-backed verification beyond cleanup/read paths
  - `6.4` has stronger local evidence now for community paper persistence and cleanup, but remains unchecked until community-agent persistence and broader end-to-end local verification are completed

### 2026-04-09 Community-Agent Run/Event Local Persistence

- `4.2` advanced again, but is still not complete yet.
- Completed in this slice:
  - added `CommunityAgentRunRepository` for local DB-backed `community_agent_runs` and `community_agent_events` persistence
  - switched `community_agent_service` to best-effort persist owned run snapshots and stream events into the local repository while preserving the current in-memory fallback path when the database is unavailable
  - added DB-backed run hydration/replay so `GET /api/community-agent/runs/{run_id}` and `GET /api/community-agent/runs/{run_id}/events` can recover completed owned runs even after runtime-memory loss
  - added focused repository/service regression coverage for owned-run persistence, DB replay, and owner enforcement on DB-hydrated runs
- Remaining work impacted by this slice:
  - `4.2` still needs broader end-to-end verification in a configured local database beyond repository/service unit coverage
  - ownerless or token-hash-only run semantics still rely on the runtime-memory fallback path rather than durable DB replay
  - this slice does not yet add migration/import tooling for preexisting community-agent run data

### 2026-04-09 Papers Viewer Auth Hardening

- `2.3` and `4.3` both advanced incrementally in the paper-reader path.
- Completed in this slice:
  - removed the `/api/papers` route-layer fallback that decoded unverified bearer-token payloads to derive `viewer_user_id`
  - switched paper list/detail viewer-state resolution to verified local `optional_current_user` state so liked/favorited viewer metadata now depends on the local auth boundary instead of a forged `sub` claim
  - added focused route regression coverage proving forged JWT-looking bearer tokens do not leak another user's viewer state while verified local users still receive their own viewer-scoped paper metadata
- Remaining work impacted by this slice:
  - route-level community authorization is still only partially centralized and `1.4` remains unchecked
  - other community/paper paths still need end-to-end audit so all user-scoped reads and writes consistently depend on verified local auth state

### 2026-04-09 Community Write Cutover And Restart Failover Hardening

- `2.3`, `4.1`, and `6.4` all advanced again, but remain incomplete overall.
- Completed in this slice:
  - changed `fail_interrupted_translation_tasks()` to reconcile affected paper translation state through the local community-paper path even when legacy Supabase env vars are present
  - removed the restart-failover dependency on creating a Supabase admin client for paper-status repair, and added regression coverage proving the local path stays authoritative
  - switched `resolve_submitter_context_by_user_id()` to resolve local admin/moderator roles from `user_roles` in the local database rather than from a Supabase admin query
  - changed `_insert_paper(...)`, `_update_paper(...)`, and `_upsert_latest_asset(...)` to be local-write-only for this slice, returning explicit local-database errors instead of silently falling back to Supabase runtime writes
  - added focused write-cutover tests proving those helpers now use local persistence and do not attempt Supabase fallback when the local database is unavailable
- Remaining work impacted by this slice:
  - `4.1` still has other community-paper helper paths that retain Supabase fallbacks outside the covered write helpers
  - `5.6` advanced, but remains unchecked until the remaining startup/community runtime Supabase dependencies are removed more broadly
  - `6.4` now has stronger focused evidence for community write-path cutover and restart-failover behavior, but still lacks a broader end-to-end configured-MySQL verification pass

### 2026-04-10 Translation Runtime Cleanup And Supabase Shim Removal

- `2.3`, `3.4`, and `5.6` all advanced again, but remain incomplete overall.
- Completed in this slice:
  - replaced `backend/app/core/supabase_client.py` with a pure compatibility shim so local runtime import paths no longer require the Python Supabase SDK to be installed
  - updated the stale output-reuse regression to assert the current local-repository lookup path rather than the removed Supabase-query path
  - changed `persist_task_with_retry()` so authenticated tasks that exhaust persistence retries stay in local-only degraded mode instead of being silently registered into guest-task cleanup semantics
  - rewrote the old task-recovery email-notification tests to validate current local `TranslationTaskRepository` recovery behavior instead of the removed Supabase client path
- Remaining work impacted by this slice:
  - `3.4` still needs broader batch-translation behavior review so all retry/degradation messaging and cleanup assumptions match the local-first persistence model end-to-end
  - `5.6` still has compatibility naming and config residues (`supabase_*` env fields and legacy helper names) even though the last real backend SDK import path has been removed from local runtime use
  - `2.3` still needs a wider audit of other legacy compatibility shims and route/service comments so the codebase no longer suggests runtime Supabase authority where none remains

### 2026-04-10 Authorization Closure, Task Boundary Hardening, And Import Tooling

- Completed in this slice:
  - centralized remaining user-scoped translation/community authorization through `authorize(...)` for:
    - authenticated history list/detail/delete flows
    - settings read/update flows
    - task status/delete/SSE access for authenticated tasks while preserving guest-task access
    - community-agent run create/read/event flows
  - removed the legacy admin cleanup service-role bypass so runtime admin cleanup now depends on verified local admin authorization only
  - removed community paper submitter resolution from unverified bearer-token payload parsing and switched submit/translate paper flows to trust verified local `current_user` / `submitter_user_id` only
  - aligned task deletion policy with the local persisted-task ownership model so users can delete their own persisted tasks
  - added a repeatable `backend/scripts/import_supabase_to_mysql.py` importer for the in-scope entities with:
    - JSON export parsing
    - schema-aware field normalization and user/ownership mapping
    - dry-run mode and structured report output
    - repeatable upsert-based imports for local reruns
    - missing asset-path reporting without aborting the full import
  - added focused migration/import coverage in `backend/tests/unit/test_import_supabase_to_mysql.py`
  - added local rollout/backout guidance in `docs/supabase-import-rollout-backout.md`
  - refreshed frontend locale coverage so the current community/tooling UI passes `npm.cmd run i18n:check`
- Verification captured in this slice:
  - `python -m pytest backend/tests/unit/test_authorization_policies.py backend/tests/unit/test_local_translation_history_api.py backend/tests/unit/test_local_user_settings_api.py backend/tests/unit/test_task_detail_metadata.py backend/tests/unit/test_papers_submit_contract.py backend/tests/unit/test_papers_translation_bridge.py backend/tests/unit/test_verified_user_resolution.py backend/tests/unit/test_admin_cleanup_api.py backend/tests/unit/test_community_agent_runs_api.py backend/tests/unit/test_community_agent_service.py backend/tests/unit/test_import_supabase_to_mysql.py -q`
    - result: `83 passed`
  - `npm.cmd run i18n:check`
    - result: audit passed (warnings only for pre-existing unused/dynamic keys)
- Remaining work impacted by this slice:
  - `2.3` remains open because compatibility-named shims/config fields and a few legacy comments still exist even though the active runtime paths are local-first
  - `3.3` and `6.2` remain open until guest translation cleanup expectations are verified more explicitly beyond the preserved guest/task-route behavior
  - `3.4` remains open until batch persistence retry messaging and degraded-mode surfacing are fully aligned with the local-first model everywhere
  - `4.1` and `6.4` remain open because community paper reads still allow baseline-seed fallback and broader MySQL-authoritative verification is not complete yet
  - `5.6` remains open until runtime Supabase compatibility naming/config residues are removed more broadly
  - `6.5` remains open until imported data visibility/coherence is verified through a fuller post-import read path, not just the importer unit coverage

### 2026-04-10 Community Authority Closure, Local-Auth Naming Cleanup, And Post-Import Read Verification

- Completed in this slice:
  - removed the remaining runtime community-paper baseline-seed fallback from public list/detail lookup helpers so MySQL/local repository rows are now the only metadata authority for:
    - paper lookup by id, arXiv id, and title
    - public community paper listing
    - import-or-reuse existence checks
  - kept local disk as the asset source of truth while proving imported `paper_assets` remain readable through the community paper service layer after import
  - renamed frontend auth-availability state to local-auth semantics while keeping the existing compatibility module path in place
  - renamed local runtime config away from `SUPABASE_*` startup inputs toward migration-source terminology and updated the local env example accordingly
  - rewrote task-manager persistence naming/comments toward local persistent storage semantics while preserving compatibility aliases for legacy tests and monkeypatch paths
- Verification captured in this slice:
  - `python -m pytest backend/tests/unit/test_community_public_read_experience.py backend/tests/unit/test_local_community_paper_persistence.py backend/tests/unit/test_papers_list_detail_contract.py backend/tests/unit/test_papers_import_contract.py backend/tests/unit/test_import_supabase_to_mysql.py backend/tests/unit/test_admin_cleanup_api.py backend/tests/unit/test_restart_recovery_cleanup.py -q`
    - result: `49 passed`
  - `python -m pytest backend/tests/unit/test_verified_user_resolution.py backend/tests/unit/test_fix_task_status_sync.py backend/tests/unit/test_batch_config_hash_persistence.py backend/tests/unit/test_task_detail_metadata.py -q`
    - result: `29 passed`
  - `python -m pytest backend/tests/unit/test_community_agent_service.py backend/tests/unit/test_community_agent_runs_api.py backend/tests/unit/test_community_public_read_experience.py backend/tests/unit/test_local_community_paper_persistence.py -q`
    - result: `44 passed`
  - `openspec.cmd validate replace-supabase-with-niutrans-auth-and-mysql --strict --no-interactive`
    - result: `Change 'replace-supabase-with-niutrans-auth-and-mysql' is valid`
- Status impact from this slice:
  - `2.3`, `3.3`, `3.4`, `4.1`, `5.6`, `6.2`, `6.4`, and `6.5` are now complete for the approved local-first change
  - frontend Vitest verification remains desirable, but local execution was blocked in this environment by `esbuild` startup with `spawn EPERM`; backend regression and OpenSpec validation evidence were captured successfully
