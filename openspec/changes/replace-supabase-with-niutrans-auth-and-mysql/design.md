## Context

The current project uses Supabase as both an auth dependency and a persistence backbone. Several backend routes assume that a frontend-provided Supabase token can be forwarded to a user-scoped client, and several services assume that admin behavior can rely on service-role access or Supabase-managed metadata. The frontend also depends directly on Supabase session lifecycle for bootstrap, login, registration, OTP verification, and logout.

The requested migration is broader than "swap one login API." It replaces the runtime ownership of:

- login state
- JWT/session semantics
- user/data authorization
- persisted task and community metadata

This change is intentionally local-first. Ubuntu deployment and COS migration come later.

## Goals

- Remove runtime Supabase dependency from local development and validation.
- Keep current product behavior as stable as possible, especially guest translation mode.
- Use NiuTrans only for credential verification, not as the application's runtime session authority.
- Centralize authorization in application code rather than database-specific RLS rules.
- Move in-scope persistent business data to MySQL.
- Provide repeatable local migration scripts for current Supabase data.

## Non-Goals

- Implement full SSO, OAuth callback, or browser redirect-based upstream login.
- Implement local registration, OTP verification, password recovery, refresh token rotation, or multi-device session management beyond current needs.
- Deploy the new stack to Ubuntu in this change.
- Integrate Tencent COS in this change.

## Decisions

### Decision: Keep the in-app login form as the formal login flow

The application keeps its own login page and posts credentials to the local backend. The backend then calls the NiuTrans login API and issues a local token after successful upstream verification.

Why:

- the app must create its own durable auth boundary
- simple browser redirection to a NiuTrans login page cannot produce a usable local session without a formal callback protocol
- local JWT/session control is needed to fully replace Supabase-backed auth behavior

### Decision: Registration and account recovery stay external

The frontend keeps visible entry points for registration and account maintenance, but those entries redirect users to NiuTrans-managed pages.

Why:

- those flows are outside the requested migration scope
- available documentation currently covers login but not a full local replacement contract for registration or recovery

### Decision: Replace RLS with explicit app-layer ownership checks

Authorization will be enforced by backend dependencies plus repository filters rather than database RLS.

Examples:

- history/settings query by local `user_id`
- admin cleanup checks local admin roles
- public paper APIs filter by `visibility` and `status`
- community-agent conversations scope to the local authenticated owner

Why:

- this matches the explicit goal of replacing Supabase RLS ownership
- it removes hidden behavior from database-specific auth helpers

### Decision: Use MySQL as the only business database in this phase

MySQL stores in-scope entities for auth mapping, settings, history, papers, assets, and community-agent persistence. Local disk remains the storage source for large paper/task assets.

Why:

- matches the requested target state
- keeps COS out of the first migration
- separates metadata persistence from file storage complexity

### Decision: Keep guest translation mode

Guest users can continue using the translation entry flow, but protected features remain login-gated and persistent user data continues to require authentication.

Why:

- preserves current user-facing behavior
- avoids turning the migration into a product-scope change

### Decision: No refresh token in the first local-first migration

The first migration change will issue only an access token plus server-side session record. There is no refresh-token flow in this phase.

Why:

- the user explicitly scoped this phase away from more complex session mechanics
- local validation needs a simpler auth system that is complete enough to be safe, not feature-complete across all future UX cases
- session invalidation can still be implemented through server-side session state and token version checks

### Decision: Treat data migration as a repeatable script workflow

Current Supabase data volume is expected to be manageable, but migration still needs repeatability and validation. The team should be able to rerun import scripts during local testing instead of relying on one-off manual movement.

Why:

- local verification will likely require multiple migration passes
- later Ubuntu rollout can reuse the same data-shaping logic

### Decision: Do not require dual-write or shadow rollout for the local-first change

This change targets a local validation milestone, not an in-production cutover. The required risk controls are rerunnable imports, backups, dry-run support, and explicit rollback points rather than production-grade dual-write complexity.

Why:

- dual-write increases implementation scope and failure modes
- the current priority is local correctness and complete Supabase detachment
- production rollout controls can be introduced in the later Ubuntu deployment change

