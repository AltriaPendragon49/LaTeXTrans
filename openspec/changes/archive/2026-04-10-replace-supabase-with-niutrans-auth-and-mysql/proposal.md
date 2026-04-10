# Change: Replace Supabase with NiuTrans-backed local auth and MySQL persistence

## Why

The project currently depends on Supabase for login state, JWT handling, user-scoped authorization, task/history persistence, settings, community paper data, and community-agent conversation storage. That coupling blocks the team's goal of owning auth, authorization, and persistence behavior directly inside the application.

The first priority is a local-first migration that fully removes runtime Supabase dependency while keeping current product behavior intact: guest translation stays available, authenticated features keep working, and existing local file assets remain usable.

## What Changes

- Replace Supabase-backed frontend auth/session behavior with an in-app login form that authenticates through the local backend.
- Delegate credential verification to the NiuTrans login API, then issue local project JWT/session tokens after successful upstream login.
- Replace Supabase RLS-dependent authorization with app-layer ownership and role checks.
- Replace Supabase persistent storage with MySQL for users, sessions, translation tasks, user settings, community papers, paper assets, and community-agent persistence.
- Keep file/object storage on local disk for this change; do not integrate COS yet.
- Add repeatable local migration scripts to copy current Supabase data into MySQL and validate local file-path references.
- Update login/register UI so registration and account-management entry points redirect to NiuTrans-managed pages instead of using local Supabase sign-up or OTP flows.
- Remove runtime Supabase configuration and SDK requirements from local startup after migration is complete.

## Impact

- Affected specs: `user-auth`, `user-settings`, `translation-history`, `TaskRuntimeState`, `community-schema-foundation`, `batch-translation`, `web-api`, `web-ui`
- Affected backend areas: auth dependencies, settings/history routes, translation persistence, paper/community services, community-agent persistence, startup/admin cleanup
- Affected frontend areas: auth context, login/register UI, gated feature entry points, token bootstrap, settings/history/community-agent fetch flows
- Affected local infrastructure: database configuration, migration scripts, local validation workflow
- Deferred intentionally: Ubuntu rollout, COS rollout, expanded account-management features beyond current scope
