## Context
The current community-paper experience already exposes feed cards, a paper-detail header favorite placeholder, viewer-state fields, and persisted aggregate columns such as `like_count`, `favorite_count`, and `view_count`. However, the implemented behavior is still below the requested product contract:

- favorites are modeled as a single flat relation rather than folder-based organization
- likes are not available as a user-facing persistent toggle
- view counting increments directly without per-day principal de-duplication
- homepage sort values still use legacy `hot` / `translated` semantics

This change is limited to community papers. Public browsing and reading remain available to guests, while favorites and likes become authenticated-only interaction surfaces.

## Goals / Non-Goals
- Goals:
  - Persist community-paper favorites, likes, and views in backend/database state
  - Support favorite folders with explicit management rules and multi-folder paper assignment
  - Keep engagement counts stable across refresh, re-login, and cross-viewer reads
  - Replace outdated feed sorting with `latest`, `views`, and `likes`
  - Reuse existing feed/detail UI structure where practical
- Non-Goals:
  - Adding comment or report functionality in this rollout
  - Requiring login merely to browse the community homepage or read paper detail
  - Building a generalized cross-product interaction-event platform
  - Delivering risk- or anti-fraud-grade anonymous identity enforcement

## Decisions

### Decision: Use normalized relationship tables for engagement persistence
Favorites, folder membership, likes, and de-duplicated views will be represented as explicit relational records rather than JSON blobs on the user profile or a generalized event bus.

Why:
- the product requires unique folder names per user, many-to-many paper-folder assignment, and deterministic removal behavior
- feed sorting depends on stable aggregate counts
- current backend already follows repository/service patterns around `papers`, `paper_assets`, and viewer-state lookups

Alternatives considered:
- Store folder state in a user-scoped JSON blob: rejected because rename/delete/diff/pagination and consistency become awkward
- Build a generic interaction event platform: rejected because it adds architecture cost beyond the requested scope

### Decision: Define favorite state as "paper belongs to at least one folder for the current user"
The UI will highlight the favorite button whenever the current user has at least one folder relation for the paper. The shared picker will open for both the favorited and unfavorited states.

Why:
- matches the confirmed product behavior
- avoids a misleading mismatch between per-folder storage and a single-button mental model

Consequence:
- removing one folder relation does not clear the active favorite state if other folder relations still exist
- clearing all selected folders and submitting returns the paper to the unfavorited state

### Decision: Persist inline-created folders immediately, but defer paper assignment until explicit confirm
When a user creates a folder from the favorite picker, the folder row is created immediately, auto-selected in the picker, and visually highlighted. The paper-folder relation is not committed until the user presses the explicit confirm action.

Why:
- matches the requested "new folder succeeds, auto-selects, but does not auto-complete favorite" behavior
- keeps folder creation semantics deterministic and avoids temporary client-only folders

Trade-off:
- a user may end up with an empty folder if they create it and then close the picker without confirming paper assignment

### Decision: Keep fast aggregate counters on `papers`
The source of truth for membership stays in relationship tables, while `papers.like_count`, `papers.favorite_count`, and `papers.view_count` remain derived counters used for feed display and sorting.

Definitions:
- `like_count`: number of like relations for the paper
- `favorite_count`: number of distinct users who currently favorite the paper through at least one folder
- `view_count`: number of accepted detail-entry views after per-day de-duplication

Why:
- feed ordering needs fast, stable sort columns
- existing schema and payloads already expose these counts

### Decision: Count views only from detail-entry events with application-layer daily de-duplication
Homepage exposure does not count as a view. The frontend records a view only when entering paper detail. The backend accepts the event idempotently for a given `(paper_id, business_date, principal_type, principal_key)`.

Principal resolution:
- authenticated user: `principal_type=user`, `principal_key=user_id`
- guest: `principal_type=anon`, `principal_key=sha256(local_anon_id)`

Business date:
- use the project’s UTC+8 business day convention for daily de-duplication

Why:
- aligns with the requested counting rule
- avoids over-counting from card rendering
- gives a practical, maintainable anonymous strategy without strong-device fingerprinting

### Decision: Replace feed sort values with `latest`, `views`, and `likes`
The feed contract will remove `hot` and `translated` from this surface.

Sort rules:
- `latest`: original arXiv publication time descending, then creation time descending
- `views`: `view_count` descending, then the `latest` rule
- `likes`: `like_count` descending, then the `latest` rule

Why:
- matches requested product semantics
- uses deterministic tie-breaking shared across sort modes

### Decision: Gate interaction surfaces, not public reading
Guests can still browse the homepage and open paper detail. Favorites and likes require login. The favorites sidebar entry is shown only to authenticated users, and direct guest access to favorites routes should enter the login flow.

Why:
- preserves current public-read positioning while enforcing the new authenticated interaction rules

## API / Data Shape

### Proposed backend surfaces
- `GET /api/papers/favorite-folders`
- `POST /api/papers/favorite-folders`
- `PATCH /api/papers/favorite-folders/{folder_id}`
- `DELETE /api/papers/favorite-folders/{folder_id}`
- `GET /api/papers/favorite-folders/{folder_id}/papers`
- `GET /api/papers/{paper_id}/favorite-folders`
- `PUT /api/papers/{paper_id}/favorite-folders`
- `POST /api/papers/{paper_id}/like`
- `DELETE /api/papers/{paper_id}/like`
- `POST /api/papers/{paper_id}/view`

### Proposed viewer-state additions
- `liked: boolean`
- `favorited: boolean`
- optional `favorite_folder_count: number`

The favorite-assignment write should accept the full selected folder set for the paper, allowing the backend to compute additions/removals in one deterministic transaction.

## Risks / Trade-offs
- Empty-folder accumulation is possible because inline-created folders persist before paper assignment confirmation.
  - Mitigation: keep folder delete available and avoid hidden implicit cleanup.
- Derived counters can drift if updates are not transactionally coordinated with relationship writes.
  - Mitigation: update relationship rows and counter adjustments together inside backend service/repository transactions.
- Anonymous view counting is only reasonably stable, not absolute.
  - Mitigation: document that clearing the local anonymous id may allow recounting, which is acceptable for this feature level.
- Feed cache layers can temporarily serve stale counts after interaction writes.
  - Mitigation: invalidate or bypass affected cache entries after like/favorite/view writes touching paper aggregates.

## Migration Plan
1. Add schema changes for favorite folders, folder-paper relations, and daily paper views plus supporting indexes/constraints.
2. Extend repository/service logic to update relationship rows and aggregate counters consistently.
3. Extend paper list/detail and interaction endpoints with authenticated viewer-state semantics.
4. Add favorites routes/pages and shared favorite picker UI.
5. Replace feed sort controls and wire likes/views/favorites to persisted backend data.
6. Update tests, i18n copy, and backend file index entries.

## Open Questions
- None at proposal time; the confirmed product semantics are sufficient for implementation planning.