## Auth Contract

### Local auth endpoints

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

Optional later extensions such as refresh or session listing are intentionally out of scope for this first change.

### Login request

```json
{
  "identifier": "user@example.com",
  "password": "secret"
}
```

The backend transforms this into the NiuTrans login payload:

- `identifier`
- `password`
- `loginMode=Password`

### Login success response

```json
{
  "access_token": "<local-jwt>",
  "token_type": "Bearer",
  "expires_in": 28800,
  "user": {
    "id": "usr_xxx",
    "external_provider": "niutrans",
    "external_user_id": "179017",
    "roles": ["user"],
    "display_name": null
  }
}
```

### Auth error contract

- `401 AUTH_INVALID_CREDENTIALS`: upstream credential verification failed
- `401 AUTH_SESSION_INVALID`: token expired, revoked, or session missing
- `403 AUTH_FORBIDDEN`: authenticated but not authorized
- `503 AUTH_UPSTREAM_UNAVAILABLE`: NiuTrans auth temporarily unavailable

The API response body should carry a stable machine-readable `code` plus a user-facing `message`.

### Session bootstrap

`GET /api/auth/me` is the single frontend bootstrap endpoint.

- if the local token is valid, it returns the local user payload
- if the token is invalid or missing, it returns `401 AUTH_SESSION_INVALID`
- the frontend must treat that response as the canonical logged-out signal

### JWT claims

The local access token should minimally include:

- `iss`: current application identifier
- `aud`: current application API audience
- `sub`: local user id
- `sid`: local session id
- `ver`: user token-version integer
- `provider`: `niutrans`
- `external_user_id`: mapped NiuTrans `userId`
- `roles`: local roles
- `iat`
- `exp`

### Auth security strategy

- JWT algorithm: `HS256`
- signing secret: env-based versioned keys such as `AUTH_JWT_KEYS=v3:current-secret,v2:old-secret`
- verification rule: sign with the newest active key, verify against all non-retired keys
- token transport: default `Authorization: Bearer <token>`
- optional web storage mode: `httpOnly` cookie may be introduced later, but is not required for this first local migration
- session binding: every token must carry `sid` and must match an active server-side session row
- revocation: logout revokes current `sid`; admin/global revocation bumps `users.token_version`
- expiry: fixed access-token TTL with no refresh token in this phase
- secret rotation trigger: deploy new env key version, keep previous key for verification during migration window, then retire it
- logging rule: never log raw upstream passwords, local JWTs, or full upstream tokens

### Token lifecycle

- access token only in this phase
- recommended TTL: 8 hours for local validation
- no refresh token in this phase
- frontend behavior on expiry: clear local auth state and require re-login

### Token invalidation

Invalidation is enforced server-side through session state plus token version checks.

- logout revokes only the current `sid`
- admin "kick user" or security reset increments `users.token_version`
- middleware rejects tokens whose `sid` is revoked or whose `ver` no longer matches the current user row

### Multi-device policy

The first migration phase allows multiple active sessions, but session management UI is out of scope.

- each login creates a new `sid`
- logout revokes only the current session
- admin/global revocation invalidates all sessions by token-version bump

This gives complete behavior without requiring a full multi-device management surface.

## Authorization Model

### Enforcement layers

1. Authentication middleware resolves `current_user`
2. Route dependency selects guest, authenticated, or admin requirement
3. Service-layer policy check evaluates resource access
4. Repository query scopes returned rows to the authorized set

### Unified authorization entrypoint

The backend should expose one policy API:

```python
authorize(user, resource, action, context=None) -> AuthorizationResult
```

Where:

- `resource` examples: `task`, `settings`, `paper`, `paper_asset`, `community_conversation`, `admin_cleanup`
- `action` examples: `read`, `create`, `update`, `delete`, `moderate`
- `context` includes ownership ids, visibility, status, and other resource attributes needed for a decision

### Policy package structure

The authorization rules should live in a dedicated package rather than inside routes:

```text
backend/app/policies/
  __init__.py
  base.py
  task_policy.py
  paper_policy.py
  settings_policy.py
  community_agent_policy.py
  admin_policy.py
```

