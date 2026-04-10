# Local Supabase Replacement Design

Date: 2026-04-09
Topic: Replace Supabase with NiuTrans-backed auth and MySQL persistence for local-first validation

## Context

The current project still relies on Supabase for several core responsibilities:

- frontend auth state and access-token lifecycle
- backend user-scoped reads that depend on Supabase JWT + RLS
- admin bypass paths that depend on Supabase service-role behavior
- persistent storage for translation history, user settings, community papers, and community-agent conversations

The goal of this change is not to add a broader user system. It is to replace only the capabilities the current project already receives from Supabase, while keeping the product behavior stable enough to validate the migration locally first.

## Approved Scope

This design covers the first migration change only.

- Replace all runtime Supabase dependencies in the current project.
- Keep guest translation mode.
- Replace login/auth/session handling with a local auth chain backed by the NiuTrans login API.
- Replace persistent business data storage with MySQL.
- Keep file assets on local disk for this phase.
- Migrate existing Supabase data into local MySQL for local verification.
- Migrate the currently active community paper display flow and community-agent persistence.

This design does not include:

- Ubuntu server rollout
- COS object storage rollout
- new registration, password-reset, OTP, or multi-device session features
- expanding business scope beyond current Supabase-backed behaviors

## Auth Model

### Upstream identity source

NiuTrans remains the external identity provider for credential verification.

- Login API: `https://niutrans.com/niutrans-auth/auth/login`
- Registration page: `https://niutrans.com/login?active=3`
- Login page: `https://niutrans.com/login?active=0`

### Local session model

The application keeps its own in-app login form as the only formal sign-in path.

1. The frontend submits credentials to the local backend.
2. The backend calls the NiuTrans login API.
3. On success, the backend maps `userId` into a local `users` record.
4. The backend issues the project's own JWT/session token.
5. All later API requests use only the local token.

This avoids a half-decoupled state where Supabase is removed but the application still depends directly on external token semantics.

### Registration and recovery

Registration and account recovery stay outside local implementation scope.

- The UI keeps visible entry points.
- Those entry points redirect users to NiuTrans-managed pages.
- The local app does not implement registration or OTP verification during this change.

## Authorization Model

Supabase RLS is replaced by explicit app-layer authorization.

- `optional_current_user` supports guest-accessible routes.
- `require_current_user` protects authenticated routes.
- `require_admin_user` protects administrative routes.

Ownership is enforced in repositories and service queries, not in database-side RLS rules.

- private task/history/settings rows filter by local `user_id`
- public paper reads filter by `visibility` and `status`
- community-agent conversation history filters by local owner
- admin-only operations check local roles rather than service-role keys or upstream metadata

Guest behavior stays intact:

- guests can still create temporary translation tasks
- guest tasks remain non-persistent for user history semantics
- protected features such as history, settings, and persisted community-agent conversations still require sign-in

## Data Model Direction

MySQL becomes the only business database in this phase.

Primary entities in scope:

- `users`
- local auth session or token-version support tables
- `translation_tasks`
- `user_settings`
- `papers`
- `paper_assets`
- community-agent conversations, turns, runs, and events as needed by current behavior

Key mapping rule:

- local `users.id` is the canonical app user id
- `external_provider='niutrans'`
- `external_user_id=<niutrans userId>`

This preserves an external identity bridge without making the rest of the application depend on external token structure.

## Storage Model

This first change keeps asset storage on local disk.

- task files remain under existing local upload/output roots
- community paper library assets remain stored as relative local paths
- MySQL stores metadata and file-path references only

COS is explicitly deferred until after local migration is stable.

## Migration Strategy

The migration is treated as a repeatable local script workflow, not a one-off manual copy.

### Data migration targets

- user settings
- translation task rows
- community paper rows
- paper asset rows
- community-agent persisted conversation data

### Data migration rules

- migrate low-volume Supabase data into MySQL
- validate referenced local file paths during migration
- report missing files without aborting every other row
- create local users before dependent rows so ownership is stable

### Practical interpretation

The stored data is expected to be lightweight enough for local migration, but the platform replacement is still large enough to require staged implementation and verification.

## Frontend Changes

The frontend auth layer is refactored together with the backend.

- remove Supabase client/session usage from auth state management
- keep the in-app login form
- send login requests to the local backend
- store only the local app token/session
- keep register/recovery entry points as outbound links to NiuTrans pages
- update unauthenticated messaging across login-gated pages to refer to NiuTrans account sign-in where appropriate

Affected experience areas:

- login page
- settings gating
- history gating
- community-agent gating
- auth-derived session bootstrap and logout behavior

## Phased Implementation Order

1. Auth foundation
2. MySQL infrastructure and core repositories
3. Translation mainline persistence replacement
4. Community paper and community-agent persistence replacement
5. Local data migration scripts and cleanup of Supabase runtime dependencies
6. Local end-to-end validation

## Local Acceptance Criteria

The first migration change is considered successful only when all of the following are true locally:

- the frontend no longer depends on Supabase SDK/session handling for runtime auth
- the backend no longer requires Supabase URL, anon key, or service-role key for runtime startup
- in-app login succeeds through NiuTrans credential verification plus local session issuance
- guest translation still works
- authenticated history and settings work through MySQL
- community paper display and community-agent persistence work through MySQL
- migrated rows from Supabase are visible in the local MySQL-backed flows
- file references continue to resolve against local disk

## Risks And Trade-offs

- This is a broad replacement change, so implementation must be staged even though it lands under one OpenSpec change.
- The project currently has little existing MySQL infrastructure, so auth and persistence foundations must be added together.
- Admin semantics should not depend on inferred upstream metadata in this phase; local roles are simpler and safer.
- COS and Ubuntu deployment are deliberately excluded to keep the local-first migration verifiable.
