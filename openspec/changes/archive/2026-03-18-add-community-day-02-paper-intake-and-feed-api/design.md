# Day 2 Community Paper Intake/API Technical Design

## Summary
Day 2 turns the Day 1 paper-first schema into a working API contract, but under a stricter product model: the community is an official-first publishing surface, and user translations only fill uncovered gaps. The key technical consequence is that `papers` must explicitly model community admission and community-default selection.

This change therefore has two parts:
- an additive `papers` refinement migration
- a new `papers` API layer for submit, list, detail, and view

## Product Model
### Community content
- Official community content is the default feed backbone.
- User community content is fallback-only.
- User translation history is not the same thing as community publication.

### Official override
- For matching `arxiv_id`, an official submission supersedes fallback visibility.
- Day 2 does not create two competing community paper rows for the same `arxiv_id`.
- Upload-only papers are not automatically deduplicated or overridden by content similarity.

## Schema Refinement
This change adds only additive columns and indexes on `public.papers`:
- `community_status text not null default 'user_fallback' check (community_status in ('official', 'user_fallback'))`
- `community_selected_task_id text null`
- `community_selected_asset_id uuid null`
- `official_published_at timestamptz null`

Indexes:
- `papers_community_status_created_at_idx`
- `papers_official_published_at_idx` with `where official_published_at is not null`

No existing columns are removed or repurposed. `translation_tasks` and `user_settings` remain untouched.

## Admission Rules
### Upload submit
- Always creates a new paper row.
- Admin/moderator submitters create `official` papers.
- Normal users create `user_fallback` papers.
- Upload submissions do not auto-match an existing paper, even if upload metadata hints at an arXiv identifier.

### arXiv submit
- If no paper exists for `arxiv_id`:
  - admin/moderator → create `official`
  - normal user → create `user_fallback`
- If a paper exists and submitter is normal user:
  - existing `official` → reuse existing official paper
  - existing `user_fallback` → reuse existing fallback paper
- If a paper exists and submitter is admin/moderator:
  - update the existing row to `official`
  - refresh community-selected task/asset pointers as the new official intake completes

## Old Route Reuse Strategy
### `/upload`
Day 2 reuses the existing upload route function to:
- persist the source files locally
- run LaTeX validation
- create the underlying intake task

The new `papers` service then:
- creates the community paper row
- creates the initial `paper_assets` record
- updates community-selected pointers

### `/arxiv`
Day 2 reuses the existing arXiv route function to:
- validate `arxiv_id`
- create the underlying task
- start the background download

The new `papers` service then:
- creates or reuses the paper row
- stores community admission fields
- schedules a follow-up background sync that records the downloaded source path into `paper_assets`

## Community-Selected Fields
`community_selected_task_id` and `community_selected_asset_id` represent the version the community detail page should prefer right now. In Day 2 they may still point at intake/source artifacts rather than translated output. Day 4 can tighten them toward translated assets without changing the field shape.

## API Contract
### `POST /api/papers/submit`
Accepted modes:
- `multipart/form-data` with `file`
- `application/json` with `arxiv_id`

Authentication:
- required

Response:
- `paper`
- `task`
- `admission_result`

### `GET /api/papers`
Returns:
- community-visible paper cards only
- official-first ordering
- latest asset summary

### `GET /api/papers/{paper_id}`
Returns:
- public paper detail
- community-selection metadata
- optional viewer-state enrichment

### `POST /api/papers/{paper_id}/view`
Behavior:
- checks public visibility
- increments `view_count`
- returns the updated count

## Sorting Rules
### `latest`
Order by:
1. official papers first
2. `official_published_at desc nulls last`
3. `created_at desc`

### `translated`
Order by:
1. official papers first
2. completed translations first
3. `official_published_at desc nulls last`
4. `created_at desc`

### `hot`
Order by:
1. official papers first
2. `view_count desc`
3. `like_count desc`
4. `created_at desc`

## Security Model
- Submit API requires a valid authenticated user.
- Admin/moderator status is read from `user_roles`.
- Writes to `papers` and `paper_assets` happen through the service-role client.
- Public list/detail/view only expose papers that remain visible under Day 1 public visibility rules.

## Testing Strategy
### Migration contract test
- Verify new `papers` columns exist in the Day 2 migration SQL.
- Verify indexes exist.
- Verify no `translation_tasks` or `user_settings` changes are declared.

### Submit tests
- upload creates fallback or official paper based on roles
- arXiv creates, reuses, or promotes as expected
- unauthenticated submit fails

### Read tests
- list orders official before fallback
- detail returns viewer-state and community-selected fields
- invisible papers return `404`

### View test
- visible paper increments `view_count`

## Supabase Application
Day 2 applies one additive migration to the main project via Supabase MCP and then verifies the resulting `papers` columns/indexes before backend runtime work is considered complete.