Expected shape:

- each policy exposes `can_<action>(user, resource, context=None)`
- `authorize(...)` delegates to the appropriate policy module
- routes call the shared authorization entrypoint instead of embedding ownership checks inline

### Policy model

This phase uses a hybrid model:

- RBAC for broad authority such as `admin`
- ownership and visibility checks for resource-specific decisions

That is effectively "RBAC + resource attributes", but still centralized under one authorization entrypoint rather than scattered conditionals.

### Default policy matrix

- guest:
  - can `create` guest translation tasks
  - can `read` public papers
  - cannot access settings, history, or persisted community-agent conversations
- user:
  - can manage own settings and own persisted tasks
  - can create and manage own community-agent conversations
  - can read public papers and own interaction records
- admin:
  - can run cleanup flows
  - can manage protected community entities
  - can revoke user sessions

## Data Shape

### Users

- local primary key
- external provider marker (`niutrans`)
- external user id from NiuTrans login response
- role or role-link data for local admin checks

### Auth/session

- local JWT/session model
- optional session-tracking or token-version support for invalidation/logout semantics

### Translation tasks

- preserve current task metadata needed for history, status reconciliation, output reuse, and community paper linkage
- bind authenticated tasks to local `user_id`
- keep guest tasks outside persistent authenticated history behavior

### Community data

- preserve `papers` and `paper_assets`
- preserve active community-agent conversation/run persistence
- retain public-reader semantics independent of the persistence backend

## MySQL Schema Outline

The first execution-ready change needs an explicit schema baseline. The DDL below is intentionally skeletal but concrete enough to drive implementation and migration planning.

### `users`

```sql
create table users (
  id varchar(36) primary key,
  external_provider varchar(32) not null,
  external_user_id varchar(64) not null,
  email varchar(255) null,
  display_name varchar(255) null,
  token_version int not null default 1,
  status varchar(32) not null default 'active',
  created_at datetime not null,
  updated_at datetime not null,
  unique key uq_users_provider_external (external_provider, external_user_id)
);
```

### `user_roles`

```sql
create table user_roles (
  user_id varchar(36) not null,
  role varchar(64) not null,
  created_at datetime not null,
  primary key (user_id, role),
  constraint fk_user_roles_user foreign key (user_id) references users(id)
);
```

### `auth_sessions`

```sql
create table auth_sessions (
  id varchar(36) primary key,
  user_id varchar(36) not null,
  status varchar(32) not null default 'active',
  issued_at datetime not null,
  expires_at datetime not null,
  revoked_at datetime null,
  last_seen_at datetime null,
  client_ip varchar(64) null,
  user_agent varchar(512) null,
  key idx_auth_sessions_user_status (user_id, status),
  constraint fk_auth_sessions_user foreign key (user_id) references users(id)
);
```

### `user_settings`

```sql
create table user_settings (
  user_id varchar(36) primary key,
  default_source_language varchar(16) not null default 'en',
  default_target_language varchar(16) not null default 'zh',
  translation_mode varchar(32) not null default 'full',
  compile_strategy varchar(32) not null default 'auto',
  translation_model varchar(128) null,
  generate_glossary boolean not null default true,
  use_author_api boolean not null default true,
  custom_base_url text null,
  custom_api_key_encrypted text null,
  default_formatting json null,
  updated_at datetime not null,
  constraint fk_user_settings_user foreign key (user_id) references users(id)
);
```

### `translation_tasks`

```sql
create table translation_tasks (
  task_id varchar(64) primary key,
  user_id varchar(36) null,
  source_type varchar(32) not null,
  arxiv_id varchar(64) null,
  status varchar(32) not null,
  stage varchar(64) null,
  progress int not null default 0,
  source_language varchar(16) not null,
  target_language varchar(16) not null,
  translation_mode varchar(32) not null,
  compile_strategy varchar(32) not null,
  translation_model varchar(128) null,
  config_hash varchar(128) null,
  source_path text null,
  output_path text null,
  formatting json null,
  email_notification boolean not null default false,
  created_at datetime not null,
  completed_at datetime null,
  key idx_translation_tasks_user_created (user_id, created_at),
  key idx_translation_tasks_arxiv_hash (arxiv_id, config_hash),
  constraint fk_translation_tasks_user foreign key (user_id) references users(id)
);
```

