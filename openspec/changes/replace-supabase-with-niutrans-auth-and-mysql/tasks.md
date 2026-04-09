## 1. Auth Foundation

- [x] 1.1 Add backend auth endpoints for in-app login, logout, and current-user bootstrap using the NiuTrans login API as the upstream credential verifier.
- [x] 1.2 Define and implement the local JWT/session contract, including claims, TTL, no-refresh behavior, current-device logout, session invalidation, and multi-device policy.
- [x] 1.3 Add local JWT/session issuance and verification, plus `optional_current_user`, `require_current_user`, and `require_admin_user` dependencies.
- [ ] 1.4 Introduce a centralized authorization entrypoint such as `authorize(user, resource, action, context)` and remove route-level ad hoc ownership logic.
- [x] 1.5 Define local user mapping based on NiuTrans `userId` and seed an initial local admin strategy that does not depend on Supabase metadata or service-role behavior.
- [ ] 1.6 Replace frontend Supabase auth state management with local token/session handling and authenticated session bootstrap.
- [ ] 1.7 Update login/register/recovery UI so in-app login remains local, while registration and account-management entry points redirect to NiuTrans-managed pages.

## 2. MySQL Persistence Foundation

- [x] 2.1 Add MySQL connection, migration workflow, and repository/service helpers suitable for local development and later server rollout.
- [ ] 2.2 Finalize MySQL DDL, indexes, unique constraints, and foreign-key strategy for users, auth/session support, translation tasks, user settings, community papers, paper assets, and currently used community-agent persistence records.
- [ ] 2.3 Replace runtime Supabase admin-client and user-client access paths with MySQL-backed repositories and app-layer authorization filters.

## 3. Translation Mainline Migration

- [ ] 3.1 Move authenticated translation-task persistence, history retrieval, task deletion, and reconciliation flows from Supabase to MySQL.
- [x] 3.2 Move user-settings storage and retrieval from Supabase to MySQL while preserving current default-setting behavior.
- [ ] 3.3 Keep guest translation behavior intact, including non-persistent guest task semantics and existing cleanup expectations.
- [ ] 3.4 Replace batch-translation persistence retry behavior so it targets MySQL/local fallback semantics instead of Supabase-specific retry assumptions.

## 4. Community Migration

- [ ] 4.1 Move community paper metadata and paper-asset persistence from Supabase to MySQL while keeping local disk paths as the asset source of truth.
- [ ] 4.2 Move community-agent conversation/run persistence from Supabase-backed auth context to MySQL-backed local user context.
- [ ] 4.3 Replace community authorization assumptions that currently depend on RLS/service-role patterns with explicit app-layer ownership and admin checks.

## 5. Data Migration And Cleanup

- [ ] 5.1 Add repeatable local migration scripts that import current Supabase rows into MySQL for the in-scope entities.
- [ ] 5.2 Define explicit schema-mapping and field-conversion rules for each migrated entity, including user identity mapping and JSON field normalization.
- [ ] 5.3 Implement migration dry-run mode, validation reports, checksum or count verification, and a clear rollback procedure for local testing.
- [ ] 5.4 Write and maintain a rollout note covering migration window, data backup, and rollback triggers for the local-first cutover.
- [ ] 5.5 Validate migrated file-path references against the local disk layout and emit actionable reports for missing assets without aborting all imports.
- [ ] 5.6 Remove runtime Supabase SDK/config dependencies from local startup paths once MySQL-backed flows are complete.
- [ ] 5.7 Update local setup documentation and env examples so local validation no longer requires Supabase runtime credentials.

## 6. Local Verification

- [x] 6.1 Verify in-app login via NiuTrans-backed credential validation plus local token issuance.
- [ ] 6.2 Verify guest translation still works without login.
- [ ] 6.3 Verify authenticated history and settings flows run against MySQL.
- [ ] 6.4 Verify community paper display and community-agent persistence run against MySQL.
- [ ] 6.5 Verify migrated local data is visible and coherent after import.
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