### `papers` and `paper_assets`

```sql
create table papers (
  id varchar(36) primary key,
  created_by varchar(36) null,
  source varchar(32) not null,
  arxiv_id varchar(64) null,
  title text not null,
  visibility varchar(32) not null,
  status varchar(32) not null,
  community_status varchar(32) not null,
  trans_status varchar(32) not null,
  community_selected_task_id varchar(64) null,
  trans_latest_task_id varchar(64) null,
  view_count int not null default 0,
  download_count int not null default 0,
  created_at datetime not null,
  updated_at datetime not null,
  key idx_papers_visibility_status_created (visibility, status, created_at),
  unique key uq_papers_arxiv_id (arxiv_id)
);

create table paper_assets (
  id varchar(36) primary key,
  paper_id varchar(36) not null,
  task_id varchar(64) null,
  asset_type varchar(32) not null,
  storage_backend varchar(32) not null,
  file_path text not null,
  file_name varchar(255) not null,
  mime_type varchar(255) not null,
  created_at datetime not null,
  key idx_paper_assets_paper_type (paper_id, asset_type),
  constraint fk_paper_assets_paper foreign key (paper_id) references papers(id)
);
```

### Community-agent persistence

At minimum:

- `community_conversations`
- `community_conversation_turns`
- `community_agent_runs`
- `community_agent_events` if persisted event replay remains required

Core indexes should cover:

- owner + updated time
- run id lookup
- conversation id + sequence

## Migration Design

### Source-to-target mapping

- Supabase auth users or inferred user identity -> `users`
- `user_settings` -> `user_settings`
- `translation_tasks` -> `translation_tasks`
- `papers` -> `papers`
- `paper_assets` -> `paper_assets`
- community-agent conversation tables -> MySQL conversation/run tables

### Field conversion rules

- Supabase `auth.uid()` ownership becomes explicit local `user_id`
- NiuTrans external identity mapping is keyed by `external_provider + external_user_id`
- JSONB fields become MySQL `json`
- timestamps normalize to UTC `datetime`
- relative asset paths remain relative when possible; absolute local paths are normalized during import

### Validation strategy

- dry-run mode: compute mappings and produce reports without writing
- import mode: write inside bounded batches
- post-import verification:
  - row counts by entity
  - per-table sample verification
  - path existence checks for file-backed rows
  - task ownership spot checks

### Rollback strategy

For local-first validation, rollback is file and database based:

1. snapshot or dump the local MySQL database before import
2. write imports with idempotent upsert rules where safe
3. if import validation fails, drop or restore the local MySQL schema from backup
4. rerun after fixing mapping rules

This is the required rollback strategy for this phase; production cutover rollback will be handled in the later server deployment change.

## Local Rollout Controls

The first change should still define minimal engineering controls:

- `AUTH_PROVIDER_MODE=niutrans_local`
- `ENABLE_SUPABASE_IMPORT_READONLY=true` for migration scripts only
- `MIGRATION_DRY_RUN=true` for validation runs

Runtime business flows should not depend on Supabase once the migration is complete, but migration tooling may still read from Supabase in a controlled read-only mode.

## Migration Plan

1. Build auth and MySQL foundations.
2. Move translation history/settings/task persistence.
3. Move community paper and community-agent persistence.
4. Import existing Supabase data into MySQL.
5. Validate local disk asset references.
6. Remove runtime Supabase dependency from local startup and local feature paths.

## Risks / Trade-offs

- The code migration is materially larger than the data migration.
- Current specs and code mention Supabase in many places, so this change needs wide but disciplined spec deltas.
- Admin role semantics should stay local-first in this phase to avoid dependence on undocumented upstream metadata rules.
- Keeping this change local-first avoids deployment noise but means deployment specs can be updated later when Ubuntu rollout is planned.
